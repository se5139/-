# v73 Final User Approval Workflow

- Adds final user checklist before producing user-approved submission candidate ZIP.
- Keeps v72 autofix/lock workflow and does not overwrite originals.
- Requires explicit confirmation for human origin, 32 static preview, 24 animated preview, GIF review, phrase review, dark mode readability, copyright similarity, official spec recheck, API key exclusion, and final approval.
- Generates Jinja2 HTML report, CSV checklist, approval manifest, manual review ZIP, user-approved ZIP, and SQLite learning DB.
- This is a local review workflow and does not guarantee Kakao approval or revenue.
