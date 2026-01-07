"""Data models for WinGSM Backup Manager."""
from dataclasses import dataclass, field
from datetime import datetime, time
from enum import Enum
from typing import List, Optional


class ScheduleType(Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    INTERVAL = "interval"


class CloudBackupType(Enum):
    NONE = "none"
    ONEDRIVE = "onedrive"
    GOOGLE_CLOUD = "google_cloud"


class BackupStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ServerConfig:
    """Configuration for a game server."""
    server_id: str
    server_name: str
    game_type: str = ""
    server_path: str = ""
    save_game_path: str = ""
    enabled: bool = True

    def to_dict(self):
        return {
            "server_id": self.server_id,
            "server_name": self.server_name,
            "game_type": self.game_type,
            "server_path": self.server_path,
            "save_game_path": self.save_game_path,
            "enabled": self.enabled
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            server_id=data.get("server_id", ""),
            server_name=data.get("server_name", ""),
            game_type=data.get("game_type", ""),
            server_path=data.get("server_path", ""),
            save_game_path=data.get("save_game_path", ""),
            enabled=data.get("enabled", True)
        )


@dataclass
class BackupSchedule:
    """Configuration for a backup schedule."""
    schedule_id: str = ""
    name: str = ""
    server_ids: List[str] = field(default_factory=list)
    schedule_type: ScheduleType = ScheduleType.DAILY
    time: time = field(default_factory=lambda: datetime.now().time())
    interval_minutes: int = 60
    days_of_week: List[int] = field(default_factory=list)  # 0=Monday, 6=Sunday
    enabled: bool = True
    backup_path: str = ""
    retention_days: int = 7
    enable_cloud_backup: bool = False
    cloud_backup_type: CloudBackupType = CloudBackupType.NONE
    cloud_backup_path: str = "WinGSMBackups"

    def to_dict(self):
        return {
            "schedule_id": self.schedule_id,
            "name": self.name,
            "server_ids": self.server_ids,
            "schedule_type": self.schedule_type.value,
            "time": self.time.strftime("%H:%M:%S"),
            "interval_minutes": self.interval_minutes,
            "days_of_week": self.days_of_week,
            "enabled": self.enabled,
            "backup_path": self.backup_path,
            "retention_days": self.retention_days,
            "enable_cloud_backup": self.enable_cloud_backup,
            "cloud_backup_type": self.cloud_backup_type.value,
            "cloud_backup_path": self.cloud_backup_path
        }

    @classmethod
    def from_dict(cls, data):
        time_str = data.get("time", "00:00:00")
        if isinstance(time_str, str):
            time_obj = datetime.strptime(time_str, "%H:%M:%S").time()
        else:
            time_obj = datetime.now().time()

        return cls(
            schedule_id=data.get("schedule_id", ""),
            name=data.get("name", ""),
            server_ids=data.get("server_ids", []),
            schedule_type=ScheduleType(data.get("schedule_type", "daily")),
            time=time_obj,
            interval_minutes=data.get("interval_minutes", 60),
            days_of_week=data.get("days_of_week", []),
            enabled=data.get("enabled", True),
            backup_path=data.get("backup_path", ""),
            retention_days=data.get("retention_days", 7),
            enable_cloud_backup=data.get("enable_cloud_backup", False),
            cloud_backup_type=CloudBackupType(data.get("cloud_backup_type", "none")),
            cloud_backup_path=data.get("cloud_backup_path", "WinGSMBackups")
        )


@dataclass
class ServerBackupResult:
    """Result of a server backup operation."""
    server_id: str
    server_name: str
    success: bool = False
    backup_path: str = ""
    cloud_backup_path: str = ""
    cloud_backup_success: bool = False
    error_message: str = ""
    backup_size_bytes: int = 0


@dataclass
class BackupJob:
    """A backup job execution."""
    job_id: str = ""
    schedule_id: str = ""
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    status: BackupStatus = BackupStatus.PENDING
    message: str = ""
    server_results: List[ServerBackupResult] = field(default_factory=list)

    def to_dict(self):
        return {
            "job_id": self.job_id,
            "schedule_id": self.schedule_id,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "status": self.status.value,
            "message": self.message,
            "server_results": [
                {
                    "server_id": r.server_id,
                    "server_name": r.server_name,
                    "success": r.success,
                    "backup_path": r.backup_path,
                    "cloud_backup_path": r.cloud_backup_path,
                    "cloud_backup_success": r.cloud_backup_success,
                    "error_message": r.error_message,
                    "backup_size_bytes": r.backup_size_bytes
                }
                for r in self.server_results
            ]
        }


class OneDriveAccountType(Enum):
    PERSONAL = "personal"
    BUSINESS = "business"


@dataclass
class OneDriveConfig:
    """OneDrive configuration."""
    client_id: str = ""
    tenant_id: str = "common"
    account_type: OneDriveAccountType = OneDriveAccountType.PERSONAL
    is_authenticated: bool = False


@dataclass
class GoogleCloudConfig:
    """Google Cloud configuration."""
    project_id: str = ""
    bucket_name: str = ""
    credentials_json_path: str = ""
    is_initialized: bool = False


@dataclass
class ApplicationConfig:
    """Main application configuration."""
    windowsgsm_path: str = ""
    default_backup_path: str = ""
    servers: List[ServerConfig] = field(default_factory=list)
    schedules: List[BackupSchedule] = field(default_factory=list)
    onedrive_config: OneDriveConfig = field(default_factory=OneDriveConfig)
    google_cloud_config: GoogleCloudConfig = field(default_factory=GoogleCloudConfig)

    def to_dict(self):
        return {
            "windowsgsm_path": self.windowsgsm_path,
            "default_backup_path": self.default_backup_path,
            "servers": [s.to_dict() for s in self.servers],
            "schedules": [s.to_dict() for s in self.schedules],
            "onedrive_config": {
                "client_id": self.onedrive_config.client_id,
                "tenant_id": self.onedrive_config.tenant_id,
                "account_type": self.onedrive_config.account_type.value,
                "is_authenticated": self.onedrive_config.is_authenticated
            },
            "google_cloud_config": {
                "project_id": self.google_cloud_config.project_id,
                "bucket_name": self.google_cloud_config.bucket_name,
                "credentials_json_path": self.google_cloud_config.credentials_json_path,
                "is_initialized": self.google_cloud_config.is_initialized
            }
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            windowsgsm_path=data.get("windowsgsm_path", ""),
            default_backup_path=data.get("default_backup_path", ""),
            servers=[ServerConfig.from_dict(s) for s in data.get("servers", [])],
            schedules=[BackupSchedule.from_dict(s) for s in data.get("schedules", [])],
            onedrive_config=OneDriveConfig(
                client_id=data.get("onedrive_config", {}).get("client_id", ""),
                tenant_id=data.get("onedrive_config", {}).get("tenant_id", "common"),
                account_type=OneDriveAccountType(data.get("onedrive_config", {}).get("account_type", "personal")),
                is_authenticated=data.get("onedrive_config", {}).get("is_authenticated", False)
            ),
            google_cloud_config=GoogleCloudConfig(
                project_id=data.get("google_cloud_config", {}).get("project_id", ""),
                bucket_name=data.get("google_cloud_config", {}).get("bucket_name", ""),
                credentials_json_path=data.get("google_cloud_config", {}).get("credentials_json_path", ""),
                is_initialized=data.get("google_cloud_config", {}).get("is_initialized", False)
            )
        )

