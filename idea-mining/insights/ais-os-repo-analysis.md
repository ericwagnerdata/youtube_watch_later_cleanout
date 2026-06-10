# AIS-OS repo analysis — what's worth borrowing for the command center

**Source:** https://github.com/nateherkai/AIS-OS (Nate Herk's "AI Operating System" starter kit for Claude Code)
**Access method:** `git clone --depth 1` succeeded (gh CLI not installed locally). All file contents below are read directly from the clone, not paraphrased from memory.
**Analyzed:** 2026-06-10

---

## Step 1 — Actual file tree

The repo is small (14 tracked files, ~1,200 lines total, mostly the README and one framework doc):

```
AIS-OS/
├── README.md                       (133 lines — marketing + framework overview)
├── CLAUDE.md                       (46 lines — templated operating manual, {{placeholders}})
├── EXPANSIONS.md                   (77 lines — "what to add as you grow" + anti-patterns)
├── LICENSE                         (MIT)
├── .gitignore                      (8 lines — .env, audits/, settings.local.json)
├── aios-intake.md                  (85 lines — 7-question onboarding source-of-truth)
├── connections.md                  (17 lines — 7-row registry of reachable systems)
├── context/.gitkeep                (empty — filled by /onboard)
├── archives/.gitkeep               (empty — "move old stuff here, don't delete")
├── decisions/
│   └── log.md                      (21 lines — append-only decision log + entry format)
├── references/
│   └── 3ms-framework.md            (236 lines — "the operator brain", trademarked)
└── .claude/
    └── skills/
        ├── onboard/SKILL.md        (105 lines — 7-question wizard, one-time)
        ├── audit/SKILL.md          (180 lines — Four-Cs scoreboard, recurring)
        └── level-up/SKILL.md       (160 lines — Three-Ms automation interview, weekly)
```

There are **no subagents** (`.claude/agents/` is only mentioned in EXPANSIONS as a future add), **no settings.json**, **no hooks**, **no scripts**, **no MCP config**. It is a thin template plus three thinking-skill prompts plus one big framework essay. Honest assessment: ~70% of the value is the two conceptual frameworks (Four Cs, Three Ms) and the `/audit` rubric. The rest is course-funnel scaffolding tied to Nate Herk's paid Skool community.

---

## Step 2 — The actual structure (quoted)

**The Four Cs (architecture / what you build)** — from README:

| # | Layer | "This layer is in place" test |
|---|---|---|
| 1 | **Context** | Fresh session answers "what does this business do and who works here?" without browsing |
| 2 | **Connections** | "What's on my calendar tomorrow and what tasks are due?" → live data, no paste |
| 3 | **Capabilities** | A short phrase triggers a multi-step workflow that produces an artifact |
| 4 | **Cadence** | Laptop closed. A brief lands in the inbox. A teammate messages it and gets a real answer |

> "Context is non-skippable. Connections + Capabilities can build in parallel. Cadence is last — don't automate workflows that don't work manually."

**The Three Ms (operator brain / how you think)** — Mindset → Method → Machine. Key reusable mechanics:
- **Default Shift:** before doing a task the old way, ask "to what extent can AI be leveraged here?"
- **EAD (Eliminate → Automate → Delegate), eliminate first:** "Don't automate waste."
- **Autonomy Spectrum L0–L4, default to the lowest level that works.** "Workflows beat agents."
- **Bike Method (4 phases):** training-wheels → guided → watched → hands-off. Ships `bike-method-phase: 1` into every scaffolded artifact so manual validation can't be skipped.
- **Kill Switch:** tear down automations that cost more to maintain than they save.

**The `/audit` skill** is the single most concretely useful artifact. It scores a Claude Code project 0–100 across the Four Cs (25 each), is **read-only**, detects structure by *intent not exact path* (so it works on non-canonical layouts), ranks gaps by `(points lost) × (impact multiplier)`, and prints a scoreboard with stage thresholds (Foundation / Built / Compounding / Autonomous). Notably it already knows how to find a harness `memory/` dir at `~/.claude/projects/<id>/memory/MEMORY.md`.

**`connections.md`** — a 7-row table keyed by "Tier-1 Universal Data Domains" (Revenue, Customer, Calendar, Communication, Tasks, Meetings, Knowledge) with columns Domain / Tool / Mechanism / Auth / Last-checked. Mechanism is deliberately MCP-agnostic (`mcp` | `script` | `export` | `key+ref` | `not yet connected`).

**`decisions/log.md`** — append-only, dated entries: Decision / Why / Alternatives / Owner.

