# Working agreement

- Never stage or commit files.
- The user performs all Git operations.
- Implement one roadmap feature at a time.
- Stop and report after each feature.
- Run project commands through `just`.
- Run `just check` before every handoff.
- When handing off a completed feature to the user, summarize in brief bullet point what was achieved, and how the user can test this new functionality manually.
- Use a non-default available port for Streamlit smoke tests.
- Report discovered bugs promptly; do not pursue speculative fixes.
- If `.pth` import corruption appears, immediately run:
  `just rebuild-environment`
- Treat `.agents/` and `.claude/` as user-owned.
- Never include `data/`, artwork, databases, exports, or literary content in Git.
- Never use soft language: includes adjectives and adverbs to soften problems or make something sound genuine. Be objective and get to the point of what you're describing.
- Ask questions until you don't need to make assumptions.
- After 2 failed attempts at fixing the same bug, stop and ask — do not try a 3rd hypothesis on your own. Count explicitly: attempt 1 fails, try attempt 2; attempt 2 fails, STOP and report both failed hypotheses, stop the work immediately and surface it for the user to decide next steps. You must explain the problem and/or bug that you encountered to the user. Do not: decide it's "out of scope" and route around it; keep executing the rest of a todo list while it's unresolved; theorize about root cause further on your own; take any corrective or compensating action. Report the finding, then wait. 
- A diagnostic question vs. a design/intent question are different.** "Why is this failing" is discoverable in code/logs/state — investigate it independently. "What should this system do here" is not discoverable — it's a decision that exists only in the user's head as the system's designer. When a failure's fix isn't obviously mechanical (a missing registration entry, a typo, an off-by-one), pause and ask what the intended design is rather than reasoning harder toward a confident-looking guess.
- Never call something "difficult," "expensive," or a "sunk cost," and never let effort factor into a decision. Evaluate purely on what's architecturally correct long-term. If something is genuinely low-priority, say so based on relevance/impact, not effort.
- `Learnings.md` is a problem-indexed reference, not a session log. Every entry: a searchable problem title, then **Symptom** (exact error text, where in the process it broke), **Cause**, **Resolution**, and **Caveat** if one exists. Organize by system/component, never by build phase, session, or chronological order. Exclude phase numbers, "this session" language, prompt-sequence narrative, and pure "verified: ..." testing-log paragraphs that don't teach something reusable — that content belongs in `Progress.md` instead, which is the correct home for phase-by-phase chronological narrative.
- Create reusable code components or modules: never rewrite code for the same logic, behavior, or design twice; instead generalize it with parameters so you write it once but the parameters allow it to be reused in different contexts.