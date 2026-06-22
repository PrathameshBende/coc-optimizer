# Clash of Clans Upgrade Optimizer

A CP-SAT-based scheduler that computes the **optimal upgrade order** for a Clash of Clans village. Given a village export, the project builds a task graph of all possible upgrades (buildings, lab research, pets), resolves infrastructure dependencies, and solves the resource-constrained project scheduling problem to minimize the total makespan (real-world days to max).

## How It Works

1. **Metadata Parsing** – Reads game data files (`clash-of-clans-data/data/home/`) to extract upgrade durations and prerequisite requirements per building, troop, spell, siege machine, and pet.
2. **Village State** – Loads a JSON village export (e.g. from Clash of Clans API) to determine current levels and upgrade timers.
3. **Task Graph Generation** – Produces a DAG where each node is a single upgrade step. Dependencies encode:
   - Sequential levels (must upgrade Ln before Ln+1)
   - Infrastructure requirements (e.g. Lab L10 needed for troop L8)
4. **CP-SAT Optimization** – Uses Google OR-Tools to assign tasks to machines (5 builders, 1 lab, 1 pet house) and find the schedule with the minimum makespan.
5. **GTK UI** – A simple Adwaita-based window showing the current schedule with recalculation support.

## Project Structure

```
optimizer/
├── main.py                  # Entry point for JSON task scheduling (test cases)
├── scheduler.py             # Orchestrator for the exact solver (uses old parser.py)
├── exact_scheduler.py       # CP-SAT solver (OR-Tools) with progress callback
├── simulator.py             # (Deprecated) Older copy of exact_scheduler logic
├── task_generator.py        # Builds the unified upgrade task graph
├── models.py                # Data classes: Task, TaskSchedule, ResourceType, NormalizedLevel, etc.
├── run_pipeline.py          # End-to-end pipeline: metadata → tasks → solve → schedule.json
├── analyze_limits.py        # Analyzes total workload and theoretical lower bounds
├── validate_schedule.py     # Validates a computed schedule for dependency violations
├── critical_path.py         # Computes critical path lengths (CPL) for each task
├── parsers/
│   ├── __init__.py          # parse_all_metadata() entry point
│   ├── builder_parser.py    # Parses building/hero/defense JSONs → NormalizedTaskMetadata
│   ├── lab_parser.py        # Parses troops/spells/siege JSONs → NormalizedTaskMetadata
│   ├── pet_parser.py        # Parses pet JSONs → NormalizedTaskMetadata
│   └── utils.py             # Shared: load_json_clean(), extract_duration(), parse_count_by_th()
├── ui/
│   └── widget.py            # GTK4/Adwaita desktop UI for schedule visualization
├── test_cases/
│   ├── simple.json          # 3 independent tasks, 2 machines
│   ├── complex.json         # 15 tasks with chains, 5 machines
│   └── chains.json          # 3 sequential tasks, 1 machine
├── schedule.json            # Generated schedule output (JSON for UI)
├── village_export.json      # Example village export
├── parsed_metadata.json     # Cached normalized metadata
├── coc-tracker.tar.gz       # Extension file compressed (GNOME Shell extension)
└── clash-of-clans-data/     # Game data files (gitignored submodule/checkout)
```

## Installation

Requires Python 3.11+ and OR-Tools.

### Optional: GNOME Shell Extension

The `coc-tracker.tar.gz` file contains a GNOME Shell extension for Clash of Clans tracking. To install:

```bash
# Extract and install the extension
tar -xzf coc-tracker.tar.gz
cd coc-tracker
./install.sh
```

This extension provides additional Clash of Clans game data integration and tracking features.

```bash
# Clone the repo
git clone <repo-url>
cd optimizer

# Install dependencies
pip install ortools

# (Optional) For the GTK UI
# Ubuntu/Debian:
sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-4.0 gir1.2-adw-1
# Fedora:
sudo dnf install python3-gobject gtk4 libadwaita
```

## Usage

### 1. Run the full pipeline

```bash
python run_pipeline.py village_export.json [path_to_data_dir]
```

The data directory defaults to `clash-of-clans-data/data/home`. Output is written to `schedule.json`.

### 2. Analyze workload limits

```bash
python analyze_limits.py village_export.json [path_to_data_dir]
```

Shows total upgrade hours per resource type and theoretical minimum makespan.

### 3. Validate a schedule

```bash
python validate_schedule.py village_export.json [path_to_data_dir]
```

