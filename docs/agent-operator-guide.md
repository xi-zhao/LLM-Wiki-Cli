# Wikify Agent Operator Guide

This guide is for agents such as Codex, Claude Code, OpenClaw, and local automation wrappers. Humans should not need this guide for normal use.

The product rule is simple: human request, agent operation, wiki result.

Never make the human read request artifacts, queues, validation reports, or JSON envelopes by default. Use those artifacts yourself, then give the human a short knowledge-base change summary.

## Default Human Request

Treat these as equivalent save/organize requests:

```text
Save this article to my wiki: https://...
Help me save this file.
Make this WeChat public account article easy to find later.
把这个链接整理进我的 wiki。
帮我保存这篇文章。
这个文件帮我归档一下。
```

The human is asking for a durable wiki result, not for CLI instructions.

## Operating Flow

### 1. Capture the source

Call:

```bash
wikify ingest <locator>
```

Use the URL, file path, or other locator the human gave you. For WeChat public account articles, pass the `mp.weixin.qq.com` article URL directly.

`wikify ingest` is allowed to fetch network content because the save action is explicit. Do not use `wikify sync` to fetch URLs; sync is offline change detection.

### 2. Read the trusted request

After successful ingest, inspect the trusted agent request under:

```text
.wikify/ingest/requests/
```

Use it to find source metadata, cleaned content pointers, workspace context, permission semantics, recovery guidance, page quality standards, and the expected human summary shape.

Do not show this artifact to the human unless they ask for debugging details.

### 3. Update the wiki when needed

If the deterministic ingest/wikiize path already produced a good page and refreshed views, keep the final response short.

If the content needs semantic organization, do the work as the trusted agent:

- merge duplicate pages when it improves the wiki
- split large imported content into clearer pages when useful
- add links to existing topics
- preserve source traceability
- keep claims tied to source-backed material

Use `wikify trusted-op begin` before broad edits, especially merges, splits, deletes, or multi-file rewrites:

```bash
wikify trusted-op begin --path wiki/pages/example.md --reason "merge imported article into existing topic"
```

Then edit the scoped wiki files directly. When done, complete the operation:

```bash
wikify trusted-op complete --operation-path .wikify/trusted-operations/op_<id>.json
```

If the operation needs to be reverted, use:

```bash
wikify trusted-op rollback --operation-path .wikify/trusted-operations/op_<id>.json
```

Rollback is hash-guarded. If files changed after completion, Wikify refuses the rollback instead of overwriting newer work.

### 4. Validate and refresh human views

Use validation and view generation when your edit changes wiki content:

```bash
wikify validate --strict --write-report
wikify views
```

If validation fails, fix the wiki or explain the blocking issue. Do not tell the human to inspect JSON unless that is the only honest next step.

### 5. Reply to the human

Give a short human-facing summary:

- what was saved
- where it is in the wiki
- any important related pages or topics
- whether anything needs review

Good response shape:

```text
已保存并整理进 wiki：<title>。
主要页面：wiki/pages/<page>.md
我也把它关联到了 <topic>，之后可以从 views/index.md 或本地静态 wiki 入口找到。
```

Bad response shape:

```text
我写入了 .wikify/queues/ingest-items.json，并生成了 trusted request。
你可以运行 wikify views。
```

Those details are agent/debug surfaces, not the normal product experience.

## Boundaries

- Do not hide network fetches behind `sync`; use explicit `ingest`.
- Do not invent unsupported claims when source extraction is weak.
- Do not remove source references to make pages cleaner.
- Do not expose raw JSON artifacts to humans by default.
- Do not run hidden provider calls inside Wikify. If semantic work is needed, you are the external trusted agent.
- Do not skip `trusted-op` for high-blast-radius wiki edits.

## Recovery

For deterministic patch bundles, use `wikify apply` and `wikify rollback`.

For broad trusted-agent edits that you made directly, use `wikify trusted-op begin`, `complete`, and `rollback`.

If rollback refuses a hash mismatch, stop and inspect the current files. A later edit happened after the operation completed, and overwriting it would be unsafe.
