"""Service for backing up to OneDrive."""
import os
from pathlib import Path
from typing import Optional, Callable

import msal
from msal import PublicClientApplication


class OneDriveBackupService:
    """Service for uploading backups to OneDrive."""

    def __init__(self):
        """Initialize the OneDrive backup service."""
        self.app: Optional[PublicClientApplication] = None
        self.access_token: Optional[str] = None
        self.is_authenticated = False
        self.graph_endpoint = "https://graph.microsoft.com/v1.0"
        self.device_code_callback: Optional[Callable[[str], None]] = None

    async def authenticate(self, client_id: str, tenant_id: str = "common", is_personal: bool = True) -> bool:
        """Authenticate with OneDrive using MSAL.
        
        Args:
            client_id: Azure AD application client ID
            tenant_id: Tenant ID for business accounts (ignored for personal)
            is_personal: True for personal OneDrive, False for business
        """
        try:
            # For personal accounts, always use "consumers" endpoint
            # For business accounts, use the specified tenant ID
            authority_tenant = "consumers" if is_personal else tenant_id
            
            self.app = PublicClientApplication(
                client_id=client_id,
                authority=f"https://login.microsoftonline.com/{authority_tenant}"
            )

            # Scopes for Microsoft Graph API
            # Note: offline_access is added automatically by MSAL, don't include it
            scopes = [
                "https://graph.microsoft.com/Files.ReadWrite",
                "https://graph.microsoft.com/User.Read"
            ]

            # Try to get token from cache first
            accounts = self.app.get_accounts()
            if accounts:
                result = self.app.acquire_token_silent(scopes, account=accounts[0])
                if result and "access_token" in result:
                    self.access_token = result["access_token"]
                    self.is_authenticated = True
                    return True

            # For personal accounts, use device code flow (no redirect URI needed)
            # For business accounts, try interactive flow first, fall back to device code
            if is_personal:
                # Initiate device code flow
                flow = self.app.initiate_device_flow(scopes=scopes)
                
                if "user_code" not in flow:
                    error_desc = flow.get("error_description", "Unknown error")
                    raise Exception(f"Failed to initiate device code flow: {error_desc}")
                
                # Display device code to user via callback
                if self.device_code_callback:
                    message = (
                        f"To sign in, use a web browser to open the page:\n"
                        f"{flow['verification_uri']}\n\n"
                        f"And enter the code: {flow['user_code']}"
                    )
                    self.device_code_callback(message)
                
                # Wait for user to complete authentication
                result = self.app.acquire_token_by_device_flow(flow)
            else:
                # For business accounts, try interactive with proper redirect URI
                try:
                    result = self.app.acquire_token_interactive(
                        scopes=scopes,
                        redirect_uri="http://localhost"
                    )
                except Exception:
                    # Fall back to device code flow if interactive fails
                    flow = self.app.initiate_device_flow(scopes=scopes)
                    
                    if "user_code" not in flow:
                        error_desc = flow.get("error_description", "Unknown error")
                        raise Exception(f"Failed to initiate device code flow: {error_desc}")
                    
                    if self.device_code_callback:
                        message = (
                            f"To sign in, use a web browser to open the page:\n"
                            f"{flow['verification_uri']}\n\n"
                            f"And enter the code: {flow['user_code']}"
                        )
                        self.device_code_callback(message)
                    
                    result = self.app.acquire_token_by_device_flow(flow)

            # Check for errors in the result
            if result and "error" in result:
                error_msg = result.get("error_description", result.get("error", "Unknown error"))
                raise Exception(f"Authentication failed: {error_msg}")
            
            if result and "access_token" in result:
                self.access_token = result["access_token"]
                self.is_authenticated = True
                return True

            self.is_authenticated = False
            return False
        except Exception as e:
            self.is_authenticated = False
            # Re-raise the exception with details so the GUI can show it
            raise

    async def upload_backup(self, local_file_path: str, remote_path: str) -> bool:
        """Upload a backup file to OneDrive."""
        if not self.is_authenticated or not self.access_token:
            raise RuntimeError("Not authenticated. Please authenticate first.")

        try:
            import aiohttp

            if not Path(local_file_path).exists():
                raise FileNotFoundError(f"Backup file not found: {local_file_path}")

            # Normalize remote path
            if not remote_path.startswith("/"):
                remote_path = "/" + remote_path
            remote_path = remote_path.replace("\\", "/")
            if remote_path.endswith("/") and len(remote_path) > 1:
                remote_path = remote_path.rstrip("/")

            # Ensure folder exists
            folder_id = await self._ensure_folder_exists(remote_path)

            # Upload file
            file_name = Path(local_file_path).name
            if folder_id:
                upload_url = f"{self.graph_endpoint}/me/drive/items/{folder_id}:/{file_name}:/content"
            else:
                upload_url = f"{self.graph_endpoint}/me/drive/root:/{file_name}:/content"

            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/zip"
            }

            async with aiohttp.ClientSession() as session:
                with open(local_file_path, "rb") as f:
                    async with session.put(upload_url, headers=headers, data=f) as response:
                        return response.status in [200, 201, 204]

        except ImportError:
            # Fallback to requests if aiohttp not available
            import requests

            if not Path(local_file_path).exists():
                raise FileNotFoundError(f"Backup file not found: {local_file_path}")

            # Normalize remote path
            if not remote_path.startswith("/"):
                remote_path = "/" + remote_path
            remote_path = remote_path.replace("\\", "/")
            if remote_path.endswith("/") and len(remote_path) > 1:
                remote_path = remote_path.rstrip("/")

            # Ensure folder exists
            folder_id = await self._ensure_folder_exists(remote_path)

            # Upload file
            file_name = Path(local_file_path).name
            if folder_id:
                upload_url = f"{self.graph_endpoint}/me/drive/items/{folder_id}:/{file_name}:/content"
            else:
                upload_url = f"{self.graph_endpoint}/me/drive/root:/{file_name}:/content"

            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/zip"
            }

            with open(local_file_path, "rb") as f:
                response = requests.put(upload_url, headers=headers, data=f)
                return response.status_code in [200, 201, 204]

    async def _ensure_folder_exists(self, folder_path: str) -> Optional[str]:
        """Ensure a folder exists in OneDrive, return folder ID."""
        try:
            import aiohttp

            # Try to get the folder
            get_url = f"{self.graph_endpoint}/me/drive/root:{folder_path}"
            headers = {"Authorization": f"Bearer {self.access_token}"}

            async with aiohttp.ClientSession() as session:
                async with session.get(get_url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get("id")

            # Folder doesn't exist, create it
            path_parts = folder_path.strip("/").split("/")
            current_path = ""

            for part in path_parts:
                new_path = f"{current_path}/{part}" if current_path else part

                # Try to get folder
                get_url = f"{self.graph_endpoint}/me/drive/root:{new_path}"
                async with aiohttp.ClientSession() as session:
                    async with session.get(get_url, headers=headers) as response:
                        if response.status == 200:
                            data = await response.json()
                            current_path = new_path
                            continue

                # Create folder
                if current_path:
                    parent_url = f"{self.graph_endpoint}/me/drive/root:{current_path}"
                else:
                    parent_url = f"{self.graph_endpoint}/me/drive/root"

                create_data = {
                    "name": part,
                    "folder": {},
                    "@microsoft.graph.conflictBehavior": "rename"
                }

                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        f"{parent_url}/children",
                        headers=headers,
                        json=create_data
                    ) as response:
                        if response.status in [200, 201]:
                            data = await response.json()
                            current_path = new_path

            # Get final folder ID
            final_url = f"{self.graph_endpoint}/me/drive/root:{folder_path}"
            async with aiohttp.ClientSession() as session:
                async with session.get(final_url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get("id")

            return None

        except ImportError:
            # Fallback to requests
            import requests

            headers = {"Authorization": f"Bearer {self.access_token}"}

            # Try to get the folder
            get_url = f"{self.graph_endpoint}/me/drive/root:{folder_path}"
            response = requests.get(get_url, headers=headers)

            if response.status_code == 200:
                return response.json().get("id")

            # Create folder structure
            path_parts = folder_path.strip("/").split("/")
            current_path = ""

            for part in path_parts:
                new_path = f"{current_path}/{part}" if current_path else part

                get_url = f"{self.graph_endpoint}/me/drive/root:{new_path}"
                response = requests.get(get_url, headers=headers)

                if response.status_code == 200:
                    current_path = new_path
                    continue

                # Create folder
                if current_path:
                    parent_url = f"{self.graph_endpoint}/me/drive/root:{current_path}"
                else:
                    parent_url = f"{self.graph_endpoint}/me/drive/root"

                create_data = {
                    "name": part,
                    "folder": {},
                    "@microsoft.graph.conflictBehavior": "rename"
                }

                response = requests.post(
                    f"{parent_url}/children", headers=headers, json=create_data
                )

                if response.status_code in [200, 201]:
                    current_path = new_path

            # Get final folder ID
            final_url = f"{self.graph_endpoint}/me/drive/root:{folder_path}"
            response = requests.get(final_url, headers=headers)

            if response.status_code == 200:
                return response.json().get("id")

            return None

    async def test_connection(self) -> bool:
        """Test the OneDrive connection."""
        if not self.is_authenticated or not self.access_token:
            return False

        try:
            import aiohttp

            headers = {"Authorization": f"Bearer {self.access_token}"}
            url = f"{self.graph_endpoint}/me"

            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    return response.status == 200

        except ImportError:
            import requests

            headers = {"Authorization": f"Bearer {self.access_token}"}
            url = f"{self.graph_endpoint}/me"
            response = requests.get(url, headers=headers)
            return response.status_code == 200

