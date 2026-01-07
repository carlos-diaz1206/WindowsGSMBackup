"""Dialog for application settings."""
import tkinter as tk
from tkinter import filedialog, ttk
from typing import Optional

from ..models import ApplicationConfig


class SettingsDialog:
    """Dialog for application settings."""

    def __init__(self, parent, config: ApplicationConfig):
        """Initialize the settings dialog."""
        self.config = config
        self.result: Optional[ApplicationConfig] = None
        self.parent = parent

        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Settings")
        self.dialog.geometry("500x200")

        self._create_ui()
        self._load_settings()

    def show(self):
        """Show the dialog and wait for result."""
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        self.dialog.wait_window()
        return self.result

    def _create_ui(self):
        """Create the user interface."""
        row = 0

        # WindowsGSM Path
        ttk.Label(self.dialog, text="WindowsGSM Path:").grid(
            row=row, column=0, sticky=tk.W, padx=5, pady=5
        )
        self.windowsgsm_path_var = tk.StringVar()
        ttk.Entry(self.dialog, textvariable=self.windowsgsm_path_var, width=40).grid(
            row=row, column=1, sticky=tk.W, padx=5, pady=5
        )
        ttk.Button(
            self.dialog, text="Browse...", command=self._browse_windowsgsm_path
        ).grid(row=row, column=2, padx=5, pady=5)
        row += 1

        # Default Backup Path
        ttk.Label(self.dialog, text="Default Backup Path:").grid(
            row=row, column=0, sticky=tk.W, padx=5, pady=5
        )
        self.backup_path_var = tk.StringVar()
        ttk.Entry(self.dialog, textvariable=self.backup_path_var, width=40).grid(
            row=row, column=1, sticky=tk.W, padx=5, pady=5
        )
        ttk.Button(
            self.dialog, text="Browse...", command=self._browse_backup_path
        ).grid(row=row, column=2, padx=5, pady=5)
        row += 1

        # Buttons
        button_frame = ttk.Frame(self.dialog)
        button_frame.grid(row=row, column=0, columnspan=3, pady=20)

        ttk.Button(button_frame, text="OK", command=self._on_ok).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=self._on_cancel).pack(
            side=tk.LEFT, padx=5
        )

    def _load_settings(self):
        """Load settings into UI."""
        self.windowsgsm_path_var.set(self.config.windowsgsm_path or "")
        self.backup_path_var.set(self.config.default_backup_path or "")

    def _browse_windowsgsm_path(self):
        """Browse for WindowsGSM path."""
        path = filedialog.askdirectory(initialdir=self.windowsgsm_path_var.get())
        if path:
            self.windowsgsm_path_var.set(path)

    def _browse_backup_path(self):
        """Browse for backup path."""
        path = filedialog.askdirectory(initialdir=self.backup_path_var.get())
        if path:
            self.backup_path_var.set(path)

    def _on_ok(self):
        """Handle OK button click."""
        self.config.windowsgsm_path = self.windowsgsm_path_var.get()
        self.config.default_backup_path = self.backup_path_var.get()

        self.result = self.config
        self.dialog.destroy()

    def _on_cancel(self):
        """Handle Cancel button click."""
        self.dialog.destroy()

