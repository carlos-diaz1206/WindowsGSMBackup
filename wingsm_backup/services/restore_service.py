"""Service for restoring backups."""
import os
import shutil
import zipfile
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple


class BackupInfo:
    """Information about a backup file."""
    
    def __init__(self, filepath: Path, server_id: str, server_name: str):
        self.filepath = filepath
        self.server_id = server_id
        self.server_name = server_name
        self.timestamp = self._extract_timestamp(filepath.name)
        self.size_bytes = filepath.stat().st_size
        
    def _extract_timestamp(self, filename: str) -> Optional[datetime]:
        """Extract timestamp from backup filename."""
        try:
            # Expected formats: 
            # ServerName_YYYY-MM-DD_HH-MM-SS.zip (with dashes)
            # ServerName_YYYYMMDD_HHMMSS.zip (without dashes)
            parts = filename.replace('.zip', '').split('_')
            if len(parts) >= 3:
                date_str = parts[-2]
                time_str = parts[-1]
                timestamp_str = f"{date_str}_{time_str}"
                
                # Try format with dashes first
                try:
                    return datetime.strptime(timestamp_str, "%Y-%m-%d_%H-%M-%S")
                except ValueError:
                    pass
                
                # Try format without dashes
                try:
                    return datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
                except ValueError:
                    pass
                
                # Try alternative: look for date in folder structure
                # Sometimes timestamp is in format YYYY-MM-DD_HH-MM-SS
                try:
                    return datetime.strptime(timestamp_str.replace('-', ''), "%Y%m%d_%H%M%S")
                except ValueError:
                    pass
                    
        except Exception:
            pass
        return None
    
    def get_display_name(self) -> str:
        """Get display name for the backup."""
        if self.timestamp:
            return f"{self.server_name} - {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
        return f"{self.server_name} - {self.filepath.name}"
    
    def get_size_display(self) -> str:
        """Get human-readable size."""
        size = self.size_bytes
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0
        return f"{size:.2f} TB"


class RestoreService:
    """Service for restoring backups."""
    
    def __init__(self):
        """Initialize the restore service."""
        pass
    
    def discover_backups(self, backup_path: str, servers: List) -> List[BackupInfo]:
        """Discover all available backups in the backup directory.
        
        Args:
            backup_path: Path to the backup directory
            servers: List of ServerConfig objects
            
        Returns:
            List of BackupInfo objects
        """
        backups = []
        backup_dir = Path(backup_path)
        
        if not backup_dir.exists():
            return backups
        
        # Create a map of server IDs to server names
        server_map = {s.server_id: s.server_name for s in servers}
        
        # Look for backups in server subdirectories
        for server_dir in backup_dir.iterdir():
            if not server_dir.is_dir():
                continue
            
            server_id = server_dir.name
            server_name = server_map.get(server_id, f"Server {server_id}")
            
            # Find all zip files in the server directory (both direct and in subdirectories)
            # Look for *.zip directly in server folder
            for backup_file in server_dir.glob("*.zip"):
                try:
                    backup_info = BackupInfo(backup_file, server_id, server_name)
                    backups.append(backup_info)
                except Exception:
                    continue
            
            # Also look for *.zip in timestamp subdirectories (one level deep)
            for subdir in server_dir.iterdir():
                if subdir.is_dir():
                    for backup_file in subdir.glob("*.zip"):
                        try:
                            backup_info = BackupInfo(backup_file, server_id, server_name)
                            backups.append(backup_info)
                        except Exception:
                            continue
        
        # Sort by timestamp (newest first)
        backups.sort(key=lambda b: b.timestamp if b.timestamp else datetime.min, reverse=True)
        
        return backups
    
    def restore_backup(
        self, 
        backup_info: BackupInfo, 
        destination_path: str,
        create_backup: bool = True
    ) -> Tuple[bool, str]:
        """Restore a backup to the specified destination.
        
        Args:
            backup_info: BackupInfo object containing backup details
            destination_path: Path where files should be restored
            create_backup: Whether to create a backup of existing files before restoring
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            dest_path = Path(destination_path)
            
            # Validate backup file exists
            if not backup_info.filepath.exists():
                return False, f"Backup file not found: {backup_info.filepath}"
            
            # Validate destination exists
            if not dest_path.exists():
                return False, f"Destination path does not exist: {dest_path}"
            
            # Create backup of existing files if requested
            if create_backup and any(dest_path.iterdir()):
                backup_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_dest = dest_path.parent / f"{dest_path.name}_backup_{backup_timestamp}"
                
                try:
                    shutil.copytree(dest_path, backup_dest)
                except Exception as e:
                    return False, f"Failed to create backup of existing files: {str(e)}"
            
            # Extract the backup
            try:
                with zipfile.ZipFile(backup_info.filepath, 'r') as zip_ref:
                    # Get list of files in the zip
                    file_list = zip_ref.namelist()
                    
                    # Files to skip (executables and DLLs that shouldn't be overwritten)
                    skip_extensions = ['.exe', '.dll', '.bat', '.cmd']
                    
                    extracted_count = 0
                    skipped_count = 0
                    error_count = 0
                    
                    # Extract files one by one, skipping problematic files
                    for file_name in file_list:
                        # Skip executable files
                        if any(file_name.lower().endswith(ext) for ext in skip_extensions):
                            skipped_count += 1
                            continue
                        
                        try:
                            zip_ref.extract(file_name, dest_path)
                            extracted_count += 1
                        except PermissionError:
                            # Skip files we can't write (might be in use)
                            skipped_count += 1
                        except Exception as e:
                            # Log but continue with other files
                            error_count += 1
                            print(f"Warning: Failed to extract {file_name}: {str(e)}")
                    
                    if extracted_count == 0:
                        return False, "No files were extracted from the backup"
                    
                    message = f"Successfully restored {extracted_count} file(s) to {dest_path}"
                    if skipped_count > 0:
                        message += f"\n{skipped_count} file(s) skipped (executables/locked files)"
                    if error_count > 0:
                        message += f"\n{error_count} file(s) failed to extract"
                    
                    return True, message
                
            except zipfile.BadZipFile:
                return False, "Backup file is corrupted or invalid"
            except Exception as e:
                return False, f"Failed to extract backup: {str(e)}"
                
        except Exception as e:
            return False, f"Restore failed: {str(e)}"
    
    def delete_backup(self, backup_info: BackupInfo) -> Tuple[bool, str]:
        """Delete a backup file.
        
        Args:
            backup_info: BackupInfo object to delete
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            if backup_info.filepath.exists():
                backup_info.filepath.unlink()
                return True, f"Deleted backup: {backup_info.filepath.name}"
            else:
                return False, "Backup file not found"
        except Exception as e:
            return False, f"Failed to delete backup: {str(e)}"
    
    def get_backup_contents(self, backup_info: BackupInfo) -> List[str]:
        """Get list of files contained in a backup.
        
        Args:
            backup_info: BackupInfo object
            
        Returns:
            List of file paths contained in the backup
        """
        try:
            with zipfile.ZipFile(backup_info.filepath, 'r') as zip_ref:
                return zip_ref.namelist()
        except Exception:
            return []

