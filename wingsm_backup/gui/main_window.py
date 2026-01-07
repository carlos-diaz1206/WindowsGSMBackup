"""Main window for WinGSM Backup Manager."""
import asyncio
import threading
import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import messagebox, ttk
from typing import List, Optional

from ..config_manager import ConfigManager
from ..models import BackupJob, BackupSchedule, ServerConfig
from ..services.backup_service import BackupService
from ..services.google_cloud_backup_service import GoogleCloudBackupService
from ..services.onedrive_backup_service import OneDriveBackupService
from ..services.restore_service import RestoreService
from ..services.scheduler_service import SchedulerService
from ..services.windowsgsm_service import WindowsGSMService
from .schedule_dialog import ScheduleDialog
from .settings_dialog import SettingsDialog


class MainWindow:
    """Main application window."""

    def __init__(self):
        """Initialize the main window."""
        self.root = tk.Tk()
        self.root.title("WinGSM Backup Manager")
        self.root.geometry("900x600")
        self.root.minsize(600, 400)

        # Initialize services
        self.config_manager = ConfigManager()
        config = self.config_manager.get_config()

        self.windowsgsm_service = WindowsGSMService(config.windowsgsm_path)
        self.backup_service = BackupService(self.windowsgsm_service)
        self.restore_service = RestoreService()
        self.onedrive_service = OneDriveBackupService()
        self.google_cloud_service = GoogleCloudBackupService()
        self.scheduler_service = SchedulerService(
            self.backup_service,
            self.windowsgsm_service,
            self.onedrive_service,
            self.google_cloud_service,
        )

        self.scheduler_service.backup_completed_callback = self.on_backup_completed

        # Initialize cloud services
        self._initialize_cloud_services(config)

        # Data
        self.servers: List[ServerConfig] = []
        self.schedules: List[BackupSchedule] = []

        # Create UI
        self._create_ui()

        # Load data
        self.load_servers()
        self.load_schedules()
        self.refresh_backups()

        # Start scheduler
        self.scheduler_service.start()
        for schedule in self.schedules:
            if schedule.enabled:
                self.scheduler_service.add_schedule(schedule)

    def _create_ui(self):
        """Create the user interface."""
        # Menu bar
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Settings", command=self.show_settings)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)

        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="View Documentation", command=self.show_documentation)
        help_menu.add_command(label="Report Issue / Support", command=self.open_support_link)

        # Toolbar
        toolbar = ttk.Frame(self.root)
        toolbar.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)

        ttk.Button(toolbar, text="Settings", command=self.show_settings).pack(
            side=tk.RIGHT, padx=2
        )
        ttk.Button(toolbar, text="Refresh Servers", command=self.load_servers).pack(
            side=tk.RIGHT, padx=2
        )

        # Notebook (tabs)
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Servers tab
        self._create_servers_tab()

        # Schedules tab
        self._create_schedules_tab()

        # Restore tab
        self._create_restore_tab()

        # Bottom frame with status bar and exit button
        bottom_frame = ttk.Frame(self.root)
        bottom_frame.pack(side=tk.BOTTOM, fill=tk.X)

        # Status bar
        self.status_bar = ttk.Label(
            bottom_frame, text="Ready", relief=tk.SUNKEN, anchor=tk.W
        )
        self.status_bar.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Exit button
        ttk.Button(bottom_frame, text="Exit", command=self.on_closing, width=10).pack(
            side=tk.RIGHT, padx=5, pady=2
        )

    def _create_servers_tab(self):
        """Create the servers tab."""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Servers")

        # Treeview for servers
        columns = ("Server Name", "Game Type", "Server ID", "Status")
        self.servers_tree = ttk.Treeview(frame, columns=columns, show="tree headings", selectmode="browse")
        self.servers_tree.heading("#0", text="Enabled")
        self.servers_tree.heading("Server Name", text="Server Name")
        self.servers_tree.heading("Game Type", text="Game Type")
        self.servers_tree.heading("Server ID", text="Server ID")
        self.servers_tree.heading("Status", text="Status")

        self.servers_tree.column("#0", width=60)
        self.servers_tree.column("Server Name", width=200)
        self.servers_tree.column("Game Type", width=150)
        self.servers_tree.column("Server ID", width=200)
        self.servers_tree.column("Status", width=100)

        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self.servers_tree.yview)
        self.servers_tree.configure(yscrollcommand=scrollbar.set)

        self.servers_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def _create_schedules_tab(self):
        """Create the schedules tab."""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Schedules")

        # Buttons
        button_frame = ttk.Frame(frame)
        button_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=5)

        ttk.Button(
            button_frame, text="Add Schedule", command=self.add_schedule
        ).pack(side=tk.LEFT, padx=2)
        ttk.Button(
            button_frame, text="Edit Schedule", command=self.edit_schedule
        ).pack(side=tk.LEFT, padx=2)
        ttk.Button(
            button_frame, text="Delete Schedule", command=self.delete_schedule
        ).pack(side=tk.LEFT, padx=2)
        ttk.Button(
            button_frame, text="Run Backup Now", command=self.run_backup_now
        ).pack(side=tk.RIGHT, padx=2)

        # Treeview for schedules
        columns = ("Type", "Status", "Description", "Cloud")
        self.schedules_tree = ttk.Treeview(
            frame, columns=columns, show="tree headings", selectmode="browse"
        )
        self.schedules_tree.heading("#0", text="Schedule Name")
        self.schedules_tree.heading("Type", text="Type")
        self.schedules_tree.heading("Status", text="Status")
        self.schedules_tree.heading("Description", text="Description")
        self.schedules_tree.heading("Cloud", text="Cloud Backup")

        self.schedules_tree.column("#0", width=200)
        self.schedules_tree.column("Type", width=100)
        self.schedules_tree.column("Status", width=100)
        self.schedules_tree.column("Description", width=300)
        self.schedules_tree.column("Cloud", width=150)

        scrollbar = ttk.Scrollbar(
            frame, orient=tk.VERTICAL, command=self.schedules_tree.yview
        )
        self.schedules_tree.configure(yscrollcommand=scrollbar.set)

        self.schedules_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def _create_restore_tab(self):
        """Create the restore tab."""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Restore")

        # Top controls frame
        controls_frame = ttk.Frame(frame)
        controls_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)

        ttk.Button(
            controls_frame, text="Refresh Backups", command=self.refresh_backups
        ).pack(side=tk.LEFT, padx=2)

        ttk.Label(controls_frame, text="Backup Location:").pack(side=tk.LEFT, padx=(20, 5))
        self.backup_location_label = ttk.Label(controls_frame, text="Not set", foreground="red")
        self.backup_location_label.pack(side=tk.LEFT, padx=5)

        # Main content area
        content_frame = ttk.Frame(frame)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Left side - Backup list
        list_frame = ttk.LabelFrame(content_frame, text="Available Backups", padding=5)
        list_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))

        # Treeview for backups
        columns = ("Date/Time", "Size", "Server")
        self.backups_tree = ttk.Treeview(
            list_frame, columns=columns, show="tree headings", selectmode="browse"
        )
        self.backups_tree.heading("#0", text="Server / Backup")
        self.backups_tree.heading("Date/Time", text="Date/Time")
        self.backups_tree.heading("Size", text="Size")
        self.backups_tree.heading("Server", text="Server ID")

        self.backups_tree.column("#0", width=250)
        self.backups_tree.column("Date/Time", width=150)
        self.backups_tree.column("Size", width=100)
        self.backups_tree.column("Server", width=100)

        backup_scrollbar = ttk.Scrollbar(
            list_frame, orient=tk.VERTICAL, command=self.backups_tree.yview
        )
        self.backups_tree.configure(yscrollcommand=backup_scrollbar.set)

        self.backups_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        backup_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.backups_tree.bind("<<TreeviewSelect>>", self.on_backup_selected)

        # Right side - Details and actions
        right_frame = ttk.Frame(content_frame)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH)

        # Details frame
        details_frame = ttk.LabelFrame(right_frame, text="Backup Details", padding=10)
        details_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 5))

        self.detail_labels = {}
        detail_fields = [
            ("Server Name:", "server_name"),
            ("Backup Date:", "backup_date"),
            ("File Size:", "file_size"),
            ("File Path:", "file_path"),
            ("Files in Backup:", "file_count")
        ]

        for i, (label_text, key) in enumerate(detail_fields):
            ttk.Label(details_frame, text=label_text, font=("TkDefaultFont", 9, "bold")).grid(
                row=i, column=0, sticky=tk.W, pady=2
            )
            value_label = ttk.Label(details_frame, text="-", wraplength=250)
            value_label.grid(row=i, column=1, sticky=tk.W, pady=2, padx=(5, 0))
            self.detail_labels[key] = value_label

        # Actions frame
        actions_frame = ttk.LabelFrame(right_frame, text="Actions", padding=10)
        actions_frame.pack(fill=tk.X)

        ttk.Button(
            actions_frame, text="Restore Selected Backup", command=self.restore_backup, width=25
        ).pack(pady=2, fill=tk.X)

        ttk.Button(
            actions_frame, text="View Backup Contents", command=self.view_backup_contents, width=25
        ).pack(pady=2, fill=tk.X)

        ttk.Button(
            actions_frame, text="Delete Selected Backup", command=self.delete_backup, width=25
        ).pack(pady=2, fill=tk.X)

        # Store reference to selected backup and backup dictionary
        self.selected_backup = None
        self.backups_dict = {}

    def _initialize_cloud_services(self, config):
        """Initialize cloud backup services."""
        # Initialize OneDrive if configured
        if (
            config.onedrive_config.client_id
            and config.onedrive_config.is_authenticated
        ):
            # Note: Authentication will need to be done interactively
            pass

        # Initialize Google Cloud if configured
        if (
            config.google_cloud_config.project_id
            and config.google_cloud_config.bucket_name
        ):
            self.google_cloud_service.initialize(
                config.google_cloud_config.project_id,
                config.google_cloud_config.bucket_name,
                config.google_cloud_config.credentials_json_path or None,
            )

    def load_servers(self):
        """Load servers from WindowsGSM."""
        discovered_servers = self.windowsgsm_service.discover_servers()
        config = self.config_manager.get_config()
        
        # If no servers discovered, we still show what's in config
        if not discovered_servers and config.servers:
            self.servers = config.servers
        else:
            # Merge discovered with saved configurations
            self.servers = discovered_servers
            for discovered in self.servers:
                saved = next((s for s in config.servers if s.server_id == discovered.server_id), None)
                if saved:
                    discovered.enabled = saved.enabled
                    # If we already have a custom save game path, keep it if it's still valid
                    if saved.save_game_path and Path(saved.save_game_path).exists():
                        discovered.save_game_path = saved.save_game_path
            
            # Also keep servers from config that weren't discovered (e.g. manually added or path changed)
            # but only if they are still enabled or have custom paths
            for saved in config.servers or []:
                if not any(s.server_id == saved.server_id for s in self.servers):
                    self.servers.append(saved)

        # Update config
        config.servers = self.servers
        self.config_manager.update_config(config)

        self.refresh_servers_list()

    def refresh_servers_list(self):
        """Refresh the servers list display."""
        # Clear existing items
        for item in self.servers_tree.get_children():
            self.servers_tree.delete(item)

        for server in self.servers:
            status = (
                "Running"
                if self.windowsgsm_service.is_server_running(server.server_id)
                else "Stopped"
            )
            enabled_text = "✓" if server.enabled else ""

            self.servers_tree.insert(
                "",
                tk.END,
                text=enabled_text,
                values=(
                    server.server_name,
                    server.game_type or "Unknown",
                    server.server_id,
                    status,
                ),
                tags=(server.server_id,),
            )
        
        self.status_bar.config(text=f"Loaded {len(self.servers)} servers")

    def load_schedules(self):
        """Load schedules from configuration."""
        config = self.config_manager.get_config()
        self.schedules = config.schedules or []
        self.refresh_schedules_list()

    def refresh_schedules_list(self):
        """Refresh the schedules list display."""
        # Clear existing items
        for item in self.schedules_tree.get_children():
            self.schedules_tree.delete(item)

        for schedule in self.schedules:
            status = "Enabled" if schedule.enabled else "Disabled"
            cloud_info = (
                f"{schedule.cloud_backup_type.value}"
                if schedule.enable_cloud_backup
                else "None"
            )
            description = self._get_schedule_description(schedule)

            self.schedules_tree.insert(
                "",
                tk.END,
                text=schedule.name,
                values=(schedule.schedule_type.value, status, description, cloud_info),
                tags=(schedule.schedule_id,),
            )

    def _get_schedule_description(self, schedule: BackupSchedule) -> str:
        """Get a description string for a schedule."""
        if schedule.schedule_type.value == "daily":
            return f"Daily at {schedule.time.strftime('%H:%M')}"
        elif schedule.schedule_type.value == "weekly":
            days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
            day_names = [days[d] for d in schedule.days_of_week]
            return f"Weekly on {', '.join(day_names)} at {schedule.time.strftime('%H:%M')}"
        else:
            return f"Every {schedule.interval_minutes} minutes"

    def add_schedule(self):
        """Add a new backup schedule."""
        dialog = ScheduleDialog(self.root, self.servers, self.config_manager.get_config())
        result = dialog.show()
        
        if result:
            self.schedules.append(result)
            self._save_and_refresh_schedules()

    def edit_schedule(self):
        """Edit the selected schedule."""
        selection = self.schedules_tree.selection()
        if not selection:
            messagebox.showinfo("No Selection", "Please select a schedule to edit.")
            return

        item = self.schedules_tree.item(selection[0])
        schedule_id = item["tags"][0]
        schedule = next((s for s in self.schedules if s.schedule_id == schedule_id), None)

        if schedule:
            dialog = ScheduleDialog(
                self.root, self.servers, self.config_manager.get_config(), schedule
            )
            result = dialog.show()
            
            if result:
                index = next(
                    (
                        i
                        for i, s in enumerate(self.schedules)
                        if s.schedule_id == schedule_id
                    ),
                    -1,
                )
                if index >= 0:
                    self.schedules[index] = result
                    self._save_and_refresh_schedules()

    def _save_and_refresh_schedules(self):
        """Save configuration and refresh the schedules list."""
        config = self.config_manager.get_config()
        config.schedules = self.schedules
        self.config_manager.update_config(config)

        # Update background scheduler
        self.scheduler_service.stop()
        self.scheduler_service.start()
        for schedule in self.schedules:
            if schedule.enabled:
                self.scheduler_service.add_schedule(schedule)

        self.refresh_schedules_list()

    def delete_schedule(self):
        """Delete the selected schedule."""
        selection = self.schedules_tree.selection()
        if not selection:
            messagebox.showinfo("No Selection", "Please select a schedule to delete.")
            return

        if messagebox.askyesno(
            "Confirm Delete", "Are you sure you want to delete this schedule?"
        ):
            item = self.schedules_tree.item(selection[0])
            schedule_id = item["tags"][0]

            self.schedules = [s for s in self.schedules if s.schedule_id != schedule_id]

            config = self.config_manager.get_config()
            config.schedules = self.schedules
            self.config_manager.update_config(config)

            self.scheduler_service.remove_schedule(schedule_id)
            self.refresh_schedules_list()

    def run_backup_now(self):
        """Run backup for the selected schedule immediately."""
        selection = self.schedules_tree.selection()
        if not selection:
            messagebox.showinfo(
                "No Selection", "Please select a schedule to run."
            )
            return

        item = self.schedules_tree.item(selection[0])
        schedule_id = item["tags"][0]
        schedule = next((s for s in self.schedules if s.schedule_id == schedule_id), None)

        if schedule:
            self.status_bar.config(text="Running backup...")
            threading.Thread(
                target=self._run_backup_thread, args=[schedule], daemon=True
            ).start()

    def _run_backup_thread(self, schedule: BackupSchedule):
        """Run backup in a separate thread."""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            job = loop.run_until_complete(
                self.scheduler_service.execute_backup_async(schedule.schedule_id, self.servers)
            )

            success_count = sum(1 for r in job.server_results if r.success)
            total_count = len(job.server_results)
            cloud_count = sum(1 for r in job.server_results if r.cloud_backup_success)

            message = f"Backup {job.status.value}: {success_count}/{total_count} servers backed up successfully"
            if schedule.enable_cloud_backup:
                message += f", {cloud_count}/{total_count} cloud uploads successful"

            self.root.after(0, lambda: messagebox.showinfo("Backup Complete", message))
            self.root.after(0, lambda: self.status_bar.config(text="Ready"))
        except Exception as ex:
            self.root.after(
                0,
                lambda: messagebox.showerror("Error", f"Backup failed: {str(ex)}"),
            )
            self.root.after(0, lambda: self.status_bar.config(text="Ready"))

    def on_backup_completed(self, job: BackupJob):
        """Handle backup completion callback."""
        success_count = sum(1 for r in job.server_results if r.success)
        message = f"Backup {job.status.value}: {success_count}/{len(job.server_results)} servers backed up successfully"
        self.root.after(0, lambda: self.status_bar.config(text=message))

    def show_settings(self):
        """Show the settings dialog."""
        dialog = SettingsDialog(
            self.root,
            self.config_manager.get_config()
        )
        result = dialog.show()
        if result:
            config = result
            self.config_manager.update_config(config)
            
            # Update services with new configuration
            self.windowsgsm_service = WindowsGSMService(config.windowsgsm_path)
            self.backup_service.windowsgsm_service = self.windowsgsm_service
            self.scheduler_service.windowsgsm_service = self.windowsgsm_service
            
            self._initialize_cloud_services(config)
            self.load_servers()

    def refresh_backups(self):
        """Refresh the list of available backups."""
        config = self.config_manager.get_config()
        
        # Update backup location label
        if config.default_backup_path:
            self.backup_location_label.config(
                text=config.default_backup_path, foreground="green"
            )
        else:
            self.backup_location_label.config(
                text="Not set - Configure in Settings", foreground="red"
            )
            return
        
        # Clear existing items
        for item in self.backups_tree.get_children():
            self.backups_tree.delete(item)
        
        # Clear details and state
        for label in self.detail_labels.values():
            label.config(text="-")
        self.selected_backup = None
        self.backups_dict = {}
        
        # Discover backups
        try:
            backups = self.restore_service.discover_backups(
                config.default_backup_path, self.servers
            )
            
            if not backups:
                # Insert a message if no backups found
                self.backups_tree.insert("", "end", text="No backups found", values=("", "", ""))
                return
            
            # Group backups by server
            backups_by_server = {}
            for backup in backups:
                if backup.server_id not in backups_by_server:
                    backups_by_server[backup.server_id] = []
                backups_by_server[backup.server_id].append(backup)
            
            # Store backups in a dictionary keyed by filepath for easy lookup
            self.backups_dict = {str(backup.filepath): backup for backup in backups}
            
            # Add to tree
            for server_id, server_backups in backups_by_server.items():
                server_name = server_backups[0].server_name
                # Add server node
                server_node = self.backups_tree.insert(
                    "", "end", text=f"{server_name} ({len(server_backups)} backups)",
                    values=("", "", server_id), tags=("server",)
                )
                
                # Add backup nodes under server
                for backup in server_backups:
                    date_str = backup.timestamp.strftime("%Y-%m-%d %H:%M:%S") if backup.timestamp else "Unknown"
                    self.backups_tree.insert(
                        server_node, "end",
                        text=backup.filepath.name,
                        values=(date_str, backup.get_size_display(), backup.server_id),
                        tags=("backup", str(backup.filepath))
                    )
                    
            self.status_bar.config(text=f"Found {len(backups)} backup(s)")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load backups: {str(e)}")
            self.status_bar.config(text=f"Error loading backups: {str(e)}")

    def on_backup_selected(self, event):
        """Handle backup selection in the tree."""
        selection = self.backups_tree.selection()
        if not selection:
            return
        
        item = self.backups_tree.item(selection[0])
        tags = item["tags"]
        
        # Check if it's a backup item (not a server node)
        if "backup" not in tags:
            self.selected_backup = None
            for label in self.detail_labels.values():
                label.config(text="-")
            return
        
        # Get the backup from the dictionary using filepath
        backup_filepath = tags[1]  # The filepath we stored
        self.selected_backup = None
        
        if hasattr(self, 'backups_dict') and backup_filepath in self.backups_dict:
            self.selected_backup = self.backups_dict[backup_filepath]
        
        if self.selected_backup:
            # Update details
            self.detail_labels["server_name"].config(text=self.selected_backup.server_name)
            
            if self.selected_backup.timestamp:
                date_str = self.selected_backup.timestamp.strftime("%Y-%m-%d %H:%M:%S")
            else:
                date_str = "Unknown"
            self.detail_labels["backup_date"].config(text=date_str)
            
            self.detail_labels["file_size"].config(text=self.selected_backup.get_size_display())
            self.detail_labels["file_path"].config(text=str(self.selected_backup.filepath))
            
            # Get file count
            try:
                contents = self.restore_service.get_backup_contents(self.selected_backup)
                self.detail_labels["file_count"].config(text=str(len(contents)))
            except Exception:
                self.detail_labels["file_count"].config(text="Error reading")

    def restore_backup(self):
        """Restore the selected backup."""
        if not self.selected_backup:
            messagebox.showinfo("No Selection", "Please select a backup to restore.")
            return
        
        # Find the server for this backup
        server = None
        for s in self.servers:
            if s.server_id == self.selected_backup.server_id:
                server = s
                break
        
        if not server:
            messagebox.showerror("Error", "Server not found for this backup.")
            return
        
        if not server.save_game_path:
            messagebox.showerror("Error", "Save game path not configured for this server.")
            return
        
        # Confirm restoration
        msg = (
            f"Restore backup to:\n{server.save_game_path}\n\n"
            f"Server: {server.server_name}\n"
            f"Backup Date: {self.selected_backup.timestamp.strftime('%Y-%m-%d %H:%M:%S') if self.selected_backup.timestamp else 'Unknown'}\n\n"
            f"This will:\n"
            f"1. Create a backup of existing files\n"
            f"2. Stop the server (if running)\n"
            f"3. Restore save game files (executables will be skipped)\n"
            f"4. Restart the server\n\n"
            f"Note: Server executables (.exe, .dll) won't be overwritten.\n"
            f"Only save game data will be restored.\n\n"
            f"Continue?"
        )
        
        if not messagebox.askyesno("Confirm Restore", msg):
            return
        
        # Perform restoration in a thread
        def do_restore():
            try:
                # Update status
                self.root.after(0, lambda: self.status_bar.config(text=f"Stopping server {server.server_name}..."))
                
                # Stop server if running
                was_running = self.windowsgsm_service.is_server_running(server.server_id)
                if was_running:
                    self.windowsgsm_service.stop_server(server.server_id)
                    # Wait for server to stop and release file handles
                    import time
                    self.root.after(0, lambda: self.status_bar.config(text="Waiting for server to fully stop..."))
                    time.sleep(8)  # Increased wait time to ensure files are released
                
                # Restore backup
                self.root.after(0, lambda: self.status_bar.config(text="Restoring backup..."))
                success, message = self.restore_service.restore_backup(
                    self.selected_backup,
                    server.save_game_path,
                    create_backup=True
                )
                
                if success:
                    # Restart server if it was running
                    if was_running:
                        self.root.after(0, lambda: self.status_bar.config(text="Restarting server..."))
                        self.windowsgsm_service.start_server(server.server_id)
                    
                    self.root.after(0, lambda: messagebox.showinfo("Success", message))
                    self.root.after(0, lambda: self.status_bar.config(text="Restore completed successfully"))
                else:
                    self.root.after(0, lambda: messagebox.showerror("Error", message))
                    self.root.after(0, lambda: self.status_bar.config(text=f"Restore failed: {message}"))
                    
            except Exception as e:
                error_msg = f"Restore failed: {str(e)}"
                self.root.after(0, lambda: messagebox.showerror("Error", error_msg))
                self.root.after(0, lambda: self.status_bar.config(text=error_msg))
        
        threading.Thread(target=do_restore, daemon=True).start()

    def view_backup_contents(self):
        """View the contents of the selected backup."""
        if not self.selected_backup:
            messagebox.showinfo("No Selection", "Please select a backup to view.")
            return
        
        try:
            contents = self.restore_service.get_backup_contents(self.selected_backup)
            
            if not contents:
                messagebox.showinfo("Empty", "No files found in backup.")
                return
            
            # Create a window to show contents
            contents_window = tk.Toplevel(self.root)
            contents_window.title(f"Backup Contents - {self.selected_backup.filepath.name}")
            contents_window.geometry("600x400")
            
            # Add scrollable text widget
            frame = ttk.Frame(contents_window)
            frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            scrollbar = ttk.Scrollbar(frame)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            text = tk.Text(frame, wrap=tk.NONE, yscrollcommand=scrollbar.set)
            text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.config(command=text.yview)
            
            # Add contents
            text.insert("1.0", f"Files in backup ({len(contents)} files):\n\n")
            for file_path in sorted(contents):
                text.insert(tk.END, f"{file_path}\n")
            
            text.config(state="disabled")
            
            # Add close button
            ttk.Button(
                contents_window, text="Close", command=contents_window.destroy
            ).pack(pady=10)
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to read backup contents: {str(e)}")

    def delete_backup(self):
        """Delete the selected backup."""
        if not self.selected_backup:
            messagebox.showinfo("No Selection", "Please select a backup to delete.")
            return
        
        # Confirm deletion
        msg = (
            f"Delete this backup?\n\n"
            f"Server: {self.selected_backup.server_name}\n"
            f"Date: {self.selected_backup.timestamp.strftime('%Y-%m-%d %H:%M:%S') if self.selected_backup.timestamp else 'Unknown'}\n"
            f"File: {self.selected_backup.filepath.name}\n\n"
            f"This cannot be undone!"
        )
        
        if not messagebox.askyesno("Confirm Delete", msg):
            return
        
        try:
            success, message = self.restore_service.delete_backup(self.selected_backup)
            
            if success:
                messagebox.showinfo("Success", message)
                self.refresh_backups()  # Reload the list
            else:
                messagebox.showerror("Error", message)
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to delete backup: {str(e)}")

    def show_documentation(self):
        """Show the documentation in a new window."""
        try:
            # Find README.md in the project root
            readme_path = Path(__file__).parent.parent.parent / "README.md"
            
            if not readme_path.exists():
                messagebox.showerror("Error", "README.md not found in project directory.")
                return
            
            # Read README content
            with open(readme_path, 'r', encoding='utf-8') as f:
                readme_content = f.read()
            
            # Create documentation window
            doc_window = tk.Toplevel(self.root)
            doc_window.title("WinGSM Backup Manager - Documentation")
            doc_window.geometry("800x600")
            
            # Add frame and scrollable text widget
            frame = ttk.Frame(doc_window)
            frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            # Scrollbars
            y_scrollbar = ttk.Scrollbar(frame)
            y_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            x_scrollbar = ttk.Scrollbar(frame, orient=tk.HORIZONTAL)
            x_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
            
            # Text widget
            text = tk.Text(
                frame,
                wrap=tk.WORD,
                yscrollcommand=y_scrollbar.set,
                xscrollcommand=x_scrollbar.set,
                font=("Consolas", 10)
            )
            text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            
            y_scrollbar.config(command=text.yview)
            x_scrollbar.config(command=text.xview)
            
            # Insert README content
            text.insert("1.0", readme_content)
            text.config(state="disabled")
            
            # Add close button
            button_frame = ttk.Frame(doc_window)
            button_frame.pack(fill=tk.X, padx=10, pady=5)
            
            ttk.Button(
                button_frame, text="Close", command=doc_window.destroy
            ).pack(side=tk.RIGHT)
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load documentation: {str(e)}")
    
    def open_support_link(self):
        """Open the support/issues page in the default browser."""
        support_url = "https://github.com/carlos-diaz1206/WindowsGSMBackup/issues"
        try:
            webbrowser.open(support_url)
            self.status_bar.config(text=f"Opened {support_url} in browser")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open browser: {str(e)}")
            # Fallback: show URL in a messagebox
            messagebox.showinfo(
                "Support Link",
                f"Please visit:\n{support_url}\n\nto report issues or get support."
            )

    def run(self):
        """Run the application."""
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.mainloop()

    def on_closing(self):
        """Handle window closing."""
        self.scheduler_service.stop()
        self.root.destroy()

