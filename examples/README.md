# Examples

This directory holds small public examples that show how the repository is meant
to be used without shipping a private working knowledge base.

## Included examples

- `decide-quantum-topic.json`
  - Example output from `fokb decide --maintenance-path topics/quantum-computing-industry.md`
  - Shows the step-based decision contract used by agents

## Sample walkthrough

From the repository root:

```bash
fokb init
fokb check
fokb stats
fokb show quantum-computing-industry --scope topics
fokb decide --maintenance-path topics/quantum-computing-industry.md
```

## Why examples live here

The public repo should demonstrate:

- repository layout
- command surface
- output contract

It should not expose:

- private article archives
- personal working notes
- machine-local runtime state
