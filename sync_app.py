# RUN THIS FILE (THIS IS THE MAIN.PY FILE)
import customtkinter as ctk
from tkinter import filedialog, messagebox
import threading
import os
from typing import Dict, List
from pathlib import Path
import time

from file_uploader import FileUploader
from folder_manager import FolderManager
from ui_components import (
    ProgressFrame, LogFrame, ControlPanel, ThemeColors, ThemeManager,
    StylishButton, play_completion_animation
)

class FolderFortSync:
    def __init__(self):
        self.setup_window()
        self.uploader = FileUploader()
        self.folder_manager = None
        self.failed_uploads = []
        self.is_paused = False    # Track pause state
        self.is_stopping = False  # Track stopping state

        self.setup_ui()
        self.bind_callbacks()

    def setup_window(self):
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.root = ctk.CTk()
        self.root.title("Folder Fort Sync")

        # Window dimensions
        window_width = 900
        window_height = 700

        # Get screen dimensions
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()

        # Calculate position for center of screen
        center_x = int((screen_width - window_width) / 2)
        center_y = int((screen_height - window_height) / 2)

        # Set window position to center of screen
        self.root.geometry(f"{window_width}x{window_height}+{center_x}+{center_y}")
        self.root.configure(fg_color=ThemeColors.BG_PRIMARY)

        # Set minimum window size
        self.root.minsize(800, 600)

        # Create a streamlined title bar with integrated status
        self.title_bar = ctk.CTkFrame(
            self.root, 
            fg_color=ThemeColors.BG_SECONDARY,
            height=32  # Reduced height
        )
        self.title_bar.pack(side="top", fill="x")

        # App logo and name - more compact layout
        app_title = ctk.CTkLabel(
            self.title_bar,
            text="Folder Fort",
            font=("SF Pro Display", 13, "bold"),
            text_color=ThemeColors.TEXT_PRIMARY
        )
        app_title.pack(side="left", padx=(10, 1), pady=4)

        app_title_accent = ctk.CTkLabel(
            self.title_bar,
            text="Sync",
            font=("SF Pro Display", 13, "bold"),
            text_color=ThemeColors.ACCENT
        )
        app_title_accent.pack(side="left", padx=(0, 5))

        # Add version inline with title
        app_version = ctk.CTkLabel(
            self.title_bar,
            text="v1.1",
            font=("SF Pro Display", 10),
            text_color=ThemeColors.TEXT_TERTIARY
        )
        app_version.pack(side="left", padx=(0, 0))

        # Status indicator (right side) - more compact
        self.status_indicator = ctk.CTkLabel(
            self.title_bar,
            text="●",
            font=("SF Pro Display", 16),
            text_color=ThemeColors.SUCCESS
        )
        self.status_indicator.pack(side="right", padx=(0, 5))

        self.status_text = ctk.CTkLabel(
            self.title_bar,
            text="Ready",
            font=("SF Pro Display", 12),
            text_color=ThemeColors.TEXT_PRIMARY
        )
        self.status_text.pack(side="right", padx=(0, 5))

        # Set window icon if platform supports it
        try:
            # Different approach based on platform
            import platform
            if platform.system() == "Windows":
                self.root.iconbitmap("icon.ico")
            elif platform.system() == "Darwin":  # macOS
                pass  # macOS uses the app bundle for icons
            else:  # Linux and others
                try:
                    from PIL import Image, ImageTk
                    import base64
                    import io
                except ImportError:
                    # Skip icon setup if PIL is not available
                    print("Note: Pillow not available, skipping icon setup")
                    pass

                # Simple folder icon as base64 (fallback if no icon file exists)
                folder_icon = "iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAYAAABzenr0AAAABHNCSVQICAgIfAhkiAAAAAlwSFlzAAAOxAAADsQBlSsOGwAAABl0RVh0U29mdHdhcmUAd3d3Lmlua3NjYXBlLm9yZ5vuPBoAAAGxSURBVFiF7ZY9TsNAEIU/O05DCQeggOQSXICGM9BwAArOAAUFR6DhAJTmANScg46Ugo4iRZQo2R12KRKJn+BNQsErdtea9+bNz44NkZGR8U8QAPKhR8DMDlRV39z9/Lut2WxmZnZiZjYajV6MMRX+dswAqOvakVL3wPjLQlVVIyB3rhN5GzDGLMxsMRwOp8aYubruJdJKKU+zJRaRfdRam+9aVNVD4CnwWWi73cOu7UMZDAaJtLOxiLh4vLtPzOxta2L3uUjv+STCYDB4THw6nR4mJH+qqupiFwnDt6YbkfO6rueqijFmICJnwGWwLjc3m/SfLyxnAPf39y5wF46rqnoADmNXJBGWZTkXkRPgLPTLb8E/KsEeUJZlJSL3wOXfku8lAFAUxQKYARR7/j9kLwEi0gANQFEUs0TkF4jIuZk5AGPMvTGmSUgeJQCQpYjcBfFJVKeUIC9yo+q7dYfkyVBVH4FH4FFEDsIhJCJnZnYbCN3dL/7SgJnNu6nVXeADMEkk70nVP3G3eRdF8RCuyqIoFsG7JyJvwFsg8sF4PH5Jld9kZGRkZGRkZGRkZPwtH/uyTBfEhIGiAAAAAElFTkSuQmCC"

                try:
                    # Try to load an actual icon file if it exists
                    icon = Image.open("icon.png")
                except:
                    # Use the embedded base64 icon as fallback
                    icon_data = base64.b64decode(folder_icon)
                    icon = Image.open(io.BytesIO(icon_data))

                icon_photo = ImageTk.PhotoImage(icon)
                self.root.iconphoto(True, icon_photo)
        except Exception as e:
            # Fail silently if icon setting doesn't work
            print(f"Could not set window icon: {str(e)}")

        # Configure grid weights
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

    def setup_ui(self):
        # Main container with improved padding balance
        self.main_frame = ctk.CTkFrame(
            self.root,
            fg_color=ThemeColors.BG_PRIMARY
        )
        self.main_frame.pack(expand=True, fill="both", padx=15, pady=(10, 15))

        # Theme switch removed - using static dark theme

        # Organize UI in top (form) and bottom (progress & logs) sections with proper proportion
        self.top_section = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.top_section.pack(fill="x", pady=(0, 5))

        self.bottom_section = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.bottom_section.pack(expand=True, fill="both")

        # Configure grid weights to allow log frame to expand properly
        self.bottom_section.grid_rowconfigure(1, weight=1)
        self.bottom_section.grid_columnconfigure(0, weight=1)

        # Control Panel in top section
        self.control_panel = ControlPanel(
            self.top_section,
            callbacks={
                "browse": self.browse_folder,
                "start": self.start_sync,
                "pause": self.pause_sync,
                "resume": self.resume_sync,
                "stop": self.stop_sync,
                "retry": self.retry_failed,
                "refresh_folders": self.refresh_cloud_folders,
                "show_message": self.show_message
            }
        )
        self.control_panel.pack(fill="x")

        # Progress Frame in bottom section
        self.progress_frame = ProgressFrame(self.bottom_section)
        self.progress_frame.grid(row=0, column=0, sticky="ew", pady=(5, 5), padx=5)

        # Log Frame in bottom section - given more space
        self.log_frame = LogFrame(self.bottom_section)
        self.log_frame.grid(row=1, column=0, sticky="nsew", pady=(0, 5), padx=5)

        # Set up network recovery handler in the uploader
        if hasattr(self.uploader, 'set_network_recovery_callback'):
            self.uploader.set_network_recovery_callback(self.handle_network_recovery)

    def handle_network_recovery(self):
        """Handle network recovery events with enhanced visual feedback and better logging"""
        # Count failed uploads for better user feedback
        failed_count = 0
        if hasattr(self.uploader, 'failed_uploads_details'):
            failed_count = len(self.uploader.failed_uploads_details)
        elif hasattr(self, 'failed_uploads'):
            failed_count = len(self.failed_uploads)

        # Log with comprehensive information (instead of multiple similar logs)
        recovery_message = f"Network connection restored! Auto-retrying {failed_count} failed uploads." if failed_count > 0 else "Network connection restored! Resuming uploads."
        self.log_frame.log(recovery_message, "success")
            
        # Show visual recovery animation
        self.progress_frame.indicate_network_recovery()

        # Update status indicator with animated effect
        def animate_recovery():
            # First show the recovery state
            self.root.after(0, lambda: self.status_indicator.configure(
                text="↻", 
                text_color=ThemeColors.SUCCESS
            ))
            self.root.after(0, lambda: self.status_text.configure(
                text=f"Network Restored - Auto-Retrying {failed_count} files" if failed_count > 0 else "Network Restored - Resuming"
            ))

            # Animate the status indicator to show activity
            for i in range(6):
                self.root.after(i*300, lambda idx=i: self.status_indicator.configure(
                    text="↻" if idx % 2 == 0 else "⟳",
                    text_color=ThemeColors.SUCCESS
                ))

            # After animation, restore normal active status
            self.root.after(2000, lambda: self.status_indicator.configure(
                text="●", 
                text_color=ThemeColors.SUCCESS
            ))
            self.root.after(2000, lambda: self.status_text.configure(
                text="Uploading"
            ))

        threading.Thread(target=animate_recovery, daemon=True).start()

    def bind_callbacks(self):
        self.upload_callbacks = {
            'on_success': self.handle_upload_success,
            'on_error': self.handle_upload_error,
            'on_progress': self.handle_upload_progress,
            'on_notice': self.handle_upload_notice
        }

    def handle_upload_notice(self, message: str):
        """Handle informational notices from the uploader"""
        # For network recovery, only log and don't show popup (reduce popup clutter)
        if "Network connection restored" in message:
            # Just log it without any popup - we'll show visual indicators only
            self.log_frame.log(message, "info")
            self.log_frame.log("Auto-retry in progress. No manual action needed!", "success")
            
            # Show recovery animation
            self.progress_frame.indicate_network_recovery()
        else:
            # For other notices, just log them without popup
            self.log_frame.log(message, "info")

    def show_message(self, message: str, level: str = "info"):
        """Show message to user and log it"""
        if level == "error":
            messagebox.showerror("Error", message)
        elif level == "warning":
            messagebox.showwarning("Warning", message)
        else:
            messagebox.showinfo("Information", message)
        self.log_frame.log(message, level)

    def browse_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.control_panel.folder_path.delete(0, "end")
            self.control_panel.folder_path.insert(0, folder)

    def refresh_cloud_folders(self):
        """Refresh the list of cloud folders"""
        api_token = self.control_panel.get_api_token()
        server_url = self.control_panel.get_server_url()

        if not api_token:
            self.log_frame.log("Please enter API token first", "error")
            return

        if not server_url:
            self.log_frame.log("Please enter server URL first", "error")
            return

        # Show loading indicator
        self.status_indicator.configure(text="○", text_color=ThemeColors.WARNING)
        self.status_text.configure(text="Refreshing folders...")

        # Update without blocking UI
        def do_refresh():
            try:
                self.folder_manager = FolderManager(api_token, server_url)
                folders = self.folder_manager.list_folders()
                folder_names = list(folders.keys())

                # Update UI from main thread
                self.root.after(0, lambda: self.control_panel.update_cloud_folders(folder_names))
                self.root.after(0, lambda: self.log_frame.log("Cloud folders refreshed successfully", "success"))
                self.root.after(0, lambda: self.status_indicator.configure(text="●", text_color=ThemeColors.SUCCESS))
                self.root.after(0, lambda: self.status_text.configure(text="Ready"))
            except Exception as e:
                error_msg = str(e)
                self.root.after(0, lambda: self.log_frame.log(f"Failed to refresh folders: {error_msg}", "error"))
                self.root.after(0, lambda: self.status_indicator.configure(text="●", text_color=ThemeColors.ERROR))
                self.root.after(0, lambda: self.status_text.configure(text="Error refreshing folders"))

        threading.Thread(target=do_refresh, daemon=True).start()

    def start_sync(self):
        api_token = self.control_panel.get_api_token()
        server_url = self.control_panel.get_server_url()
        folder_path = self.control_panel.get_folder_path()
        selected_cloud_folder = self.control_panel.get_selected_cloud_folder()

        if not all([api_token, server_url, folder_path, selected_cloud_folder]):
            self.log_frame.log("Please provide API token, server URL, local folder path, and select a cloud destination", "error")
            return

        # Update status with visual cue
        self.status_indicator.configure(text="⟳", text_color=ThemeColors.ACCENT)
        self.status_text.configure(text="Preparing sync...")

        # Reset progress tracking state completely for a fresh start
        self.is_paused = False
        self.is_stopping = False

        # Reset the uploader's progress tracking
        if hasattr(self.uploader, 'total_uploaded'):
            self.uploader.total_uploaded = 0

        # Reset progress bar to 0
        self.progress_frame.progress_var.set(0)
        self.progress_frame.total_var.set("0%")
        self.progress_frame.speed_var.set("0 B/s")
        self.progress_frame.eta_var.set("Calculating...")

        # Reset progress bar colors and status - PROCESSING is blue (ACCENT)
        self.progress_frame.progress_bar.configure(progress_color=ThemeColors.ACCENT)
        self.progress_frame.status_indicator.configure(text="PROCESSING", text_color=ThemeColors.ACCENT)
        self.progress_frame.is_paused = False
        self.progress_frame.is_pausing = False

        # Show initial animation in the progress bar
        self.progress_frame.indicate_activity()

        # Clear any previous failed uploads
        if hasattr(self.uploader, 'failed_uploads_details'):
            self.uploader.failed_uploads_details = []
        self.failed_uploads = []

        # Stop any existing uploader threads before starting new ones
        if hasattr(self.uploader, 'stop'):
            try:
                self.uploader.stop()
            except:
                pass

        # Create a fresh uploader instance for this new sync session
        self.uploader = FileUploader()

        # Restore network recovery callback
        if hasattr(self.uploader, 'set_network_recovery_callback'):
            self.uploader.set_network_recovery_callback(self.handle_network_recovery)

        # Create the folder manager and prepare sync
        try:
            self.folder_manager = FolderManager(api_token, server_url)
            # Start sync in separate thread
            threading.Thread(target=self._sync_process, daemon=True).start()
        except Exception as e:
            self.status_indicator.configure(text="●", text_color=ThemeColors.ERROR)
            self.status_text.configure(text="Setup Failed")
            self.log_frame.log(f"Failed to initialize sync: {str(e)}", "error")

    def _sync_process(self):
        try:
            folder_path = self.control_panel.get_folder_path()
            selected_cloud_folder = self.control_panel.get_selected_cloud_folder()

            # Get the cloud folder ID
            cloud_folders = self.folder_manager.list_folders()
            cloud_folder_id = cloud_folders.get(selected_cloud_folder)

            if not cloud_folder_id:
                self.log_frame.log(f"Could not find cloud folder: {selected_cloud_folder}", "error")
                return

            # Check if user wants to preserve parent folder structure
            preserve_parent = True  # We'll make this a default behavior

            parent_folder_id = cloud_folder_id
            if preserve_parent:
                # Get parent folder name from the selected path
                parent_folder_name = os.path.basename(folder_path)
                self.log_frame.log(f"Using parent folder name: {parent_folder_name}")

                # Check if parent folder already exists
                existing_folders = self.folder_manager.list_folders(cloud_folder_id)

                if parent_folder_name in existing_folders:
                    parent_folder_id = existing_folders[parent_folder_name]
                    self.log_frame.log(f"Using existing parent folder: {parent_folder_name} (ID: {parent_folder_id})")
                else:
                    # Create the parent folder (folder_manager will handle short names)
                    parent_folder_id = self.folder_manager.create_folder(parent_folder_name, cloud_folder_id)
                    if parent_folder_id:
                        self.log_frame.log(f"Created parent folder: {parent_folder_name} (ID: {parent_folder_id})")
                    else:
                        self.log_frame.log(f"Failed to create parent folder. Using destination folder instead.", "warning")
                        parent_folder_id = cloud_folder_id
            else:
                self.log_frame.log(f"Using destination folder directly without creating parent folder.")

            # Create folder structure for subfolders
            self.log_frame.log("Creating folder structure...")
            folder_map = self.folder_manager.ensure_folder_structure(folder_path, parent_folder_id)

            # Collect files for upload
            files_to_upload = []
            for root, _, files in os.walk(folder_path):
                for file in files:
                    full_path = os.path.join(root, file)

                    # Calculate relative path from base folder
                    rel_path = os.path.relpath(root, folder_path)

                    # Normalize path for consistent lookup
                    norm_rel_path = rel_path.replace("\\", "/")
                    if norm_rel_path == ".":
                        norm_rel_path = ""

                    # Get the folder ID for this path
                    target_id = folder_map.get(norm_rel_path, parent_folder_id)

                    # Debug log to see which parent folder is being used
                    self.log_frame.log(f"File: {file} - Located at: {norm_rel_path} - Will upload to folder ID: {target_id}")

                    files_to_upload.append((full_path, target_id))

            total_files = len(files_to_upload)
            self.log_frame.log(f"Found {total_files} files to upload")

            # Check if we have any files to upload
            if total_files == 0:
                self.log_frame.log("No files found to upload. Please check the selected folder.", "warning")
                # Show a message box to ensure user sees it
                self.show_message("No files found to upload. Please check that the selected folder contains files.", "warning")
                return

            # Start upload workers
            self.uploader.start_upload_workers()

            # Queue files for upload
            for file_path, parent_id in files_to_upload:
                self.uploader.queue_upload(
                    file_path,
                    parent_id,
                    self.control_panel.get_server_url(),
                    self.control_panel.get_api_token(),
                    self.upload_callbacks,
                    folder_path
                )

            # Wait for completion
            self.uploader.upload_queue.join()

            self.show_summary()

        except Exception as e:
            self.log_frame.log(f"Sync error: {str(e)}", "error")

    def handle_upload_success(self, file_path: str, speed: float):
        # Use consistent log format with timestamp generated in the log method
        self.log_frame.log(f"Uploaded: {os.path.basename(file_path)}", "success")

        # Update progress
        self.progress_frame.update_progress(
            self.uploader.total_uploaded,
            self.uploader.upload_queue.qsize() + self.uploader.total_uploaded,
            speed
        )

        # Update status bar
        remaining = self.uploader.upload_queue.qsize()
        self.status_text.configure(
            text=f"Uploading: {self.uploader.total_uploaded} completed, {remaining} remaining")

        # Update the progress frame status to SYNCING on first upload
        if self.uploader.total_uploaded == 1:
            # Ensure we show SYNCING instead of PROCESSING - Use green for active uploads
            self.progress_frame.status_indicator.configure(text="SYNCING", text_color=ThemeColors.SUCCESS)
            # Change progress bar color to green (SUCCESS) when actually syncing
            self.progress_frame.progress_bar.configure(progress_color=ThemeColors.SUCCESS)

        # If this was the last file, update status
        if remaining == 0:
            self.status_text.configure(text="Upload complete!")

    def handle_upload_error(self, error: str):
        self.log_frame.log(error, "error")

        # Store the original error message
        if error not in self.failed_uploads:
            self.failed_uploads.append(error)

        # Extract and store the file path for easier retry
        if isinstance(error, str) and "Upload error for " in error:
            try:
                # Extract file path from the error message
                parts = error.split("Upload error for ")
                if len(parts) > 1:
                    file_path = parts[1].split(":")[0].strip()

                    # Store the file path directly if it exists and isn't already in the list
                    if os.path.exists(file_path) and file_path not in self.failed_uploads:
                        self.failed_uploads.append(file_path)
                        print(f"Added file path to failed_uploads for retry: {file_path}")
            except Exception as e:
                print(f"Error extracting file path from error message: {str(e)}")
                # If extraction fails, we still have the original error message

    def handle_upload_progress(self, current: int, total: int, speed: float):
        self.progress_frame.update_progress(current, total, speed)

    def pause_sync(self):
        """Pause sync with proper visual animation transitions - using same mechanism as stop"""
        # First update buttons (disable pause, enable resume)
        self.control_panel.update_button_states(paused=True)

        # Set pausing state
        self.is_paused = False
        self.is_pausing = True

        # Update UI immediately to show pausing state
        self.status_indicator.configure(text="⏸", text_color=ThemeColors.WARNING)
        self.status_text.configure(text="Pausing...")

        # Show PAUSING animation first - critical for proper visual feedback
        self.progress_frame.indicate_pausing()

        # Force immediate UI update
        self.root.update_idletasks()

        # Log the pause action
        self.log_frame.log("⏸️ Sync pausing...", "warning")

        # Get current active threads BEFORE pausing
        active_thread_count = 0
        active_threads = []
        if hasattr(self.uploader, 'upload_threads'):
            active_threads = [t for t in self.uploader.upload_threads if t.is_alive()]
            active_thread_count = len(active_threads)

        # Log the actual number of active threads
        if active_thread_count > 0:
            self.log_frame.log(f"⚠️ Note: {active_thread_count} active uploads may complete before fully paused", "warning")

        # Start pause in a separate thread with longer animation timeout
        threading.Thread(target=lambda: self._pause_sync_thread(active_threads), daemon=True).start()

    def _pause_sync_thread(self, active_threads):
        """Pause the uploader - using same logic as stop but for pause context"""
        try:
            # Set the pause flag in the uploader
            self.uploader.pause()

            # Console warning with actual thread count
            print(f"Upload pausing - flag set")
            print(f"Pause flag status: {self.uploader.pause_flag.is_set()}")
            print(f"Tracking {len(active_threads)} active threads until they complete")

            # Now track thread status with shorter timeout (0.8 seconds)
            self._track_active_threads_for_pause(active_threads, max_wait=0.8)

        except Exception as e:
            self.log_frame.log(f"Error pausing sync: {str(e)}", "error")
            # Always ensure UI shows paused state
            self.root.after(100, self._transition_to_fully_paused)

    def _track_active_threads_for_pause(self, active_threads, max_wait=3.0):
        """Track specific file uploads that were in progress when pause was clicked"""
        # First time setup - get the names of files being uploaded when pause was clicked
        if not hasattr(self, '_files_being_uploaded_at_pause'):
            # Get the actual filenames from the upload queue
            self._files_being_uploaded_at_pause = []

            # Get files being actively uploaded by threads
            for thread in active_threads:
                if hasattr(thread, 'current_file') and thread.current_file:
                    filename = os.path.basename(thread.current_file)
                    self._files_being_uploaded_at_pause.append(filename)
                    print(f"Thread {thread.name} is uploading: {filename}")

            # If we couldn't get specific files, fallback to counting
            if not self._files_being_uploaded_at_pause:
                active_count = len(active_threads)
                self._active_thread_count_at_pause = active_count
                print(f"Couldn't get filenames, tracking {active_count} active threads instead")

            print(f"Pause tracking: tracking {len(self._files_being_uploaded_at_pause)} specific files in progress")            
            # Log the state for clarity
            self.log_frame.log(f"Pausing - waiting for active uploads to complete...", "info")

        # Simple check - see if any tracked files are still being uploaded
        files_still_uploading = False

        # Check which specific files are still being uploaded
        for thread in [t for t in active_threads if t.is_alive()]:
            if hasattr(thread, 'current_file') and thread.current_file:
                filename = os.path.basename(thread.current_file)
                if filename in self._files_being_uploaded_at_pause:
                    files_still_uploading = True
                    print(f"Still uploading tracked file: {filename}")

        # Fallback if we couldn't track specific files - check if thread count decreased
        if not self._files_being_uploaded_at_pause and hasattr(self, '_active_thread_count_at_pause'):
            current_active = len([t for t in active_threads if t.is_alive()])
            if current_active < self._active_thread_count_at_pause:
                files_still_uploading = False
            else:
                files_still_uploading = True

        # Check if we should transition to fully paused state
        transition_to_paused = not files_still_uploading

        if transition_to_paused:
            # Update UI to fully paused state
            self.log_frame.log("All active uploads at pause time have completed", "info")
            self._transition_to_fully_paused("all tracked uploads completed")

            # Clean up tracking variables
            if hasattr(self, '_files_being_uploaded_at_pause'):
                delattr(self, '_files_being_uploaded_at_pause')
            if hasattr(self, '_active_thread_count_at_pause'):
                delattr(self, '_active_thread_count_at_pause')
        else:
            # Continue checking at short intervals
            self.root.after(100, lambda: self._track_active_threads_for_pause(active_threads))

    def _transition_to_fully_paused(self, reason=""):
        """Synchronized transition to fully paused state - uses same logic as stop to fully stopped"""
        print(f"Transitioning to fully paused state: {reason}")

        # Update UI elements in coordinated manner
        # First update text status for immediate feedback
        self.status_text.configure(text="Paused")

        # Then trigger the full paused animation
        # Pass a callback to execute when animation completes
        self.progress_frame.indicate_paused(
            callback=lambda: self.root.after(300, self._finish_pause_transition)
        )

        # Log pause completion
        self.log_frame.log("⏸️ Sync paused", "warning")
        self.log_frame.log("➡️ Click RESUME to continue upload", "info")

        # Set final state flag
        self.is_pausing = False
        self.is_paused = True

    def _finish_pause_transition(self):
        """Complete the pause transition with UI cleanup and consistency (matches stop logic)"""
        # Ensure UI consistency
        self._ensure_pause_ui_consistency()

    def _ensure_pause_ui_consistency(self):
        """Make sure all UI elements are in sync for pause state"""
        try:
            # Force consistent state across all UI elements
            if not self.is_paused:
                return  # User already resumed

            # Status indicators
            self.status_indicator.configure(text="⏸", text_color=ThemeColors.WARNING)
            self.status_text.configure(text="Paused")

            # Progress frame
            self.progress_frame.is_pausing = False
            self.progress_frame.is_paused = True
            self.progress_frame.status_indicator.configure(text="PAUSED", text_color=ThemeColors.WARNING)
            self.progress_frame.progress_bar.configure(progress_color=ThemeColors.WARNING)
            self.progress_frame.speed_var.set("Paused")
            self.progress_frame.eta_var.set("Paused")
            self.progress_frame.speed_icon.configure(text="⏸", text_color=ThemeColors.WARNING)

            # Force UI update
            self.progress_frame.update_idletasks()
            self.root.update_idletasks()

            print("Pause UI consistency ensured")
        except Exception as e:
            print(f"Error ensuring pause UI consistency: {e}")

    def resume_sync(self):
        """Resume uploads with synchronized UI updates"""
        # Clear the paused flag immediately
        self.is_paused = False

        # Update buttons first (enable pause, disable resume)
        self.control_panel.update_button_states(paused=False)

        # Update UI elements in synchronized order
        try:
            # First update text status for immediate feedback
            self.status_indicator.configure(text="●", text_color=ThemeColors.SUCCESS)
            self.status_text.configure(text="Resuming...")
            self.root.update_idletasks()  # Force immediate update

            # Now transition progress frame with animation
            self.progress_frame.indicate_resumed()
            self.root.update_idletasks()  # Force immediate update

            # Log the resume action
            self.log_frame.log("▶️ Sync resumed", "success")

            # Resume the actual upload operations after UI updates
            try:
                self.uploader.resume()
                self.status_text.configure(text="Uploading")
            except Exception as e:
                self.log_frame.log(f"Error resuming uploads: {str(e)}", "error")

            # Ensure UI consistency
            self.root.after(100, self._ensure_resume_ui_consistency)

            # Verify uploads are working after a delay
            threading.Timer(1.0, self._check_upload_progress).start()
        except Exception as e:
            self.log_frame.log(f"Error updating UI for resume: {str(e)}", "error")
            # Basic fallback
            self.status_text.configure(text="Uploading")

    def _ensure_resume_ui_consistency(self):
        """Make sure all UI elements are in sync for resume state"""
        try:
            if self.is_paused:
                return  # User paused again

            # Force consistent state across all UI elements
            self.status_indicator.configure(text="●", text_color=ThemeColors.SUCCESS)
            self.status_text.configure(text="Uploading")

            # Progress frame - use green (SUCCESS) for active syncing
            self.progress_frame.is_paused = False
            self.progress_frame.is_pausing = False
            self.progress_frame.status_indicator.configure(text="SYNCING", text_color=ThemeColors.SUCCESS)
            self.progress_frame.progress_bar.configure(progress_color=ThemeColors.SUCCESS)  # Green for active syncing
            self.progress_frame.speed_icon.configure(text="↑", text_color=ThemeColors.SUCCESS)  # Green for active syncing

            # Force UI update
            self.progress_frame.update_idletasks()
            self.root.update_idletasks()
        except Exception as e:
            print(f"Error ensuring resume UI consistency: {e}")

    def _check_upload_progress(self):
        """Check if uploads are progressing after resume"""
        if hasattr(self.uploader, 'upload_threads'):
            active_threads = [t for t in self.uploader.upload_threads if t.is_alive()]

            if len(active_threads) == 0:
                self.log_frame.log("No active upload threads detected. Restarting workers...", "warning")
                self.uploader.start_upload_workers()

                # Schedule another check to verify restart worked
                threading.Timer(1.0, self._verify_restart).start()
            else:
                # Make sure pause flag is definitely cleared
                if self.uploader.pause_flag.is_set() and not self.is_paused:
                    self.log_frame.log("Pause flag still set despite resume. Clearing it again...", "warning")
                    self.uploader.pause_flag.clear()

                self.log_frame.log(f"Upload progress checked: {len(active_threads)} active threads", "info")

    def _verify_restart(self):
        """Verify that upload threads restarted properly"""
        if hasattr(self.uploader, 'upload_threads'):
            active_threads = [t for t in self.uploader.upload_threads if t.is_alive()]
            if len(active_threads) == 0 and not self.is_paused:
                self.log_frame.log("Upload threads failed to restart. Trying one more time...", "warning")
                # Try a more aggressive restart
                self.uploader.stop()
                time.sleep(0.2)  # Shorter delay for responsiveness
                self.uploader.start_upload_workers()

    def stop_sync(self):
        """Stop sync with proper visual animation transitions"""
        # Confirm before stopping
        confirmation = messagebox.askyesno("Confirmation", "Are you sure you want to stop the sync process?")
        if confirmation:
            # Set stopping state
            self.is_stopping = True

            # Update UI immediately to show stopping state
            self.status_indicator.configure(text="⏹", text_color=ThemeColors.ERROR)
            self.status_text.configure(text="Stopping...")

            # Show STOPPING animation first - critical for proper visual feedback
            # This starts the blinking animation and "STOPPING" text
            self.progress_frame.indicate_stopping()

            # Force immediate UI update
            self.root.update_idletasks()

            # Log the stop action
            self.log_frame.log("⏹️ Sync stopping...", "error")

            # Get current active threads BEFORE stopping
            active_thread_count = 0
            active_threads = []
            if hasattr(self.uploader, 'upload_threads'):
                active_threads = [t for t in self.uploader.upload_threads if t.is_alive()]
                active_thread_count = len(active_threads)

            # Log the actual number of active threads
            if active_thread_count > 0:
                self.log_frame.log(f"⚠️ Note: {active_thread_count} active uploads may complete before fully stopped", "warning")

            # Stop all uploads in a separate thread, but with longer animation timeout
            # to ensure proper visual feedback
            threading.Thread(target=lambda: self._stop_sync_thread(active_threads, force_kill=True), daemon=True).start()

    def _stop_sync_thread(self, active_threads, force_kill=True):
        """Stop the uploader and force terminate all active threads"""
        try:
            # Stop the uploader (this will terminate worker threads)
            self.uploader.stop()

            # Console warning with actual thread count
            print(f"Upload stopping - flag set")
            print(f"Stop flag status: True")
            print(f"Tracking {len(active_threads)} active threads until they complete")

            # If force_kill is enabled, try to interrupt threads immediately
            if force_kill and active_threads:
                # Allow a very brief moment for clean termination
                time.sleep(0.2)

                # Force kill any remaining threads
                still_active = [t for t in active_threads if t.is_alive()]
                if still_active:
                    print(f"Force terminating {len(still_active)} remaining threads")
                    for t in still_active:
                        try:
                            if hasattr(t, '_Thread__stop'):
                                t._Thread__stop()
                        except:
                            pass  # Best effort only

            # Now track thread status with shorter timeout (0.8 seconds)
            self._track_active_threads_for_stop(active_threads, max_wait=0.8)

        except Exception as e:
            self.log_frame.log(f"Error stopping sync: {str(e)}", "error")
            # Always ensure UI shows stopped state
            self.root.after(100, self._transition_to_fully_stopped)

    def _track_active_threads_for_stop(self, active_threads, max_wait=3.0):
        """Track specific file uploads that were in progress when stop was clicked"""
        # First time setup - get the names of files being uploaded when stop was clicked
        if not hasattr(self, '_files_being_uploaded_at_stop'):
            self._files_being_uploaded_at_stop = []
            for thread in active_threads:
                if hasattr(thread, 'current_file') and thread.current_file:
                    filename = os.path.basename(thread.current_file)
                    self._files_being_uploaded_at_stop.append(filename)
                    print(f"Thread {thread.name} is uploading: {filename}")

            # Fallback if we couldn't get specific files
            if not self._files_being_uploaded_at_stop:
                active_count = len(active_threads)
                self._active_thread_count_at_stop = active_count
                print(f"Couldn't get filenames, tracking {active_count} active threads instead")

            print(f"Stop tracking: tracking {len(self._files_being_uploaded_at_stop)} specific files in progress")
            self.log_frame.log(f"Stopping - waiting for active uploads to complete...", "info")

        files_still_uploading = False
        for thread in [t for t in active_threads if t.is_alive()]:
            if hasattr(thread, 'current_file') and thread.current_file:
                filename = os.path.basename(thread.current_file)
                if filename in self._files_being_uploaded_at_stop:
                    files_still_uploading = True
                    print(f"Still uploading tracked file: {filename}")

        #Fallback if we couldn't track specific files
        if not self._files_being_uploaded_at_stop and hasattr(self, '_active_thread_count_at_stop'):
            current_active = len([t for t in active_threads if t.is_alive()])
            if current_active < self._active_thread_count_at_stop:
                files_still_uploading = False
            else:
                files_still_uploading = True

        transition_to_stopped = not files_still_uploading

        if transition_to_stopped:
            self.log_frame.log("All active uploads at stop time have completed", "info")
            self._transition_to_fully_stopped("all tracked uploads completed")

            if hasattr(self, '_files_being_uploaded_at_stop'):
                delattr(self, '_files_being_uploaded_at_stop')
            if hasattr(self, '_active_thread_count_at_stop'):
                delattr(self, '_active_thread_count_at_stop')
        else:
            self.root.after(100, lambda: self._track_active_threads_for_stop(active_threads))

    def _transition_to_fully_stopped(self, reason=""):
        """Synchronized transition to fully stopped state"""
        print(f"Transitioning to fully stopped state: {reason}")

        # Update UI elements in coordinated manner
        # First update text status for immediate feedback
        self.status_text.configure(text="Stopped")

        # Then trigger the full stopped animation
        # Pass a callback to execute when animation completes
        self.progress_frame.indicate_stopped(
            callback=lambda: self.root.after(300, self._finish_stop_transition)
        )

        # Log stop completion
        self.log_frame.log("✓ Sync fully stopped", "error")
        self.log_frame.log("➡️ Click START to begin a new upload", "info")

        # Clear stopping state
        self.is_stopping = False

    def _finish_stop_transition(self):
        """Complete the stop transition with UI cleanup and reset button"""
        # Ensure UI consistency first
        self._ensure_stop_ui_consistency()

        # Then show reset button with smooth animation
        self._show_reset_button()

    def _ensure_stop_ui_consistency(self):
        """Make sure all UI elements are in sync for stopped state"""
        try:
            # Force consistent state across all UI elements
            self.status_indicator.configure(text="⏹", text_color=ThemeColors.ERROR)
            self.status_text.configure(text="Stopped")

            # Progress frame
            if hasattr(self.progress_frame, 'is_stopping'):
                self.progress_frame.is_stopping = False
            if hasattr(self.progress_frame, 'is_stopped'):
                self.progress_frame.is_stopped = True

            self.progress_frame.status_indicator.configure(text="STOPPED", text_color=ThemeColors.ERROR)
            self.progress_frame.progress_bar.configure(progress_color=ThemeColors.ERROR)
            self.progress_frame.speed_var.set("Stopped")
            self.progress_frame.eta_var.set("Click START for new upload")
            self.progress_frame.speed_icon.configure(text="⏹", text_color=ThemeColors.ERROR)

            # Force UI update
            self.progress_frame.update_idletasks()
            self.root.update_idletasks()

            print("Stop UI consistency ensured")
        except Exception as e:
            print(f"Error ensuring stop UI consistency: {e}")

    def _show_reset_button(self):
        """Show a reset button after stopping - NO animations, NO transparency"""
        try:
            # Make sure any previous reset button is removed first
            if hasattr(self, 'reset_button'):
                self._safely_destroy_reset_button()
                
            # Make sure upload button is also removed if it exists
            if hasattr(self, 'new_upload_button'):
                self._safely_destroy_upload_button()
                
            # Wait a tiny bit to ensure destruction completed
            time.sleep(0.05)
            
            # Create a reset button that appears after stopping
            self.reset_button = StylishButton(
                self.progress_frame,
                text="🔄 Reset Progress",
                command=self._reset_after_stop,
                fg_color=ThemeColors.ACCENT,
                hover_color=ThemeColors.ACCENT_LIGHT,
                width=150,
                height=30
            )

            # Position it in the center - directly with normal colors
            self.reset_button.place(relx=0.5, rely=0.85, anchor="center")
            
            # Apply colors directly first for immediate visibility
            self.reset_button.configure(fg_color=ThemeColors.ACCENT, text_color=ThemeColors.TEXT_PRIMARY)
            
            # Then do the fade-in animation
            self._fade_in_reset_button()
            
        except Exception as e:
            print(f"Error creating reset button: {e}")

    def _fade_in_reset_button(self):
        """Simple fade-in animation for reset button"""
        try:
            if not hasattr(self, 'reset_button') or not self.reset_button.winfo_exists():
                return

            # Original colors
            original_fg = ThemeColors.ACCENT
            original_text = ThemeColors.TEXT_PRIMARY
            bg_color = ThemeColors.BG_PRIMARY

            # Start with background color (not "transparent") to avoid errors
            self.reset_button.configure(fg_color=bg_color, text_color=bg_color)

            # Fade in over 5 steps
            steps = 5
            for i in range(1, steps+1):
                # Calculate opacity
                opacity = i / steps

                # Blend colors with background for fade effect
                fg_color = self._blend_colors(bg_color, original_fg, opacity)
                text_color = self._blend_colors(bg_color, original_text, opacity)

                # Apply colors
                self.reset_button.configure(fg_color=fg_color, text_color=text_color)
                self.reset_button.update_idletasks()

                # Short delay between steps
                time.sleep(0.03)

            # Ensure final state is correct
            self.reset_button.configure(fg_color=original_fg, text_color=original_text)

            # Add subtle bounce if desired
            self._add_subtle_bounce_to_reset_button()
        except Exception as e:
            print(f"Error in button fade animation: {e}")
            # Fallback - just show the button
            try:
                if hasattr(self, 'reset_button') and self.reset_button.winfo_exists():
                    self.reset_button.configure(fg_color=ThemeColors.ACCENT, text_color=ThemeColors.TEXT_PRIMARY)
            except:
                pass

    def _add_subtle_bounce_to_reset_button(self):
        """Add a very subtle bounce effect for extra polish"""
        try:
            if not hasattr(self, 'reset_button') or not self.reset_button.winfo_exists():
                return

            # Define subtle bounce keyframes (scale values)
            bounce_scales = [1.0, 1.05, 1.0]
            bounce_times = [0, 80, 150]  # milliseconds

            # Apply each scale with appropriate timing
            for i, scale in enumerate(bounce_scales):
                self.root.after(bounce_times[i], 
                    lambda s=scale: self._apply_button_scale(s))
        except Exception as e:
            print(f"Error adding button bounce: {e}")

    def _apply_button_scale(self, scale):
        """Apply scale effect to button"""
        try:
            if hasattr(self, 'reset_button') and self.reset_button.winfo_exists():
                # Calculate new dimensions
                orig_width = 150
                orig_height = 30
                new_width = int(orig_width * scale)
                new_height = int(orig_height * scale)

                # Apply new dimensions, keeping button centered
                self.reset_button.configure(width=new_width, height=new_height)
        except Exception as e:
            print(f"Error scaling button: {e}")

    def _reset_after_stop(self):
        """Reset the UI to default state after stopping"""
        try:
            # Provide immediate visual feedback that button was clicked
            try:
                if hasattr(self, 'reset_button') and self.reset_button.winfo_exists():
                    self.reset_button.configure(text="Resetting...")
                    self.reset_button.update_idletasks()
            except:
                pass

            # Slide button out with smooth animation
            self._animate_reset_button_exit()

            # Reset the UI state after animation
            self.root.after(180, self._complete_reset_after_button_exit)
        except Exception as e:
            print(f"Error handling reset button: {e}")
            # Emergency fallback
            self._complete_reset_after_button_exit()

    def _animate_reset_button_exit(self):
        """Buttery smooth exit animation for reset button with enhanced fade-out effect"""
        try:
            if not hasattr(self, 'reset_button') or not self.reset_button.winfo_exists():
                return

            # First move the button out to the right as it fades away
            # This creates a smoother exit animation without position jitter
            
            # Get the original position before animation
            if not hasattr(self, '_reset_button_orig_position'):
                self._reset_button_orig_position = {
                    'relx': 0.5,  # Center position
                    'rely': 0.85  # Position from top
                }
            
            # Use background color for fading instead of transparency
            bg_color = ThemeColors.BG_PRIMARY
            original_color = ThemeColors.ACCENT
            text_color = ThemeColors.TEXT_PRIMARY
            
            # Much smoother animation with more steps and optimized timing
            steps = 20  # Increased for smoother animation
            
            # Use after() instead of sleep for smoother animation
            def animate_frame(step):
                if step >= steps or not hasattr(self, 'reset_button') or not self.reset_button.winfo_exists():
                    # Final cleanup after animation
                    self._safely_destroy_reset_button()
                    
                    # Clean up animation state
                    if hasattr(self, '_reset_button_orig_position'):
                        delattr(self, '_reset_button_orig_position')
                    return
                
                # Calculate progress with easing for smoother motion
                # Using cubic easing for more natural movement
                progress = step / steps
                eased_progress = progress * progress * (3.0 - 2.0 * progress)  # Cubic easing
                
                # Blend colors using eased progress
                fg_blend = self._blend_colors(original_color, bg_color, eased_progress)
                text_blend = self._blend_colors(text_color, bg_color, eased_progress)
                
                # Apply colors
                self.reset_button.configure(
                    fg_color=fg_blend,
                    text_color=text_blend
                )
                
                # Smooth horizontal slide with subtle acceleration
                new_x = self._reset_button_orig_position['relx'] + (eased_progress * 0.3)
                self.reset_button.place(
                    relx=new_x,
                    rely=self._reset_button_orig_position['rely'],
                    anchor="center"
                )
                
                # Schedule next frame with consistent timing (6ms between frames for 60+ FPS)
                self.root.after(6, lambda: animate_frame(step + 1))
            
            # Start the animation
            animate_frame(0)
                
        except Exception as e:
            print(f"Error in button exit animation: {e}")
            # Fallback - just destroy the button immediately
            self._safely_destroy_reset_button()

    def _safely_destroy_reset_button(self):
        """Safely destroy the reset button to avoid widget errors"""
        try:
            if hasattr(self, 'reset_button'):
                try:
                    if self.reset_button.winfo_exists():
                        # First hide it (safer than immediate destroy)
                        self.reset_button.place_forget()
                        
                        # Then destroy after a tiny delay
                        self.root.after(20, self._finalize_button_destroy)
                    else:
                        # Already destroyed, just remove the attribute
                        delattr(self, 'reset_button')
                except Exception as inner_e:
                    print(f"Error checking reset button existence: {inner_e}")
                    # Just try to remove the attribute
                    if hasattr(self, 'reset_button'):
                        delattr(self, 'reset_button')
        except Exception as e:
            print(f"Error in safe button destruction: {e}")
            # Still try to clean up attribute
            if hasattr(self, 'reset_button'):
                delattr(self, 'reset_button')

    def _finalize_button_destroy(self):
        """Final button cleanup"""
        try:
            if hasattr(self, 'reset_button'):
                if self.reset_button.winfo_exists():
                    self.reset_button.destroy()
                delattr(self, 'reset_button')
        except Exception as e:
            print(f"Finalize button destroy error: {e}")
            # Remove attribute regardless
            if hasattr(self, 'reset_button'):
                delattr(self, 'reset_button')

    def _complete_reset_after_button_exit(self):
        """Complete the reset process after button has been handled"""
        try:
            # Reset the progress frame
            self._reset_progress_frame()

            # Reset status indicator with subtle animation
            self._animate_status_to_ready()

            # Log the reset action
            self.log_frame.log("🔄 Progress reset. Ready for new upload.", "success")
        except Exception as e:
            print(f"Error in reset completion: {e}")
            # Basic fallback
            self.status_indicator.configure(text="●", text_color=ThemeColors.SUCCESS)
            self.status_text.configure(text="Ready")

    def _animate_status_to_ready(self):
        """Smooth animation for status transition to ready"""
        try:
            # Define animation frames (color, text)
            frames = [
                (ThemeColors.ERROR, "⏹", "Reset in progress..."),
                (ThemeColors.WARNING, "↻", "Preparing..."),
                (ThemeColors.SUCCESS, "●", "Ready")
            ]

            # Schedule each frame
            for i, (color, icon, text) in enumerate(frames):
                self.root.after(i*120, lambda c=color, ic=icon, t=text: 
                    self._update_status_frame(c, ic, t))
        except Exception as e:
            print(f"Status animation error: {e}")
            # Fallback
            self.status_indicator.configure(text="●", text_color=ThemeColors.SUCCESS)
            self.status_text.configure(text="Ready")

    def _update_status_frame(self, color, icon, text):
        """Update status frame with given parameters"""
        try:
            self.status_indicator.configure(text=icon, text_color=color)
            self.status_text.configure(text=text)
        except Exception as e:
            print(f"Error updating status frame: {e}")

    def _reset_progress_frame(self):
        """Reset the progress frame to initial state"""
        try:
            # Reset progress bar to 0 with smooth animation
            current = self.progress_frame.progress_var.get()

            # If there's a significant amount to animate, do it smoothly
            if current > 0.05:
                steps = 8
                for i in range(steps+1):
                    progress = current * (1 - (i/steps))
                    self.progress_frame.progress_var.set(progress)
                    if i < steps:  # Don't sleep on the last iteration
                        time.sleep(0.01)  # Quick but visible
            else:
                # Just set to 0 directly
                self.progress_frame.progress_var.set(0)

            # Reset other UI elements
            self.progress_frame.total_var.set("0%")
            self.progress_frame.speed_var.set("0 B/s")
            self.progress_frame.eta_var.set("Calculating...")

            # Reset colors smoothly
            if self.progress_frame.progress_bar.cget("progress_color") != ThemeColors.ACCENT:
                # Animate color transition
                current_color = self.progress_frame.progress_bar.cget("progress_color")
                target_color = ThemeColors.ACCENT
                steps = 6
                for i in range(steps+1):
                    blend = i/steps
                    color = self._blend_colors(current_color, target_color, blend)
                    self.progress_frame.progress_bar.configure(progress_color=color)
                    if i < steps:  # Don't sleep on the last iteration
                        time.sleep(0.01)  # Quick but visible

            # Reset state with blank status text
            self.progress_frame.status_indicator.configure(text="", text_color=ThemeColors.TEXT_PRIMARY)

            # Reset state flags
            self.progress_frame.is_paused = False
            self.progress_frame.is_pausing = False
            if hasattr(self.progress_frame, 'is_stopping'):
                self.progress_frame.is_stopping = False
            if hasattr(self.progress_frame, 'is_stopped'):
                self.progress_frame.is_stopped = False

            # Reset speed icon
            self.progress_frame.speed_icon.configure(text="↑", text_color=ThemeColors.ACCENT)

            # Force update
            self.progress_frame.update_idletasks()
        except Exception as e:
            print(f"Error in reset_progress_frame: {e}")
            # Basic fallback
            try:
                self.progress_frame.progress_var.set(0)
                self.progress_frame.progress_bar.configure(progress_color=ThemeColors.ACCENT)
                self.progress_frame.status_indicator.configure(text="", text_color=ThemeColors.TEXT_PRIMARY)
            except:
                pass

    def retry_failed(self):
        if not self.failed_uploads:
            self.show_message("No failed uploads to retry", "info")
            return

        threading.Thread(target=self._retry_process, daemon=True).start()

    def _retry_process(self):
        self.log_frame.log("Retrying failed uploads...")

        # Check if structured failed upload details exist in the uploader
        if hasattr(self.uploader, 'failed_uploads_details') and self.uploader.failed_uploads_details:
            structured_retry = True
            retry_items = self.uploader.failed_uploads_details
            self.log_frame.log(f"Found {len(retry_items)} structured failed uploads to retry", "info")
        # Fall back to legacy method if no structured data
        elif self.failed_uploads:
            structured_retry = False
            retry_items = self.failed_uploads
            self.log_frame.log(f"Found {len(retry_items)} unstructured failed uploads to retry", "info")
        else:
            self.log_frame.log("No failed uploads to retry", "warning")
            return

        # Process failed uploads
        retry_count = 0

        if structured_retry:
            # Process structured retry data (more reliable)
            for item in list(retry_items):
                file_path = item['file_path']
                target_folder_id = item['target_folder_id']

                if os.path.exists(file_path) and os.path.isfile(file_path):
                    self.log_frame.log(f"Retrying upload: {os.path.basename(file_path)}", "info")

                    # Make sure upload workers are running
                    if not self.uploader.upload_threads or not any(t.is_alive() for t in self.uploader.upload_threads):
                        self.uploader.start_upload_workers()

                    # Re-queue the upload using stored folder ID
                    self.uploader.queue_upload(
                        file_path,
                        target_folder_id,
                        self.control_panel.get_server_url(),
                        self.control_panel.get_api_token(),
                        self.upload_callbacks,
                        self.control_panel.get_folder_path()
                    )

                    retry_count += 1

                    # Remove from the list after queuing
                    retry_items.remove(item)
                else:
                    self.log_frame.log(f"File no longer exists: {file_path}", "warning")
                    retry_items.remove(item)
        else:
            # Legacy method - extract file paths from error messages
            extracted_file_paths = []

            # First, look for complete file paths in the list
            for item in list(retry_items):
                if isinstance(item, str):
                    if os.path.exists(item) and os.path.isfile(item):
                        # This is a direct file path
                        extracted_file_paths.append(item)
                        self.log_frame.log(f"Found file to retry: {os.path.basename(item)}", "info")
                        continue

                    # Try to extract file path from error message
                    if "Upload error for " in item:
                        parts = item.split("Upload error for ")
                        if len(parts) > 1:
                            file_path = parts[1].split(":")[0].strip()
                            if os.path.exists(file_path) and os.path.isfile(file_path):
                                extracted_file_paths.append(file_path)
                                self.log_frame.log(f"Found file to retry: {os.path.basename(file_path)}", "info")

            # If we couldn't extract paths, notify user
            if not extracted_file_paths:
                self.log_frame.log("Could not find valid files to retry from the error list.", "warning")
                return

            # Retry each file using the legacy mechanism
            retry_count = len(extracted_file_paths)

            # Get folder path and parent folder ID
            folder_path = self.control_panel.get_folder_path()
            selected_cloud_folder = self.control_panel.get_selected_cloud_folder()

            # Make sure we have the folder manager initialized
            if not self.folder_manager:
                try:
                    api_token = self.control_panel.get_api_token()
                    server_url = self.control_panel.get_server_url()

                    if not api_token or not server_url:
                        self.log_frame.log("Missing API token or server URL", "error")
                        return

                    self.folder_manager = FolderManager(api_token, server_url)
                except Exception as e:
                    self.log_frame.log(f"Failed to initialize folder manager: {str(e)}", "error")
                    return

            try:
                # Get the cloud folder info
                cloud_folders = self.folder_manager.list_folders()
                cloud_folder_id = cloud_folders.get(selected_cloud_folder)

                if not cloud_folder_id:
                    self.log_frame.log(f"Could not find cloud folder: {selected_cloud_folder}", "error")
                    return

                # Get parent folder ID if it exists
                parent_folder_name = os.path.basename(folder_path)
                parent_folder_id = None

                existing_folders = self.folder_manager.list_folders(cloud_folder_id)
                if parent_folder_name in existing_folders:
                    parent_folder_id = existing_folders[parent_folder_name]
                    self.log_frame.log(f"Found parent folder: {parent_folder_name} (ID: {parent_folder_id})", "info")

                if not parent_folder_id:
                    self.log_frame.log("Could not find parent folder ID. Using destination folder instead.", "warning")
                    parent_folder_id = cloud_folder_id

                # Start upload workers if needed
                if not hasattr(self.uploader, 'upload_threads') or not any(t.is_alive() for t in self.uploader.upload_threads):
                    self.log_frame.log("Starting upload workers for retry operation", "info")
                    self.uploader.start_upload_workers()

                # Retry each file
                for file_path in extracted_file_paths:
                    if os.path.exists(file_path):
                        self.log_frame.log(f"Queuing {os.path.basename(file_path)} for retry", "info")
                        self.uploader.queue_upload(
                            file_path,
                            parent_folder_id,
                            self.control_panel.get_server_url(),
                            self.control_panel.get_api_token(),
                            self.upload_callbacks,
                            folder_path
                        )
                    else:
                        self.log_frame.log(f"File no longer exists: {file_path}", "error")

                # Clear the processed items from the failed uploads list
                for path in extracted_file_paths:
                    if path in self.failed_uploads:
                        self.failed_uploads.remove(path)

                # Also clear any error messages for files we've processed
                self.failed_uploads = [item for item in self.failed_uploads if not any(
                    path in str(item) for path in extracted_file_paths
                )]

            except Exception as e:
                self.log_frame.log(f"Error during retry process: {str(e)}", "error")
                return

        # Show result
        if retry_count > 0:
            self.log_frame.log(f"Started retry for {retry_count} files", "success")

            # Animate the progress bar to indicate activity
            self.progress_frame.indicate_activity()
        else:
            self.log_frame.log("No valid files found to retry", "warning")

    def show_summary(self):
        total = self.uploader.total_uploaded + len(self.failed_uploads)
        failed = len(self.failed_uploads)
        successful = self.uploader.total_uploaded

        # Play a subtle completion animation
        self._play_completion_animation()

        summary = (
            f"Sync Complete\n\n"
            f"Total Files: {total}\n"
            f"Successfully Uploaded: {successful}\n"
            f"Failed: {failed}"
        )

        self.show_message(summary, "info")

        # Add a "New Upload" button after completion
        self._show_new_upload_button()

    def _show_new_upload_button(self):
        """Show a button to start a new upload - NO animations, NO transparency"""
        try:
            # Make sure any previous button is removed first
            if hasattr(self, 'new_upload_button'):
                self._safely_destroy_upload_button()
                
            # Make sure reset button is also removed if it exists
            if hasattr(self, 'reset_button'):
                self._safely_destroy_reset_button()
                
            # Wait a tiny bit to ensure destruction completed
            time.sleep(0.05)

            # Create a "New Upload" button that appears after completion
            self.new_upload_button = StylishButton(
                self.progress_frame,
                text="🔄 Start New Upload",
                command=self._prepare_new_upload,
                fg_color=ThemeColors.SUCCESS,
                hover_color=ThemeColors.SUCCESS_LIGHT,
                width=160,
                height=36
            )

            # Position it in the center with normal colors
            self.new_upload_button.place(relx=0.5, rely=0.85, anchor="center")
            
            # Apply colors directly first for immediate visibility
            self.new_upload_button.configure(fg_color=ThemeColors.SUCCESS, text_color=ThemeColors.TEXT_PRIMARY)
            
            # Then do the fade-in animation
            self._fade_in_new_upload_button()

        except Exception as e:
            print(f"Error creating new upload button: {e}")
            # Don't attempt fallback as it might cause more errors

    def _fade_in_new_upload_button(self):
        """Simple fade-in animation for new upload button"""
        try:
            if not hasattr(self, 'new_upload_button') or not self.new_upload_button.winfo_exists():
                return

            # Original colors
            original_fg = ThemeColors.SUCCESS
            original_text = ThemeColors.TEXT_PRIMARY

            # Start with background color instead of transparent
            bg_color = ThemeColors.BG_PRIMARY
            self.new_upload_button.configure(fg_color=bg_color, text_color=bg_color)

            # Fade in over 5 steps
            steps = 5
            for i in range(1, steps+1):
                # Calculate opacity
                opacity = i / steps

                # Blend colors with background for fade effect
                fg_color = self._blend_colors("transparent", original_fg, opacity)
                text_color = self._blend_colors("transparent", original_text, opacity)

                # Apply colors
                self.new_upload_button.configure(fg_color=fg_color, text_color=text_color)
                self.new_upload_button.update_idletasks()

                # Short delay between steps
                time.sleep(0.03)

            # Ensure final state is correct
            self.new_upload_button.configure(fg_color=original_fg, text_color=original_text)

            # Add subtle bounce if desired
            self._add_subtle_bounce_to_new_button()
        except Exception as e:
            print(f"Error in button fade animation: {e}")
            # Fallback - just show the button
            try:
                if hasattr(self, 'new_upload_button') and self.new_upload_button.winfo_exists():
                    self.new_upload_button.configure(fg_color=ThemeColors.SUCCESS, text_color=ThemeColors.TEXT_PRIMARY)
            except:
                pass

    def _add_subtle_bounce_to_new_button(self):
        """Add a very subtle bounce effect for extra polish"""
        try:
            if not hasattr(self, 'new_upload_button') or not self.new_upload_button.winfo_exists():
                return

            # Define subtle bounce keyframes (scale values)
            bounce_scales = [1.0, 1.04, 0.98, 1.0]
            bounce_times = [0, 80, 150, 220]  # milliseconds

            # Apply each scale with appropriate timing
            for i, scale in enumerate(bounce_scales):
                self.root.after(bounce_times[i], 
                    lambda s=scale: self._apply_new_button_scale(s))
        except Exception as e:
            print(f"Error adding button bounce: {e}")

    def _apply_new_button_scale(self, scale):
        """Apply scale effect to new upload button"""
        try:
            if hasattr(self, 'new_upload_button') and self.new_upload_button.winfo_exists():
                # Calculate new dimensions
                orig_width = 160
                orig_height = 36
                new_width = int(orig_width * scale)
                new_height = int(orig_height * scale)

                # Apply new dimensions, keeping button centered
                self.new_upload_button.configure(width=new_width, height=new_height)
        except Exception as e:
            print(f"Error scaling button: {e}")

    def _safely_destroy_upload_button(self):
        """Safely destroy the new upload button to avoid widget errors"""
        try:
            if hasattr(self, 'new_upload_button'):
                try:
                    if self.new_upload_button.winfo_exists():
                        # First hide it (safer than immediate destroy)
                        self.new_upload_button.place_forget()
                        
                        # Then destroy after a tiny delay
                        self.root.after(20, self._finalize_upload_button_destroy)
                    else:
                        # Already destroyed, just remove the attribute
                        delattr(self, 'new_upload_button')
                except Exception as inner_e:
                    print(f"Error checking button existence: {inner_e}")
                    # Just try to remove the attribute
                    if hasattr(self, 'new_upload_button'):
                        delattr(self, 'new_upload_button')
        except Exception as e:
            print(f"Error in safe button destruction: {e}")
            # Still try to clean up attribute
            if hasattr(self, 'new_upload_button'):
                delattr(self, 'new_upload_button')

    def _finalize_upload_button_destroy(self):
        """Final upload button cleanup"""
        try:
            if hasattr(self, 'new_upload_button'):
                if self.new_upload_button.winfo_exists():
                    self.new_upload_button.destroy()
                delattr(self, 'new_upload_button')
        except Exception as e:
            print(f"Finalize button destroy error: {e}")
            # Remove attribute regardless
            if hasattr(self, 'new_upload_button'):
                delattr(self, 'new_upload_button')

    def _prepare_new_upload(self):
        """Reset the UI and prepare for a new upload with smooth transitions"""
        try:
            # Provide immediate visual feedback that button was clicked
            if hasattr(self, 'new_upload_button') and self.new_upload_button.winfo_exists():
                self.new_upload_button.configure(state="disabled", text="Preparing...")
                self.new_upload_button.update_idletasks()

                # Add subtle click animation
                self._add_button_click_animation()

            # Begin the exit animation after a tiny delay
            self.root.after(50, self._animate_new_upload_button_exit)

            # Schedule the reset procedure to happen after animation completes
            self.root.after(300, self._reset_for_new_upload)
        except Exception as e:
            print(f"Error preparing new upload: {e}")
            # Fallback - ensure reset happens
            self.root.after(100, self._reset_for_new_upload)

    def _add_button_click_animation(self):
        """Add subtle pressed effect to button"""
        try:
            if hasattr(self, 'new_upload_button') and self.new_upload_button.winfo_exists():
                # Flash button background subtly
                orig_color = self.new_upload_button.cget("fg_color")
                darker = self._darken_color(orig_color, 0.15)

                self.new_upload_button.configure(fg_color=darker)
                self.root.after(80, lambda: 
                    self.new_upload_button.configure(fg_color=orig_color) 
                    if hasattr(self, 'new_upload_button') and self.new_upload_button.winfo_exists() else None)
        except Exception as e:
            print(f"Button click animation error: {e}")

    def _darken_color(self, color, amount=0.1):
        """Darken a hex color by the given amount (0-1)"""
        try:
            # Convert hex to RGB
            r = int(color[1:3], 16)
            g = int(color[3:5], 16)
            b = int(color[5:7], 16)

            # Darken each component
            r = max(0, int(r * (1 - amount)))
            g = max(0, int(g * (1 - amount)))
            b = max(0, int(b * (1 - amount)))

            # Convert back to hex
            return f"#{r:02x}{g:02x}{b:02x}"
        except:
            return color

    def _animate_new_upload_button_exit(self):
        """Buttery smooth exit animation for new upload button with enhanced transitions"""
        try:
            if not hasattr(self, 'new_upload_button') or not self.new_upload_button.winfo_exists():
                return

            # First save original position before animating
            if not hasattr(self, '_upload_button_orig_position'):
                self._upload_button_orig_position = {
                    'relx': 0.5,  # Center position
                    'rely': 0.85  # Position from top
                }
            
            # Use background color for fading instead of transparency
            bg_color = ThemeColors.BG_PRIMARY
            original_color = ThemeColors.SUCCESS
            text_color = ThemeColors.TEXT_PRIMARY
            
            # Significantly smoother animation with more steps and better timing
            steps = 20  # Increased for buttery smooth animation
            
            # Use after() instead of sleep for smoother animation
            def animate_frame(step):
                if step >= steps or not hasattr(self, 'new_upload_button') or not self.new_upload_button.winfo_exists():
                    # Final cleanup after animation
                    self._safely_destroy_upload_button()
                    
                    # Clean up position data
                    if hasattr(self, '_upload_button_orig_position'):
                        delattr(self, '_upload_button_orig_position')
                    return
                
                # Calculate progress with cubic easing for natural movement
                progress = step / steps
                eased_progress = progress * progress * (3.0 - 2.0 * progress)  # Cubic easing
                
                # Blend colors using eased progress
                fg_blend = self._blend_colors(original_color, bg_color, eased_progress)
                text_blend = self._blend_colors(text_color, bg_color, eased_progress)
                
                # Apply colors with smooth transition
                self.new_upload_button.configure(
                    fg_color=fg_blend,
                    text_color=text_blend
                )
                
                # Smooth horizontal slide with subtle acceleration
                new_x = self._upload_button_orig_position['relx'] + (eased_progress * 0.3)
                self.new_upload_button.place(
                    relx=new_x,
                    rely=self._upload_button_orig_position['rely'],
                    anchor="center"
                )
                
                # Schedule next frame with consistent timing (6ms between frames for 60+ FPS)
                self.root.after(6, lambda: animate_frame(step + 1))
            
            # Start the animation
            animate_frame(0)
                
        except Exception as e:
            print(f"Error in button exit animation: {e}")
            # Fallback - just destroy the button immediately
            self._safely_destroy_upload_button()

    def _reset_for_new_upload(self):
        """Complete reset for new upload"""
        try:
            # Safely destroy the new upload button
            try:
                if hasattr(self, 'new_upload_button'):
                    self.new_upload_button.place_forget()
                    self.new_upload_button.destroy()
                    delattr(self, 'new_upload_button')
            except Exception as e:
                print(f"Button cleanup error (non-critical): {e}")

            # Reset the progress frame
            self._reset_progress_frame()

            # Reset status indicator
            self.status_indicator.configure(text="●", text_color=ThemeColors.SUCCESS)
            self.status_text.configure(text="Ready for New Upload")

            # Log the reset action
            self.log_frame.log("🔄 Ready for new upload", "success")

            # Create a fresh uploader instance
            self.uploader = FileUploader()

            # Restore network recovery callback
            if hasattr(self.uploader, 'set_network_recovery_callback'):
                self.uploader.set_network_recovery_callback(self.handle_network_recovery)

            # Reset state flags
            self.is_paused = False
            self.is_stopping = False
            self.failed_uploads = []

        except Exception as e:
            print(f"Error in reset for new upload: {e}")

    def _play_completion_animation(self):
        """Play a smoother, more visually appealing completion animation"""
        # Use the enhanced animation from ui_components
        from ui_components import play_completion_animation

        # Update status indicator
        self.status_indicator.configure(text="✓", text_color=ThemeColors.SUCCESS)
        self.status_text.configure(text="Sync Complete")

        # Play the progress bar animation
        play_completion_animation(self.progress_frame)

        # Subtle animation for the log frame to draw attention to completion
        def highlight_log():
            original_color = self.log_frame.cget("fg_color")
            highlight_color = ThemeColors.SUCCESS
            fade_steps = 10

            # Briefly highlight the log frame
            for i in range(fade_steps):
                # Fade in
                blend = i / fade_steps
                color = self._blend_colors(original_color, highlight_color, blend * 0.3)  # Only 30% blend for subtlety
                self.log_frame.configure(fg_color=color)
                self.root.update()
                time.sleep(0.02)

            # Hold for a moment
            time.sleep(0.2)

            # Fade back
            for i in range(fade_steps):
                blend = (fade_steps - i) / fade_steps
                color = self._blend_colors(original_color, highlight_color, blend * 0.3)
                self.log_frame.configure(fg_color=color)
                self.root.update()
                time.sleep(0.02)

            # Reset to original
            self.log_frame.configure(fg_color=original_color)

        # Start the log highlight animation in a separate thread
        threading.Thread(target=highlight_log, daemon=True).start()

    # Theme toggle functionality removed - using static dark theme

    def _blend_colors(self, color1, color2, blend_factor):
        """Helper to blend colors for animations"""
        try:
            # Check if colors are valid hex strings
            if not isinstance(color1, str) or not isinstance(color2, str):
                return ThemeColors.BG_PRIMARY if blend_factor > 0.5 else ThemeColors.BG_SECONDARY

            if not color1.startswith('#') or not color2.startswith('#'):
                return ThemeColors.BG_PRIMARY

            if len(color1) != 7 or len(color2) != 7:
                return ThemeColors.BG_PRIMARY

            # Convert hex to RGB
            r1, g1, b1 = int(color1[1:3], 16), int(color1[3:5], 16), int(color1[5:7], 16)
            r2, g2, b2 = int(color2[1:3], 16), int(color2[3:5], 16), int(color2[5:7], 16)

            # Linear interpolation
            r = int(r1 + (r2 - r1) * blend_factor)
            g = int(g1 + (g2 - g1) * blend_factor)
            b = int(b1 + (b2 - b1) * blend_factor)

            # Convert back to hex
            return f"#{r:02x}{g:02x}{b:02x}"
        except Exception as e:
            print(f"Error blending colors: {e}")
            return ThemeColors.BG_PRIMARY

    def run(self):
        # Show welcome message with animated entry
        def show_welcome_sequence():
            time.sleep(0.3)  # Brief delay for UI to initialize

            # Welcome messages with staggered appearance
            messages = [
                ("Welcome to Folder Fort Sync!", "info"),
                ("Ready to secure your files in the cloud?", "info"),
                ("Quick Tip: Save your API token for faster login next time.", "info"),
                ("Quick Tip: Use Refresh to scan available cloud folders.", "info"),
                ("Quick Tip: Progress animations show sync status at a glance.", "info")
            ]

            # Log messages directly without popups
            for i, (msg, level) in enumerate(messages):
                self.root.after(i*800, lambda idx=i: self.log_frame.log(messages[idx][0], messages[idx][1]))

            # Subtle animation for the status indicator
            colors = [ThemeColors.ACCENT, ThemeColors.SUCCESS]
            for i in range(5):
                self.root.after(i*300 + 500, lambda idx=i: self.status_indicator.configure(
                    text_color=colors[idx % 2]
                ))

            # Finally set to ready state
            self.root.after(3000, lambda: self.status_indicator.configure(
                text="●", 
                text_color=ThemeColors.SUCCESS
            ))

        # Start welcome sequence in a separate thread to avoid blocking
        threading.Thread(target=show_welcome_sequence, daemon=True).start()

        # Start the app event loop
        self.root.mainloop()

if __name__ == "__main__":
    app = FolderFortSync()
    app.run()