# Unified Ingest Pipeline Design

**Date:** 2026-04-30
**Status:** Draft for review
**Scope:** Next milestone candidate

## Problem

Wikify currently has two ingest stories:

- Legacy URL ingest can process web and WeChat article URLs through scripts and write `articles/`, `sources/`, and `sorted/` artifacts.
- The v0.2 personal wiki flow has source registry, sync, wikiization, views, agent exports, and maintenance, but URL sources are intentionally offline during `sync` and do not become first-class source-backed wiki pages without an explicit handoff.

This split makes ingest feel like a script collection rather than the front door of the product. It also makes future source types risky: every new source can add another path around the wiki object model.

## Product Goal

Make ingest a first-class, explicit, source-backed pipeline:

```text
registered source or explicit locator
  -> adapter fetch
  -> normalized document
  -> canonical source item
  -> wikiization queue
  -> wiki page objects
  -> human views and agent context
```

The first strong validation source is WeChat public account articles from `mp.weixin.qq.com`. The architecture should also fit normal web pages and local documents without creating a second pipeline.

## Human Product Surface

Humans should primarily see the final organized wiki, not the pipeline machinery.

The human-facing product surface is:

- `wikify ingest <locator>` to add new knowledge.
- `wikify views` or a future `wikify open` to inspect the organized wiki.
- Generated Markdown/static wiki pages under `views/` and `views/site/`.

The machine-facing surface is:

- source registry
- sync
- ingest queues
- source item objects
- wikiization queues
- validation reports
- agent exports
- maintenance tasks

Those machine artifacts must remain stable and inspectable for agents, debugging, and recovery, but product copy and default user workflows should not require humans to understand them. A normal user should be able to think: "I gave Wikify source material; Wikify updated my wiki."

## Non-Goals

- No hidden network work in `wikify sync`.
- No hidden provider calls, embeddings, vector databases, or background watchers.
- No browser GUI or desktop workflow.
- No broad rewrite of every legacy ingest script in the first slice.
- No claim-level semantic extraction beyond what current deterministic wikiization can safely support.

## Recommended Approach

Build a unified ingest pipeline with adapter interfaces, then migrate WeChat URL ingest first.

This keeps the product shape clean while reducing rewrite risk. Existing scripts can be wrapped or reused behind adapters during the first milestone, then retired once behavior is covered by tests.

## CLI Surface

Keep `wikify ingest <locator>` as the explicit, human-friendly, network-capable entrypoint.

Add focused options:

```bash
wikify ingest <locator>
wikify ingest <locator> --source src_<id>
wikify ingest <locator> --adapter wechat_url
wikify ingest <locator> --dry-run
wikify ingest <locator> --write-raw
wikify ingest <locator> --queue-wikiize
```

Rules:

- `wikify ingest` may fetch network content because the user invoked ingest explicitly.
- `wikify ingest` should run the full user-visible path by default: ingest, queue wikiization, wikiize the ingested item when deterministic content is available, validate, and refresh human views. Advanced flags may stop after lower-level artifacts for agents and debugging.
- `wikify source add --type url` still only registers.
- `wikify sync` still records URL sources as offline remote items and never fetches them.
- `--queue-wikiize` is the default for successful normalized documents unless `--dry-run` is set.

## Architecture

### Core Module

Add `wikify/ingest/` with small modules:

- `pipeline.py`: orchestration, result envelopes, run lifecycle.
- `adapters.py`: adapter protocol and adapter registry.
- `documents.py`: normalized document and asset contracts.
- `artifacts.py`: path helpers and atomic writes.
- `errors.py`: typed ingest errors.

Each module should have one job. Adapter code should not write final wiki objects directly; it returns normalized data to the pipeline.

### Adapter Protocol

Each adapter implements:

```python
class IngestAdapter:
    name: str

    def can_handle(locator: str, source: dict | None) -> bool: ...
    def fetch(request: IngestRequest) -> FetchedPayload: ...
    def normalize(payload: FetchedPayload) -> NormalizedDocument: ...
```

First adapters:

- `wechat_url`: handles `https://mp.weixin.qq.com/...`
- `web_url`: handles normal `http` and `https` pages
- `local_document`: handles local Markdown, text, and HTML files when ingest is called directly

## Artifact Contract

Successful ingest writes:

```text
.wikify/ingest/runs/<run-id>.json
.wikify/ingest/items/<item-id>.json
.wikify/queues/ingest-items.json
sources/raw/<adapter>/<item-id>/
artifacts/objects/source_items/<item-id>.json
```

Optional adapter raw assets live under `sources/raw/...`:

- fetched HTML
- fetched text
- metadata JSON
- downloaded image metadata
- adapter diagnostics

The canonical `source_item` object is the handoff to `wikify wikiize`. Wikiization should not need to know whether a source item came from WeChat, a web page, or a local file.

## Normalized Document

The normalized document should include:

