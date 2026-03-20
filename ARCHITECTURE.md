# ComputerAssist — System Architecture

> Local-only ML system that learns your personal computer behaviour patterns and automates repetitive sequences. No LLM, no cloud, individually trained per user.

---

## The Big Picture

Five data collectors → Feature Extraction → Prediction Layer (HMM → VMM → Fuzzy Pattern Store → Confidence Aggregator → Phase Gate) → Execution Layer (Training path or Executing path) → Feedback Collection → back to models.

A personal server runs in parallel: receives logs, trains HMM overnight via Baum-Welch, syncs model back every morning.

---

## Layer 1 — Input Layer

### Five Collectors (run in parallel, independently)

| Component | What it watches | How |
|---|---|---|
| **OS Events Collector** | App launches, window focus, file ops, process spawns | inotify/fanotify, evdev |
| **Shell / Terminal Collector** | Every command — before/after execution, exit code, duration, working dir | zsh `precmd` / `preexec` hooks |
| **WezTerm Collector** | Pane splits, tab creation, window events — unified view across WSL + PowerShell | WezTerm Lua API |
| **Context Signals Collector** | Battery %, wifi SSID, GPS/location, time of day, day of week | System APIs |
| **App Integrations** | Structured in-app events (browser, editor, etc.) | Community plugin API |

Context Signals matter because the same action can mean different things in different contexts — home vs work, morning vs night.

### ★ Feature Extraction Layer *(most critical component)*

Takes raw events from all five collectors and produces a **Unified Event Stream** of structured, weighted feature vectors.

Key behaviour:
- **Weight separation**: splits commands into base + args with different weights
  - `z ~/projects/myapp` → `{cmd: "z", weight: HIGH}` + `{arg: "~/projects/myapp", weight: LOW}`
  - Command name is highly predictive. Specific path varies and shouldn't dominate.
- Assigns initial **type-based base weights** to all features
- Normalises all five sources into a **consistent schema**
- Tags every event with session context

Every downstream model's quality depends entirely on this layer. Garbage in = garbage out.

---

## Layer 2 — Prediction Layer

Three models run in sequence. Order matters.

### Step 1: HMM — Hidden Markov Model

**Job:** Answer "what kind of session are you in right now?" — not predict next action.

- Receives the Unified Event Stream
- Discovers **hidden workflow states** entirely unsupervised — no labels, no predefined workflows
  - Examples: "deployment session", "coding startup sequence", "end-of-day wrap-up"
- Has its own internal per-feature dynamic weight system
- **Trained overnight on personal server** via Baum-Welch (expensive — offloaded)
- **Output:** `(current_workflow_state, confidence_%)` → fed into VMM

### Step 2: VMM — Variable-Order Markov Model *(core prediction engine)*

**Job:** Predict the user's next action.

- Receives **two inputs simultaneously:**
  1. Unified Event Stream (from Feature Extraction)
  2. HMM output: `workflow_state × confidence`
- HMM influence is automatically scaled: `effective_weight = VMM_trust_weight × HMM_confidence`
  - If HMM is 90% confident → strong context signal
  - If HMM is 35% confident → influence auto-dampens, can't corrupt VMM
- **Variable lookback depth:** learns per-context how much history matters (not a fixed N steps)
- **Continuous online learning:** updates on every single event — no retraining, no batch
- Per-pattern, per-feature dynamic weight system (see Weight System section)
- **Output:** `(predicted_next_action, probability_score)` → both go forward

### Step 3: Fuzzy Pattern Store

**Job:** Validate VMM's prediction and boost confidence if it matches a known pattern.

- Receives VMM's predicted next action
- Stores confirmed recurring sequences with per-sequence weight profiles
- **Fuzzy weighted matching:**
  - High-weight features (command name, app) → must match exactly
  - Low-weight features (specific path, arguments) → flexible
  - `z ~/projectA` and `z ~/projectB` match the same stored pattern
- **Mid-sequence bonus:** if the user has already completed the first steps of a known N-step pattern, confidence boost is especially strong
- **Output:** `pattern_boost_signal` → sent to Confidence Aggregator

### Confidence Aggregator

**Job:** Combine all signals into one final confidence score and apply the threshold.

- **Inputs:**
  - VMM probability score
  - Fuzzy Pattern Store boost (including mid-sequence bonus)
- Produces one final confidence number
- **Applies the threshold:** predictions below threshold are dropped here — nothing below threshold reaches execution
- Single decision point before any action is taken
- **Output:** above-threshold prediction + confidence → Phase Gate

### Phase Gate *(diamond node — manual decision)*

**Job:** Route predictions based on current operating mode.

- **Manual user-controlled switch** — not automated
- User flips it themselves after watching the Taskbar Widget long enough to trust prediction accuracy
- **Training Mode:** predictions go to Taskbar Widget only — never executed
- **Executing Mode:** predictions go to Suggestion UI → Executor

---

## Server Sidebar — Personal Server

Runs in parallel to the prediction layer. Completely separate from the real-time prediction loop.

```
Laptop                          Personal Server (local network, no cloud)
------                          ----------------------------------------
Feature Extraction
    │ event logs (periodic)
    └──────────────────────────► Log Shipping
                                      │
Feedback Collection                   │ ◄── training data from Feedback
    │ training data (periodic)        │
    └──────────────────────────►      │
                                      ▼
                                 HMM Batch Training
                                 (Baum-Welch, overnight)
                                      │
                                      ▼
                                 Model Sync
                                      │ updated HMM model
                                      │ (on first startup each day)
                                      ▼
                                    HMM  ◄──────────────── (back on laptop)
```