### 4. Run on simple test cases

```bash
python main.py test_cases/simple.json
python main.py test_cases/chains.json
python main.py test_cases/complex.json
```

### 5. Launch the GTK UI

```bash
python ui/widget.py
```

## Resource Types & Machine Counts

| Resource | Machines | Description |
|----------|----------|-------------|
| `BUILDER` | 5 | Building upgrades, hero upgrades, traps |
| `LAB` | 1 | Troop, spell, and siege machine research |
| `PET` | 1 | Pet upgrades |

## Configuration

Machine counts are defined in `run_pipeline.py` and `validate_schedule.py` as a `MACHINE_COUNTS` dict. The solver time limit defaults to 180 seconds (pipeline) or 120 seconds (validation) and can be adjusted via the `time_limit_seconds` parameter in `solve_exact()`.

## Dependencies

- **ortools** – Google OR-Tools CP-SAT solver
- **Python 3.11+** – Uses `pathlib`, `dataclasses`, `enum`
- **PyGObject / GTK4 / Adwaita** – (optional) for the UI widget

## Known Issues

- `scheduler.py` imports `parser` module that only exists as bytecode (`parser.py` source is missing). This file is used only by `main.py` for test-case scheduling; the full pipeline uses `run_pipeline.py` instead.
- Multiple files contain hardcoded absolute paths to `/home/zorro/Projects/optimizer/` — see the file path audit section below.

## Hardcoded File Paths

| File | Line | Hardcoded Path |
|------|------|----------------|
| `ui/widget.py` | 18 | `/home/zorro/Projects/optimizer/schedule.json` |
| `ui/widget.py` | 19 | `/home/zorro/Projects/optimizer/completed_tasks.json` |
| `ui/widget.py` | 20 | `/home/zorro/Projects/optimizer/village_export.json` |
| `ui/widget.py` | 21 | `/home/zorro/Projects/optimizer/clash-of-clans-data/data/home` |
| `ui/widget.py` | 143 | `/home/zorro/Projects/optimizer` (as `cwd`) |
| `run_pipeline.py` | 93 | `/home/zorro/Projects/optimizer/clash-of-clans-data/data/home` |
| `analyze_limits.py` | 108 | `/home/zorro/Projects/optimizer/clash-of-clans-data/data/home` |
| `validate_schedule.py` | 130 | `/home/zorro/Projects/optimizer/clash-of-clans-data/data/home` |

Additionally, `scheduler.py:3` has a stale import `from parser import parse_input` — the `parser.py` source file is missing (only `.pyc` bytecode remains), though it was the JSON test-case parser.

## Dealing with Hardcoded Paths

### Python Files
The following Python files contain hardcoded absolute paths that should be made configurable:

1. **`ui/widget.py`** (lines 18, 19, 20, 21, 143)
2. **`run_pipeline.py`** (line 93)
3. **`analyze_limits.py`** (line 108)
4. **`validate_schedule.py`** (line 130)

**Solution:** Replace hardcoded paths with relative paths or configuration variables:
- Use `pathlib.Path(__file__).parent` for paths relative to the script location
- Create a configuration system or environment variables for customizable paths
- Use `os.path.expanduser("~")` for user-specific paths

### GNOME Shell Extension
The extension in `coc-tracker.tar.gz` (`extension.js`) contains hardcoded paths (lines 9, 10, 11-12, 190). To fix:

**Solution:** 
1. Extract the extension: `tar -xzf coc-tracker.tar.gz`
2. Edit `extension.js` to use relative paths or configurable paths
3. Re-package: `tar -czf coc-tracker.tar.gz coc-tracker/`
4. Reinstall the extension

**Recommended approach:** Modify the extension to accept paths as extension settings or use relative paths from the extension's installation directory.

## Hardcoded Paths in Extension

The GNOME Shell extension in `coc-tracker.tar.gz` also contains hardcoded paths:

| File | Line | Hardcoded Path |
|------|------|----------------|
| `extension.js` | 9 | `/home/zorro/Projects/optimizer/schedule.json` |
| `extension.js` | 10 | `/home/zorro/Projects/optimizer/village_export.json` |
| `extension.js` | 11-12 | `/home/zorro/Projects/optimizer/run_pipeline.py` |
| `extension.js` | 190 | `/home/zorro/Projects/optimizer` (working directory) |

These paths are used by the extension to interact with the optimizer's pipeline and data files.