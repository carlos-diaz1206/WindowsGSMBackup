# WinGSM Backup Manager

A self-contained Python application for automatically backing up savegame files from game servers managed by WindowsGSM. The application features a GUI interface built with tkinter and scheduling capabilities.

## Features

- **Automatic Server Discovery**: Automatically discovers game servers configured in WindowsGSM
- **Flexible Scheduling**: Create daily, weekly, or interval-based backup schedules
- **Server Management**: Automatically stops servers before backup and restarts them after
- **Local Backups**: Creates compressed ZIP archives of savegame files
- **Backup Restoration**: Browse and restore backups with automatic server stop/restart
- **Retention Management**: Automatically cleans up old backups based on retention settings
- **User-Friendly GUI**: tkinter-based interface for easy configuration and monitoring

## Requirements

- Python 3.8 or later
- Windows 10 or later
- WindowsGSM installed and configured

## Installation

### Quick Install (Windows)

1. **Install Python** (if not already installed)
   - Download and install Python 3.8 or later from [python.org](https://www.python.org/downloads/)
   - **Important**: Check "Add Python to PATH" during installation

2. **Run the installer**
   - Double-click `install.bat` in the project directory
   - This will automatically install all required packages

3. **Run the application**
   - **Option 1**: Double-click `run.bat` - Console window minimizes automatically
   - **Option 2**: Double-click `run_hidden.vbs` - No console window at all
   - **Option 3**: Run `python main.py` from command line - Console minimizes on startup

### Manual Installation

1. **Install Python**

   Download and install Python 3.8 or later from [python.org](https://www.python.org/downloads/).

2. **Install Dependencies**

   Open a terminal/command prompt in the project directory and run:

   ```bash
   pip install -r requirements.txt
   ```

   Or install packages individually:

   ```bash
   pip install APScheduler msal google-cloud-storage requests aiohttp
   ```

3. **Run the Application**

   ```bash
   python main.py
   ```

## Configuration

### Initial Setup

1. Launch the application: `python main.py`
2. Click **Settings** (or File > Settings) to configure:
   - WindowsGSM installation path (if not in default location)
   - Default backup path for local backups

## Usage

### Getting Help

Access documentation and support from the **Help** menu:
- **View Documentation**: Opens the README documentation in a scrollable window
- **Report Issue / Support**: Opens the GitHub issues page to report bugs or request features

### Creating a Backup Schedule

1. Go to the **Schedules** tab
2. Click **Add Schedule**
3. Configure the schedule:
   - **Schedule Name**: A descriptive name for the schedule
   - **Schedule Type**: 
     - Daily: Runs at a specific time each day
     - Weekly: Runs on specific days of the week at a specific time
     - Interval: Runs every X minutes
   - **Time**: The time to run (for Daily/Weekly)
   - **Interval**: Minutes between backups (for Interval)
   - **Days of Week**: Select days (for Weekly)
   - **Backup Path**: Local directory to store backups
   - **Retention Days**: How many days to keep backups (older backups are automatically deleted)
   - **Select Servers**: Check the servers to include in this schedule
4. Click **OK**

### Running a Backup Manually

1. Select a schedule from the **Schedules** tab
2. Click **Run Backup Now**

### Managing Servers

- Servers are automatically discovered from WindowsGSM
- Use checkboxes to enable/disable servers for backups
- Click **Refresh Servers** to rediscover servers
- Server status (Running/Stopped) is displayed in the list

### Restoring Backups

1. Go to the **Restore** tab
2. Click **Refresh Backups** to scan for available backups
3. Browse backups organized by server and date
4. Select a backup to view details:
   - Server name
   - Backup date and time
   - File size
   - Number of files
5. Click **View Backup Contents** to see what files are in the backup
6. Click **Restore Selected Backup** to restore:
   - The app will create a backup of existing files first
   - Stop the server (if running)
   - Extract save game files to the server's save game directory
   - Server executables (.exe, .dll) are skipped automatically
   - Restart the server automatically
7. Click **Delete Selected Backup** to remove old backups

**Note:** During restoration, only save game data files are restored. Server executables and DLL files are intentionally skipped to prevent permission errors and maintain server integrity.

## How It Works

1. When a scheduled backup runs:
   - The application stops each configured game server
   - Waits for the server to fully stop
   - Creates a ZIP archive of the savegame files
   - Restarts the game server
   - Cleans up old backups based on retention settings

2. Backup files are organized as:
   ```
   BackupPath/
     ServerId/
       YYYY-MM-DD_HH-mm-ss/
         ServerName_YYYY-MM-DD_HH-mm-ss.zip
   ```

## Project Structure

```
wingsm_backup/
├── __init__.py
├── models.py              # Data models
├── config_manager.py      # Configuration management
├── services/
│   ├── __init__.py
│   ├── windowsgsm_service.py      # WindowsGSM integration
│   ├── backup_service.py           # Local backup operations
│   ├── restore_service.py          # Backup restoration
│   └── scheduler_service.py       # Backup scheduling
└── gui/
    ├── __init__.py
    ├── main_window.py     # Main application window
    ├── schedule_dialog.py # Schedule configuration dialog
    └── settings_dialog.py # Settings configuration dialog
main.py                    # Application entry point
requirements.txt           # Python dependencies
```

## Troubleshooting

### Servers Not Discovered
- Verify WindowsGSM is installed and configured
- Check the WindowsGSM path in Settings
- Ensure servers are properly configured in WindowsGSM

### Backup Fails
- Verify the backup path is writable
- Check that savegame directories exist and are accessible
- Review error messages in the status bar

### Server Won't Stop/Start
- Verify WindowsGSM.exe is accessible
- Check WindowsGSM server configuration
- Ensure you have permissions to manage the servers

### Restore Fails
- Verify the backup file exists and is not corrupted
- Ensure the server's save game path is correctly configured
- Check that you have write permissions to the destination directory
- The server will be stopped during restore - wait for it to fully shut down (8 seconds)
- If you get permission errors, ensure no other programs are accessing the server files
- Executables (.exe, .dll) are automatically skipped - this is normal behavior
- Some locked files may be skipped - the restore will continue with other files

### Python Import Errors
- Make sure all dependencies are installed: `pip install -r requirements.txt`
- Verify you're using Python 3.8 or later: `python --version`

## File Locations

- **Configuration**: `%LocalAppData%\WinGSMBackup\config.json`
- **Backups**: As configured in schedules (default: `%Documents%\WinGSMBackups`)

## Security Notes

- Keep your configuration file secure
- Backups are stored locally in the configured backup directory

## Building a Standalone Executable (Optional)

You can create a standalone executable using PyInstaller:

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name WinGSMBackup main.py
```

The executable will be in the `dist` folder.

## Launch Scripts

The project includes convenient launch scripts for Windows:

- **`install.bat`** - Installs all required Python packages automatically
- **`run.bat`** - Quick launcher for the application (console minimizes automatically)
- **`run_hidden.vbs`** - Launches the application with no console window at all

Simply double-click these files to use them. They will check for Python installation and provide helpful error messages if something is missing.

**Note**: The console window automatically minimizes when the application starts to keep your desktop clean while still allowing error messages to be displayed if needed.

## License

This project is provided as-is for use with WindowsGSM game server management.

## Support

For issues related to:
- **WindowsGSM**: Visit [WindowsGSM Documentation](https://docs.windowsgsm.com)
- **This Application**: Create an issue in the repository
