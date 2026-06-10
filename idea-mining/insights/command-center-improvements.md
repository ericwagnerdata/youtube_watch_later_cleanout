# Command-center improvements — from the Nate Herk "AIOS / second brain" videos

Source: `8QQ_INxAhRs` (second brain) + `0WDkwMxj13s` (Opus 4.8 operating system),
both by Nate Herk (AI Automation). n8n cluster covered separately in
[n8n-videos-extract.md](n8n-videos-extract.md).

Bottom line: these two videos mostly **validate** the command center's existing design.
Nate's whole pitch (a chief-of-staff agent over a markdown "router" that points to
projects, subagents, and skills, improved a little every day) is already what this repo
is. The genuinely additive stuff is small, and a couple of his headline moves are wrong
for Eric specifically. Below: what to adopt, what to skip, and the honest reasoning.

## The big question: "all repos inside the command center" (his "other worlds")

Nate moves full Claude Code projects into one folder (`other worlds/`) inside his main
OS repo. His three stated reasons:
1. **Sync** — push one repo to GitHub, pull on the laptop, instead of pushing six.
2. **Reach** — the main OS can `cd` into any project and work on it.
3. **One source of truth** — no scavenger hunt for "where did I put that."

**Recommendation: do NOT physically nest the repos.** Eric already has the *valuable*
part (reasons 2 and 3) without the cost:

- `additionalDirectories` in `.claude/settings.json` already lets the command center
  read, edit, and `cd` into every wired-in project. Reach: already solved.
- The `projects/` registry is a **better** version of Nate's "I keep docs on where each
  project lives" — it's the explicit map that lets Claude find and `cd` to anything.
  Source of truth: already solved, and version-controlled.
- The costs of literally nesting them are real for Eric and not for Nate: his projects
  span **different drives and sync roots** (OneDrive, `G:/My Drive`, business folders),
  several are **independent git repos with their own remotes** (career-ops,
  todo_command_center), and some aren't repos at all. Nesting = nested-git / submodule
  mess + OneDrive-vs-Google-Drive sync conflicts + polluting a "no app code" orchestration
  repo with everything.
- Nate's reason #1 (one-push sync) only helps because his sub-projects probably aren't
  independent repos. Eric's already push independently, which is fine and arguably better.

So: Eric is already running the smart version of "other worlds." The only follow-through
worth doing is **making sure every active project's path is in the registry** so Claude
reliably finds and `cd`s to it (it currently is).

## Worth adopting (small, high-signal)

1. **Reactive prompting / iterate the brief on failure.** Don't pre-write giant agent
   prompts. Add a corrective rule or example only after you watch a subagent get it
   wrong, then "update the brief so this never happens again." Already the spirit of
   `principles.md`; make it an explicit habit for the `.claude/agents/` files.

2. **Reverse-engineer workflows into reusable units.** After a session does something
   well end-to-end, ask "what did we do to get here?" and capture it. For Eric the
   vehicle is a **subagent or a natural-language trigger**, NOT a slash command he has
   to remember (see his standing preference). This is how `job-scout`, `todoist`, etc.
   already came to be — keep doing it deliberately.

3. **A "grill me" / interview behavior.** Nate's most useful skill: have the agent
   interview you with 15-30 questions to pull knowledge out of your head into the
   system. Maps directly onto how memories + registry entries should get richer. Could
   be a natural-language trigger ("grill me about X") rather than a command.

4. **Try the built-in `/insights` report.** Nate claims Claude Code has a built-in
   `/insights` that scans local sessions and outputs an HTML "what's working / quick
   wins / features to try" report. Worth running once to see if it surfaces real
   improvements. (Claimed built-in — verify before relying on it.)

5. **Per-subagent model selection.** Run cheap triage/lookup subagents on Haiku,
   research/writing/judgment on Opus. Check whether the `.claude/agents/` files set a
   model; set the cheap ones explicitly.

6. **"Keys not prompts" — scope what agents can DO, not just what you tell them.** His
   cautionary tale: an agent auto-sent a discount email to 150K people because it *could*.
   A prompt is never a permission layer. Eric's instinct is already here (application-
   writer is "generate, never submit"). As cadence/automation grows (hooks, scheduled
   scans), keep gating anything that **sends or publishes** behind a real capability
   boundary, not just an instruction.

## Skip (cost > value for Eric)

- **Physically nesting all repos** — see above.
- **A fancy AIOS dashboard / Obsidian graph** — Nate himself skips it; only build a view
  when it moves a real metric. (Eric's purpose-built HTML dashboards like `todoist.html`
  are different and fine.)
- **The one-shot relationship-map HTML** — cute demo, no durable value.
- **Heavy cadence/automation right now** — "earn it"; automate only battle-tested
  workflows, and only where it moves the northstar.
- **Slash-command-heavy skills** — Nate's #1 feature is exactly the thing Eric has
  chosen not to depend on. Adopt the *value* (captured, iterated workflows) via subagents
  + natural-language triggers instead.

## Already doing it (validation, no action)

CLAUDE.md as a router; registry as the map; subagents for delegation; compounding memory;
verify-the-work (principles + resume-critic); generate-never-submit permission instinct;
"context is king" (jobs.tsv + registry over vector DBs). The videos are a sanity check
that the architecture is sound.