- **Log Shipping:** periodic shipment of event logs + feedback data to server
- **HMM Batch Training:** Baum-Welch on all accumulated data, overnight while laptop is off
- **Model Sync:** on first laptop startup each day, pulls fresh HMM model from server

HMM is the only model trained on the server. VMM and Fuzzy Pattern Store update continuously and locally.

---

## Layer 3 — Execution Layer

### Training Mode Path

```
Phase Gate ──► Training Mode ──► Taskbar / Topbar Widget
```

- Predictions are computed but **never executed**
- Taskbar Widget shows live prediction + confidence score
- User watches and judges accuracy before deciding to flip Phase Gate

### Executing Mode Path

```
Phase Gate ──► Executing Mode ──► Suggestion UI ──► Executor
```

- **Suggestion UI:** shows readable description of pending action sequence, cancel shortcut, 2–3 second countdown. If already mid-sequence (first steps already taken manually), can skip countdown and complete instantly.
- **Executor:** runs actions at OS level — app launches, shell commands, file operations. Injects commands into WezTerm for terminal workflows. Future: per-app actions via plugin API.

### Feedback Collection *(both paths converge here)*

Four feedback modes:

| Mode | Trigger | Signal | How system learns |
|---|---|---|---|
| **Shadow mode** | Continuous, both phases | Implicit | Compares prediction to what user actually did |
| **Accept** | User accepts suggestion | Strong positive | Updates VMM + Pattern Store |
| **Reject** | User cancels before execution | Negative | Subsequent log = ground truth for what should have happened |
| **Undo** | User undoes after execution | Negative | Subsequent log = correction |

**Key principle:** The event log always captures ground truth. The system always sees what the user actually did — no labelling required. Reject + Undo both result in the subsequent real actions being available as the correct answer.

---

## Feedback Loops

Three dashed arrows going back up from Feedback Collection:

1. **→ VMM** — immediate online weight update (happens right now, every event)
2. **→ Fuzzy Pattern Store** — confirms or invalidates stored patterns
3. **→ Log Shipping (Server)** — feedback + corrections shipped as HMM training data

One additional dashed arrow from the server:
- **Model Sync → HMM** — delivers updated model each morning

---

## Weight System *(cross-cutting — inside HMM, VMM, and Fuzzy Pattern Store)*

**Two-tier weight system:**

### Tier 1: Base weights per feature type
| Feature type | Base weight |
|---|---|
| Command name / app name | HIGH |
| Event type | MEDIUM |
| Context signals (location, time, etc.) | MEDIUM |
| Arguments / specific paths | LOW |

### Tier 2: Per-pattern adaptive weights
Each individual stored pattern learns which features actually predict it:

- If Pattern A always fires when wifi SSID = "home-network" → location weight rises *for Pattern A only*
- If Pattern B fires regardless of location → location weight stays low *for Pattern B*
- Different patterns independently discover their own predictive features

Weights update continuously from feedback (Accept → reinforce, Reject/Undo → adjust down).

This runs inside HMM, VMM, and Fuzzy Pattern Store as an independent internal system in each.

---

## Complete Edge List

### Forward (solid arrows)
```
OS Events Collector        ──► Feature Extraction
Shell/Terminal Collector   ──► Feature Extraction
WezTerm Collector          ──► Feature Extraction
Context Signals Collector  ──► Feature Extraction
App Integrations           ──► Feature Extraction

Feature Extraction  ──[Unified Event Stream]──► HMM
Feature Extraction  ──[Unified Event Stream]──► VMM
Feature Extraction  ──[event logs]────────────► Log Shipping

HMM  ──[workflow state × confidence]──► VMM
VMM  ──[prediction]───────────────────► Fuzzy Pattern Store
VMM  ──[probability]──────────────────► Confidence Aggregator
Fuzzy Pattern Store  ──[pattern boost]► Confidence Aggregator

Confidence Aggregator  ──► Phase Gate
Log Shipping           ──► HMM Batch Training
HMM Batch Training     ──► Model Sync

Phase Gate  ──[training mode]───► Training Mode
Phase Gate  ──[executing mode]──► Executing Mode

Training Mode   ──► Taskbar Widget
Executing Mode  ──► Suggestion UI
Suggestion UI   ──► Executor

Taskbar Widget  ──► Feedback Collection
Executor        ──► Feedback Collection
```

### Feedback (dashed arrows)
```
Model Sync           - - [updated model] - -► HMM
Feedback Collection  - - [↺ VMM online update] - -► VMM
Feedback Collection  - - [↺ Pattern Store update] - -► Fuzzy Pattern Store
Feedback Collection  - - [↺ training data] - -► Log Shipping
```

---

## Files in This Project

| File | Purpose |
|---|---|
| `ARCHITECTURE.md` | This file — full logic reference |
| `flowchart.html` | HTML/CSS flowchart (latest iteration) |
| `flowchart.drawio` | draw.io version (open at app.diagrams.net) |
| `flowchart_drawio.py` | Script that generates flowchart.drawio |
| `flowchart_gen.py` | Earlier Python SVG generator (abandoned) |
