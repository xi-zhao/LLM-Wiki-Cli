# sample-kb

This directory is a tiny public example knowledge base for `fokb`.

It shows the intended shape without exposing a private working repository.

## Use it

```bash
cd file-organizer
export FOKB_BASE="$(pwd)/sample-kb"

fokb stats
fokb show agent-knowledge-loops --scope topics
fokb show 2026-04-10_agent-knowledge-loops --scope parsed
fokb digest agent-knowledge-loops.md
```

## What is included

- one raw note
- one parsed article note
- one brief note
- one topic
- one digest
- one source index
- one Obsidian navigation page

## Why it exists

The public repo should demonstrate the product surface, not publish a private working KB.
