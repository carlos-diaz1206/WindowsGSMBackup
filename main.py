#!/usr/bin/env python3
"""Main entry point for WinGSM Backup Manager."""
import sys
import platform
from wingsm_backup.gui.main_window import MainWindow


def minimize_console():
    """Minimize the console window on Windows."""
    if platform.system() == "Windows":
        try:
            import ctypes
            # Get console window handle
            hwnd = ctypes.windll.kernel32.GetConsoleWindow()
            if hwnd:
                # SW_MINIMIZE = 6
                ctypes.windll.user32.ShowWindow(hwnd, 6)
        except Exception:
            # If minimizing fails, just continue
            pass


def main():
    """Run the application."""
    # Minimize console window on startup
    minimize_console()
    
    app = MainWindow()
    app.run()


if __name__ == "__main__":
    main()

