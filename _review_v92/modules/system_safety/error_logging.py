"""v92 safe error diagnostics and logging utilities.

This module is based on the user-provided error/logging draft, but is adapted
for this project with safer defaults:
- logs are stored in the user's app-data folder, not inside the code folder;
- API keys and sensitive-looking values are masked before any file write;
- log files rotate to avoid unlimited growth;
- user-facing Streamlit errors show an error ID first and hide traceback in an expander;
- action logs keep button/workflow names and sanitized metadata only.
"""

from __future__ import annotations

import json
import logging
import os
import re
import shutil
import time
import traceback
import zipfile
from datetime import datetime
from functools import wraps
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Callable, Optional

try:  # Streamlit is optional for test scripts and module imports.
    import streamlit as st  # type: ignore
except Exception:  # pragma: no cover
    st = None  # type: ignore

APP_DATA_ENV = "KAKAO_EMOTICON_USER_DATA_DIR"
APP_DATA_DIRNAME = "KakaoEmoticonProfitSystemV92"
MAX_LOG_BYTES = 512 * 1024
BACKUP_COUNT = 4


class AppError(Exception):
    """Base application error."""


class ConfigError(AppError):
    """Configuration error."""


class DataError(AppError):
    """Data processing error."""


class ProcessingError(AppError):
    """Rendering, packaging, or workflow processing error."""


def get_app_data_dir() -> Path:
    """Return the persistent user-data folder for this app.

    Windows uses %LOCALAPPDATA% when available. Linux/macOS test environments use
    ~/.local/share. The location can be overridden in tests with
    KAKAO_EMOTICON_USER_DATA_DIR.
    """
    override = os.environ.get(APP_DATA_ENV)
    if override:
        base = Path(override).expanduser()
    elif os.name == "nt":
        local = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
        base = Path(local) if local else Path.home() / "AppData" / "Local"
        base = base / APP_DATA_DIRNAME
    else:
        base = Path.home() / ".local" / "share" / APP_DATA_DIRNAME
    base.mkdir(parents=True, exist_ok=True)
    return base


def get_log_dir() -> Path:
    log_dir = get_app_data_dir() / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


SENSITIVE_PATTERNS = [
    re.compile(r"sk-proj-[A-Za-z0-9_\-]{12,}"),
    re.compile(r"sk-[A-Za-z0-9_\-]{12,}"),
    re.compile(r"AIza[0-9A-Za-z_\-]{16,}"),
    re.compile(r"(?i)(api[_-]?key|secret|token|password|passwd|pwd)\s*[:=]\s*['\"]?([^'\"\s,;]+)"),
]


def mask_sensitive_text(value: Any) -> str:
    """Mask API keys, password-like values, and overly precise home paths."""
    text = str(value)
    for pattern in SENSITIVE_PATTERNS:
        if pattern.groups >= 2:
            text = pattern.sub(lambda m: f"{m.group(1)}=***MASKED***", text)
        else:
            text = pattern.sub("***MASKED_KEY***", text)
    # Hide exact Windows user profile segment while preserving enough path context.
    text = re.sub(r"C:\\\\Users\\\\[^\\\\\s]+", r"C:\\Users\\***", text)
    text = re.sub(r"/home/[^/\s]+", "/home/***", text)
    return text


def _sanitize_obj(value: Any, max_text_len: int = 1200) -> Any:
    if isinstance(value, dict):
        safe: dict[str, Any] = {}
        for k, v in value.items():
            key = mask_sensitive_text(k)
            if re.search(r"(?i)(api[_-]?key|secret|token|password|passwd|pwd)", str(k)):
                safe[key] = "***MASKED***"
            else:
                safe[key] = _sanitize_obj(v, max_text_len=max_text_len)
        return safe
    if isinstance(value, (list, tuple, set)):
        return [_sanitize_obj(v, max_text_len=max_text_len) for v in list(value)[:80]]
    text = mask_sensitive_text(value)
    if len(text) > max_text_len:
        text = text[:max_text_len] + "...<truncated>"
    return text


