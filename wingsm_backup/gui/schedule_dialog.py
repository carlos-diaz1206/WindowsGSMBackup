"""Dialog for creating/editing backup schedules."""
import tkinter as tk
import uuid
import copy
from datetime import datetime, time
from tkinter import filedialog, messagebox, ttk
from typing import List, Optional

from ..models import BackupSchedule, CloudBackupType, ScheduleType, ServerConfig
from ..config_manager import ApplicationConfig


class ScheduleDialog:
    """Dialog for schedule configuration."""

    def __init__(
        self,
        parent,
        servers: List[ServerConfig],
        config: ApplicationConfig,
        schedule: Optional[BackupSchedule] = None,
    ):
        """Initialize the schedule dialog."""
        self.servers = servers
        self.config = config
        self.result: Optional[BackupSchedule] = None
        self.parent = parent

        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Add Schedule" if schedule is None else "Edit Schedule")
        self.dialog.geometry("800x600")

        # Initialize schedule with a copy to avoid modifying original until OK
        if schedule:
            self.schedule = copy.deepcopy(schedule)
        else:
            self.schedule = BackupSchedule(
                schedule_id=str(uuid.uuid4()),
                backup_path=config.default_backup_path,
                time=datetime.now().time(),
            )

        self._create_ui()
        # Force update to ensure widgets are ready
        self.dialog.update_idletasks()
        self._load_schedule()

    def show(self):
        """Show the dialog and wait for result."""
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        self.dialog.wait_window()
        return self.result

    def _create_ui(self):
        """Create the user interface."""
        # Schedule Name
        ttk.Label(self.dialog, text="Schedule Name:").grid(
            row=0, column=0, sticky=tk.W, padx=5, pady=5
        )
        self.name_var = tk.StringVar()
        ttk.Entry(self.dialog, textvariable=self.name_var, width=40).grid(
            row=0, column=1, columnspan=2, sticky=tk.W, padx=5, pady=5
        )

        # Schedule Type
        ttk.Label(self.dialog, text="Schedule Type:").grid(
            row=1, column=0, sticky=tk.W, padx=5, pady=5
        )
        self.type_var = tk.StringVar(value="daily")
        type_combo = ttk.Combobox(
            self.dialog, textvariable=self.type_var, values=["daily", "weekly", "interval"], state="readonly", width=37
        )
        type_combo.grid(row=1, column=1, columnspan=2, sticky=tk.W, padx=5, pady=5)
        type_combo.bind("<<ComboboxSelected>>", self._on_type_changed)

        # Time
        ttk.Label(self.dialog, text="Time:").grid(
            row=2, column=0, sticky=tk.W, padx=5, pady=5
        )
        self.time_var = tk.StringVar(value="00:00")
        ttk.Entry(self.dialog, textvariable=self.time_var, width=20).grid(
            row=2, column=1, sticky=tk.W, padx=5, pady=5
        )
        ttk.Label(self.dialog, text="(HH:MM)").grid(
            row=2, column=2, sticky=tk.W, padx=5, pady=5
        )

        # Interval Minutes
        ttk.Label(self.dialog, text="Interval (minutes):").grid(
            row=3, column=0, sticky=tk.W, padx=5, pady=5
        )
        self.interval_var = tk.IntVar(value=60)
        ttk.Spinbox(
            self.dialog, from_=1, to=10080, textvariable=self.interval_var, width=20
        ).grid(row=3, column=1, sticky=tk.W, padx=5, pady=5)

        # Days of Week
        ttk.Label(self.dialog, text="Days of Week:").grid(
            row=4, column=0, sticky=tk.W, padx=5, pady=5
        )
        days_frame = ttk.Frame(self.dialog)
        days_frame.grid(row=4, column=1, columnspan=2, sticky=tk.W, padx=5, pady=5)
        self.days_vars = []
        days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        for i, day in enumerate(days):
            var = tk.BooleanVar()
            self.days_vars.append(var)
            ttk.Checkbutton(days_frame, text=day, variable=var).grid(
                row=0, column=i, padx=2
            )

        # Enabled
        self.enabled_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(self.dialog, text="Enabled", variable=self.enabled_var).grid(
            row=5, column=0, columnspan=3, sticky=tk.W, padx=5, pady=5
        )

        # Backup Path
        ttk.Label(self.dialog, text="Backup Path:").grid(
            row=6, column=0, sticky=tk.W, padx=5, pady=5
        )
        self.backup_path_var = tk.StringVar()
        ttk.Entry(self.dialog, textvariable=self.backup_path_var, width=30).grid(
            row=6, column=1, sticky=tk.W, padx=5, pady=5
        )
        ttk.Button(
            self.dialog, text="Browse...", command=self._browse_backup_path
        ).grid(row=6, column=2, sticky=tk.W, padx=5, pady=5)

        # Retention Days
        ttk.Label(self.dialog, text="Retention (days):").grid(
            row=7, column=0, sticky=tk.W, padx=5, pady=5
        )
        self.retention_var = tk.IntVar(value=7)
        ttk.Spinbox(
            self.dialog, from_=1, to=365, textvariable=self.retention_var, width=20
        ).grid(row=7, column=1, sticky=tk.W, padx=5, pady=5)

        # Cloud Backup
        self.cloud_enabled_var = tk.BooleanVar()
        ttk.Checkbutton(
            self.dialog,
            text="Enable Cloud Backup",
            variable=self.cloud_enabled_var,
            command=self._on_cloud_changed,
        ).grid(row=8, column=0, columnspan=3, sticky=tk.W, padx=5, pady=5)

        ttk.Label(self.dialog, text="Cloud Service:").grid(
            row=9, column=0, sticky=tk.W, padx=5, pady=5
        )
        self.cloud_type_var = tk.StringVar(value="onedrive")
        cloud_combo = ttk.Combobox(
            self.dialog,
            textvariable=self.cloud_type_var,
            values=["onedrive", "google_cloud"],
            state="readonly",
            width=37,
        )
        cloud_combo.grid(row=9, column=1, columnspan=2, sticky=tk.W, padx=5, pady=5)

        ttk.Label(self.dialog, text="Cloud Path:").grid(
            row=10, column=0, sticky=tk.W, padx=5, pady=5
        )
        self.cloud_path_var = tk.StringVar(value="WinGSMBackups")
        ttk.Entry(self.dialog, textvariable=self.cloud_path_var, width=40).grid(
            row=10, column=1, columnspan=2, sticky=tk.W, padx=5, pady=5
        )

        # Servers
        ttk.Label(self.dialog, text="Select Servers:").grid(
            row=11, column=0, sticky=tk.NW, padx=5, pady=5
        )
        servers_frame = ttk.Frame(self.dialog)
        servers_frame.grid(row=11, column=1, columnspan=2, sticky=tk.NSEW, padx=5, pady=5)

        scrollbar = ttk.Scrollbar(servers_frame, orient=tk.VERTICAL)
        self.servers_listbox = tk.Listbox(
            servers_frame, selectmode=tk.MULTIPLE, yscrollcommand=scrollbar.set
        )
        scrollbar.config(command=self.servers_listbox.yview)

        for server in self.servers:
            self.servers_listbox.insert(tk.END, f"{server.server_name} ({server.server_id})")

        self.servers_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Buttons
        button_frame = ttk.Frame(self.dialog)
        button_frame.grid(row=12, column=0, columnspan=3, pady=10)

        ttk.Button(button_frame, text="OK", command=self._on_ok).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=self._on_cancel).pack(
            side=tk.LEFT, padx=5
        )

        self.dialog.grid_rowconfigure(11, weight=1)
        self.dialog.grid_columnconfigure(1, weight=1)

        self._on_type_changed()
        self._on_cloud_changed()
        
    def _on_type_changed(self, event=None):
        """Handle schedule type change."""
        schedule_type = self.type_var.get()
        if schedule_type == "interval":
            self.time_var.set("00:00")
            # Disable time and days, enable interval
            for widget in self.dialog.grid_slaves(row=2):
                widget.config(state="disabled")
            for widget in self.dialog.grid_slaves(row=4):
                if isinstance(widget, ttk.Checkbutton):
                    widget.config(state="disabled")
            for widget in self.dialog.grid_slaves(row=3):
                widget.config(state="normal")
        elif schedule_type == "weekly":
            # Enable time and days, disable interval
            for widget in self.dialog.grid_slaves(row=2):
                widget.config(state="normal")
            for widget in self.dialog.grid_slaves(row=4):
                if isinstance(widget, ttk.Checkbutton):
                    widget.config(state="normal")
            for widget in self.dialog.grid_slaves(row=3):
                widget.config(state="disabled")
        else:  # daily
            # Enable time, disable days and interval
            for widget in self.dialog.grid_slaves(row=2):
                widget.config(state="normal")
            for widget in self.dialog.grid_slaves(row=4):
                if isinstance(widget, ttk.Checkbutton):
                    widget.config(state="disabled")
            for widget in self.dialog.grid_slaves(row=3):
                widget.config(state="disabled")

    def _on_cloud_changed(self):
        """Handle cloud backup checkbox change."""
        enabled = self.cloud_enabled_var.get()
        for widget in self.dialog.grid_slaves(row=9):
            widget.config(state="normal" if enabled else "disabled")
        for widget in self.dialog.grid_slaves(row=10):
            widget.config(state="normal" if enabled else "disabled")

    def _browse_backup_path(self):
        """Browse for backup path."""
        path = filedialog.askdirectory(initialdir=self.backup_path_var.get())
        if path:
            self.backup_path_var.set(path)

    def _load_schedule(self):
        """Load schedule data into UI."""
        if not self.dialog.winfo_exists():
            return
            
        self.name_var.set(self.schedule.name)
        self.type_var.set(self.schedule.schedule_type.value)
        self.time_var.set(self.schedule.time.strftime("%H:%M"))
        self.interval_var.set(self.schedule.interval_minutes)
        self.enabled_var.set(self.schedule.enabled)
        self.backup_path_var.set(self.schedule.backup_path)
        self.retention_var.set(self.schedule.retention_days)
        self.cloud_enabled_var.set(self.schedule.enable_cloud_backup)
        self.cloud_type_var.set(self.schedule.cloud_backup_type.value)
        self.cloud_path_var.set(self.schedule.cloud_backup_path)

        # Load days of week
        for i, var in enumerate(self.days_vars):
            var.set(i in self.schedule.days_of_week)

        # Load selected servers
        for i, server in enumerate(self.servers):
            if server.server_id in self.schedule.server_ids:
                self.servers_listbox.selection_set(i)

        self._on_type_changed()

    def _on_ok(self):
        """Handle OK button click."""
        if not self.name_var.get().strip():
            messagebox.showwarning("Validation Error", "Please enter a schedule name.")
            return

        selected_indices = self.servers_listbox.curselection()
        if not selected_indices:
            messagebox.showwarning(
                "Validation Error", "Please select at least one server."
            )
            return

        schedule_type = self.type_var.get()
        if schedule_type == "weekly" and not any(
            var.get() for var in self.days_vars
        ):
            messagebox.showwarning(
                "Validation Error",
                "Please select at least one day of the week for weekly schedules.",
            )
            return

        # Parse time
        try:
            time_str = self.time_var.get()
            time_obj = datetime.strptime(time_str, "%H:%M").time()
        except ValueError:
            messagebox.showerror("Validation Error", "Invalid time format. Use HH:MM")
            return

        # Update schedule
        self.schedule.name = self.name_var.get().strip()
        self.schedule.schedule_type = ScheduleType(schedule_type)
        self.schedule.time = time_obj
        self.schedule.interval_minutes = self.interval_var.get()
        self.schedule.enabled = self.enabled_var.get()
        self.schedule.backup_path = self.backup_path_var.get()
        self.schedule.retention_days = self.retention_var.get()
        self.schedule.enable_cloud_backup = self.cloud_enabled_var.get()
        self.schedule.cloud_backup_type = CloudBackupType(self.cloud_type_var.get())
        self.schedule.cloud_backup_path = self.cloud_path_var.get()

        # Days of week
        self.schedule.days_of_week = [
            i for i, var in enumerate(self.days_vars) if var.get()
        ]

        # Selected servers
        self.schedule.server_ids = [
            self.servers[i].server_id for i in selected_indices
        ]

        self.result = self.schedule
        self.dialog.destroy()

    def _on_cancel(self):
        """Handle Cancel button click."""
        self.dialog.destroy()

