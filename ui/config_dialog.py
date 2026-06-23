"""
Configuration UI for Clash of Clans Upgrade Optimizer
"""

import json
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, Gio
from pathlib import Path
import logging
from config import ConfigManager
from typing import Dict, Any

class ConfigDialog:
    """Configuration dialog for the optimizer"""
    
    def __init__(self, parent=None):
        self.parent = parent
        self.config_manager = ConfigManager()
        self.logger = logging.getLogger(__name__)
        
        # Create dialog
        self.dialog = Adw.Window(title="Configuration")
        self.dialog.set_default_size(500, 600)
        
        # Create main box
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.dialog.set_content(self.main_box)
        
        # Create notebook for tabs
        self.notebook = Gtk.Notebook()
        self.main_box.append(self.notebook)
        
        # Create tabs
        self.create_machine_tab()
        self.create_paths_tab()
        self.create_solver_tab()
        self.create_logging_tab()
        self.create_extension_tab()
        
        # Action buttons
        self.create_action_buttons()
    
    def create_machine_tab(self):
        """Create machine configuration tab"""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_margin_top(12)
        box.set_margin_bottom(12)
        box.set_margin_start(12)
        box.set_margin_end(12)
        
        # Title
        title = Gtk.Label(label="Machine Configuration", halign=Gtk.Align.START)
        title.get_style_context().add_class('title-1')
        box.append(title)
        
        # Builder count
        builder_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        builder_label = Gtk.Label(label="Builder Count:")
        builder_spin = Gtk.SpinButton.new_with_range(1, 20, 1)
        builder_spin.set_value(self.config_manager.config.machine.builder_count)
        
        builder_box.append(builder_label)
        builder_box.append(builder_spin)
        box.append(builder_box)
        
        # Lab count
        lab_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        lab_label = Gtk.Label(label="Lab Count:")
        lab_spin = Gtk.SpinButton.new_with_range(1, 5, 1)
        lab_spin.set_value(self.config_manager.config.machine.lab_count)
        
        lab_box.append(lab_label)
        lab_box.append(lab_spin)
        box.append(lab_box)
        
        # Pet count
        pet_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        pet_label = Gtk.Label(label="Pet House Count:")
        pet_spin = Gtk.SpinButton.new_with_range(1, 3, 1)
        pet_spin.set_value(self.config_manager.config.machine.pet_count)
        
        pet_box.append(pet_label)
        pet_box.append(pet_spin)
        box.append(pet_box)
        
        # Store references
        self.builder_spin = builder_spin
        self.lab_spin = lab_spin
        self.pet_spin = pet_spin
        
        # Add separator
        separator = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        box.append(separator)
        
        # Environment selection
        env_label = Gtk.Label(label="Environment:", halign=Gtk.Align.START)
        box.append(env_label)
        
        env_combo = Gtk.ComboBoxText()
        env_combo.append("development", "Development")
        env_combo.append("production", "Production")
        env_combo.append("testing", "Testing")
        env_combo.set_active_id(self.config_manager.config.environment.value)
        
        box.append(env_combo)
        
        self.env_combo = env_combo
        
        self.notebook.append(box, "Machines")
    
    def create_paths_tab(self):
        """Create paths configuration tab"""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_margin_top(12)
        box.set_margin_bottom(12)
        box.set_margin_start(12)
        box.set_margin_end(12)
        
        # Title
        title = Gtk.Label(label="File Paths", halign=Gtk.Align.START)
        title.get_style_context().add_class('title-1')
        box.append(title)
        
        # Data directory
        data_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        data_label = Gtk.Label(label="Data Directory:")
        data_entry = Gtk.Entry()
        data_entry.set_text(self.config_manager.config.paths.data_dir)
        
        data_button = Gtk.Button(label="Browse...")
        data_button.connect('clicked', self.on_browse_data_dir, data_entry)
        
        data_box.append(data_label)
        data_box.append(data_entry)
        data_box.append(data_button)
        box.append(data_box)
        
        # Schedule file
        schedule_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        schedule_label = Gtk.Label(label="Schedule File:")
        schedule_entry = Gtk.Entry()
        schedule_entry.set_text(self.config_manager.config.paths.schedule_file)
        
        schedule_box.append(schedule_label)
        schedule_box.append(schedule_entry)
        box.append(schedule_box)
        
        # Village export file
        village_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        village_label = Gtk.Label(label="Village Export File:")
        village_entry = Gtk.Entry()
        village_entry.set_text(self.config_manager.config.paths.village_export_file)
        
        village_box.append(village_label)
        village_box.append(village_entry)
        box.append(village_box)
        
        # Store references
        self.data_entry = data_entry
        self.schedule_entry = schedule_entry
        self.village_entry = village_entry
        
        self.notebook.append(box, "Paths")
    
    def create_solver_tab(self):
        """Create solver configuration tab"""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_margin_top(12)
        box.set_margin_bottom(12)
        box.set_margin_start(12)
        box.set_margin_end(12)
        
        # Title
        title = Gtk.Label(label="Solver Configuration", halign=Gtk.Align.START)
        title.get_style_context().add_class('title-1')
        box.append(title)
        
        # Time limit
        time_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        time_label = Gtk.Label(label="Time Limit (seconds):")
        time_spin = Gtk.SpinButton.new_with_range(10, 3600, 10)
        time_spin.set_value(self.config_manager.config.solver.time_limit_seconds)
        
        time_box.append(time_label)
        time_box.append(time_spin)
        box.append(time_box)
        
        # Gap percentage
        gap_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        gap_label = Gtk.Label(label="Target Gap (%):")
        gap_spin = Gtk.SpinButton.new_with_range(0.1, 50.0, 0.1)
        gap_spin.set_value(self.config_manager.config.solver.target_gap_percentage)
        
        gap_box.append(gap_label)
        gap_box.append(gap_spin)
        box.append(gap_box)
        
        # Progress callback
        progress_check = Gtk.CheckButton(label="Enable Progress Callback")
        progress_check.set_active(self.config_manager.config.solver.enable_progress_callback)
        box.append(progress_check)
        
        # Store references
        self.time_spin = time_spin
        self.gap_spin = gap_spin
        self.progress_check = progress_check
        
        self.notebook.append(box, "Solver")
    
    def create_logging_tab(self):
        """Create logging configuration tab"""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_margin_top(12)
        box.set_margin_bottom(12)
        box.set_margin_start(12)
        box.set_margin_end(12)
        
        # Title
        title = Gtk.Label(label="Logging Configuration", halign=Gtk.Align.START)
        title.get_style_context().add_class('title-1')
        box.append(title)
        
        # Log level
        level_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        level_label = Gtk.Label(label="Log Level:")
        level_combo = Gtk.ComboBoxText()
        level_combo.append("DEBUG", "Debug")
        level_combo.append("INFO", "Info")
        level_combo.append("WARNING", "Warning")
        level_combo.append("ERROR", "Error")
        level_combo.append("CRITICAL", "Critical")
        level_combo.set_active_id(self.config_manager.config.logging.level)
        
        level_box.append(level_label)
        level_box.append(level_combo)
        box.append(level_box)
        
        # Log file
        file_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        file_label = Gtk.Label(label="Log File:")
        file_entry = Gtk.Entry()
        file_entry.set_text(self.config_manager.config.logging.file or "")
        
        file_button = Gtk.Button(label="Browse...")
        file_button.connect('clicked', self.on_browse_log_file, file_entry)
        
        file_box.append(file_label)
        file_box.append(file_entry)
        file_box.append(file_button)
        box.append(file_box)
        
        # Store references
        self.level_combo = level_combo
        self.file_entry = file_entry
        
        self.notebook.append(box, "Logging")
    
    def create_extension_tab(self):
        """Create extension configuration tab"""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_margin_top(12)
        box.set_margin_bottom(12)
        box.set_margin_start(12)
        box.set_margin_end(12)
        
        # Title
        title = Gtk.Label(label="Extension Configuration", halign=Gtk.Align.START)
        title.get_style_context().add_class('title-1')
        box.append(title)
        
        # Extension enabled
        ext_enabled = Gtk.CheckButton(label="Enable GNOME Shell Extension")
        ext_enabled.set_active(self.config_manager.config.extension_enabled)
        box.append(ext_enabled)
        
        # Refresh interval
        refresh_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        refresh_label = Gtk.Label(label="Refresh Interval (seconds):")
        refresh_spin = Gtk.SpinButton.new_with_range(1, 60, 1)
        refresh_spin.set_value(self.config_manager.config.extension_refresh_interval)
        
        refresh_box.append(refresh_label)
        refresh_box.append(refresh_spin)
        box.append(refresh_box)
        
        # Notifications
        notifications = Gtk.CheckButton(label="Enable Notifications")
        notifications.set_active(self.config_manager.config.extension_notifications)
        box.append(notifications)
        
        # Store references
        self.ext_enabled = ext_enabled
        self.refresh_spin = refresh_spin
        self.notifications = notifications
        
        self.notebook.append(box, "Extension")
    
    def create_action_buttons(self):
        """Create action buttons"""
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        button_box.set_margin_top(12)
        button_box.set_margin_bottom(12)
        button_box.set_margin_start(12)
        button_box.set_margin_end(12)
        button_box.set_halign(Gtk.Align.END)
        
        # Save button
        save_button = Gtk.Button(label="Save")
        save_button.connect('clicked', self.on_save)
        button_box.append(save_button)
        
        # Cancel button
        cancel_button = Gtk.Button(label="Cancel")
        cancel_button.connect('clicked', self.on_cancel)
        button_box.append(cancel_button)
        
        self.main_box.append(button_box)
    
    def on_browse_data_dir(self, button, entry):
        """Handle data directory browse button"""
        dialog = Gtk.FileChooserDialog(
            title="Select Data Directory",
            action=Gtk.FileChooserAction.SELECT_FOLDER,
            transient_for=self.dialog
        )
        dialog.add_button("Cancel", Gtk.ResponseType.CANCEL)
        dialog.add_button("Select", Gtk.ResponseType.OK)
        
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            entry.set_text(dialog.get_filename())
        dialog.destroy()
    
    def on_browse_log_file(self, button, entry):
        """Handle log file browse button"""
        dialog = Gtk.FileChooserDialog(
            title="Select Log File",
            action=Gtk.FileChooserAction.SAVE,
            transient_for=self.dialog
        )
        dialog.add_button("Cancel", Gtk.ResponseType.CANCEL)
        dialog.add_button("Save", Gtk.ResponseType.OK)
        
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            entry.set_text(dialog.get_filename())
        dialog.destroy()
    
    def on_save(self, button):
        """Handle save button"""
        try:
            # Update machine configuration
            self.config_manager.config.machine.builder_count = int(self.builder_spin.get_value())
            self.config_manager.config.machine.lab_count = int(self.lab_spin.get_value())
            self.config_manager.config.machine.pet_count = int(self.pet_spin.get_value())
            
            # Update environment
            self.config_manager.config.environment = self.env_combo.get_active_id()
            
            # Update paths
            self.config_manager.config.paths.data_dir = self.data_entry.get_text()
            self.config_manager.config.paths.schedule_file = self.schedule_entry.get_text()
            self.config_manager.config.paths.village_export_file = self.village_entry.get_text()
            
            # Update solver configuration
            self.config_manager.config.solver.time_limit_seconds = int(self.time_spin.get_value())
            self.config_manager.config.solver.target_gap_percentage = float(self.gap_spin.get_value())
            self.config_manager.config.solver.enable_progress_callback = self.progress_check.get_active()
            
            # Update logging configuration
            self.config_manager.config.logging.level = self.level_combo.get_active_id()
            self.config_manager.config.logging.file = self.file_entry.get_text() or None
            
            # Update extension configuration
            self.config_manager.config.extension_enabled = self.ext_enabled.get_active()
            self.config_manager.config.extension_refresh_interval = int(self.refresh_spin.get_value())
            self.config_manager.config.extension_notifications = self.notifications.get_active()
            
            # Validate configuration
            if not self.config_manager.validate_config():
                dialog = Adw.MessageDialog(
                    title="Configuration Error",
                    text="Invalid configuration settings. Please check your inputs.",
                    transient_for=self.dialog
                )
                dialog.add_response("OK", "OK")
                dialog.present()
                return
            
            # Save configuration
            self.config_manager.save_config()
            
            # Show success message
            dialog = Adw.MessageDialog(
                title="Configuration Saved",
                text="Configuration has been saved successfully.",
                transient_for=self.dialog
            )
            dialog.add_response("OK", "OK")
            dialog.present()
            
            # Close dialog
            self.dialog.close()
            
        except Exception as e:
            dialog = Adw.MessageDialog(
                title="Error",
                text=f"Failed to save configuration: {e}",
                transient_for=self.dialog
            )
            dialog.add_response("OK", "OK")
            dialog.present()
    
    def on_cancel(self, button):
        """Handle cancel button"""
        self.dialog.close()
    
    def show(self):
        """Show the configuration dialog"""
        self.dialog.present()

class ConfigApp:
    """Simple application to show configuration dialog"""
    
    def __init__(self):
        self.app = Adw.Application(application_id="com.example.coc.optimizer.config")
        self.app.connect('activate', self.on_activate)
    
    def on_activate(self, app):
        """Handle application activation"""
        self.win = Adw.ApplicationWindow(application=app)
        self.win.set_title("CoC Optimizer Configuration")
        self.win.set_default_size(600, 400)
        
        # Create button to show config dialog
        button = Gtk.Button(label="Open Configuration")
        button.connect('clicked', self.on_config_clicked)
        
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_margin_top(12)
        box.set_margin_bottom(12)
        box.set_margin_start(12)
        box.set_margin_end(12)
        box.append(button)
        
        self.win.set_content(box)
        self.win.present()
    
    def on_config_clicked(self, button):
        """Handle config button click"""
        dialog = ConfigDialog(self.win)
        dialog.show()
    
    def run(self):
        """Run the application"""
        self.app.run()

if __name__ == "__main__":
    app = ConfigApp()
    app.run()