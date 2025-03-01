import os
import requests
import threading
import time
from pathlib import Path
from typing import Dict, List, Tuple, Optional

class FolderManager:
    def __init__(self, api_token: str, base_url: str):
        self.api_token = api_token
        self.base_url = base_url
        self.folder_cache = {}
        self.lock = threading.Lock()

    def _make_request(self, method: str, endpoint: str, **kwargs) -> Tuple[bool, dict]:
        """Make an API request with proper error handling"""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
            "Accept": "application/json"  # Explicitly request JSON response
        }
        kwargs['headers'] = {**kwargs.get('headers', {}), **headers}

        try:
            response = requests.request(method, url, **kwargs)
            print(f"API Response ({method} {endpoint}): {response.status_code}")

            # Check if response is HTML instead of JSON
            content_type = response.headers.get('content-type', '')
            if 'html' in content_type.lower():
                print(f"Received HTML response instead of JSON")
                return False, {}

            if response.content:
                try:
                    data = response.json()
                    # Print response data for debugging
                    if response.status_code >= 400:
                        print(f"Error response: {data}")
                    return response.status_code < 400, data
                except ValueError as e:
                    print(f"Failed to parse JSON response: {e}")
                    print(f"Response content: {response.content[:200]}")
                    return False, {}
            return True, {}

        except requests.exceptions.RequestException as e:
            print(f"API request failed ({method} {endpoint}): {str(e)}")
            return False, {}
        except ValueError as e:
            print(f"Failed to parse response ({method} {endpoint}): {str(e)}")
            return False, {}

    def list_folders(self, parent_id: Optional[int] = None) -> Dict[str, int]:
        """List all folders, optionally under a specific parent"""
        params = {"type": "folder"}
        if parent_id is not None:
            params["parentIds"] = [str(parent_id)]

        success, data = self._make_request('GET', '/drive/file-entries', params=params)
        if not success:
            return {}

        folders = []
        if isinstance(data, dict) and 'data' in data:
            folders = data['data']
        elif isinstance(data, list):
            folders = data

        return {folder["name"]: folder["id"] for folder in folders if "name" in folder and "id" in folder}

    def create_folder(self, name: str, parent_id: Optional[int] = None) -> Optional[int]:
        """Create a new folder and return its ID"""
        # Validate folder name - API requires at least 3 characters
        original_name = name
        if len(name) < 3:
            print(f"Warning: Folder name '{name}' is less than 3 characters long. Adding underscores to meet 3-character requirement.")
            # Add underscores until name is at least 3 characters
            while len(name) < 3:
                name += "_"
            print(f"Adjusted folder name: '{name}'")
        
        payload = {
            "name": name,
            "type": "folder"
        }

        if parent_id is not None:
            payload["parentId"] = parent_id

        success, data = self._make_request('POST', '/folders', json=payload)
        if not success:
            print(f"Failed to create folder: {name}. Response data: {data}")
            return None

        if isinstance(data, dict):
            folder_id = data.get('id')
            if folder_id:
                # Record folder ID in cache
                self.folder_cache[name] = folder_id
                return folder_id

            # Alternative response structure
            folder_data = data.get('folder', {})
            if isinstance(folder_data, dict):
                folder_id = folder_data.get('id')
                if folder_id:
                    # Record folder ID in cache
                    self.folder_cache[name] = folder_id
                return folder_id

        print(f"Unexpected response format for folder creation: {data}")
        return None

    def ensure_folder_structure(self, local_path: str, cloud_parent_id: int) -> Dict[str, int]:
        """Create necessary folder structure in cloud storage"""
        folder_map = {"": cloud_parent_id}
        local_path = os.path.normpath(local_path)

        # Get all subdirectories first
        subdirs = []
        for root, dirs, _ in os.walk(local_path):
            rel_path = os.path.relpath(root, local_path)
            if rel_path == ".":
                rel_path = ""
            subdirs.append(rel_path)

        # Sort by path depth to ensure parent folders are created first
        subdirs.sort(key=lambda p: len(Path(p).parts))

        # Log the folder structure that will be created
        print(f"Creating folder structure with {len(subdirs)} directories")
        for subdir in subdirs:
            if subdir:  # Skip empty path (root)
                print(f"  - {subdir}")

        # Create folder structure
        for rel_path in subdirs:
            if not rel_path:  # Skip empty path (root)
                continue

            # Convert Windows path to proper format
            clean_path = rel_path.replace("\\", "/")
            parent_path = os.path.dirname(clean_path).replace("\\", "/")
            folder_name = os.path.basename(clean_path)

            # Get parent folder ID from our map
            parent_id = folder_map.get(parent_path)

            if parent_id is None:
                print(f"Error: Parent path '{parent_path}' not found in folder map")
                # Skip this folder creation since parent doesn't exist
                print(f"Skipping folder creation: {clean_path}")
                continue

            print(f"Creating folder '{folder_name}' under parent path '{parent_path}' (ID: {parent_id})")

            # Check if folder exists under the correct parent
            existing_folders = self.list_folders(parent_id)
            
            # First check exact name match
            if folder_name in existing_folders:
                folder_id = existing_folders[folder_name]
                print(f"Found existing folder: {clean_path} -> {folder_id}")
            else:
                # Create folder under the correct parent
                folder_id = self.create_folder(folder_name, parent_id)
                if folder_id:
                    print(f"Created new folder: {clean_path} -> {folder_id}")
                else:
                    print(f"Create folder API call returned None for {folder_name}")
                time.sleep(0.5)  # Rate limiting

            if folder_id:
                # Use the original path in our folder map
                folder_map[clean_path] = folder_id
                print(f"Mapped folder path '{clean_path}' to ID {folder_id}")
            else:
                print(f"Failed to create/map folder: {clean_path}")
        
        print(f"Final folder mapping: {folder_map}")
        return folder_map

    def get_folder_path(self, folder_id: int) -> str:
        """Get the full path of a folder by its ID"""
        success, data = self._make_request('GET', f'/drive/file-entries/{folder_id}')
        if success and isinstance(data, dict):
            return data.get("path", "")
        return ""