# Night relay — the semaphore

**One file, one writer at a time. Both night agents read this FIRST and write to it LAST.**

The whole point: agent A runs alone, finishes, flips the state. Agent B refuses to exist until it sees
that flip. No overlap, no shared files, no coordination beyond this document.

## State

```
STATE: AUDIT-RUNNING
SINCE: 2026-08-19T23:56Z
BY: agent A — philosophy audit (RM15)
```

**Legal transitions, in order. Nothing skips.**

| From | Who moves it | To |
|---|---|---|
| `READY-FOR-AUDIT` | agent A (philosophy audit) on start | `AUDIT-RUNNING` |
| `AUDIT-RUNNING` | agent A on finish | `AUDIT-DONE` |
| `AUDIT-DONE` | agent B (builder) on start | `BUILD-RUNNING` |
| `BUILD-RUNNING` | agent B on finish | `BUILD-DONE` |

## The rules, both agents

1. **Read the `STATE:` line before doing anything else.** If it is not the state your role starts
   from, **stop immediately and write nothing.** Say which state you found and exit. A wrong-state
   start is the only failure mode this file exists to prevent.
2. **Claim it by writing your transition first**, with a UTC timestamp, before any other work. Commit
   that immediately — a claim nobody can see is not a claim.
3. **`AUDIT-RUNNING` or `BUILD-RUNNING` older than 4 hours is a dead agent.** Append a note saying
   so, move the state back one step, and stop. Do not take over its work.
4. **Never edit another role's section.** Append to your own.
5. **On finish, write the handoff below your transition** — not a summary of what you did, but what
   the next role needs *decided*. Then commit.

## Agent A — verdicts (fill on finish)

*Per RM15's three-way test. The builder reads this and nothing else about the audit.*

```
report-never-repair in server.INSTRUCTIONS  ->
§2 domain rules, per bullet                 ->
the attestation contradiction (§1 ran?)     ->
refusals that SURVIVE, and why they are ours ->
refusals REPLACED, and what the tool must now do ->
DISCRIMINATOR: specified / still blocked, and by what ->
```

## Agent B — handoff (fill on finish)

```
built:
skills written:
left undone, and why:
```

---

*Appended history below. Newest last. Never rewrite an earlier entry.*

### 2026-08-19T23:56Z — agent A claims the audit

Found `READY-FOR-AUDIT`, moved to `AUDIT-RUNNING`. Running RM15 per
`docs/PRIMER-philosophy-audit.md`. Unattended run; the owner is reachable for the first ten minutes
only, which is being spent on §6's questionnaire (the attestation contradiction) because that is the
one item the primer forbids deciding alone.
