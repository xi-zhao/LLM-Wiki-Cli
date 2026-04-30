# Star Optimized README Design

## Goal

Rewrite the public GitHub README so a new visitor can understand Wikify's value in seconds, run a useful demo quickly, and decide whether the project is worth starring.

## Problem

The previous README was technically accurate but front-loaded internal concepts: control planes, queues, artifacts, validation reports, and protocol details. That is useful for agents and maintainers, but weak for discovery. A GitHub visitor needs to know what the project does, why it is useful, how to try it, and where to find deeper docs.

## Design

The README should use an inverted-pyramid structure:

1. One-line value proposition.
2. Three to five concrete benefits.
3. A short demo.
4. Difference from familiar alternatives.
5. Agent workflow and recovery model.
6. Links to deep docs.

The README should avoid exposing request artifacts, queues, and protocol schemas as the human product surface. Those details remain linked through the agent operator guide, protocol reference, and Chinese product document.

## Acceptance

- The first screen says Wikify turns links, files, repos, and notes into an agent-maintained local wiki.
- The README contains "Why Star Wikify?", "30-Second Demo", and clear OpenClaw/Codex/Claude Code positioning.
- The README still preserves the product boundary that humans see wiki results while agents inspect machine artifacts.
- Existing documentation tests lock the new public positioning.
