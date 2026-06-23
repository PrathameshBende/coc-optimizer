import St from 'gi://St';
import GLib from 'gi://GLib';
import Gio from 'gi://Gio';
import Clutter from 'gi://Clutter';
import Meta from 'gi://Meta';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import { Extension } from 'resource:///org/gnome/shell/extensions/extension.js';

// ── config loader ──────────────────────────────────────────────────────────
// Reads config.json from the extension directory.
// Falls back to defaults if the file does not exist or is malformed.

const DEFAULT_CONFIG = {
    schedule_file: 'schedule.json',
    village_file: 'village_export.json',
    python_path: '/usr/bin/python3',
    pipeline_script: 'run_pipeline.py',
    pipeline_cwd: '.',
    resource_order: [
        'BUILDER 1','BUILDER 2','BUILDER 3','BUILDER 4','BUILDER 5',
        'LAB 1','PET 1'
    ]
};

function _loadConfig(configDir) {
    const configPath = GLib.build_filenamev([configDir, 'config.json']);
    try {
        const [ok, contents] = GLib.file_get_contents(configPath);
        if (!ok) return DEFAULT_CONFIG;
        const parsed = JSON.parse(new TextDecoder().decode(contents));
        return Object.assign({}, DEFAULT_CONFIG, parsed);
    } catch {
        return DEFAULT_CONFIG;
    }
}

// These will be set when the extension enables — they depend on the
// extension's own installation directory so they cannot be module-level.
var SCHEDULE_PATH;
var VILLAGE_PATH;
var PIPELINE_CMD;
var PIPELINE_CWD;
var RESOURCE_ORDER;

// ── helpers ──────────────────────────────────────────────────────────────────

function readJSON(path) {
    try {
        const [ok, contents] = GLib.file_get_contents(path);
        if (!ok) return null;
        return JSON.parse(new TextDecoder().decode(contents));
    } catch { return null; }
}

function writeJSON(path, obj) {
    const data = JSON.stringify(obj, null, 2);
    GLib.file_set_contents(path, data);
}

