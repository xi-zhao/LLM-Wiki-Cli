# RELEASE-CHECKLIST

## Goal

Prepare `file-organizer/` for a clean GitHub release of **LLM-Wiki-Cli** as an agent-facing product, not as a dump of local working data.

---

## 1. What should be included

### Product docs
- `README.md`
- `LLM-Wiki-Cli-README.md`
- `QUICKSTART.md`
- `scripts/README.md`
- `scripts/fokb_protocol.md`

### Core CLI and scripts
- `scripts/fokb.py`
- `scripts/ingest_any_url.py`
- `scripts/wiki_lint.py`
- `scripts/ingest_result_enricher.py`
- `scripts/topic_maintainer.py`
- `scripts/source_index_manager.py`
- `scripts/generate_topic_digest.py`

### Optional ingest/fetch modules
Include only if intended for the first public release:
- `scripts/ingest_wechat_direct_url.py`
- `scripts/ingest_web_direct_url.py`
- `scripts/fetch_wechat_article.py`
- `scripts/fetch_web_article.py`

### Tests
At minimum:
- `tests/test_fokb.py`

Optional if stable:
- `tests/test_fetch_web_article.py`
- `tests/test_ingest_web_direct_url.py`
- `tests/test_ingest_wechat_direct_url.py`

### Packaging
- `pyproject.toml`
- any required install/runtime metadata files
- `.gitignore`

---

## 2. What should NOT be included

### Runtime state
- `sorted/last-ingest-payload.json`
- `sorted/maintenance-history.json`
- `sorted/system-state.json`

### Local archives and materials
- `archive/`
- `materials/`

### Local knowledge content dump
Do not publish the current working KB wholesale:
- `articles/raw/`
- `articles/parsed/`
- `articles/briefs/`
- most `sorted/*.md`
- most local topic/timeline working content unless intentionally curated

### Trash / machine-local artifacts
- `.DS_Store`
- `__pycache__/`
- `*.pyc`
- `.pytest_cache/`

---

## 3. Recommended release shape

Prefer a **minimal publishable product repo**:

- docs
- CLI
- protocol
- tests
- packaging files

Do **not** mix in:
- private working notes
- historical ingest outputs
- material bundles
- local state snapshots

---

## 4. Pre-publish checks

### Contract checks
- [ ] `fokb_protocol.md` matches real CLI output
- [ ] `README.md` points clearly to full product docs
- [ ] `LLM-Wiki-Cli-README.md` reflects current command surface

### CLI checks
- [ ] `python3 scripts/fokb.py check`
- [ ] `python3 scripts/fokb.py stats`
- [ ] `python3 scripts/fokb.py maintenance --last`
- [ ] `python3 scripts/fokb.py decide --maintenance-path <sample-path>`

### Test checks
- [ ] `python3 tests/test_fokb.py`
- [ ] other public tests if included

### Repo hygiene
- [ ] no `.DS_Store`
- [ ] no `__pycache__`
- [ ] no local state JSONs tracked
- [ ] no accidental content dump in `articles/`, `materials/`, `archive/`

---

## 5. Suggested release flow

1. Keep product docs and protocol files committed
2. Keep runtime state and local content ignored
3. Curate a minimal example set later if needed (`examples/` or `sample-kb/`)
4. Run tests
5. Recheck `git status`
6. Only then push to GitHub

---

## 6. Current release posture

Current project status is:

- product docs are ready
- CLI contract is largely productized
- repository still contains substantial local working data

Conclusion:

## The product is publishable, but the repository still needs selective release hygiene.
