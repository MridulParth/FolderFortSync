import os
import requests
import threading
import time
import mimetypes
from pathlib import Path
from queue import Queue
from typing import Dict, List, Tuple, Optional

class FileUploader:
    CHUNK_SIZE = 1024 * 1024  # 1MB chunks for better memory management
    MAX_CONCURRENT_UPLOADS = 3

    def __init__(self):
        self.upload_queue = Queue()
        self.active_uploads = []
        self.stop_flag = threading.Event()
        self.pause_flag = threading.Event()
        self.upload_threads = []
        self.total_uploaded = 0
        self.total_size = 0
        self.current_speed = 0
        self.upload_start_time = 0
        self.lock = threading.Lock()
        self._speed_update_time = time.time()
        self._bytes_since_last_update = 0

    def start_upload_workers(self):
        """Start upload worker threads"""
        self.upload_threads = []
        self.total_uploaded = 0
        self.total_size = 0
        self.upload_start_time = time.time()
        self._speed_update_time = time.time()
        self._bytes_since_last_update = 0

        for _ in range(self.MAX_CONCURRENT_UPLOADS):
            thread = threading.Thread(target=self._upload_worker, daemon=True)
            thread.start()
            self.upload_threads.append(thread)

    def _update_speed(self, bytes_uploaded: int):
        """Update upload speed calculation"""
        with self.lock:
            self._bytes_since_last_update += bytes_uploaded
            current_time = time.time()
            elapsed = current_time - self._speed_update_time

            if elapsed >= 1.0:  # Update speed every second
                self.current_speed = self._bytes_since_last_update / elapsed
                self._bytes_since_last_update = 0
                self._speed_update_time = current_time

    def _upload_worker(self):
        """Worker thread for processing uploads"""
        while not self.stop_flag.is_set():
            try:
                if self.pause_flag.is_set():
                    time.sleep(0.5)
                    continue

                if self.upload_queue.empty():
                    time.sleep(0.1)
                    continue

                upload_task = self.upload_queue.get()
                if upload_task is None:
                    break

                if len(upload_task) == 6:
                    file_path, target_folder_id, base_url, api_token, callbacks, base_path = upload_task
                else:
                    # Handle older format for backward compatibility
                    file_path, target_folder_id, base_url, api_token, callbacks = upload_task
                    base_path = None
                    
                self._upload_file(file_path, target_folder_id, base_url, api_token, callbacks, base_path)
                self.upload_queue.task_done()

            except Exception as e:
                if callbacks and 'on_error' in callbacks:
                    callbacks['on_error'](str(e))

    def _upload_file(self, file_path: str, target_folder_id: int, base_url: str, api_token: str, callbacks: Dict, base_path: str = None):
        """Upload a single file with proper error handling and progress tracking"""
        try:
            file_size = os.path.getsize(file_path)
            file_name = os.path.basename(file_path)
            mime_type = mimetypes.guess_type(file_path)[0] or 'application/octet-stream'
            
            # For uploads, we don't need to calculate relative paths as we're using the direct parent ID
            # The API uses the parent ID to place the file in the correct folder
            # rel_path is only needed for logging purposes
            rel_path = self._get_relative_path(file_path, base_path)

            # Prepare upload request
            upload_url = f"{base_url}/uploads"
            headers = {'Authorization': f'Bearer {api_token}'}

            with open(file_path, 'rb') as f:
                # Create form data
                files = {
                    'file': (file_name, f, mime_type),
                }
                data = {
                    'parentId': str(target_folder_id),
                    # No need to include relativePath as we're uploading directly to the correct parent folder
                }

                # Upload file
                start_time = time.time()
                print(f"Uploading {file_name} to folder ID: {target_folder_id} (path context: {rel_path})")
                response = requests.post(upload_url, headers=headers, files=files, data=data)

                if response.status_code == 201:
                    elapsed = time.time() - start_time
                    speed = file_size / elapsed if elapsed > 0 else 0
                    self._update_speed(file_size)

                    with self.lock:
                        self.total_uploaded += 1

                    if callbacks.get('on_success'):
                        callbacks['on_success'](file_path, self.current_speed)
                else:
                    error_msg = f"Upload failed for {file_name}: {response.text} (folder ID: {target_folder_id})"
                    if callbacks.get('on_error'):
                        callbacks['on_error'](error_msg)
                    raise Exception(error_msg)

        except Exception as e:
            if callbacks.get('on_error'):
                callbacks['on_error'](f"Upload error for {file_path}: {str(e)}")
            raise

    def _get_relative_path(self, file_path: str, base_path: str = None) -> str:
        """Convert local path to relative path for cloud storage, preserving folder structure"""
        if base_path is None:
            return ""
        
        # Normalize paths to handle different path formats
        file_path = os.path.normpath(file_path)
        base_path = os.path.normpath(base_path)
        
        # Ensure base_path ends with separator for proper relative path calculation
        if not base_path.endswith(os.sep):
            base_path += os.sep
            
        # Check if file_path actually starts with base_path
        if file_path.startswith(base_path):
            # Get the directory portion of the file path, relative to the base path
            file_dir = os.path.dirname(file_path)
            rel_dir = os.path.relpath(file_dir, base_path)
            
            # Convert to forward slashes for API consistency
            rel_dir = rel_dir.replace('\\', '/')
            
            # Handle root directory case
            if rel_dir == '.' or not rel_dir:
                return ""
                
            # Prevent duplicate folder nesting by checking if rel_dir contains parent folder name
            parts = rel_dir.split('/')
            if len(parts) > 1 and parts[0] == parts[1]:
                # Remove the duplicate folder reference
                parts.pop(0)
                rel_dir = '/'.join(parts)
                
            return rel_dir
            
        return ""

    def queue_upload(self, file_path: str, target_folder_id: int, base_url: str, api_token: str, callbacks: Dict, base_path: str = None):
        """Add a file to the upload queue"""
        # Update total size
        try:
            with self.lock:
                self.total_size += os.path.getsize(file_path)
        except OSError:
            pass  # Ignore errors in size calculation
        self.upload_queue.put((file_path, target_folder_id, base_url, api_token, callbacks, base_path))

    def pause(self):
        """Pause all uploads"""
        self.pause_flag.set()

    def resume(self):
        """Resume all uploads"""
        self.pause_flag.clear()

    def stop(self):
        """Stop all uploads gracefully"""
        self.stop_flag.set()
        
        # Clear the queue to prevent blocked join
        while not self.upload_queue.empty():
            try:
                self.upload_queue.get_nowait()
                self.upload_queue.task_done()
            except Exception:
                pass
                
        # Add termination signals
        for _ in self.upload_threads:
            try:
                self.upload_queue.put(None, block=False)
            except Exception:
                pass
            
        # Join threads with timeout to avoid hanging
        for thread in self.upload_threads:
            try:
                thread.join(timeout=0.5)  # Shorter timeout to avoid UI freeze
            except Exception:
                pass
            
        self.upload_threads.clear()
        self.total_uploaded = 0
        self.total_size = 0
        self.current_speed = 0