function fmtDuration(seconds) {
    if (seconds <= 0) return 'Done';
    const d = Math.floor(seconds / 86400);
    const h = Math.floor((seconds % 86400) / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = seconds % 60;
    if (d > 0) return `${d}d ${h}h ${m}m`;
    if (h > 0) return `${h}h ${m}m`;
    if (m > 0) return `${m}m ${s}s`;
    return `${s}s`;
}

function nowSec() { return Math.floor(Date.now() / 1000); }

// ── state file (persists start timestamps) ───────────────────────────────────
// Format: { "BUILDER 1:::task_id": unixTimestamp }

function stateFilePath(extDir) {
    return GLib.build_filenamev([extDir, 'state.json']);
}

function loadState(extDir) {
    return readJSON(stateFilePath(extDir)) || {};
}

function saveState(extDir, state) {
    writeJSON(stateFilePath(extDir), state);
}

function stateKey(resource, taskId) { return `${resource}:::${taskId}`; }

// ── manual resource overrides (foreign tasks manually assigned via "Other") ──
// Stored as { resourceName: [taskObj, ...] }. Merged onto the front of that
// resource's native task list every time cards are built, since the native
// list is always freshly re-read from schedule.json on every rebuild.

function overridesFilePath(extDir) {
    return GLib.build_filenamev([extDir, 'overrides.json']);
}

function loadOverrides(extDir) {
    return readJSON(overridesFilePath(extDir)) || {};
}

function saveOverrides(extDir, overrides) {
    writeJSON(overridesFilePath(extDir), overrides);
}

function posFilePath(extDir) {
    return GLib.build_filenamev([extDir, 'pos.json']);
}

function loadPos(extDir) {
    const p = readJSON(posFilePath(extDir));
    return (p && typeof p.x === 'number') ? p : { x: 20, y: 60 };
}

function savePos(extDir, x, y) {
    writeJSON(posFilePath(extDir), { x, y });
}



// ── village_export level patching ────────────────────────────────────────────

const VILLAGE_ARRAYS = [
    'buildings','buildings2','heroes','heroes2',
    'units','units2','siege_machines','spells',
    'pets','equipment','helpers'
];

function dataIdToArrayName(dataId) {
    const prefix = Math.floor(dataId / 1000000);
    switch (prefix) {
        case 1:  return 'buildings';
        case 4:  return 'units';
        case 12: return 'traps';
        case 26: return 'spells';
        case 28: return 'heroes';
        case 73: return 'pets';
        case 90: return 'equipment';
        case 93: return 'helpers';
        default: return null;
    }
}

function patchVillageLevel(villagePath, dataId, targetLevel) {
    const village = readJSON(villagePath);
    if (!village) return false;
    let patched = false;
    let foundAnyMatch = false;
    for (const arr of VILLAGE_ARRAYS) {
        if (!village[arr]) continue;
        const matches = village[arr].filter(e => e.data === dataId);
        if (!matches.length) continue;
        foundAnyMatch = true;

        // The instance being upgraded is one currently sitting at targetLevel - 1.
        const fromLevel = targetLevel - 1;
        let fromEntry = matches.find(e => e.lvl === fromLevel);

        if (!fromEntry) {
            // No exact match at targetLevel-1 — this happens for pets/heroes
            // whose first schedulable task jumps from "unowned" (often lvl 0,
            // or simply absent from the export) straight to a level higher
            // than 1. Fall back to the entry with the highest level below
            // targetLevel, so we still correctly split/move it rather than
            // blindly incrementing whatever we find.
            const below = matches.filter(e => e.lvl < targetLevel);
            if (below.length) {
                fromEntry = below.reduce((a, b) => (a.lvl >= b.lvl ? a : b));
            }
        }

        if (!fromEntry) {
            // Still nothing usable (e.g. matches exist but all at/above
            // targetLevel already) — nothing sensible to do here, skip this
            // array rather than corrupting data.
            continue;
        }

        // Decrement (or remove) the source-level group.
        const fromCnt = fromEntry.cnt ?? 1;
        if (fromCnt > 1) {
            fromEntry.cnt = fromCnt - 1;
        } else {
            const idx = village[arr].indexOf(fromEntry);
            village[arr].splice(idx, 1);
        }

        // Increment (or create) the target-level group.
        const toEntry = village[arr].find(e => e.data === dataId && e.lvl === targetLevel);
        if (toEntry) {
            toEntry.cnt = (toEntry.cnt ?? 1) + 1;
        } else {
            village[arr].push({ data: dataId, lvl: targetLevel, cnt: 1 });
        }

        patched = true;
        break;
    }

    if (!patched && !foundAnyMatch) {
        // Nothing exists for this dataId anywhere — likely a pet/hero being
        // unlocked/owned for the first time. Create it directly at the
        // target level in the correct array based on its ID prefix.
        const arrName = dataIdToArrayName(dataId);
        if (arrName) {
            if (!village[arrName]) village[arrName] = [];
            village[arrName].push({ data: dataId, lvl: targetLevel, cnt: 1 });
            patched = true;
        }
    }

    if (patched) writeJSON(villagePath, village);
    return patched;
}

// ── pipeline runner ──────────────────────────────────────────────────────────

function runPipeline(callback) {
    try {
        const launcher = new Gio.SubprocessLauncher({
            flags: Gio.SubprocessFlags.STDOUT_PIPE | Gio.SubprocessFlags.STDERR_MERGE
        });
        launcher.set_cwd(PIPELINE_CWD);
        const proc = launcher.spawnv(PIPELINE_CMD);
        proc.communicate_utf8_async(null, null, (_proc, res) => {
            let output = '';
            try {
                const [, stdout] = _proc.communicate_utf8_finish(res);
                output = stdout || '';
            } catch (e) {
                log(`[coc-tracker] pipeline communicate error: ${e}`);
            }
            if (!_proc.get_successful()) {
                log(`[coc-tracker] pipeline exited with failure. Output:\n${output}`);
            } else {
                log(`[coc-tracker] pipeline finished OK. Output:\n${output}`);
            }
            if (callback) callback();
        });
    } catch(e) {
        log(`[coc-tracker] pipeline spawn error: ${e}`);
        if (callback) callback();
    }
}

// ── main extension ────────────────────────────────────────────────────────────

export default class CoCTracker extends Extension {
    enable() {
        this._extDir = this.path;
        this._state  = loadState(this._extDir);
        this._overrides = loadOverrides(this._extDir);
        this._schedule = null;
        this._timerSrc = null;
        this._dropdownOpen = null; // { resource, actor }
        this._pipelineRunning = false;
        this._pos = loadPos(this._extDir);

        // Load configuration and resolve paths
        const cfg = _loadConfig(this._extDir);
        const resolve = (p) => p.startsWith('/') ? p : GLib.build_filenamev([this._extDir, p]);
        SCHEDULE_PATH = resolve(cfg.schedule_file);
        VILLAGE_PATH  = resolve(cfg.village_file);
        PIPELINE_CMD  = [cfg.python_path, resolve(cfg.pipeline_script), VILLAGE_PATH];
        PIPELINE_CWD  = resolve(cfg.pipeline_cwd);
        RESOURCE_ORDER = cfg.resource_order;

        this._buildWidget();
        this._loadSchedule();
        this._startTick();
    }

    disable() {
        if (this._timerSrc) { GLib.source_remove(this._timerSrc); this._timerSrc = null; }
        if (this._widget) { this._widget.destroy(); this._widget = null; }
        this._closeDropdown();
    }

    // ── widget skeleton ──────────────────────────────────────────────────────

    _buildWidget() {
        // Root container — sits on the desktop layer
        this._widget = new St.BoxLayout({
            vertical: true,
            style_class: 'coc-widget',
            reactive: true,
            track_hover: true,
            x: this._pos.x,
            y: this._pos.y,
        });
        this._widget.set_width(260);

        // Put it below all windows but above wallpaper
        Main.layoutManager._backgroundGroup.add_child(this._widget);

        // Drag via header
        this._dragging = false;
        this._dragOffsetX = 0;
        this._dragOffsetY = 0;

        // Header
        const header = new St.BoxLayout({ style_class: 'coc-header', vertical: false });
        const title = new St.Label({ text: '⚔ CoC Tracker', style_class: 'coc-title' });
        header.add_child(title);

        // Spacer
        const spacer = new St.Widget({ x_expand: true });
        header.add_child(spacer);

        // Recalculate button
        this._recalcBtn = new St.Button({ label: '⟳ Recalc', style_class: 'coc-header-btn' });
        this._recalcBtn.connect('clicked', () => this._onRecalc());
        header.add_child(this._recalcBtn);


        // Drag handle is the title label ONLY — Recalc button keeps its own
        // click handling, completely unaffected by drag press/release events.
        title.reactive = true;
        title.track_hover = true;
        title.connect('button-press-event', (_actor, event) => {
            if (event.get_button() !== 1) return Clutter.EVENT_PROPAGATE;
            this._dragging = true;
            const [ex, ey] = event.get_coords();
            this._dragOffsetX = ex - this._widget.x;
            this._dragOffsetY = ey - this._widget.y;
            return Clutter.EVENT_STOP;
        });
        title.connect('motion-event', (_actor, event) => {
            if (!this._dragging) return Clutter.EVENT_PROPAGATE;
            const [ex, ey] = event.get_coords();
            this._widget.x = ex - this._dragOffsetX;
            this._widget.y = ey - this._dragOffsetY;
            return Clutter.EVENT_STOP;
        });
        title.connect('button-release-event', (_actor, event) => {
            if (!this._dragging) return Clutter.EVENT_PROPAGATE;
            this._dragging = false;
            this._pos = { x: this._widget.x, y: this._widget.y };
            savePos(this._extDir, this._pos.x, this._pos.y);
            return Clutter.EVENT_STOP;
        });
        this._widget.add_child(header);

        // Running label (shown during pipeline)
        this._runningLabel = new St.Label({ text: '⏳ Running optimizer…', style_class: 'coc-running-label', visible: false });
        this._widget.add_child(this._runningLabel);

        // Cards container
        this._cardsBox = new St.BoxLayout({ vertical: true, style_class: '' });
        this._widget.add_child(this._cardsBox);

        // Card actors keyed by resource name
        this._cards = {};
    }

    // ── schedule loading ─────────────────────────────────────────────────────

    _loadSchedule() {
        this._schedule = readJSON(SCHEDULE_PATH);
        this._rebuildCards();
    }

    // ── card building ────────────────────────────────────────────────────────

    _rebuildCards() {
        // Clear existing cards
        this._cardsBox.destroy_all_children();
        this._cards = {};

        if (!this._schedule) {
            const err = new St.Label({ text: 'schedule.json not found', style: 'color:#ff6666;font-size:11px;padding:6px;' });
            this._cardsBox.add_child(err);
            return;
        }

        const resources = this._schedule.resources || {};

        for (const res of RESOURCE_ORDER) {
            const nativeTasks = resources[res] || [];
            const overrideTasks = this._overrides[res] || [];
            // Override tasks go first — they're what's actually running now.
            const tasks = [...overrideTasks, ...nativeTasks];
            if (!tasks.length) continue;
            const card = this._buildCard(res, tasks);
            this._cards[res] = card;
            this._cardsBox.add_child(card.root);
        }
    }

    _buildCard(resource, tasks) {
        const root = new St.BoxLayout({ vertical: true, style_class: 'coc-card', style: 'margin-top:5px;' });

        const resLabel = new St.Label({ text: resource, style_class: 'coc-resource-label' });
        root.add_child(resLabel);

        const content = new St.BoxLayout({ vertical: true });
        root.add_child(content);

        const card = { root, content, resource, tasks, mode: null };
        this._renderCardStructure(card);
        return card;
    }

    // Rebuild the structural layout (buttons, labels) only when the card's
    // mode (idle/active/done/finished) actually changes — not every tick.
    _renderCardStructure(card) {
        const { content, resource, tasks } = card;
        const resolved = this._resolveCardState(resource, tasks);
        const { currentTask, nextTask, isIdle, isDone } = resolved;

        const mode = (!currentTask && !nextTask) ? 'allDone'
                   : isIdle ? 'idle'
                   : isDone ? 'done'
                   : 'active';

        content.destroy_all_children();
        card.mode = mode;
        card.resolved = resolved;

        if (mode === 'allDone') {
            const lbl = new St.Label({ text: 'All done ✓', style_class: 'coc-done-label' });
            content.add_child(lbl);
            card.root.style_class = 'coc-card coc-card-idle';
            return;
        }

        const task = currentTask || nextTask;

        const nameRow = new St.BoxLayout({ vertical: false });
        const nameLbl = new St.Label({
            text: `${task.name}  →  Lv ${task.level}`,
            style_class: 'coc-task-name',
            x_expand: true,
        });
        nameRow.add_child(nameLbl);
        content.add_child(nameRow);

        if (mode === 'idle') {
            card.root.style_class = 'coc-card coc-card-idle';
            const idleLbl = new St.Label({ text: 'Idle — next up:', style_class: 'coc-idle-label' });
            content.add_child(idleLbl);

            const btnRow = new St.BoxLayout({ vertical: false, style: 'spacing:6px;margin-top:3px;' });

            const startBtn = new St.Button({ label: '▶ Start', style_class: 'coc-btn-start' });
            startBtn.connect('clicked', () => this._onStart(resource, nextTask));
            btnRow.add_child(startBtn);

            const completeBtn = new St.Button({ label: '… Other', style_class: 'coc-btn-complete' });
            completeBtn.connect('clicked', () => this._onCompleteOther(resource, completeBtn));
            btnRow.add_child(completeBtn);

            content.add_child(btnRow);

        } else if (mode === 'done') {
            card.root.style_class = 'coc-card coc-card-idle';
            const doneLbl = new St.Label({ text: '✓ Finished — collect & start next', style_class: 'coc-done-label' });
            content.add_child(doneLbl);

            const completeBtn = new St.Button({ label: '… Other', style_class: 'coc-btn-complete' });
            completeBtn.connect('clicked', () => this._onCompleteOther(resource, completeBtn));
            content.add_child(completeBtn);

        } else {
            // active
            card.root.style_class = 'coc-card coc-card-active';

            const timeLbl = new St.Label({ text: '', style_class: 'coc-time-label' });
            content.add_child(timeLbl);
            card.timeLbl = timeLbl;

            const BAR_W = 220;
            const barBg = new St.Widget({
                style_class: 'coc-progress-bar-bg',
                width: BAR_W,
                height: 5,
                style: 'margin-top:4px;',
            });
            const barFill = new St.Widget({
                style_class: 'coc-progress-bar-fill',
                width: 2,
                height: 5,
            });
            barBg.add_child(barFill);
            content.add_child(barBg);
            card.barFill = barFill;
            card.barW = BAR_W;

            const actionRow = new St.BoxLayout({ vertical: false, style: 'spacing:6px;margin-top:4px;' });

            const completeNowBtn = new St.Button({ label: '✓ Complete Now', style_class: 'coc-btn-start' });
            completeNowBtn.connect('clicked', () => this._onCompleteNow(resource, task));
            actionRow.add_child(completeNowBtn);

            const cancelBtn = new St.Button({ label: '✕ Cancel', style_class: 'coc-btn-complete' });
            cancelBtn.connect('clicked', () => this._onCancel(resource, task));
            actionRow.add_child(cancelBtn);

            content.add_child(actionRow);

            const actionRow2 = new St.BoxLayout({ vertical: false, style: 'spacing:6px;margin-top:4px;' });

            const editBtn = new St.Button({ label: '✏ Edit Time', style_class: 'coc-btn-complete' });
            editBtn.connect('clicked', () => this._toggleEditPanel(card));
            actionRow2.add_child(editBtn);

            const completeBtn = new St.Button({ label: '… Other', style_class: 'coc-btn-complete' });
            completeBtn.connect('clicked', () => this._onCompleteOther(resource, completeBtn));
            actionRow2.add_child(completeBtn);

            content.add_child(actionRow2);

            // Inline edit panel — hidden until "Edit Time" is clicked.
            // Two separate boxes: days and hours.
            const editPanel = new St.BoxLayout({ vertical: false, style: 'spacing:5px;margin-top:5px;', visible: false });

            const daysEntry = new St.Entry({
                style_class: 'coc-dropdown-search',
                hint_text: 'Days',
                can_focus: true,
            });
            daysEntry.set_width(60);
            editPanel.add_child(daysEntry);

            const dLbl = new St.Label({ text: 'd', style_class: 'coc-resource-label', y_align: Clutter.ActorAlign.CENTER });
            editPanel.add_child(dLbl);

            const hoursEntry = new St.Entry({
                style_class: 'coc-dropdown-search',
                hint_text: 'Hours',
                can_focus: true,
            });
            hoursEntry.set_width(60);
            editPanel.add_child(hoursEntry);

            const hLbl = new St.Label({ text: 'h', style_class: 'coc-resource-label', y_align: Clutter.ActorAlign.CENTER });
            editPanel.add_child(hLbl);

            const saveBtn = new St.Button({ label: '✓ Set', style_class: 'coc-btn-start' });
            saveBtn.connect('clicked', () => {
                const d = parseInt(daysEntry.get_text(), 10) || 0;
                const h = parseInt(hoursEntry.get_text(), 10) || 0;
                if (d < 0 || h < 0) return;
                const totalHours = d * 24 + h;
                this._onEditTime(resource, task, totalHours);
            });
            editPanel.add_child(saveBtn);

            content.add_child(editPanel);
            card.editPanel = editPanel;
            card.editDaysEntry = daysEntry;
            card.editHoursEntry = hoursEntry;
        }
    }

    // Lightweight per-tick refresh — only updates text/width on existing
    // widgets when still in 'active' mode. Triggers a full structural
    // rebuild only when the card's mode has changed (e.g. active -> done).
    _refreshCard(card) {
        const resolved = this._resolveCardState(card.resource, card.tasks);
        const { currentTask, nextTask, isIdle, isDone } = resolved;
        const mode = (!currentTask && !nextTask) ? 'allDone'
                   : isIdle ? 'idle'
                   : isDone ? 'done'
                   : 'active';

        if (mode !== card.mode) {
            this._renderCardStructure(card);
            // Natural timer completion — auto bump level + rerun pipeline,
            // same as Complete Now, with no manual click required.
            if (mode === 'done' && currentTask && !this._pipelineRunning) {
                this._onCompleteNow(card.resource, currentTask);
            }
            return;
        }

        card.resolved = resolved;

        if (mode === 'active' && card.timeLbl && card.barFill) {
            const { elapsed, totalSec } = resolved;
            const remaining = totalSec - elapsed;
            card.timeLbl.set_text(`⏱ ${fmtDuration(Math.max(0, remaining))}`);

            const pct = Math.min(1, elapsed / totalSec);
            const fillW = Math.max(2, Math.floor(pct * card.barW));
            card.barFill.set_width(fillW);
        }
    }

    // ── state resolution ─────────────────────────────────────────────────────

    _resolveCardState(resource, tasks) {
        // Find the first task in schedule that has been started (has a timestamp)
        // If its time has elapsed → isDone. Otherwise → active.
        // If no task started → isIdle, nextTask = first task.

        for (let i = 0; i < tasks.length; i++) {
            const task = tasks[i];
            const key = stateKey(resource, task.task_id);
            if (this._state[key] !== undefined) {
                const startedAt = this._state[key];
                const totalSec = Math.round(task.duration_hours * 3600);
                const elapsed = nowSec() - startedAt;
                if (elapsed >= totalSec) {
                    // Done — next task is i+1
                    const nextTask = tasks[i + 1] || null;
                    return { currentTask: task, nextTask, elapsed, totalSec, isIdle: false, isDone: true };
                } else {
                    return { currentTask: task, nextTask: null, elapsed, totalSec, isIdle: false, isDone: false };
                }
            }
        }

        // Nothing started → idle, show first task as next
        return { currentTask: null, nextTask: tasks[0] || null, elapsed: 0, totalSec: 0, isIdle: true, isDone: false };
    }

    // ── actions ──────────────────────────────────────────────────────────────

    _onStart(resource, task) {
        const key = stateKey(resource, task.task_id);
        this._state[key] = nowSec();
        saveState(this._extDir, this._state);
        this._rebuildCards();
    }

    // Like _onStart, but also registers the task as a manual override on this
    // resource if it isn't already part of its native schedule list — needed
    // so _resolveCardState can actually find it on subsequent rebuilds, since
    // the native list is always re-read fresh from schedule.json.
    _onStartForeign(resource, task) {
        const nativeTasks = (this._schedule.resources || {})[resource] || [];
        const isNative = nativeTasks.some(t => t.task_id === task.task_id);
        if (!isNative) {
            if (!this._overrides[resource]) this._overrides[resource] = [];
            const already = this._overrides[resource].some(t => t.task_id === task.task_id);
            if (!already) {
                this._overrides[resource].push(task);
                saveOverrides(this._extDir, this._overrides);
            }
        }
        this._onStart(resource, task);
    }

    // Remove a task from a resource's manual overrides, if present.
    _clearOverride(resource, task) {
        if (!this._overrides[resource]) return;
        const before = this._overrides[resource].length;
        this._overrides[resource] = this._overrides[resource].filter(t => t.task_id !== task.task_id);
        if (this._overrides[resource].length !== before) {
            saveOverrides(this._extDir, this._overrides);
        }
    }

    _onCancel(resource, task) {
        const key = stateKey(resource, task.task_id);
        delete this._state[key];
        saveState(this._extDir, this._state);
        this._clearOverride(resource, task);
        this._rebuildCards();
    }

    _toggleEditPanel(card) {
        if (!card.editPanel) return;
        card.editPanel.visible = !card.editPanel.visible;
        if (card.editPanel.visible && card.editDaysEntry) {
            card.editDaysEntry.grab_key_focus();
        }
    }

    // Manually set remaining time on an already-started upgrade. Useful when
    // the upgrade was actually started earlier but logged late in the widget.
    // Recomputes the stored start timestamp so the existing countdown math
    // (elapsed = now - startedAt) just works without any other changes.
    _onEditTime(resource, task, hoursRemaining) {
        const key = stateKey(resource, task.task_id);
        const totalSec = Math.round(task.duration_hours * 3600);
        const remainingSec = Math.round(hoursRemaining * 3600);
        const elapsedSec = Math.max(0, totalSec - remainingSec);
        this._state[key] = nowSec() - elapsedSec;
        saveState(this._extDir, this._state);
        this._rebuildCards();
    }

    _onCompleteNow(resource, task) {
        // Clear its timer state first, then same flow as picking it from "Other"
        const key = stateKey(resource, task.task_id);
        delete this._state[key];
        saveState(this._extDir, this._state);
        this._clearOverride(resource, task);
        this._markComplete(task);
    }

    _onRecalc() {
        if (this._pipelineRunning) return;
        this._pipelineRunning = true;
        this._recalcBtn.set_label('⏳ Running…');
        this._recalcBtn.reactive = false;
        this._runningLabel.visible = true;

        runPipeline(() => {
            this._pipelineRunning = false;
            this._recalcBtn.set_label('⟳ Recalc');
            this._recalcBtn.reactive = true;
            this._runningLabel.visible = false;
            // NOTE: do NOT clear this._state here — a manual recalc doesn't
            // complete anything, so any in-progress upgrade timers should
            // keep running. _resolveCardState already falls back to idle
            // gracefully if a started task_id no longer exists in the new
            // schedule.
            this._loadSchedule();
        });
    }

    _onCompleteOther(resource, anchor) {
        // Close any existing dropdown
        if (this._dropdownOpen) { this._closeDropdown(); return; }

        const schedule = this._schedule;
        if (!schedule) return;

        // Collect all tasks from all resources as options
        const allTasks = [];
        for (const res of RESOURCE_ORDER) {
            const tasks = (schedule.resources || {})[res] || [];
            for (const t of tasks) {
                allTasks.push({ ...t, resource: res });
            }
        }
        if (!allTasks.length) return;

        // Alphabetical by name, then level ascending within same name
        allTasks.sort((a, b) => {
            const nameCmp = a.name.localeCompare(b.name);
            if (nameCmp !== 0) return nameCmp;
            return a.level - b.level;
        });

        // Build dropdown
        const dropdown = new St.BoxLayout({
            vertical: true,
            style_class: 'coc-dropdown-bg',
            reactive: true,
        });
        dropdown.set_width(250);

        // Search entry
        const searchEntry = new St.Entry({
            style_class: 'coc-dropdown-search',
            hint_text: 'Search…',
            can_focus: true,
        });
        dropdown.add_child(searchEntry);

        const scroll = new St.ScrollView({ style: 'max-height:300px;' });
        const innerBox = new St.BoxLayout({ vertical: true });
        scroll.set_child(innerBox);
        dropdown.add_child(scroll);

        const renderItems = (filterText) => {
            innerBox.destroy_all_children();
            const ft = filterText.trim().toLowerCase();
            const filtered = ft
                ? allTasks.filter(t => t.name.toLowerCase().includes(ft))
                : allTasks;

            for (const task of filtered) {
                const label = `${task.name} Lv${task.level}  (${task.resource})`;
                const item = new St.Button({ label, style_class: 'coc-dropdown-item', x_align: Clutter.ActorAlign.START });
                item.connect('clicked', () => {
                    this._closeDropdown();
                    const targetCard = this._cards[resource];
                    if (targetCard && (targetCard.mode === 'active' || targetCard.mode === 'done')) {
                        Main.notify('CoC Tracker',
                            `${resource} is already busy — cancel its current upgrade first.`);
                        return;
                    }
                    // Start a real timer on the resource card this dropdown was
                    // opened from — lets you override the schedule's original
                    // resource assignment and use whichever builder is free.
                    this._onStartForeign(resource, task);
                });
                innerBox.add_child(item);
            }
        };

        searchEntry.get_clutter_text().connect('text-changed', () => {
            renderItems(searchEntry.get_text());
        });

        renderItems('');

        // Position near anchor
        const [ax, ay] = anchor.get_transformed_position();
        dropdown.x = ax;
        dropdown.y = ay + anchor.height + 4;

        Main.layoutManager._backgroundGroup.add_child(dropdown);
        this._dropdownOpen = dropdown;
        searchEntry.grab_key_focus();
    }

    _closeDropdown() {
        if (this._dropdownOpen) {
            this._dropdownOpen.destroy();
            this._dropdownOpen = null;
        }
    }

    _markComplete(task) {
        // Parse data ID from task_id (format: "28000000_66_0")
        const dataId = parseInt(task.task_id.split('_')[0], 10);
        const patched = patchVillageLevel(VILLAGE_PATH, dataId, task.level);
        if (!patched) {
            log(`[coc-tracker] Could not patch village_export for dataId=${dataId}`);
        }
        // Re-run pipeline
        this._pipelineRunning = true;
        this._recalcBtn.set_label('⏳ Running…');
        this._recalcBtn.reactive = false;
        this._runningLabel.visible = true;

        runPipeline(() => {
            this._pipelineRunning = false;
            this._recalcBtn.set_label('⟳ Recalc');
            this._recalcBtn.reactive = true;
            this._runningLabel.visible = false;
            // NOTE: do NOT clear this._state here — other resources' running
            // timers are unaffected by this one task completing. The caller
            // (_onCompleteNow / natural-finish path) already removed this
            // specific task's own state key before calling _markComplete.
            this._loadSchedule();
        });
    }

    // ── tick loop ────────────────────────────────────────────────────────────

    _startTick() {
        this._timerSrc = GLib.timeout_add_seconds(GLib.PRIORITY_DEFAULT, 5, () => {
            for (const res of Object.keys(this._cards)) {
                this._refreshCard(this._cards[res]);
            }
            return GLib.SOURCE_CONTINUE;
        });
    }
}
