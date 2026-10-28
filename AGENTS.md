# OpenJLPT fork conventions

- Preserve upstream English fields and stable IDs. New Chinese content belongs in sources/zh-CN; do not hand-edit generated data.
- Apply guarded entry corrections through sources/corrections/entries.json and npm run prepare:data. If upstream content conflicts, investigate rather than rewriting the guard.
- Chinese source hashes cover original content. Never refresh a hash solely to silence stale detection. User authorization on 2026-10-28 permits Codex to review and approve Chinese content. Record reviewer=Codex, review_method=ai, reviewed_at and review_hash only after actual review. Do not imply independent human review. New unreviewed text remains draft; edits to reviewed content require re-review.
- Keep the Chinese pilot, reference evidence and quality report honest about sampling and review coverage.
- Run npm run check:data, npm run validate, npm run typecheck, npm test and Python tests for affected data/API changes. Run a static-site build and export checks for rendering changes.
- The website is statically generated. Avoid introducing a backend for localization or search.
- Keep deployment hosts and credentials out of committed documentation. Production SITE_URL is deployment configuration.
