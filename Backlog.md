# World Builder — Backlog and Technical Debt

This file records work intentionally deferred from an active feature, known limitations, technical debt, defects not addressed immediately, and future product ideas. The implementation sequence remains in `Roadmap.md`; completed work belongs in `Progress.md`.

## Status definitions

- **Proposed:** Captured but not yet prioritized.
- **Accepted:** Agreed work awaiting scheduling.
- **In progress:** Actively being addressed.
- **Blocked:** Cannot proceed until a named dependency or decision is resolved.
- **Done:** Completed; retain the entry for history and reference the relevant progress log.
- **Declined:** Deliberately not pursuing; retain the rationale.

## Priority definitions

- **P0:** Data loss, security, or application unusability.
- **P1:** Materially blocks a core workflow.
- **P2:** Important improvement with an acceptable workaround.
- **P3:** Nice-to-have enhancement or cleanup.

## Active backlog

No active backlog items. Items explicitly outside the first implementation are recorded below as future candidates.

## Future candidates

### BL-001 — LLM-assisted character summary proposals

- **Status:** Proposed
- **Priority:** P3
- **Origin:** Product discovery
- **Description:** Assemble approved universe context and ask a configured LLM to propose updates to a character summary based on newer stories and relationship developments.
- **Constraint:** Generated content must remain a proposal until manually approved. Credentials must not be stored in the portable data directory.
- **Target:** Post-v1

### BL-002 — Automated story entity suggestions

- **Status:** Proposed
- **Priority:** P3
- **Origin:** Product discovery
- **Description:** Suggest character, group, artwork, and milestone links after story import without changing canonical links automatically.
- **Target:** Post-v1

### BL-003 — Guided data export and import

- **Status:** Proposed
- **Priority:** P3
- **Origin:** Architecture discussion
- **Description:** Package the SQLite database and original artwork into a validated archive and provide a guided restore workflow.
- **Current workaround:** Stop the application and copy the complete `data/` directory manually.
- **Target:** Post-v1 unless manual copying proves unreliable.

### BL-004 — Story revision history

- **Status:** Declined
- **Priority:** P3
- **Origin:** Product discovery
- **Description:** Preserve previous versions of story Markdown.
- **Rationale:** The agreed workflow overwrites the current story record; external publishing and writing tools remain responsible for revision history.

### BL-005 — Historical graph snapshots

- **Status:** Declined
- **Priority:** P3
- **Origin:** Graph design
- **Description:** Render the relationship graph as it existed at a selected chapter.
- **Rationale:** The required graph visualizes current character and group connections only. Relationship history remains available in profiles.

### BL-006 — Native desktop packaging

- **Status:** Proposed
- **Priority:** P3
- **Origin:** Architecture discussion
- **Description:** Package the local application as a native-style macOS and Windows launcher.
- **Current workaround:** Run the Streamlit application through the reproducible `uv` environment.
- **Target:** Only if local command-line startup becomes burdensome.

## Newly discovered item template

```markdown
### BL-XXX — Short title

- **Status:** Proposed
- **Priority:** P0 | P1 | P2 | P3
- **Origin:** F-XX or session/date
- **Description:** What is missing or compromised.
- **Impact:** Why it matters.
- **Current workaround:** If one exists.
- **Proposed resolution:** Optional.
- **Target:** Feature or release, if known.
```

