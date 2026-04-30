# Human And Agent Documentation Entry Design

## Goal

Make Wikify's documentation match the product experience: humans ask agents to save or organize knowledge, agents operate the CLI, and humans receive the final wiki result.

## Design

The README should open with the product promise in plain language before exposing implementation details. It should say that the normal human action is a request such as "save this article" and that `wikify ingest <locator>` is the agent-facing tool call.

The Chinese README should provide a short three-step path: human asks, agent calls Wikify, human receives the wiki result. It should keep lower-level concepts such as queue, trusted request, validation report, and agent context clearly marked as agent/debug surfaces.

The protocol document should remain machine-facing. It should explicitly state that the protocol is not the human product surface and link agents to a dedicated operator guide.

The new agent operator guide should give agents concrete operating steps:

1. Capture the source with `wikify ingest <locator>`.
2. Read the trusted request.
3. Use `trusted-op` around broad wiki edits.
4. Validate and refresh human views.
5. Reply to the human with a short wiki change summary.

## Acceptance

- README contains a plain-language product entry and links to the agent guide.
- Chinese README contains the three-step product path.
- Protocol docs preserve machine-level detail while pointing to the guide.
- Tests assert the key phrases and guide sections so future edits do not drift back into exposing internal workflow as the human experience.
