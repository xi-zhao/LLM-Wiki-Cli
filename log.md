# File Organizer Wiki Log

该文件记录 LLM Wiki 的关键演化节点。采用 append-only 方式维护。

## [2026-04-09] bootstrap | Adopted Karpathy-style LLM Wiki pattern
- Added `file-organizer/WIKI_SCHEMA.md` to define wiki architecture, ingest/query/lint workflow, and file roles.
- Added `file-organizer/index.md` as the top-level wiki navigation entry.
- Confirmed current `file-organizer/` should be treated as a persistent markdown wiki, not only an article archive.
- Next recommended work: unify topic backlinks, add query-oriented outputs under `sorted/`, and evolve maintenance scripts from WeChat-only toward general wiki maintenance.
