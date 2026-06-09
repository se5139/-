# v58 API Key Safety / Rotation Workflow

- Added OpenAI API key safety page: `50 API 키 안전보관/교체`.
- Keeps OpenAI API usage optional and disabled by default.
- Never writes raw API keys to reports, CSV, JSON, or ZIP output.
- Generates environment-variable setup templates instead of embedding keys.
- Adds secret-leak detection for uploaded TXT/ENV/ZIP files.
- Keeps final app Python-centered; Inno Setup remains only the Windows installer wrapper.
