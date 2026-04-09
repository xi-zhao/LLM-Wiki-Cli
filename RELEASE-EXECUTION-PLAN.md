# RELEASE-EXECUTION-PLAN

This file turns the release cleanup judgment into executable repository actions.

Goal: reshape `file-organizer/` into a publishable **LLM-Wiki-Cli** product repository.

---

## 1. Release strategy

Use a **minimal publishable product surface**.

Keep:
- docs
- protocol
- CLI
- core scripts
- packaging
- tests
- optional templates

Remove from Git index:
- local KB working data
- runtime state
- material bundles
- archives
- temp outputs

---

## 2. Keep in first public release

### Must keep
- `file-organizer/README.md`
- `file-organizer/LLM-Wiki-Cli-README.md`
- `file-organizer/RELEASE-CHECKLIST.md`
- `file-organizer/QUICKSTART.md`
- `file-organizer/.gitignore`
- `file-organizer/pyproject.toml`
- `file-organizer/scripts/fokb.py`
- `file-organizer/scripts/fokb_protocol.md`
- `file-organizer/scripts/README.md`
- `file-organizer/scripts/ingest_any_url.py`
- `file-organizer/scripts/wiki_lint.py`
- `file-organizer/scripts/ingest_result_enricher.py`
- `file-organizer/scripts/topic_maintainer.py`
- `file-organizer/scripts/source_index_manager.py`
- `file-organizer/scripts/generate_topic_digest.py`
- `file-organizer/tests/test_fokb.py`

### Optional keep
- `file-organizer/scripts/ingest_web_direct_url.py`
- `file-organizer/scripts/ingest_wechat_direct_url.py`
- `file-organizer/scripts/fetch_wechat_article.py`
- `file-organizer/scripts/fetch_web_article.py`
- `file-organizer/tests/test_fetch_web_article.py`
- `file-organizer/tests/test_ingest_web_direct_url.py`
- `file-organizer/tests/test_ingest_wechat_direct_url.py`
- `file-organizer/topics/_template.md`
- `file-organizer/timelines/_template.md`
- `file-organizer/sources/index-template.md`
- `file-organizer/WIKI_SCHEMA.md`

---

## 3. Remove from Git index

### Runtime state files
```bash
git rm --cached \
  file-organizer/sorted/last-ingest-payload.json \
  file-organizer/sorted/maintenance-history.json \
  file-organizer/sorted/system-state.json \
  file-organizer/sorted/review-queue.json \
  file-organizer/sorted/resolved-review.json \
  file-organizer/sorted/wiki-lint-report.json \
  file-organizer/sorted/wechat-kb-maintenance-report.json
```

### Local content directories
```bash
git rm -r --cached \
  file-organizer/articles/raw \
  file-organizer/articles/parsed \
  file-organizer/articles/briefs \
  file-organizer/materials \
  file-organizer/archive \
  file-organizer/temp
```

### Local working outputs in sorted
```bash
git rm --cached \
  file-organizer/sorted/quantum-bullets.md \
  file-organizer/sorted/quantum-computing-industry-digest.md \
  file-organizer/sorted/quantum-financing-note-2.md \
  file-organizer/sorted/quantum-financing-outline-validation-2.md \
  file-organizer/sorted/quantum-financing-outline-validation.md \
  file-organizer/sorted/quantum-notes.md \
  file-organizer/sorted/quantum-outline.md \
  file-organizer/sorted/wechat-agent-auto-promote.md \
  file-organizer/sorted/wechat-agent-decision-validation.md \
  file-organizer/sorted/wechat-agent-summary.md
```

### Real working topics and timelines (recommended to remove unless curated as examples)
```bash
git rm --cached \
  file-organizer/topics/ai-coding-and-autoresearch.md \
  file-organizer/topics/ai-research-writing.md \
  file-organizer/topics/ai-voice-and-edge-models.md \
  file-organizer/topics/quantum-computing-industry.md \
  file-organizer/topics/quantum-financing-outline-validation-2.md \
  file-organizer/topics/tob-ai-productization.md \
  file-organizer/topics/wechat-agent-auto-promote.md \
  file-organizer/topics/wechat-agent-decision-validation.md \
  file-organizer/topics/wechat-agent-routing.md \
  file-organizer/timelines/ai-research-tools.md \
  file-organizer/timelines/quantum-computing-industry.md \
  file-organizer/timelines/tob-ai-productization.md \
  file-organizer/timelines/wechat-agent-ecosystem.md
```

### Legacy working files to review before publish
```bash
git rm --cached \
  file-organizer/index.md \
  file-organizer/log.md \
  file-organizer/inbox/2026-03-25_batch-wechat-article-intake.md
```

---

## 4. Review before running removals

Before executing the `git rm --cached` commands above, confirm whether you want to keep any of these as public examples:

- topic samples
- timeline samples
- sorted examples
- schema / trigger-rule docs

If yes, move them into a curated directory such as:
- `file-organizer/examples/`
- `file-organizer/sample-kb/`

Do not keep them mixed with local working data.

---

## 5. Dry-run commands before final publish

```bash
git status --short file-organizer
```

```bash
git diff --cached --stat
```

```bash
python3 file-organizer/tests/test_fokb.py
```

```bash
python3 file-organizer/scripts/fokb.py check
```

```bash
python3 file-organizer/scripts/fokb.py stats
```

```bash
python3 file-organizer/scripts/fokb.py decide --maintenance-path /absolute/path/to/sample.md
```

---

## 6. Publish gate

Only publish when all of the following are true:

- docs are aligned with actual CLI behavior
- tracked local KB content is removed or intentionally curated
- runtime state is not tracked
- tests pass
- `git status` reflects a clean product surface

---

## 7. Suggested final release shape

A clean first public repository should look roughly like:

- `README.md`
- `LLM-Wiki-Cli-README.md`
- `RELEASE-CHECKLIST.md`
- `RELEASE-EXECUTION-PLAN.md`
- `pyproject.toml`
- `.gitignore`
- `scripts/`
- `tests/`
- maybe `examples/` later

It should **not** look like a live personal working KB.
