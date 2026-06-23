# CoC Upgrade Tracker

A Clash of Clans upgrade scheduler + GNOME Shell desktop widget.

This project takes your village's current state (which buildings/heroes/troops you have and at what level), reads game data to figure out what every upgrade costs and requires, then uses Google's OR-Tools CP-SAT solver to compute the **optimal order** to upgrade everything. The result is a schedule that minimizes the total real-world time to max your village.

The GNOME Shell extension reads that schedule and shows you a live desktop widget with progress bars for each of your 5 builders, 1 laboratory, and 1 pet house.

---

## Table of Contents

- [What problem does this solve?](#what-problem-does-this-solve)
- [What you need](#what-you-need)
- [Quick start](#quick-start)
- [Step-by-step setup](#step-by-step-setup)
- [How to use it daily](#how-to-use-it-daily)
- [How the widget works](#how-the-widget-works)
- [How the pipeline works](#how-the-pipeline-works)
- [Project file reference](#project-file-reference)
- [Configuration reference](#configuration-reference)
- [Troubleshooting](#troubleshooting)
- [Uninstall](#uninstall)
- [Development](#development)

---

## What problem does this solve?

In Clash of Clans, you have **5 builders**, **1 laboratory**, and **1 pet house**. Each upgrade takes a certain amount of time and has prerequisites (e.g. you need Town Hall level 10 before upgrading Barracks to level 12). Deciding which builder should do what and in which order to minimize total time is a hard scheduling problem.

This project formulates it as a **resource-constrained project scheduling problem (RCPSP)** and solves it optimally using CP-SAT. The result tells you exactly which task each builder should work on, in what order, and when it will finish.

---

## What you need

- **GNOME Shell** 45–50 (run `gnome-shell --version` to check)
- **Python** 3.11+
- **pip packages**: `ortools` (`pip install ortools`)
- **System packages** (for the widget):
  - Ubuntu/Debian: `sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-4.0 gir1.2-adw-1`
  - Fedora: `sudo dnf install python3-gobject gtk4 libadwaita`
- A **village export** JSON file (see below)

---

## Quick start

```bash
# Clone the repo anywhere you want
git clone <repo-url> ~/coc-tracker
cd ~/coc-tracker

# Install dependencies
pip install ortools

# Install the GNOME Shell extension (creates a symlink)
bash install.sh

# Reload GNOME Shell: press Alt+F2, type r, press Enter

# Generate your upgrade schedule
python3 run_pipeline.py village_export.json
```

After these steps the widget will appear on your desktop showing real-time progress for every builder and lab.

---

## Step-by-step setup

### 1. Clone the repository

```bash
git clone <repo-url> ~/coc-tracker
cd ~/coc-tracker
```

The path you clone into is your **repo root**. All commands in this guide assume you are in that directory. You can clone anywhere — the setup scripts derive paths automatically.

### 2. Install Python dependencies

```bash
pip install ortools
```

If you use multiple Python versions, make sure you use Python 3.11+.

### 3. Install the GNOME Shell extension

```bash
bash install.sh
```

This script:
1. Detects the repo's absolute path using the script's own location
2. Creates the directory `~/.local/share/gnome-shell/extensions/` if needed
3. Removes any previous `coc-tracker@zorro` link or folder
4. Creates a **symlink** pointing from `~/.local/share/gnome-shell/extensions/coc-tracker@zorro` to your repo
5. Runs `gnome-extensions enable coc-tracker@zorro`

A symlink means the extension lives in your repo — there is no copy. Any changes you make to the files are reflected immediately.

**Extension identity:**
- UUID: `coc-tracker@zorro`
- Display name: "CoC Upgrade Tracker"
- Supported GNOME Shell versions: 45–50

### 4. Reload GNOME Shell

Press **Alt+F2**, type **r**, press **Enter**. The widget is not visible yet because no `schedule.json` exists — it will appear after step 5.

If you are on **Wayland** (most modern distros), the Alt+F2 → r trick may not work. In that case, log out and log back in.

### 5. Generate your upgrade schedule

```bash
python3 run_pipeline.py village_export.json
```

This reads `village_export.json` (your village's current state) and the game data in `clash-of-clans-data/`, generates all possible upgrades, runs the CP-SAT solver, and writes the optimal schedule to `schedule.json`.

**Output example:**
```
Loaded metadata for 121 items
Generated 676 tasks
Solver complete: 676 tasks scheduled, makespan: 549.0 days
```

After this completes, the widget will read `schedule.json` and display the schedule on your desktop.

---

## How to use it daily

### When you start an upgrade

1. Look at the widget — idle resources show a **"▶ Start"** button next to the next recommended task
2. Click **"▶ Start"** — the widget records the start time and begins a live countdown
3. The progress bar fills in real-time, updating every 5 seconds

### When an upgrade finishes

1. The widget automatically detects completion (the task's elapsed time reaches its duration)
2. It **patches your `village_export.json`** — increments the upgraded building's level
3. It **re-runs the pipeline** to generate an updated schedule
4. The builder is now shown as idle with the next task ready to start

### Manual control

- **"✓ Complete Now"** — mark a running task as finished immediately (useful if you forgot to track start time)
- **"✕ Cancel"** — cancel a running task and return to idle
- **"✏ Edit Time"** — adjust remaining time on a running task (e.g. if you started it hours ago but forgot to log it)
- **"… Other" / "… Other"** — assign any available task from any resource to a free builder (overrides the schedule)

### Recalculate manually

Click **"⟳ Recalc"** in the widget header to re-run the pipeline and generate a fresh schedule.

---

## How the widget works

The extension (`extension.js`) is a GNOME Shell widget that:

1. **Reads `schedule.json`** — the output of the Python pipeline
2. **Groups tasks by resource** — BUILDER 1–5, LAB 1, PET 1
3. **Tracks state per resource** — idle (no task started), active (task in progress), done (task elapsed)
4. **Shows a progress bar** for active tasks with remaining time
5. **Polls every 5 seconds** via `GLib.timeout_add_seconds`
6. **Auto-completes tasks** when their timer expires, then re-runs the pipeline

**State persistence** — The extension stores:
- `state.json` — task start timestamps per resource
- `overrides.json` — manually assigned tasks
- `pos.json` — widget position on screen

These files live in the extension's own directory (your repo root). They are cleaned up by `uninstall.sh`.

---

## How the pipeline works

### Step-by-step

```
village_export.json      clash-of-clans-data/data/home/
        |                           |
        v                           v
  [generate_tasks()] ←── [parse_all_metadata()]
        |
        v
  all possible upgrades (DAG)
        |
        v
  [solve_exact()]  ←── OR-Tools CP-SAT
        |
        v
  schedule.json (optimal order + timing)
```

1. **Metadata parsing** (`parsers/`) — Scans game data JSON files in `clash-of-clans-data/data/home/` to extract every upgradable item's name, data ID, levels, durations, and prerequisites (town hall level, lab level, etc.)
2. **Task graph generation** (`task_generator.py`) — Given your village's current levels, generates all upgrade tasks that are not yet complete. Each building/troop/pet can have multiple sequential levels, and each level has dependencies on infrastructure levels
3. **CP-SAT optimization** (`exact_scheduler.py`) — Assigns tasks to machines (builders/lab/pet house) with:
   - **Machine capacity**: 5 builders, 1 lab, 1 pet house
   - **Precedence constraints**: level N must finish before level N+1 starts
   - **Infrastructure constraints**: e.g. Lab L10 required before researching L8 troops
   - **No overlap**: a machine can only work on one task at a time
   - **Objective**: minimize makespan (total days to complete everything)
4. **Output** (`schedule.json`) — Structured JSON with tasks grouped by machine, sorted by start time, with friendly names and durations

### Resource types

| Resource | Machines | What it upgrades |
|----------|----------|------------------|
| BUILDER | 5 | Buildings, defenses, heroes, traps, walls |
| LAB | 1 | Troops, spells, siege machines |
| PET | 1 | Pets |

---

## Project file reference

### Top-level files

| File | Purpose |
|------|---------|
| `extension.js` | GNOME Shell extension — the desktop widget (811 lines) |
| `metadata.json` | GNOME Shell extension metadata (UUID, version, Shell version compatibility) |
| `stylesheet.css` | Widget styling (colors, fonts, spacing) |
| `config.json` | Extension configuration — paths, resource order |
| `install.sh` | Creates the GNOME Shell extension symlink |
| `uninstall.sh` | Removes the extension, disables it, cleans up runtime files |
| `README.md` | This file |

### Python core

| File | Purpose |
|------|---------|
| `run_pipeline.py` | End-to-end pipeline: metadata → tasks → solve → schedule.json |
| `exact_scheduler.py` | CP-SAT solver using Google OR-Tools |
| `task_generator.py` | Generates the DAG of all possible upgrades from village state and metadata |
| `models.py` | Data classes: `Task`, `TaskSchedule`, `ResourceType`, `NormalizedLevel`, `NormalizedTaskMetadata` |
| `config.py` | Configurable settings: machine counts, paths, solver parameters, environment |
| `logging_utils.py` | Structured logging classes for pipeline, validation, and analysis |
| `validation.py` | Input/output validators: village export, metadata, schedule, file paths, dependencies |
| `cache.py` | Caching system for metadata, tasks, and schedules (pickle-based, TTL support) |
| `backup.py` | Backup/restore for village data and config before pipeline runs |
| `__init__.py` | Package marker |

### Parsers (`parsers/`)

| File | Purpose |
|------|---------|
| `__init__.py` | Exports `parse_all_metadata()` |
| `builder_parser.py` | Parses building/defense/hero/trap/wall JSON files → `NormalizedTaskMetadata` |
| `lab_parser.py` | Parses troop/spell/siege JSON files → `NormalizedTaskMetadata` |
| `pet_parser.py` | Parses pet JSON files → `NormalizedTaskMetadata` |
| `utils.py` | Shared utilities: `load_json_clean()`, `extract_duration()`, `parse_count_by_th()` |

### Data files

| File | Purpose |
|------|---------|
| `village_export.json` | Your village's current state (you provide this) |
| `schedule.json` | Generated optimal schedule (pipeline output) |
| `clash-of-clans-data/` | Game data files (required, contains upgrade costs/requirements) |

---

## Configuration reference

### Extension config (`config.json`)

This file controls what the GNOME Shell widget reads and runs. All paths can be relative (resolved against the repo root) or absolute.

| Key | Default | Description |
|-----|---------|-------------|
| `schedule_file` | `schedule.json` | Path to the generated schedule JSON |
| `village_file` | `village_export.json` | Path to the village export JSON (used for auto-patching on completion) |
| `python_path` | `/usr/bin/python3` | Path to the Python 3 interpreter |
| `pipeline_script` | `run_pipeline.py` | Path to the pipeline entry point |
| `pipeline_cwd` | `.` | Working directory for pipeline subprocess |
| `resource_order` | `[BUILDER 1-5, LAB 1, PET 1]` | Order in which resource cards appear in the widget |

### Pipeline config (`pipeline-config.json` or environment variables)

The Python pipeline reads configuration from `pipeline-config.json` if it exists, falling back to defaults. Alternatively, you can override values via environment variables prefixed with `COC_`.

| Setting | Env var | Default | Description |
|---------|---------|---------|-------------|
| `machine.builder_count` | `COC_BUILDER_COUNT` | 5 | Number of builders |
| `machine.lab_count` | `COC_LAB_COUNT` | 1 | Number of laboratories |
| `machine.pet_count` | `COC_PET_COUNT` | 1 | Number of pet houses |
| `paths.data_dir` | `COC_DATA_DIR` | `clash-of-clans-data/data/home` | Game data files location |
| `paths.schedule_file` | `COC_SCHEDULE_FILE` | `schedule.json` | Output path for schedule |
| `paths.village_export_file` | `COC_VILLAGE_FILE` | `village_export.json` | Input village export |
| `solver.time_limit_seconds` | `COC_SOLVER_TIME_LIMIT` | 180 | Max seconds the solver runs |
| `solver.target_gap_percentage` | `COC_SOLVER_GAP` | 0.5 | Stop early when gap is below this % |
| `environment` | `COC_OPTIMIZER_ENV` | `development` | `development`, `production`, or `testing` |
| `logging.level` | — | `INFO` | Log level |
| `logging.file` | — | (none) | Log file path |

Example `pipeline-config.json`:
```json
{
    "machine": {
        "builder_count": 6,
        "lab_count": 2
    },
    "solver": {
        "time_limit_seconds": 300
    }
}
```

---

## Troubleshooting

### "Extension not found in GNOME Extensions app"

Run `bash install.sh` from inside the repo directory, then reload GNOME Shell.

### "Error: Village export file not found"

Make sure you have a `village_export.json` file in the repo root. You can get one from the Clash of Clans API or use the sample one included.

### "Error: Data directory not found"

The `clash-of-clans-data/` directory must be present. If you cloned without `--recurse-submodules`, it might be empty. Run:
```bash
git submodule update --init --recursive
```
Or download the game data files from the Clash of Clans developer portal.

### "No tasks generated"

Your village export might show everything already maxed, or the data directory might be pointing to the wrong location. Check `data_dir` in `pipeline-config.json`.

### Widget shows "schedule.json not found"

You haven't run the pipeline yet, or the pipeline failed. Run:
```bash
python3 run_pipeline.py village_export.json
```

### Widget doesn't appear after reload

Open the GNOME Extensions app and make sure "CoC Upgrade Tracker" is enabled. If it's not listed, run `bash install.sh` again.

---

## Uninstall

```bash
bash uninstall.sh
```

This removes:
1. The extension symlink at `~/.local/share/gnome-shell/extensions/coc-tracker@zorro`
2. Disables the extension
3. Removes runtime state files: `state.json`, `overrides.json`, `pos.json`, `cache/`
4. Removes any cached data at `~/.cache/gnome-shell/extensions/coc-tracker@zorro/`

The Python files and game data are not deleted — just the extension registration and runtime artifacts.

---

## Development

### Running tests

```bash
python3 -m unittest discover tests
```

### Project conventions

- Python files use `Path(__file__).parent` for self-relative path resolution — no hardcoded paths
- Extension paths in `config.json` are relative; `extension.js` resolves them with `GLib.build_filenamev`
- Logging goes to stdout via `logging_utils.py`
- Caching is opt-in and stored in `cache/` directory

### Adding a new parser

1. Create a new file in `parsers/` (e.g. `spell_parser.py`)
2. Implement a function that returns `list[NormalizedTaskMetadata]`
3. Add a call in `parsers/__init__.py`'s `parse_all_metadata()`

---

## License

MIT
