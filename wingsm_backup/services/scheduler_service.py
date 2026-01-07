"""Service for scheduling backups."""
import asyncio
import uuid
from datetime import datetime
from typing import List, Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from ..models import (
    BackupJob,
    BackupStatus,
    CloudBackupType,
    ServerBackupResult,
    ServerConfig,
    BackupSchedule,
)


class SchedulerService:
    """Service for managing backup schedules."""

    def __init__(
        self,
        backup_service,
        windowsgsm_service,
        onedrive_service,
        google_cloud_service,
    ):
        """Initialize the scheduler service."""
        self.backup_service = backup_service
        self.windowsgsm_service = windowsgsm_service
        self.onedrive_service = onedrive_service
        self.google_cloud_service = google_cloud_service
        self.scheduler = BackgroundScheduler()
        self.schedules: List[BackupSchedule] = []
        self.backup_completed_callback = None

    def start(self):
        """Start the scheduler."""
        if not self.scheduler.running:
            self.scheduler.start()

    def stop(self):
        """Stop the scheduler."""
        if self.scheduler.running:
            self.scheduler.shutdown()

    def add_schedule(self, schedule: BackupSchedule):
        """Add a backup schedule."""
        self.schedules.append(schedule)

        if not schedule.enabled:
            return

        job_id = f"backup_{schedule.schedule_id}"

        if schedule.schedule_type.value == "daily":
            trigger = CronTrigger(
                hour=schedule.time.hour, minute=schedule.time.minute
            )
        elif schedule.schedule_type.value == "weekly":
            # APScheduler uses 0-6 for Monday-Sunday, but we store 0-6 as Monday-Sunday
            days = [d + 1 for d in schedule.days_of_week]  # Convert to 1-7 (Mon-Sun)
            trigger = CronTrigger(
                day_of_week=",".join(str(d) for d in days),
                hour=schedule.time.hour,
                minute=schedule.time.minute,
            )
        else:  # interval
            trigger = IntervalTrigger(minutes=schedule.interval_minutes)

        self.scheduler.add_job(
            self._execute_backup_job,
            trigger=trigger,
            id=job_id,
            args=[schedule.schedule_id],
            replace_existing=True,
        )

    def remove_schedule(self, schedule_id: str):
        """Remove a backup schedule."""
        self.schedules = [s for s in self.schedules if s.schedule_id != schedule_id]
        job_id = f"backup_{schedule_id}"
        try:
            self.scheduler.remove_job(job_id)
        except Exception:
            pass

    def get_schedule(self, schedule_id: str) -> Optional[BackupSchedule]:
        """Get a schedule by ID."""
        for schedule in self.schedules:
            if schedule.schedule_id == schedule_id:
                return schedule
        return None

    def get_all_schedules(self) -> List[BackupSchedule]:
        """Get all schedules."""
        return self.schedules.copy()

    def _execute_backup_job(self, schedule_id: str):
        """Execute a backup job (called by scheduler)."""
        # Run async backup in event loop
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        loop.run_until_complete(self.execute_backup_async(schedule_id))

    async def execute_backup_async(
        self, schedule_id: str, servers: Optional[List[ServerConfig]] = None
    ) -> BackupJob:
        """Execute a backup for a schedule."""
        schedule = self.get_schedule(schedule_id)
        if not schedule:
            schedule = BackupSchedule()  # Fallback

        if servers is None:
            # Get servers from config
            from ..config_manager import ConfigManager
            config_manager = ConfigManager()
            config = config_manager.get_config()
            servers = config.servers or []

        job = BackupJob(
            job_id=str(uuid.uuid4()),
            schedule_id=schedule_id,
            start_time=datetime.now(),
            status=BackupStatus.RUNNING,
        )

        try:
            enabled_servers = [
                s
                for s in servers
                if s.server_id in schedule.server_ids and s.enabled
            ]

            for server in enabled_servers:
                try:
                    # Stop server
                    if self.windowsgsm_service.is_server_running(server.server_id):
                        self.windowsgsm_service.stop_server(server.server_id)
                        await asyncio.sleep(5)  # Wait for server to stop

                    # Perform local backup
                    result = await self.backup_service.backup_server(
                        server, schedule.backup_path
                    )
                    job.server_results.append(result)

                    # Upload to cloud if enabled
                    if (
                        result.success
                        and schedule.enable_cloud_backup
                        and result.backup_path
                    ):
                        try:
                            cloud_path = None
                            cloud_success = False

                            if schedule.cloud_backup_type == CloudBackupType.ONEDRIVE:
                                if self.onedrive_service.is_authenticated:
                                    cloud_path = (
                                        schedule.cloud_backup_path
                                        if schedule.cloud_backup_path
                                        else f"WinGSMBackups/{server.server_id}"
                                    )
                                    cloud_success = await self.onedrive_service.upload_backup(
                                        result.backup_path, cloud_path
                                    )
                                    result.cloud_backup_path = cloud_path
                                    result.cloud_backup_success = cloud_success

                            elif schedule.cloud_backup_type == CloudBackupType.GOOGLE_CLOUD:
                                if self.google_cloud_service.is_initialized:
                                    cloud_path = (
                                        f"{schedule.cloud_backup_path}/{server.server_id}"
                                        if schedule.cloud_backup_path
                                        else server.server_id
                                    )
                                    cloud_success = await self.google_cloud_service.upload_backup(
                                        result.backup_path, cloud_path
                                    )
                                    result.cloud_backup_path = cloud_path
                                    result.cloud_backup_success = cloud_success

                        except Exception as ex:
                            result.cloud_backup_success = False
                            # Don't fail the entire backup if cloud upload fails

                    # Restart server
                    if result.success:
                        self.windowsgsm_service.start_server(server.server_id)

                except Exception as ex:
                    job.server_results.append(
                        ServerBackupResult(
                            server_id=server.server_id,
                            server_name=server.server_name,
                            success=False,
                            error_message=str(ex),
                        )
                    )

            job.status = (
                BackupStatus.COMPLETED
                if all(r.success for r in job.server_results)
                else BackupStatus.FAILED
            )
            job.end_time = datetime.now()

            # Cleanup old backups
            self.backup_service.cleanup_old_backups(
                schedule.backup_path, schedule.retention_days
            )

            if self.backup_completed_callback:
                self.backup_completed_callback(job)

        except Exception as ex:
            job.status = BackupStatus.FAILED
            job.message = str(ex)
            job.end_time = datetime.now()

        return job