- stable `item_id`
- `source_id` when attached to a registered source
- original locator
- canonical locator
- adapter name
- title
- author or source account if available
- published time if available
- captured time
- body text
- cleaned Markdown body
- raw artifact paths
- asset records
- quality warnings
- fingerprint evidence

For WeChat, `source_account`, `create_time`, image count, broken asset count, and original article URL are required fields when available.

## WeChat Adapter Behavior

The WeChat adapter should wrap current working behavior first, then move logic into package modules as tests stabilize.

Required behavior:

- Detect `mp.weixin.qq.com` URLs.
- Fetch article HTML and text through the configured browser fetch path.
- Extract title, source account, publish time, canonical URL, body text, content HTML, and images.
- Save raw HTML/text/metadata/assets under `sources/raw/wechat_url/<item-id>/`.
- Produce a normalized Markdown body without obvious WeChat chrome.
- Create a canonical source item with source refs and fingerprints.
- Queue the item for `wikify wikiize`.

Failure behavior:

- If fetching is blocked, write an ingest run with `status: failed` and a typed error.
- If assets fail but text succeeds, write `status: completed_with_warnings`.
- Never fabricate body text when extraction fails.

## Data Flow

### Explicit URL Ingest

```text
wikify ingest https://mp.weixin.qq.com/s/...
  -> resolve adapter wechat_url
  -> fetch raw payload
  -> normalize document
  -> write ingest run and item artifacts
  -> write source item object
  -> upsert wikiization queue entry
```

### Registered URL Source

```text
wikify source add https://mp.weixin.qq.com/s/... --type url
wikify sync
  -> records offline remote source item only

wikify ingest https://mp.weixin.qq.com/s/... --source src_<id>
  -> fetches explicitly
  -> links normalized item to registered source id
```

This preserves the current no-hidden-network rule while letting users intentionally promote a URL source into fetched content.

## Error Handling

Add typed errors:

- `ingest_adapter_not_found`
- `ingest_fetch_failed`
- `ingest_normalization_failed`
- `ingest_artifact_write_failed`
- `ingest_source_not_found`
- `ingest_locator_invalid`
- `ingest_extraction_empty`

All errors return standard Wikify JSON envelopes and include retryability.

## Maintenance Integration

`wikify maintain` should be able to read ingest run and item artifacts after the first implementation slice.

Initial findings:

- failed ingest run
- completed ingest with warnings
- source item not queued for wikiization
- raw artifact missing
- source item object validation failure

Maintenance should queue repair/regeneration tasks; it should not rerun network fetch silently.

## User Experience

For a human user, the target flow is:

```bash
wikify ingest https://mp.weixin.qq.com/s/...
```

Expected result:

- The command returns a concise success summary and the path to the updated wiki entry.
- The organized wiki views are refreshed.
- Raw ingest diagnostics are available only as linked artifacts, not as the main experience.
- If extraction fails, the user sees a clear failure and next action, not a pile of partial pipeline files.

For agents and advanced debugging, lower-level commands remain available:

```bash
wikify source add ...
wikify sync
wikify wikiize --dry-run
wikify validate --strict
wikify agent context ...
```

This split is intentional: humans consume the final knowledge base; agents operate and repair the pipeline.

## Compatibility

Keep legacy behavior available:

- `wikify ingest <url>` still works.
- Existing output directories can remain during migration.
- Existing tests for `scripts/ingest_*` should keep passing until replaced by package-level tests.

The new pipeline becomes the source of truth for v0.2+ wikiization. Legacy script outputs are compatibility artifacts, not the primary product interface.

## Testing

Use focused `unittest` coverage:

- adapter resolution for WeChat, web, and local document locators
- dry-run writes nothing
- WeChat normalization from fixture HTML/text
- successful ingest writes run, item, raw, source item, and queue artifacts
- failed fetch writes a failed run without source item or queue entry
- asset warning produces `completed_with_warnings`
- `wikify sync` still does not fetch URL sources
- `wikify wikiize` can consume an ingested WeChat source item
- CLI envelopes and exit codes are stable

Network-dependent tests should use fixtures or fake fetchers. Live network/browser tests can be documented as smoke tests, not required unit tests.

## Acceptance Criteria

The first implementation slice is complete when:

- `wikify ingest <mp.weixin.qq.com URL>` uses the unified pipeline.
- Successful WeChat ingest produces canonical ingest and source item artifacts.
- The generated source item is queued for `wikify wikiize`.
- The default human path turns deterministic content into a source-backed wiki page and refreshes human views.
- `wikify wikiize`, `wikify views`, and `wikify agent export` can still consume the resulting artifacts as lower-level agent/debug commands.
- `wikify sync` remains offline for URL sources.
- Existing legacy ingest tests and full unit discovery pass.

## Open Product Decision

The first milestone should not decide provider-backed semantic enrichment. It should make deterministic ingest reliable first. Provider runtime can be a later adapter capability once the artifact contract is stable.