def _jsonl_append(path: Path, entry: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")


def _read_jsonl_tail(path: Path, limit: int = 10) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()[-limit:]
        return [json.loads(line) for line in lines if line.strip()]
    except Exception:
        return []


def _build_logger() -> logging.Logger:
    logger = logging.getLogger("kakao_emoticon_v92")
    logger.setLevel(logging.INFO)
    logger.propagate = False
    log_path = get_log_dir() / "app.log"
    if not any(isinstance(h, RotatingFileHandler) and getattr(h, "baseFilename", None) == str(log_path) for h in logger.handlers):
        handler = RotatingFileHandler(log_path, maxBytes=MAX_LOG_BYTES, backupCount=BACKUP_COUNT, encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
        logger.addHandler(handler)
    return logger


logger = _build_logger()


class ErrorHandler:
    """Centralized error logging and Streamlit-safe error display."""

    @staticmethod
    def errors_file() -> Path:
        return get_log_dir() / "errors.jsonl"

    @staticmethod
    def log_error(error: Exception, context: str = "", extra: Optional[dict[str, Any]] = None) -> str:
        now = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        error_id = f"ERR_{now}_{abs(hash(type(error).__name__ + str(error))) % 100000:05d}"
        raw_trace = traceback.format_exc()
        entry = {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "error_id": error_id,
            "error_type": type(error).__name__,
            "message": mask_sensitive_text(error),
            "context": mask_sensitive_text(context),
            "traceback": mask_sensitive_text(raw_trace),
            "extra": _sanitize_obj(extra or {}),
        }
        try:
            _jsonl_append(ErrorHandler.errors_file(), entry)
        except Exception as write_error:  # pragma: no cover
            logger.error("Failed to write sanitized error log: %s", mask_sensitive_text(write_error))
        logger.error("%s %s %s", error_id, mask_sensitive_text(context), mask_sensitive_text(error))
        return error_id

    @staticmethod
    def handle_streamlit_error(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return func(*args, **kwargs)
            except Exception as exc:
                error_id = ErrorHandler.log_error(exc, func.__name__)
                if st is not None:
                    st.error(f"오류가 발생했습니다. 오류 ID: {error_id}")
                    st.caption("기술 정보는 고급 보기 안에만 표시되며, API 키/비밀번호 형태 값은 마스킹됩니다.")
                    with st.expander("고급 기술 정보 보기", expanded=False):
                        st.code(mask_sensitive_text(traceback.format_exc()), language="python")
                return None
        return wrapper

    @staticmethod
    def safe_import(module_path: str, fallback: Any = None, *, required: bool = False) -> Any:
        try:
            parts = module_path.rsplit(".", 1)
            if len(parts) == 2:
                module_name, attr_name = parts
                module = __import__(module_name, fromlist=[attr_name])
                return getattr(module, attr_name)
            return __import__(module_path)
        except (ImportError, AttributeError) as exc:
            if required:
                raise ConfigError(f"필수 모듈 로드 실패: {module_path}") from exc
            logger.warning("Optional import failed: %s", mask_sensitive_text(module_path))
            return fallback

    @staticmethod
    def recent_errors(limit: int = 10) -> list[dict[str, Any]]:
        return _read_jsonl_tail(ErrorHandler.errors_file(), limit=limit)


class ActionLogger:
    """Sanitized user workflow/action logger."""

    @staticmethod
    def actions_file() -> Path:
        return get_log_dir() / "actions.jsonl"

    @staticmethod
    def log(action: str, details: Optional[dict[str, Any]] = None) -> None:
        entry = {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "action": mask_sensitive_text(action),
            "details": _sanitize_obj(details or {}),
        }
        try:
            _jsonl_append(ActionLogger.actions_file(), entry)
        except Exception as exc:  # pragma: no cover
            logger.error("Failed to write action log: %s", mask_sensitive_text(exc))
        logger.info("Action: %s", mask_sensitive_text(action))

    @staticmethod
    def recent_actions(limit: int = 10) -> list[dict[str, Any]]:
        return _read_jsonl_tail(ActionLogger.actions_file(), limit=limit)


class PerformanceLogger:
    @staticmethod
    def perf_file() -> Path:
        return get_log_dir() / "performance.jsonl"

    @staticmethod
    def log(name: str, duration_seconds: float, status: str, extra: Optional[dict[str, Any]] = None) -> None:
        entry = {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "name": mask_sensitive_text(name),
            "duration_seconds": round(duration_seconds, 4),
            "status": status,
            "extra": _sanitize_obj(extra or {}),
        }
        try:
            _jsonl_append(PerformanceLogger.perf_file(), entry)
        except Exception as exc:  # pragma: no cover
            logger.error("Failed to write performance log: %s", mask_sensitive_text(exc))

    @staticmethod
    def recent(limit: int = 10) -> list[dict[str, Any]]:
        return _read_jsonl_tail(PerformanceLogger.perf_file(), limit=limit)


def measure_performance(func: Callable) -> Callable:
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        start = time.perf_counter()
        try:
            result = func(*args, **kwargs)
            PerformanceLogger.log(func.__name__, time.perf_counter() - start, "PASS")
            return result
        except Exception as exc:
            PerformanceLogger.log(func.__name__, time.perf_counter() - start, "FAIL", {"error": str(exc)})
            raise
    return wrapper


def validate_input(validation_func: Callable) -> Callable:
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                validation_func(*args, **kwargs)
            except ValueError as exc:
                error_id = ErrorHandler.log_error(exc, f"{func.__name__}_validation")
                raise ValueError(f"입력값 검증 실패. 오류 ID: {error_id}") from exc
            return func(*args, **kwargs)
        return wrapper
    return decorator


def get_system_diagnostic_summary(limit: int = 8) -> dict[str, Any]:
    log_dir = get_log_dir()
    files = {}
    for name in ["app.log", "errors.jsonl", "actions.jsonl", "performance.jsonl"]:
        path = log_dir / name
        files[name] = {
            "path": str(path),
            "exists": path.exists(),
            "size_bytes": path.stat().st_size if path.exists() else 0,
        }
    return {
        "version": "92.0.0",
        "app_data_dir": str(get_app_data_dir()),
        "log_dir": str(log_dir),
        "files": files,
        "recent_errors": ErrorHandler.recent_errors(limit=limit),
        "recent_actions": ActionLogger.recent_actions(limit=limit),
        "recent_performance": PerformanceLogger.recent(limit=limit),
        "privacy_rules": [
            "API 키/비밀번호/토큰 형태 값은 저장 전 마스킹",
            "정확한 사용자 홈 경로 일부 마스킹",
            "로그는 프로그램 코드 폴더가 아닌 사용자 데이터 폴더에 저장",
            "로그 파일은 용량 제한과 롤링 보관 적용",
        ],
    }


def export_diagnostic_package(out_dir: Optional[Path] = None) -> Path:
    """Create a sanitized support ZIP containing logs and a summary."""
    log_dir = get_log_dir()
    target_dir = out_dir or (get_app_data_dir() / "diagnostic_exports")
    target_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    summary_path = target_dir / f"v92_diagnostic_summary_{stamp}.json"
    summary = get_system_diagnostic_summary(limit=30)
    summary_path.write_text(json.dumps(_sanitize_obj(summary), ensure_ascii=False, indent=2), encoding="utf-8")
    zip_path = target_dir / f"v92_diagnostic_logs_{stamp}.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.write(summary_path, summary_path.name)
        for name in ["app.log", "errors.jsonl", "actions.jsonl", "performance.jsonl"]:
            path = log_dir / name
            if path.exists():
                safe_copy = target_dir / f"sanitized_{name}"
                safe_copy.write_text(mask_sensitive_text(path.read_text(encoding="utf-8", errors="ignore")), encoding="utf-8")
                zf.write(safe_copy, safe_copy.name)
                try:
                    safe_copy.unlink()
                except Exception:
                    pass
    return zip_path


# Initialize log files lazily and record module load without personal details.
ActionLogger.log("v92_error_logging_module_initialized", {"log_dir": str(get_log_dir())})
