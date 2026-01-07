"""Service for backing up to Google Cloud Storage."""
import os
from pathlib import Path
from typing import Optional

try:
    from google.cloud import storage
    from google.oauth2 import service_account
    GOOGLE_CLOUD_AVAILABLE = True
except ImportError:
    GOOGLE_CLOUD_AVAILABLE = False


class GoogleCloudBackupService:
    """Service for uploading backups to Google Cloud Storage."""

    def __init__(self):
        """Initialize the Google Cloud backup service."""
        self.storage_client: Optional[storage.Client] = None
        self.bucket_name: str = ""
        self.is_initialized = False

    def initialize(
        self, project_id: str, bucket_name: str, credentials_json_path: Optional[str] = None
    ) -> bool:
        """Initialize the Google Cloud Storage client."""
        if not GOOGLE_CLOUD_AVAILABLE:
            raise ImportError(
                "Google Cloud Storage library not installed. "
                "Install with: pip install google-cloud-storage"
            )

        try:
            if credentials_json_path and Path(credentials_json_path).exists():
                # Use service account credentials from file
                credentials = service_account.Credentials.from_service_account_file(
                    credentials_json_path
                )
                self.storage_client = storage.Client(
                    project=project_id, credentials=credentials
                )
            else:
                # Use default credentials (Application Default Credentials)
                self.storage_client = storage.Client(project=project_id)

            self.bucket_name = bucket_name
            self.is_initialized = True

            # Test connection
            return self.test_connection()
        except Exception:
            self.is_initialized = False
            return False

    def test_connection(self) -> bool:
        """Test the Google Cloud Storage connection."""
        if not self.is_initialized or not self.storage_client:
            return False

        try:
            # Try to get bucket metadata
            bucket = self.storage_client.bucket(self.bucket_name)
            bucket.reload()
            return True
        except Exception:
            return False

    async def upload_backup(self, local_file_path: str, remote_path: str) -> bool:
        """Upload a backup file to Google Cloud Storage."""
        if not self.is_initialized or not self.storage_client:
            raise RuntimeError(
                "Not initialized. Please initialize with project ID and bucket name first."
            )

        try:
            if not Path(local_file_path).exists():
                raise FileNotFoundError(f"Backup file not found: {local_file_path}")

            # Normalize remote path
            remote_path = remote_path.lstrip("/").replace("\\", "/")

            bucket = self.storage_client.bucket(self.bucket_name)
            blob_name = (
                f"{remote_path.rstrip('/')}/{Path(local_file_path).name}"
                if remote_path
                else Path(local_file_path).name
            )

            blob = bucket.blob(blob_name)
            blob.upload_from_filename(local_file_path, content_type="application/zip")

            return True
        except Exception:
            return False

    async def delete_backup(self, remote_path: str) -> bool:
        """Delete a backup file from Google Cloud Storage."""
        if not self.is_initialized or not self.storage_client:
            return False

        try:
            remote_path = remote_path.lstrip("/").replace("\\", "/")
            bucket = self.storage_client.bucket(self.bucket_name)
            blob = bucket.blob(remote_path)
            blob.delete()
            return True
        except Exception:
            return False

    async def list_backups(self, remote_path_prefix: str) -> list:
        """List backup files in Google Cloud Storage."""
        if not self.is_initialized or not self.storage_client:
            return []

        try:
            remote_path_prefix = remote_path_prefix.lstrip("/").replace("\\", "/") if remote_path_prefix else ""
            bucket = self.storage_client.bucket(self.bucket_name)
            blobs = bucket.list_blobs(prefix=remote_path_prefix)
            return [blob.name for blob in blobs]
        except Exception:
            return []

