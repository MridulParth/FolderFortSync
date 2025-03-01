import customtkinter as ctk
from tkinter import filedialog, messagebox
import threading
import os
from typing import Dict, List
from pathlib import Path
import time
import threading

from file_uploader import FileUploader
from folder_manager import FolderManager
from ui_components import ProgressFrame, LogFrame, ControlPanel, ThemeColors

class FolderFortSync:
    def __init__(self):
        self.setup_window()
        self.uploader = FileUploader()
        self.folder_manager = None
        self.failed_uploads = []

        self.setup_ui()
        self.bind_callbacks()

    def setup_window(self):
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.root = ctk.CTk()
        self.root.title("Folder Fort Sync")
        self.root.geometry("900x700")
        self.root.configure(fg_color=ThemeColors.BG_PRIMARY)

        # Set minimum window size
        self.root.minsize(800, 600)

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
        # Main container with padding
        self.main_frame = ctk.CTkFrame(
            self.root,
            fg_color=ThemeColors.BG_PRIMARY
        )
        self.main_frame.pack(expand=True, fill="both", padx=20, pady=20)

        # Title
        title_label = ctk.CTkLabel(
            self.main_frame,
            text="Folder Fort Sync",
            font=("SF Pro Display", 24, "bold"),
            text_color=ThemeColors.TEXT_PRIMARY
        )
        title_label.pack(pady=(0, 20))

        # Control Panel
        self.control_panel = ControlPanel(
            self.main_frame,
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
        self.control_panel.pack(fill="x", pady=10)

        # Progress Frame
        self.progress_frame = ProgressFrame(self.main_frame)
        self.progress_frame.pack(fill="x", pady=10)

        # Log Frame
        self.log_frame = LogFrame(self.main_frame)
        self.log_frame.pack(expand=True, fill="both", pady=10)

    def bind_callbacks(self):
        self.upload_callbacks = {
            'on_success': self.handle_upload_success,
            'on_error': self.handle_upload_error,
            'on_progress': self.handle_upload_progress
        }

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
        if not api_token:
            self.show_message("Please enter API token first", "error")
            return

        try:
            self.folder_manager = FolderManager(api_token, "https://eu2.folderfort.com/api/v1")
            folders = self.folder_manager.list_folders()
            folder_names = list(folders.keys())
            self.control_panel.update_cloud_folders(folder_names)
            self.log_frame.log("Cloud folders refreshed successfully")
        except Exception as e:
            self.show_message(f"Failed to refresh folders: {str(e)}", "error")

    def start_sync(self):
        api_token = self.control_panel.get_api_token()
        folder_path = self.control_panel.get_folder_path()
        selected_cloud_folder = self.control_panel.get_selected_cloud_folder()

        if not all([api_token, folder_path, selected_cloud_folder]):
            self.show_message("Please provide API token, local folder path, and select a cloud destination", "error")
            return

        self.folder_manager = FolderManager(api_token, "https://eu2.folderfort.com/api/v1")

        # Start sync in separate thread
        threading.Thread(target=self._sync_process, daemon=True).start()

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

            # Start upload workers
            self.uploader.start_upload_workers()

            # Queue files for upload
            for file_path, parent_id in files_to_upload:
                self.uploader.queue_upload(
                    file_path,
                    parent_id,
                    "https://eu2.folderfort.com/api/v1",
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
        self.log_frame.log(f"Uploaded: {os.path.basename(file_path)}", "success")
        self.progress_frame.update_progress(
            self.uploader.total_uploaded,
            self.uploader.upload_queue.qsize() + self.uploader.total_uploaded,
            speed
        )

    def handle_upload_error(self, error: str):
        self.log_frame.log(error, "error")
        self.failed_uploads.append(error)

    def handle_upload_progress(self, current: int, total: int, speed: float):
        self.progress_frame.update_progress(current, total, speed)

    def pause_sync(self):
        self.uploader.pause()
        self.log_frame.log("Sync paused", "warning")

    def resume_sync(self):
        self.uploader.resume()
        self.log_frame.log("Sync resumed", "info")

    def stop_sync(self):
        # Confirm before stopping
        confirmation = messagebox.askyesno("Confirmation", "Are you sure you want to stop the sync process?")
        if confirmation:
            # Use a separate thread to prevent UI freeze
            threading.Thread(target=self._stop_sync_thread, daemon=True).start()
            self.log_frame.log("Stopping sync. Please wait...", "warning")

    def _stop_sync_thread(self):
        try:
            self.uploader.stop()
            self.log_frame.log("Sync stopped successfully", "warning")
        except Exception as e:
            self.log_frame.log(f"Error stopping sync: {str(e)}", "error")

    def retry_failed(self):
        if not self.failed_uploads:
            self.show_message("No failed uploads to retry", "info")
            return

        threading.Thread(target=self._retry_process, daemon=True).start()

    def _retry_process(self):
        self.log_frame.log("Retrying failed uploads...")
        for file_path, parent_id in self.failed_uploads:
            self.uploader.queue_upload(
                file_path,
                parent_id,
                "https://eu2.folderfort.com/api/v1",
                self.control_panel.get_api_token(),
                self.upload_callbacks
            )
        self.failed_uploads.clear()

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

    def _play_completion_animation(self):
        """Play a subtle completion animation on the progress bar"""
        def animate():
            colors = [ThemeColors.SUCCESS, ThemeColors.ACCENT]
            for i in range(5):  # Flash 5 times
                self.progress_frame.progress_bar.configure(progress_color=colors[i % 2])
                self.root.update()
                time.sleep(0.2)
            # Reset to original color
            self.progress_frame.progress_bar.configure(progress_color=ThemeColors.ACCENT)

        # Run animation in a separate thread to avoid UI blocking
        threading.Thread(target=animate, daemon=True).start()

    def run(self):
        # Show welcome message with quick tips
        self.log_frame.log("Welcome to Folder Fort Sync! Ready to sync your files securely?", "info")
        self.log_frame.log("Quick Tip: Save your API token for faster login.", "info")
        self.log_frame.log("Quick Tip: Use the Refresh button to choose your destination folder :D", "info")

        # Start the app event loop
        self.root.mainloop()

if __name__ == "__main__":
    app = FolderFortSync()
    app.run()