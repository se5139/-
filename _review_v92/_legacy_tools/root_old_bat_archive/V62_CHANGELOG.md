# v62 Jinja2 Template Engine

- Added Jinja2 to requirements.
- Added modules/jinja_template_engine.py.
- Added templates/v62_jinja/*.j2.
- Added sidebar menu 52 for HTML report, prompt pack, motion CSV, manifest, and ZIP generation.
- Keeps Streamlit as the app UI and uses Jinja2 for generated artifacts.
- Blocks API-key-like strings from generated reports/packages.
