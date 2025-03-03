import os
import time
import mimetypes
import threading
import requests
from queue import Queue, Empty
from typing import Dict

class FileUploader:
    def __init__(self, num_threads: int = 5):
        self.upload_queue = Queue()
        self.upload_threads = []
        self.stop_flag = threading.Event()
        self.pause_flag = threading.Event()
        self.lock = threading.Lock()
        self.num_threads = num_threads
        self.total_uploaded = 0
        self.total_size = 0
        self.current_speed = 0
        self._bytes_since_last_update = 0
        self._speed_update_time = time.time()

    def start(self):
        """Start the upload worker threads"""
        self.start_upload_workers()

    def start_upload_workers(self):
        """Start the upload worker threads - used by sync_app.py"""
        # Clear pause flag when starting workers
        self.pause_flag.clear()
        # Clear stop flag when starting workers
        self.stop_flag.clear()

        # Only start new threads if we don't have active ones
        if not self.upload_threads or all(not t.is_alive() for t in self.upload_threads):
            self.upload_threads = []
            for i in range(self.num_threads):
                thread = threading.Thread(target=self._upload_worker, name=f"UploadWorker-{i+1}")
                thread.daemon = True
                thread.start()
                self.upload_threads.append(thread)
                print(f"Started upload worker thread: {thread.name}")

    def _update_speed(self, bytes_uploaded: int):
        """Update the upload speed"""
        self._bytes_since_last_update += bytes_uploaded
        current_time = time.time()
        elapsed = current_time - self._speed_update_time

        if elapsed >= 1.0:  # Update speed every second
            self.current_speed = self._bytes_since_last_update / elapsed
            self._bytes_since_last_update = 0
            self._speed_update_time = current_time

    def _upload_worker(self):
        """Worker thread for processing uploads"""
        thread = threading.current_thread()
        thread.current_file = None  # Add tracking for current file being processed
        print(f"Upload worker thread started: {thread.name}")
        # Pre-create the event object for reuse to reduce object creation overhead
        paused_or_stopped = threading.Event()

        while not self.stop_flag.is_set():
            try:
                # Clear current file when not processing
                thread.current_file = None
                
                # Check if paused - optimized pause handling
                if self.pause_flag.is_set():
                    # When paused, check periodically but don't consume CPU
                    print(f"Worker {thread.name} paused, waiting...")

                    # Use a single wait loop with short timeouts
                    # This allows the thread to be woken up when the pause flag is cleared
                    # while minimizing CPU usage
                    while self.pause_flag.is_set() and not self.stop_flag.is_set():
                        # Event.wait returns immediately if the event is set
                        # Otherwise, it waits for the specified timeout
                        # This is more efficient than a sleep loop
                        paused_or_stopped.clear()
                        paused_or_stopped.wait(timeout=0.2)

                    # Only print this message if we're continuing (not stopping)
                    if not self.stop_flag.is_set():
                        print(f"Worker {thread.name} continuing after pause")
                    else:
                        print(f"Worker {thread.name} exiting after pause due to stop flag")
                        break
                    continue

                # Check if queue is empty
                try:
                    # Use a timeout to allow checking stop flag
                    upload_task = self.upload_queue.get(timeout=1.0)
                except Empty:
                    # Correctly catch the Empty exception from queue module
                    time.sleep(0.1)  # Avoid busy-waiting
                    continue
                except Exception as e:
                    print(f"Error getting task from queue: {str(e)}")
                    time.sleep(0.1)
                    continue

                # Handle termination signal
                if upload_task is None:
                    print(f"Worker thread {thread.name} received termination signal")
                    self.upload_queue.task_done()
                    break

                # Process the upload task
                try:
                    if len(upload_task) == 6:
                        file_path, target_folder_id, base_url, api_token, callbacks, base_path = upload_task
                    else:
                        # Handle older format for backward compatibility
                        file_path, target_folder_id, base_url, api_token, callbacks = upload_task
                        base_path = None

                    # Set current file for tracking
                    thread.current_file = file_path
                    
                    # Check if we should still proceed (might have been stopped/paused)
                    if self.stop_flag.is_set():
                        print(f"Worker thread {thread.name} detected stop flag, breaking")
                        thread.current_file = None  # Clear current file
                        self.upload_queue.task_done()
                        break

                    # Check for pause flag
                    if self.pause_flag.is_set():
                        print(f"Worker thread {thread.name} is paused, returning task to queue")
                        # If paused during processing, put task back in queue
                        self.upload_queue.put(upload_task)
                        thread.current_file = None  # Clear current file
                        self.upload_queue.task_done()
                        time.sleep(0.5)
                        continue

                    # Proceed with upload
                    self._upload_file(file_path, target_folder_id, base_url, api_token, callbacks, base_path)

                    # Clear current file after completion
                    thread.current_file = None
                    self.upload_queue.task_done()
                except Exception as e:
                    print(f"Error processing upload task: {str(e)}")
                    if callbacks and 'on_error' in callbacks:
                        callbacks['on_error'](str(e))
                    # Clear current file on error
                    thread.current_file = None
                    self.upload_queue.task_done()

            except Exception as e:
                print(f"Worker thread error: {str(e)}")
                if 'callbacks' in locals() and callbacks and 'on_error' in callbacks:
                    callbacks['on_error'](str(e))
                # Clear current file on error
                thread.current_file = None
                time.sleep(0.5)  # Avoid rapid error cycles

        # Clear current file when exiting
        thread.current_file = None
        print(f"Worker thread {thread.name} exiting")

    # Register a callback to be called when pause is complete
    def register_pause_complete_callback(self, callback):
        """Register a callback to be notified when all in-progress uploads complete after pause"""
        self.pause_complete_callback = callback

    # Track network status for auto-recovery
    def set_network_recovery_callback(self, callback):
        """Set callback for network recovery detection"""
        self.network_recovery_callback = callback

    def _upload_file(self, file_path: str, target_folder_id: int, base_url: str, api_token: str, callbacks: Dict, base_path: str = None):
        """Upload a single file with proper error handling"""
        # Memory optimization: Limit size of failed_uploads_details list
        if hasattr(self, 'failed_uploads_details') and len(self.failed_uploads_details) > 100:
            # Keep only the 50 most recent failures
            self.failed_uploads_details = self.failed_uploads_details[-50:]
            
        try:
            # Check if stopped or paused before starting the upload
            if self.stop_flag.is_set():
                if callbacks.get('on_error'):
                    callbacks['on_error'](f"Upload cancelled for {file_path}: sync was stopped")
                return

            if self.pause_flag.is_set():
                if callbacks.get('on_error'):
                    callbacks['on_error'](f"Upload deferred for {file_path}: sync is paused")
                return

            # Verify file exists
            if not os.path.exists(file_path):
                error_msg = f"File not found: {file_path}"
                if callbacks.get('on_error'):
                    callbacks['on_error'](error_msg)
                return

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

                # Check one more time before starting the actual request
                if self.stop_flag.is_set():
                    if callbacks.get('on_error'):
                        callbacks['on_error'](f"Upload cancelled for {file_path}")
                    return

                # If paused, wait until resumed or stopped
                if self.pause_flag.is_set():
                    print(f"Upload of {file_name} paused before starting request")
                    while self.pause_flag.is_set() and not self.stop_flag.is_set():
                        time.sleep(0.1)

                    # Check if we should still proceed after waiting
                    if self.stop_flag.is_set():
                        if callbacks.get('on_error'):
                            callbacks['on_error'](f"Upload cancelled for {file_path}")
                        return
                    print(f"Resuming upload of {file_name} after pause")

                try:
                    # Use a timeout to make requests more interruptible
                    response = requests.post(upload_url, headers=headers, files=files, data=data, timeout=30)

                    # Check after request if we should continue processing the response
                    if self.stop_flag.is_set():
                        if callbacks.get('on_error'):
                            callbacks['on_error'](f"Upload completed but sync stopped for {file_name}")
                        return

                    if response.status_code == 201:
                        elapsed = time.time() - start_time
                        speed = file_size / elapsed if elapsed > 0 else 0
                        self._update_speed(file_size)

                        with self.lock:
                            self.total_uploaded += 1

                        if callbacks.get('on_success'):
                            callbacks['on_success'](file_path, self.current_speed)
                    else:
                        # Include both filename and full path in error for retry functionality
                        error_msg = f"Upload failed for {file_name}: HTTP {response.status_code} - {response.text} (folder ID: {target_folder_id})"
                        if callbacks.get('on_error'):
                            # Store as a structured error that includes the file path for retry
                            callbacks['on_error'](f"Upload error for {file_path}: {error_msg}")
                        raise Exception(error_msg)

                except requests.exceptions.Timeout:
                    if callbacks.get('on_error'):
                        callbacks['on_error'](f"Upload error for {file_path}: Timeout after 30 seconds")
                    raise Exception(f"Upload timeout for {file_name}")

                except requests.exceptions.RequestException as e:
                    # This could be due to connection being closed during pause/stop
                    if self.stop_flag.is_set():
                        if callbacks.get('on_error'):
                            callbacks['on_error'](f"Upload interrupted for {file_name}: sync was stopped")
                        return

                    if callbacks.get('on_error'):
                        callbacks['on_error'](f"Upload error for {file_path}: Network error - {str(e)}")
                    raise

        except Exception as e:
            if callbacks.get('on_error'):
                # Always include the file path as the first part after "Upload error for"
                # This consistent format helps the retry functionality
                error_msg = str(e)
                if "Upload error for" not in error_msg:
                    error_msg = f"Upload error for {file_path}: {error_msg}"
                    callbacks['on_error'](error_msg)
                else:
                    callbacks['on_error'](error_msg)

                # Store failed upload details for easier retry
                if not hasattr(self, 'failed_uploads_details'):
                    self.failed_uploads_details = []

                # Store structured data about the failed upload
                self.failed_uploads_details.append({
                    'file_path': file_path,
                    'target_folder_id': target_folder_id,
                    'error': error_msg,
                    'timestamp': time.time()
                })

                # Check if it's a network error for auto-recovery
                network_errors = ['ConnectionError', 'Timeout', 'Connection aborted', 
                            'forcibly closed', 'timed out', 'Network error']

                if any(err in error_msg for err in network_errors):
                    # Flag for potential auto-recovery
                    if not hasattr(self, 'network_issues_detected'):
                        self.network_issues_detected = True

                        # Start network monitoring for auto-recovery if not already running
                        if not hasattr(self, 'network_monitor_active') or not self.network_monitor_active:
                            self.network_monitor_active = True
                            threading.Thread(target=self._monitor_network_recovery, 
                                            args=(base_url, api_token, callbacks),
                                            daemon=True).start()
            raise

    def _monitor_network_recovery(self, base_url, api_token, callbacks):
        """Monitor for network recovery and auto-retry uploads"""
        retry_interval = 5  # seconds between retry attempts
        max_retries = 30    # maximum number of retries (5 sec * 30 = 2.5 min)
        attempt = 0

        recovery_url = f"{base_url}/drive/file-entries"  # Use an API endpoint for checking

        while attempt < max_retries and hasattr(self, 'network_issues_detected') and self.network_issues_detected:
            time.sleep(retry_interval)

            # Skip if we're paused or stopped
            if self.pause_flag.is_set() or self.stop_flag.is_set():
                continue

            # Try to call an API endpoint
            try:
                headers = {'Authorization': f'Bearer {api_token}'}
                response = requests.get(recovery_url, headers=headers, timeout=3)

                if response.status_code == 200:
                    print("Network connection recovered!")

                    # Trigger callback if registered
                    if hasattr(self, 'network_recovery_callback') and self.network_recovery_callback:
                        self.network_recovery_callback()

                    # Auto-retry failed uploads
                    if hasattr(self, 'failed_uploads_details') and self.failed_uploads_details:
                        self._auto_retry_failed_uploads(callbacks)

                    # Reset network issues flag
                    self.network_issues_detected = False
                    break

            except Exception:
                # Still having network issues
                attempt += 1

        self.network_monitor_active = False

    def _auto_retry_failed_uploads(self, callbacks):
        """Automatically retry failed uploads after network recovery"""
        if not hasattr(self, 'failed_uploads_details') or not self.failed_uploads_details:
            return

        # Get unique file paths from failed uploads, most recent first
        seen_paths = set()
        unique_failures = []

        for failure in sorted(self.failed_uploads_details, key=lambda x: x['timestamp'], reverse=True):
            if failure['file_path'] not in seen_paths:
                if os.path.exists(failure['file_path']):
                    unique_failures.append(failure)
                    seen_paths.add(failure['file_path'])

        if unique_failures:
            # Log that we're auto-retrying
            if callbacks.get('on_notice') and len(unique_failures) > 0:
                callbacks['on_notice'](f"Network connection restored! Auto-retrying {len(unique_failures)} failed uploads...")

            # Queue up the retries
            for failure in unique_failures:
                # Remove this item from our failed uploads list
                if failure in self.failed_uploads_details:
                    self.failed_uploads_details.remove(failure)

                # Make sure upload workers are running
                if not self.upload_threads or not any(t.is_alive() for t in self.upload_threads):
                    self.start_upload_workers()

                # Re-queue the upload
                self.queue_upload(
                    failure['file_path'], 
                    failure['target_folder_id'],
                    # These will be provided by sync_app when queuing
                    None,  # base_url 
                    None,  # api_token
                    None,  # callbacks
                    None   # base_path
                )

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

    def queue_upload(self, file_path: str, target_folder_id: int, base_url: str = None, api_token: str = None, 
                    callbacks: Dict = None, base_path: str = None):
        """Add a file to the upload queue"""
        # If base_url and api_token are None, this is likely a retry using the latest values
        # Use the latest values stored during normal uploads
        if base_url is None and hasattr(self, 'latest_base_url'):
            base_url = self.latest_base_url
        if api_token is None and hasattr(self, 'latest_api_token'):
            api_token = self.latest_api_token
        if callbacks is None and hasattr(self, 'latest_callbacks'):
            callbacks = self.latest_callbacks

        # Store these for future retries
        if base_url is not None:
            self.latest_base_url = base_url
        if api_token is not None:
            self.latest_api_token = api_token
        if callbacks is not None:
            self.latest_callbacks = callbacks

        # Update total size
        try:
            with self.lock:
                self.total_size += os.path.getsize(file_path)
        except OSError:
            pass  # Ignore errors in size calculation

        # Try to add to queue with retries
        max_retries = 3
        for attempt in range(max_retries):
            try:
                self.upload_queue.put((file_path, target_folder_id, base_url, api_token, callbacks, base_path))
                return
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"Failed to queue upload, retrying ({attempt+1}/{max_retries}): {str(e)}")
                    time.sleep(0.5)
                else:
                    print(f"Failed to queue upload after {max_retries} attempts: {str(e)}")
                    if callbacks and 'on_error' in callbacks:
                        callbacks['on_error'](f"Failed to queue {os.path.basename(file_path)}: {str(e)}")

    def pause(self):
        """Pause all uploads"""
        # First set the pause flag to signal all threads
        self.pause_flag.set()
        print("Upload paused - flag set")

        # Track active threads for pause completion detection
        self.active_threads_at_pause = [t for t in self.upload_threads if t.is_alive()]
        self.pause_tracking_active = True
        self.pause_start_time = time.time()

        # Additional logging for debugging
        print(f"Pause flag status: {self.pause_flag.is_set()}")
        print(f"Active upload threads: {len(self.active_threads_at_pause)}")

        # Log information about the in-progress uploads
        if self.active_threads_at_pause:
            print(f"Note: {len(self.active_threads_at_pause)} uploads currently in progress may complete before pausing takes effect")
            print("This is normal behavior as we cannot safely interrupt in-progress network operations")

            # Start a thread to monitor when all in-progress uploads complete
            threading.Thread(target=self._monitor_pause_completion, daemon=True).start()

        # Create a session with a very short timeout to effectively prevent new requests
        # This helps immediately interrupt any new requests that might get started
        try:
            for session in requests.sessions.Session.__subclasses__():
                if hasattr(session, 'request'):
                    # Store original request method for later restoration
                    if not hasattr(session, '_old_request'):
                        session._old_request = session.request
                    session.request = lambda *args, **kwargs: None

            # Force immediate timeout on existing sessions
            requests.adapters.DEFAULT_RETRIES = 0
            requests.adapters.DEFAULT_TIMEOUT = 0.1
        except Exception as e:
            print(f"Error while trying to pause network operations: {str(e)}")
            # Continue anyway as the pause flag should still work

    def _monitor_pause_completion(self):
        """Monitor when all in-progress uploads at pause time complete"""
        if not hasattr(self, 'active_threads_at_pause'):
            return

        # Wait for all active uploads to complete
        max_wait_time = 300  # 5 minutes maximum wait time
        check_interval = 0.5  # Check every half second

        # Create a snapshot of the total_uploaded count at pause time
        uploads_at_pause = self.total_uploaded

        # Track how many uploads were processed during pause
        uploads_during_pause = 0

        while self.pause_flag.is_set() and self.pause_tracking_active:
            # Check if all threads are done processing their current task
            all_busy = False
            for thread in self.active_threads_at_pause[:]:  # Use slice to avoid modifying during iteration
                if not thread.is_alive():
                    # Thread has died/exited
                    self.active_threads_at_pause.remove(thread)
                else:
                    # Thread is alive, but might be waiting for next task
                    all_busy = True

            # Also check if we've processed new uploads since pausing
            if self.total_uploaded > uploads_at_pause:
                uploads_during_pause = self.total_uploaded - uploads_at_pause
                uploads_at_pause = self.total_uploaded
                all_busy = True

            # If no threads are busy or if timeout reached, break
            if not all_busy or time.time() - self.pause_start_time > max_wait_time:
                if self.pause_tracking_active and self.pause_flag.is_set():
                    completion_message = f"All in-progress uploads have completed. Sync is fully paused."
                    if uploads_during_pause > 0:
                        completion_message = f"{uploads_during_pause} files completed during pause transition. Sync is now fully paused."

                    print(completion_message)

                    # Notify any callbacks that pause is complete
                    if hasattr(self, 'pause_complete_callback') and self.pause_complete_callback:
                        self.pause_complete_callback(uploads_during_pause)

                    self.pause_tracking_active = False
                break

            time.sleep(check_interval)

    def resume(self):
        """Resume all uploads"""
        # Reset request adapter settings to normal
        requests.adapters.DEFAULT_RETRIES = 3
        requests.adapters.DEFAULT_TIMEOUT = 30

        # Reset session behaviors that were modified during pause
        for session in requests.sessions.Session.__subclasses__():
            if hasattr(session, '_old_request'):
                session.request = session._old_request

        # Clear pause flag regardless of its state to ensure uploads can proceed
        self.pause_flag.clear()
        print("Upload resumed - flag cleared")
        print(f"Pause flag status: {self.pause_flag.is_set()}")

        # Check for active threads
        active_threads = [t for t in self.upload_threads if t.is_alive()]
        print(f"Active upload threads: {len(active_threads)}")

        # If no active threads, restart them
        if not active_threads:
            print("No active upload threads found. Restarting workers...")
            # Clean up any dead threads first
            self.upload_threads = [t for t in self.upload_threads if t.is_alive()]
            self.start_upload_workers()
        else:
            print(f"Resume: Continuing with {len(active_threads)} active threads")

            # Send a notification to wake up threads that might be stuck
            for thread in self.upload_threads:
                if thread.is_alive():
                    print(f"Signaling thread {thread.name} to continue")

    def stop(self):
        """Stop all uploads gracefully"""
        print("Stopping uploads gracefully...")

        # First clear any pause flag to ensure threads can continue and then exit
        if self.pause_flag.is_set():
            self.pause_flag.clear()
            print("Cleared pause flag to allow threads to exit properly")

        # Set the stop flag to prevent new work
        self.stop_flag.set()

        # Force immediate timeout of any active requests to avoid hanging
        # Save old timeout for potential reset later
        old_timeout = getattr(requests.adapters, 'DEFAULT_TIMEOUT', 30)
        requests.adapters.DEFAULT_TIMEOUT = 0.5

        # Clear the queue to prevent blocked join
        remaining_items = []
        try:
            while not self.upload_queue.empty():
                try:
                    item = self.upload_queue.get_nowait()
                    if item is not None:  # Save non-termination signals for potential restart
                        remaining_items.append(item)
                    self.upload_queue.task_done()
                except Exception as e:
                    print(f"Error clearing queue: {str(e)}")
                    break
        except Exception as e:
            print(f"Error accessing queue: {str(e)}")

        # Add termination signals to ensure threads exit
        for _ in range(len(self.upload_threads)):
            try:
                self.upload_queue.put(None, block=False)
            except Exception as e:
                print(f"Error adding termination signal: {str(e)}")
                pass

        # Join threads with timeout to avoid hanging
        active_threads = list(self.upload_threads)  # Make a copy to avoid modification issues
        for thread in active_threads:
            if thread.is_alive():
                try:
                    print(f"Waiting for thread {thread.name} to terminate...")
                    thread.join(timeout=2.0)  # Longer timeout for proper cleanup
                except Exception as e:
                    print(f"Error joining thread: {str(e)}")

        # Clear thread list and reset counters
        self.upload_threads.clear()
        self.total_uploaded = 0
        self.total_size = 0
        self.current_speed = 0

        # Restore defaults for potential future use
        requests.adapters.DEFAULT_TIMEOUT = old_timeout

        print("Upload stopped successfully")