"""Service for interacting with WindowsGSM."""
import os
import subprocess
from pathlib import Path
from typing import List, Optional

from ..models import ServerConfig


class WindowsGSMService:
    """Service for managing WindowsGSM servers."""

    def __init__(self, windowsgsm_path: Optional[str] = None):
        """Initialize the WindowsGSM service."""
        if windowsgsm_path and Path(windowsgsm_path).exists():
            provided_path = Path(windowsgsm_path).absolute()
            
            # Smart detection: try to find the 'servers' folder in the path or its ancestors
            current = provided_path
            self.servers_path = None
            
            # Check if this folder OR any of its parents is named 'servers'
            temp = current
            while temp and len(temp.parts) > 1:
                if temp.name.lower() == "servers":
                    self.servers_path = temp
                    break
                temp = temp.parent
            
            # If not found, check if it has a subfolder named 'servers'
            if not self.servers_path and (provided_path / "servers").exists():
                self.servers_path = provided_path / "servers"
            
            # If still not found, check if it's currently inside a numbered folder (like '1')
            if not self.servers_path and provided_path.name.isdigit():
                if provided_path.parent.name.lower() == "servers":
                    self.servers_path = provided_path.parent
            
            # Final fallback: just use what was provided
            if not self.servers_path:
                self.servers_path = provided_path
            
            self.windowsgsm_path = self.servers_path.parent
        else:
            # Default WindowsGSM installation paths
            local_app_data = Path(os.getenv("LOCALAPPDATA", ""))
            self.windowsgsm_path = local_app_data / "WindowsGSM"
            self.servers_path = self.windowsgsm_path / "servers"

    def discover_servers(self) -> List[ServerConfig]:
        """Discover all configured WindowsGSM servers."""
        servers = []

        if not self.servers_path or not self.servers_path.exists():
            print(f"DEBUG: Servers path does not exist: {self.servers_path}")
            return servers

        print(f"DEBUG: Discovering servers in: {self.servers_path}")
        
        # We'll check the current folder AND its immediate subfolders for servers
        folders_to_check = [self.servers_path]
        
        # If the current folder contains numbered folders (1, 2, 3), add those too
        try:
            for item in self.servers_path.iterdir():
                if item.is_dir():
                    folders_to_check.append(item)
        except Exception as e:
            print(f"DEBUG: Error listing directory {self.servers_path}: {e}")

        seen_ids = set()
        for server_dir in folders_to_check:
            if not server_dir.is_dir():
                continue
                
            server_id = server_dir.name
            if server_id in seen_ids:
                continue

            # Look for WindowsGSM configuration files
            # WindowsGSM uses configs.json for server metadata
            configs_json = server_dir / "configs.json"
            
            if configs_json.exists():
                server = self._parse_windowsgsm_config(server_id, server_dir, configs_json)
                if server:
                    print(f"DEBUG: Found server from configs.json: {server.server_name} ({server.server_id})")
                    servers.append(server)
                    seen_ids.add(server_id)
            elif server_id.isdigit():
                # If no config found, but it's a numbered folder, try to detect from folder structure
                print(f"DEBUG: Numbered folder found: {server_id}, checking structure...")
                server = self._detect_server_from_structure(server_id, server_dir)
                if server:
                    print(f"DEBUG: Detected server: {server.server_name} ({server.server_id})")
                    servers.append(server)
                    seen_ids.add(server_id)

        return servers

    def _parse_windowsgsm_config(
        self, server_id: str, server_path: Path, config_file: Path
    ) -> Optional[ServerConfig]:
        """Parse a WindowsGSM configs.json file."""
        try:
            import json
            
            with open(config_file, "r", encoding="utf-8") as f:
                config_data = json.load(f)
            
            # Extract server information from configs.json
            server_name = config_data.get("name", f"Server {server_id}")
            game_type = config_data.get("game", "")
            
            # Find serverfiles directory
            serverfiles_dir = server_path / "serverfiles"
            
            config = ServerConfig(
                server_id=server_id,
                server_name=server_name,
                game_type=game_type,
                server_path=str(server_path)
            )

            # Try to find savegame directory
            config.save_game_path = self._find_savegame_path(serverfiles_dir if serverfiles_dir.exists() else server_path, game_type)

            return config
        except Exception as e:
            print(f"DEBUG: Error parsing configs.json: {e}")
            return None

    def _detect_server_from_structure(self, server_id: str, server_path: Path) -> Optional[ServerConfig]:
        """Detect server info from folder structure when no config is found."""
        try:
            serverfiles_dir = server_path / "serverfiles"
            
            # Try to detect game type from executables
            game_type = "Unknown"
            server_name = f"Server {server_id}"
            
            if serverfiles_dir.exists():
                # Check for common game server executables
                if (serverfiles_dir / "enshrouded_server.exe").exists():
                    game_type = "Enshrouded"
                    server_name = f"Enshrouded Server {server_id}"
                elif (serverfiles_dir / "valheim_server.exe").exists():
                    game_type = "Valheim"
                    server_name = f"Valheim Server {server_id}"
                elif (serverfiles_dir / "PalServer.exe").exists():
                    game_type = "Palworld"
                    server_name = f"Palworld Server {server_id}"
                elif (serverfiles_dir / "bedrock_server.exe").exists():
                    game_type = "Minecraft Bedrock"
                    server_name = f"Minecraft Server {server_id}"
                elif (serverfiles_dir / "srcds.exe").exists():
                    game_type = "Source Game"
                    server_name = f"Source Server {server_id}"
            
            config = ServerConfig(
                server_id=server_id,
                server_name=server_name,
                game_type=game_type,
                server_path=str(server_path)
            )
            
            # Try to find savegame directory
            config.save_game_path = self._find_savegame_path(serverfiles_dir if serverfiles_dir.exists() else server_path, game_type)
            
            return config
        except Exception as e:
            print(f"DEBUG: Error detecting server structure: {e}")
            return None

    def _find_savegame_path(self, server_path: Path, game_type: str) -> str:
        """Find the savegame directory for a server."""
        # Game-specific paths (check these first as they're most reliable)
        game_type_lower = game_type.lower() if game_type else ""
        
        if "enshrouded" in game_type_lower:
            # Enshrouded stores saves in serverfiles root
            enshrouded_path = server_path / "savegame"
            if enshrouded_path.exists():
                return str(enshrouded_path)
            # Sometimes just in serverfiles root
            return str(server_path)
        elif "valheim" in game_type_lower:
            valheim_path = server_path / "BepInEx" / "worlds"
            if valheim_path.exists():
                return str(valheim_path)
        elif "palworld" in game_type_lower:
            palworld_path = server_path / "Pal" / "Saved" / "SaveGames"
            if palworld_path.exists():
                return str(palworld_path)
        elif "minecraft" in game_type_lower:
            minecraft_path = server_path / "world"
            if minecraft_path.exists():
                return str(minecraft_path)
        
        # Common paths for unknown games
        common_paths = [
            server_path / "savegame",
            server_path / "save",
            server_path / "saves",
            server_path / "SaveGames",
            server_path / "world",
            server_path / "worlds",
            server_path / "data",
        ]

        for path in common_paths:
            if path.exists():
                return str(path)

        # Fallback to server root
        return str(server_path)

    def stop_server(self, server_id: str) -> bool:
        """Stop a game server."""
        return self._execute_windowsgsm_command(server_id, "stop")

    def start_server(self, server_id: str) -> bool:
        """Start a game server."""
        return self._execute_windowsgsm_command(server_id, "start")

    def restart_server(self, server_id: str) -> bool:
        """Restart a game server."""
        return self._execute_windowsgsm_command(server_id, "restart")

    def is_server_running(self, server_id: str) -> bool:
        """Check if a server is currently running."""
        try:
            server_dir = self.servers_path / server_id
            
            # Method 1: Check for WindowsGSM status file
            status_file = server_dir / "status.txt"
            if status_file.exists():
                try:
                    with open(status_file, 'r') as f:
                        status = f.read().strip().lower()
                        if status in ['running', 'started', 'online']:
                            return True
                except Exception:
                    pass
            
            # Method 2: Check for lock/pid files in multiple locations
            paths_to_check = [
                server_dir,
                server_dir / "serverfiles",
                server_dir / "logs"
            ]
            
            for folder in paths_to_check:
                if not folder.exists():
                    continue
                # Look for .lock, .pid, or WindowsGSM specific status files
                if list(folder.glob("*.lock")) or list(folder.glob("*.pid")):
                    return True
            
            # Method 3: Check for running process by looking for common server executables
            serverfiles_dir = server_dir / "serverfiles"
            if serverfiles_dir.exists():
                try:
                    import psutil
                    
                    # Get list of all running processes
                    exe_names = ["enshrouded_server.exe", "valheim_server.exe", "PalServer.exe", 
                                 "bedrock_server.exe", "srcds.exe"]
                    
                    for proc in psutil.process_iter(['name', 'exe']):
                        try:
                            # Safely get process info with None handling
                            proc_name = proc.info.get('name') or ''
                            proc_exe = proc.info.get('exe') or ''
                            
                            proc_name_lower = proc_name.lower() if proc_name else ''
                            proc_exe_lower = proc_exe.lower() if proc_exe else ''
                            
                            # Check if this process is one of our server executables
                            # and if it's running from this server's directory
                            for exe in exe_names:
                                exe_lower = exe.lower()
                                if exe_lower in proc_name_lower or exe_lower in proc_exe_lower:
                                    if str(serverfiles_dir).lower() in proc_exe_lower:
                                        return True
                        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                            continue
                except ImportError:
                    # psutil not available, skip this method
                    pass
                except Exception as e:
                    print(f"DEBUG: Error in process checking: {e}")
                    pass
            
            return False
        except Exception as e:
            print(f"DEBUG: Error checking server status: {e}")
            return False

    def _execute_windowsgsm_command(self, server_id: str, command: str) -> bool:
        """Execute a WindowsGSM command."""
        try:
            windowsgsm_exe = self.windowsgsm_path / "WindowsGSM.exe"

            if not windowsgsm_exe.exists():
                # Try alternative locations
                program_files = Path(os.getenv("ProgramFiles", ""))
                windowsgsm_exe = program_files / "WindowsGSM" / "WindowsGSM.exe"

            if not windowsgsm_exe.exists():
                return False

            result = subprocess.run(
                [str(windowsgsm_exe), command, server_id],
                capture_output=True,
                timeout=30,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            )

            return result.returncode == 0
        except Exception:
            return False

