#!/usr/bin/env python3
# optimizer/ui/widget.py
# pyright: reportAttributeAccessIssue=false
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GLib, Gio
import json
import subprocess
import os
import threading

class ClashOptimizerWindow(Adw.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title="Clash Optimizer")
        self.set_default_size(450, 700)
        
        self.schedule_file = "/home/zorro/Projects/optimizer/schedule.json"
        self.completed_file = "/home/zorro/Projects/optimizer/completed_tasks.json"
        self.export_file = "/home/zorro/Projects/optimizer/village_export.json"
        self.data_dir = "/home/zorro/Projects/optimizer/clash-of-clans-data/data/home"
        
        self.build_ui()
        self.load_schedule()
        self.watch_schedule()
        
    def build_ui(self):
        # FIX: Adw.ApplicationWindow requires set_content(), not set_child()
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_content(main_box)
        
        # Header
        header = Adw.HeaderBar()
        title = Adw.WindowTitle(title="🏰 Clash Optimizer", subtitle="TH15")
        header.set_title_widget(title)
        main_box.append(header)
        
        # Scrollable Content Area
        self.content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.content_box.set_margin_top(12)
        self.content_box.set_margin_bottom(12)
        self.content_box.set_margin_start(12)
        self.content_box.set_margin_end(12)
        
        scroll = Gtk.ScrolledWindow()
        scroll.set_child(self.content_box)
        scroll.set_vexpand(True)
        main_box.append(scroll)
        
        # Bottom Buttons
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        btn_box.set_margin_top(12)
        btn_box.set_margin_bottom(12)
        btn_box.set_margin_start(12)
        btn_box.set_margin_end(12)
        
        self.recalc_btn = Gtk.Button(label="Recalculate")
        self.recalc_btn.connect("clicked", self.on_recalculate)
        self.recalc_btn.set_hexpand(True)
        
        self.mark_btn = Gtk.Button(label="Mark Complete")
        self.mark_btn.connect("clicked", self.on_mark_complete)
        self.mark_btn.set_hexpand(True)
        
        btn_box.append(self.recalc_btn)
        btn_box.append(self.mark_btn)
        main_box.append(btn_box)
        
    def load_schedule(self):
        if not os.path.exists(self.schedule_file):
            return
        try:
            with open(self.schedule_file, "r") as f:
                self.schedule = json.load(f)
            GLib.idle_add(self.update_ui)
        except Exception as e:
            print(f"Error loading schedule: {e}")
        
    def update_ui(self):
        # Clear existing content
        child = self.content_box.get_first_child()
        while child:
            self.content_box.remove(child)
            child = self.content_box.get_first_child()
            
        # Overall Status
        days = self.schedule.get("makespan_days", 0)
        status_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        status_box.set_margin_bottom(12)
        
        title_lbl = Gtk.Label(label=f"Estimated Finish: {days:.1f} days")
        title_lbl.set_css_classes(["title-1"])
        title_lbl.set_halign(Gtk.Align.START)
        status_box.append(title_lbl)
        
        self.content_box.append(status_box)
        
        # Resource Cards (Matching your Project Planner mockup)
        for resource, tasks in self.schedule.get("resources", {}).items():
            if not tasks: continue
            current = tasks[0]
            next_task = tasks[1] if len(tasks) > 1 else None
            
            # Gtk.Frame creates a nice bordered card
            card = Gtk.Frame() 
            card_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
            card_box.set_margin_top(12)
            card_box.set_margin_bottom(12)
            card_box.set_margin_start(12)
            card_box.set_margin_end(12)
            card.set_child(card_box)
            
            # Title
            title = Gtk.Label(label=f"🔨 {resource}", xalign=0)
            title.set_css_classes(["heading"])
            card_box.append(title)
            
            # Current Task
            current_label = Gtk.Label(label=f"{current['name']} → L{current['level']} ({current['duration_hours']:.0f}h)", xalign=0)
            card_box.append(current_label)
            
            # Next Task
            if next_task:
                next_label = Gtk.Label(label=f"Next: {next_task['name']} → L{next_task['level']}", xalign=0)
                next_label.set_css_classes(["dim-label"])
                card_box.append(next_label)
                
            self.content_box.append(card)
            
    def watch_schedule(self):
        if os.path.exists(self.schedule_file):
            self.file_monitor = Gio.File.new_for_path(self.schedule_file).monitor_file(Gio.FileMonitorFlags.NONE, None)
            self.file_monitor.connect("changed", lambda *args: GLib.idle_add(self.load_schedule))
        
    def on_recalculate(self, button):
        self.recalc_btn.set_sensitive(False)
        self.recalc_btn.set_label("Calculating...")
        thread = threading.Thread(target=self.run_pipeline)
        thread.start()
        
    def run_pipeline(self):
        cmd = ["python", "run_pipeline.py", self.export_file, self.data_dir]
        subprocess.run(cmd, cwd="/home/zorro/Projects/optimizer")
        GLib.idle_add(self.on_calculation_done)
        
    def on_calculation_done(self):
        self.recalc_btn.set_sensitive(True)
        self.recalc_btn.set_label("Recalculate")
        
    def on_mark_complete(self, button):
        print("Mark Complete clicked! (We will implement the searchable dialog next)")

class ClashOptimizerApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id="com.clash.optimizer")
        
    def do_activate(self):
        win = ClashOptimizerWindow(self)
        win.present()

if __name__ == "__main__":
    app = ClashOptimizerApp()
    app.run(None)