**`EXPANSIONS.md`** — the best-written file in the repo. A disciplined "add a folder only when 2 of 3 yeses" gate, plus an explicit anti-pattern list (no `notes/` `misc/` `tmp/` `inbox/` graveyards; no folder-of-folders organization theater; one canonical `CLAUDE.md`; don't dump raw archives into the wiki).

---

## Step 3 — What the command center already has

| AIS-OS concept | Command-center equivalent | Verdict |
|---|---|---|
| `CLAUDE.md` router persona | `CLAUDE.md` (chief-of-staff router) | CC is **better** — real, filled, not a `{{template}}` |
| Three-Ms "operator brain" essay | `principles.md` (think/simplify/surgical/verify) | CC is **tighter**; 3Ms is richer but trademark-encumbered |
| `connections.md` registry | `projects/` registry (13 files, path + notes each) | Different axis — see gap analysis |
| `.claude/skills/` (3 thinking skills) | `.claude/agents/` (7 subagents) + `.claude/commands/` (plan-week) | CC is **better** — real agents, not prompt stubs |
| harness memory mention | actual `memory/MEMORY.md` with ~20 curated entries | CC is **far ahead** |
| `decisions/log.md` | none | **GAP** |
| `EXPANSIONS.md` growth/anti-pattern guide | none (`projects/README.md` covers registry only) | **GAP** |
| `/audit` Four-Cs scoreboard | `repo-auditor` subagent (audits *other* repos, not self) | **GAP** (no self-audit) |

Eric's repo is the more mature orchestration layer. AIS-OS is a Day-1 starter template; the command center is a running operation. So most of AIS-OS is either already covered or actively contrary to Eric's stated preferences (he won't use slash commands; AIS-OS is slash-command-first).

---

## Step 4 — Borrowable elements, ranked

### HIGH value

**1. A self-audit, as a subagent (not a slash command).**
*What it is:* AIS-OS `/audit` — a read-only Four-Cs health check that scores the AIOS and ranks gaps by leverage.
*CC status:* `repo-auditor` audits *other* repos. Nothing audits the command center itself or asks "is my orchestration layer drifting?"
*Recommendation — ADAPT.* Add a `command-center-auditor` subagent (or fold a mode into `repo-auditor`) that reads `CLAUDE.md`, `projects/*`, `.claude/agents/*`, `memory/MEMORY.md`, and reports: stale project entries, projects in the registry but missing from `additionalDirectories` (and vice-versa), agents with no natural-language trigger, memory entries that contradict registry files. Trigger it on natural language ("audit the command center", "is anything drifting?") — no slash command. Steal the *mechanism-agnostic, intent-not-path detection* and the *gap × leverage ranking*; **drop the Four-Cs framing and the 0–100 score** (vanity metric, course-gamification). Eric's axis is "projects coordinated correctly," not "Cs filled."

**2. A decisions log.**
*What it is:* `decisions/log.md` — append-only, dated, captures the *why* (Decision / Why / Alternatives / Owner).
*CC status:* missing. Decisions currently live implicitly in `memory/` (auto-accumulated) and scattered project notes.
*Recommendation — ADOPT, lightly.* Add `decisions/log.md` at the command-center root with the same terse format. This is the one piece of durable state the registry + auto-memory don't cleanly hold: *why* a call was made and what would change his mind (e.g. "comp floor lowered to $160K — 2026-06-09 — because…"). Memory is for facts; this is for reversible judgment calls. Append manually; have the chief-of-staff suggest logging when Eric makes a real decision. Keep it one file, not a folder, unless it grows.

### MEDIUM value

**3. An EXPANSIONS-style "how this repo grows" + anti-pattern guide.**
*What it is:* `EXPANSIONS.md` — when to add a folder (2-of-3-yeses gate) and an explicit list of structures that rot the repo.
*CC status:* `projects/README.md` documents the registry but there's no repo-wide "don't add `notes/`/`misc/`, don't fork CLAUDE.md, flat-beats-nested" discipline doc.
*Recommendation — ADAPT into `principles.md` or a short `STRUCTURE.md`.* Eric's `principles.md` already says "simplicity first / surgical changes" for *code*; AIS-OS's anti-patterns are about *repo structure* and complement it well. Borrow specifically: the "2 yeses to add a folder" gate, "flat with good naming beats deep nesting," "no graveyard folders," "one canonical CLAUDE.md (sub-folders can have scoped ones)." This directly reinforces Eric's anti-bloat instinct. Skip the trademark/marketing framing. **MEDIUM** because it's a nice-to-have guardrail, not a missing capability.

**4. The `connections.md` domain registry — but only for live data tools, not projects.**
*What it is:* a table of which real-world systems the OS can reach, by what mechanism, with a freshness column.
*CC status:* the `projects/` registry tracks *repos/folders*; there's no single view of *live integrations* (Todoist API, Gmail/Calendar MCP, Google Drive, the Anthropic key). These are scattered across project files.
*Recommendation — ADAPT, only if it earns its place.* Eric already has Gmail/Calendar/Drive MCPs and a Todoist pipeline wired in. A one-page `connections.md` (Tool / Mechanism / Auth state / Last-checked) would give the chief-of-staff a single answer to "what can I actually reach right now?" Borrow the **mechanism-agnostic column** (mcp/script/export/key+ref). **Skip the 7 Tier-1 domains** as a forced template — list only what's real. **MEDIUM**, leaning LOW, because the value is small until he has >5 integrations; don't pre-build the empty table (that's exactly the "premature folder" anti-pattern AIS-OS itself warns against).

### LOW value / SKIP

**5. The `/onboard` 7-question wizard — SKIP.** It's a Day-1 cold-start tool to populate an empty template. Eric's command center is already populated and evolves through use + auto-memory. The one transferable idea — *refuse typed-in voice samples, demand pasted raw writing* — is genuinely smart but already covered by his `writing-style.md` memory + career-ops voice handling. No action.

**6. The Four Cs / Three Ms frameworks as docs — SKIP as files, KEEP a few mental tools.** Both are trademarked ("™ Nate Herk, © 2026") and the README explicitly says "don't repackage as your own." More importantly, importing a 236-line operator-brain essay into a repo whose whole ethos is "minimum markdown, no speculative complexity" would be self-contradicting. **Do** keep three lightweight habits in the chief-of-staff's behavior (they cost nothing and match Eric's bias): *eliminate-before-automate*, *default to the lowest autonomy level that works / workflows beat agents*, and the *kill switch* (tear down automations that cost more than they save). These already echo `principles.md`; no new files needed.

**7. `/level-up` weekly automation interview — SKIP.** It's a slash-command ritual that produces one automation per week. Eric explicitly won't use slash commands and prefers natural-language triggers. The *spirit* (surface one manual-task-done-3x, scope it, ship the smallest version) is worth having the chief-of-staff do opportunistically, but as a behavior, not a `/level-up` skill. His existing `plan-week` command already occupies the "weekly ritual" slot.

**8. `archives/` `.gitkeep` convention — SKIP.** Premature empty folder; AIS-OS's own EXPANSIONS warns against pre-creating folders. Add an archive only when something needs archiving.

---

## Structural gaps Eric is genuinely missing (the headline)

Two, both real and both cheap:

1. **No self-audit / drift-check.** Everything audits outward (repo-auditor) or accumulates passively (memory). Nothing periodically asks "is the command center itself still wired correctly — registry vs. settings in sync, agents still triggerable, memory not contradicting the registry?" → add a `command-center-auditor` subagent.

2. **No decisions log.** Reversible judgment calls (comp floor, which projects are dormant, why a tool was disabled) live implicitly in auto-memory, which is for facts, not for *"here's the call and what would reverse it."* → add `decisions/log.md`.

Everything else AIS-OS offers, the command center already does as well or better.

## What to ignore as course-funnel / marketing bloat

- The README's "litmus test," "three felt success indicators," and "company AI-readiness → team rollout" narrative — sales copy for the Skool community, no engineering content.
- The trademarked Four-Cs / Three-Ms branding and the "companion masterclass video" hooks.
- The `bike-method-phase`/`three-ms-attribution` YAML headers that `/level-up` injects into every artifact — attribution plumbing for Nate's IP, not useful to Eric.
- The "Branch Frameworks (future hooks)" list at the end of 3ms-framework.md — a teaser table of unbuilt frameworks.

## Bottom line

AIS-OS is a **thin, well-marketed Day-1 template** wrapped around two genuinely-good conceptual frameworks and one genuinely-good tool (the `/audit` rubric). For Eric — who is already past Day 1 and runs a more mature orchestration layer — the only concrete imports worth making are a **self-audit subagent** (adapt the audit's intent-detection + leverage-ranking, drop the score) and a **decisions log** (adopt nearly verbatim). Optionally borrow the **anti-pattern discipline** from EXPANSIONS into `principles.md`. Skip everything slash-command-driven, everything trademarked, and every empty starter folder — all three conflict with how Eric actually works.
