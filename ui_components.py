import customtkinter as ctk
from typing import Callable, Dict, List
import time
import humanize
import keyring
import json
import threading
from pathlib import Path

class ThemeColors:
    BG_PRIMARY = "#1A1A1A"  # Matte black
    BG_SECONDARY = "#242424"  # Slightly lighter black
    ACCENT = "#007AFF"  # Apple blue
    TEXT_PRIMARY = "#FFFFFF"
    TEXT_SECONDARY = "#B0B0B0"
    SUCCESS = "#34C759"  # Apple green
    ERROR = "#FF3B30"  # Apple red
    WARNING = "#FF9500"  # Apple orange

class StylishButton(ctk.CTkButton):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.configure(
            corner_radius=10,
            font=("SF Pro Display", 13),
            height=32,
            hover_color=ThemeColors.BG_SECONDARY,
            fg_color=ThemeColors.ACCENT,
            text_color=ThemeColors.TEXT_PRIMARY
        )

class ProgressFrame(ctk.CTkFrame):
    CHUNK_SIZE = 1024 * 1024  # 1MB chunks for better ETA calculation

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.configure(fg_color=ThemeColors.BG_SECONDARY)

        self.progress_var = ctk.DoubleVar(value=0)
        self.speed_var = ctk.StringVar(value="0 B/s")
        self.eta_var = ctk.StringVar(value="Calculating...")
        self.total_var = ctk.StringVar(value="0%")

        # Progress bar
        self.progress_bar = ctk.CTkProgressBar(
            self, 
            variable=self.progress_var,
            width=400,
            progress_color=ThemeColors.ACCENT,
            corner_radius=10,
            height=10
        )
        self.progress_bar.pack(pady=(15, 5), padx=20, fill="x")

        # Total progress percentage
        self.total_label = ctk.CTkLabel(
            self,
            textvariable=self.total_var,
            font=("SF Pro Display", 14, "bold"),
            text_color=ThemeColors.TEXT_PRIMARY
        )
        self.total_label.pack(pady=5)

        # Stats frame for speed and ETA
        self.stats_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.stats_frame.pack(fill="x", pady=(5, 15))

        self.speed_label = ctk.CTkLabel(
            self.stats_frame,
            textvariable=self.speed_var,
            font=("SF Pro Display", 12),
            text_color=ThemeColors.TEXT_SECONDARY
        )
        self.speed_label.pack(side="left", padx=20)

        self.eta_label = ctk.CTkLabel(
            self.stats_frame,
            textvariable=self.eta_var,
            font=("SF Pro Display", 12),
            text_color=ThemeColors.TEXT_SECONDARY
        )
        self.eta_label.pack(side="right", padx=20)

        # Initialize progress bar to 0
        self.progress_bar.set(0)
        self._last_update = time.time()
        self._speed_samples = []

    def _calculate_moving_average_speed(self, current_speed: float) -> float:
        """Calculate moving average of speed over the last few samples"""
        self._speed_samples.append(current_speed)
        if len(self._speed_samples) > 5:  # Keep last 5 samples
            self._speed_samples.pop(0)
        return sum(self._speed_samples) / len(self._speed_samples)

    def update_progress(self, current: int, total: int, speed: float):
        """Update progress bar with current status"""
        if total <= 0:
            return

        # Calculate progress percentage
        progress = (current / total) * 100
        self.progress_var.set(progress / 100.0)  # Progress bar expects value between 0 and 1
        self.total_var.set(f"{progress:.1f}%")

        # Calculate and update speed with moving average
        avg_speed = self._calculate_moving_average_speed(speed)
        speed_str = humanize.naturalsize(avg_speed, binary=True) + "/s"
        self.speed_var.set(f"Speed: {speed_str}")

        # Calculate and update ETA based on remaining files
        if avg_speed > 0:
            remaining = total - current
            eta_seconds = (remaining * self.CHUNK_SIZE) / avg_speed if avg_speed > 0 else 0
            if eta_seconds > 3600:
                eta_str = f"{int(eta_seconds/3600)}h {int((eta_seconds%3600)/60)}m"
            elif eta_seconds > 60:
                eta_str = f"{int(eta_seconds/60)}m {int(eta_seconds%60)}s"
            else:
                eta_str = f"{int(eta_seconds)}s"
            self.eta_var.set(f"ETA: {eta_str}")
        else:
            self.eta_var.set("ETA: Calculating...")

        # Force immediate update of the UI
        self.progress_bar.update()
        self.update_idletasks()

class LogFrame(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.configure(fg_color=ThemeColors.BG_SECONDARY)

        self.log_text = ctk.CTkTextbox(
            self,
            width=600,
            height=200,
            font=("SF Pro Mono", 12),
            fg_color=ThemeColors.BG_PRIMARY,
            text_color=ThemeColors.TEXT_PRIMARY,
            corner_radius=10
        )
        self.log_text.pack(expand=True, fill="both", padx=15, pady=15)

    def log(self, message: str, level: str = "info"):
        timestamp = time.strftime("%H:%M:%S")
        color_map = {
            "info": ThemeColors.TEXT_PRIMARY,
            "success": ThemeColors.SUCCESS,
            "error": ThemeColors.ERROR,
            "warning": ThemeColors.WARNING
        }

        # Level-specific icons
        icon_map = {
            "info": "ℹ️",
            "success": "✅",
            "error": "❌",
            "warning": "⚠️"
        }

        icon = icon_map.get(level, "")

        # Create tags for timestamp and message
        time_tag = f"time_{timestamp}"
        msg_tag = f"{level}_{timestamp}"

        self.log_text.tag_config(time_tag, foreground=ThemeColors.TEXT_SECONDARY)
        self.log_text.tag_config(msg_tag, foreground=color_map.get(level, ThemeColors.TEXT_PRIMARY))

        # Insert with different formatting for timestamp and message
        self.log_text.insert("end", f"[{timestamp}] ", time_tag)
        self.log_text.insert("end", f"{icon} {message}\n", msg_tag)
        self.log_text.see("end")

    def clear(self):
        self.log_text.delete("1.0", "end")

class StylishEntry(ctk.CTkEntry):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.configure(
            corner_radius=10,
            height=32,
            font=("SF Pro Display", 13),
            fg_color=ThemeColors.BG_PRIMARY,
            text_color=ThemeColors.TEXT_PRIMARY,
            border_color=ThemeColors.BG_SECONDARY
        )

class ControlPanel(ctk.CTkFrame):
    def __init__(self, master, callbacks: Dict[str, Callable], **kwargs):
        super().__init__(master, **kwargs)
        self.configure(fg_color="transparent")
        self.callbacks = callbacks

        # API Configuration
        self.api_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.api_frame.pack(fill="x", pady=10)

        ctk.CTkLabel(
            self.api_frame,
            text="API Token",
            font=("SF Pro Display", 13, "bold"),
            text_color=ThemeColors.TEXT_SECONDARY
        ).pack(side="left", padx=(15, 5))

        self.api_token = StylishEntry(self.api_frame, width=300, show="•")
        self.api_token.pack(side="left", padx=5)

        self.save_token_btn = StylishButton(
            self.api_frame,
            text="Save Token",
            command=self.save_token
        )
        self.save_token_btn.pack(side="left", padx=5)
        self._create_tooltip(self.save_token_btn, "Save API token securely")

        # Load saved token if exists
        self.load_saved_token()

        # Folder Selection
        self.folder_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.folder_frame.pack(fill="x", pady=10)

        ctk.CTkLabel(
            self.folder_frame,
            text="Local Folder",
            font=("SF Pro Display", 13, "bold"),
            text_color=ThemeColors.TEXT_SECONDARY
        ).pack(side="left", padx=(15, 5))

        self.folder_path = StylishEntry(self.folder_frame, width=300)
        self.folder_path.pack(side="left", padx=5)

        browse_btn = StylishButton(
            self.folder_frame,
            text="Browse",
            command=self.callbacks.get("browse", lambda: None)
        )
        browse_btn.pack(side="left", padx=5)
        self._create_tooltip(browse_btn, "Select local folder to sync")

        # Cloud Destination Folder
        self.cloud_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.cloud_frame.pack(fill="x", pady=10)

        ctk.CTkLabel(
            self.cloud_frame,
            text="Cloud Destination",
            font=("SF Pro Display", 13, "bold"),
            text_color=ThemeColors.TEXT_SECONDARY
        ).pack(side="left", padx=(15, 5))

        self.cloud_folder = ctk.CTkComboBox(
            self.cloud_frame,
            width=300,
            font=("SF Pro Display", 13),
            fg_color=ThemeColors.BG_PRIMARY,
            text_color=ThemeColors.TEXT_PRIMARY,
            dropdown_fg_color=ThemeColors.BG_SECONDARY,
            button_color=ThemeColors.ACCENT,
            button_hover_color=ThemeColors.BG_SECONDARY,
            border_color=ThemeColors.BG_SECONDARY,
            values=["Loading folders..."]
        )
        self.cloud_folder.pack(side="left", padx=5)

        refresh_btn = StylishButton(
            self.cloud_frame,
            text="↻ Refresh",
            command=self.callbacks.get("refresh_folders", lambda: None)
        )
        refresh_btn.pack(side="left", padx=5)
        self._create_tooltip(refresh_btn, "Refresh cloud folder list")

        # Control Buttons
        self.button_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.button_frame.pack(fill="x", pady=15)

        button_configs = [
            ("Start", "start", ThemeColors.ACCENT, "Begin synchronization"),
            ("Pause", "pause", ThemeColors.WARNING, "Pause current sync"),
            ("Resume", "resume", ThemeColors.SUCCESS, "Resume paused sync"),
            ("Stop", "stop", ThemeColors.ERROR, "Stop synchronization (requires confirmation)"),
            ("Retry Failed", "retry", ThemeColors.ACCENT, "Retry failed uploads")
        ]

        for text, callback_key, color, tooltip in button_configs:
            btn = StylishButton(
                self.button_frame,
                text=text,
                command=self.callbacks.get(callback_key, lambda: None),
                fg_color=color
            )
            btn.pack(side="left", padx=8)

            # Create tooltip functionality
            self._create_tooltip(btn, tooltip)

    def update_cloud_folders(self, folders: List[str]):
        """Update the cloud folders dropdown with new values"""
        if not folders:
            folders = ["No folders found"]
        self.cloud_folder.configure(values=folders)
        self.cloud_folder.set(folders[0])

    def get_selected_cloud_folder(self) -> str:
        """Get the currently selected cloud folder"""
        return self.cloud_folder.get()

    def save_token(self):
        token = self.api_token.get().strip()
        if token:
            keyring.set_password("FolderFortSync", "api_token", token)

            # Visual feedback animation
            original_color = self.save_token_btn.cget("fg_color")
            self.save_token_btn.configure(fg_color=ThemeColors.SUCCESS, text="✓ Saved")

            # Reset button after delay
            def reset_button():
                time.sleep(1.5)
                self.save_token_btn.configure(fg_color=original_color, text="Save Token")

            threading.Thread(target=reset_button, daemon=True).start()
            self.show_message("Token saved successfully!")
        else:
            self.show_message("Please enter a token first", "error")

    def load_saved_token(self):
        try:
            saved_token = keyring.get_password("FolderFortSync", "api_token")
            if saved_token:
                self.api_token.delete(0, "end")
                self.api_token.insert(0, saved_token)
        except Exception:
            pass

    def show_message(self, message: str, level: str = "info"):
        if self.callbacks.get("show_message"):
            self.callbacks["show_message"](message, level)

    def get_api_token(self) -> str:
        return self.api_token.get().strip()

    def get_folder_path(self) -> str:
        return self.folder_path.get().strip()

    def _create_tooltip(self, widget, text):
        """Create a tooltip for a given widget"""
        tooltip = None
        delay_id = None
        
        def show_tooltip():
            nonlocal tooltip
            if tooltip is None:
                # Get position relative to screen
                x = widget.winfo_rootx() + widget.winfo_width() // 2
                y = widget.winfo_rooty() + widget.winfo_height() + 8
                
                # Create a toplevel window
                tooltip = ctk.CTkToplevel(widget)
                tooltip.wm_overrideredirect(True)
                tooltip.wm_geometry(f"+{x}+{y}")
                tooltip.attributes("-topmost", True)
                
                # Add a frame to ensure consistent appearance
                frame = ctk.CTkFrame(
                    tooltip,
                    fg_color=ThemeColors.BG_SECONDARY,
                    corner_radius=8,
                    border_width=1,
                    border_color="#333333"
                )
                frame.pack(padx=0, pady=0)
                
                # Add the label
                label = ctk.CTkLabel(
                    frame, 
                    text=text,
                    font=("SF Pro Display", 12),
                    text_color=ThemeColors.TEXT_SECONDARY,
                    padx=12,
                    pady=6
                )
                label.pack()
                
                # Prevent tooltip from stealing focus
                tooltip.update_idletasks()
                tooltip.lift()
        
        def enter(event):
            nonlocal delay_id
            # Show tooltip after a delay for better user experience
            delay_id = widget.after(500, show_tooltip)
            
        def leave(event):
            nonlocal tooltip, delay_id
            # Cancel pending tooltip if mouse left before it appeared
            if delay_id is not None:
                widget.after_cancel(delay_id)
                delay_id = None
                
            # Destroy tooltip if it exists
            if tooltip is not None:
                tooltip.destroy()
                tooltip = None
        
        # Bind events
        widget.bind("<Enter>", enter)
        widget.bind("<Leave>", leave)
        widget.bind("<Button-1>", leave)


def _play_completion_animation(self):
        """Play a smooth completion animation on the progress bar"""
        def animate():
            # Define colors for smooth transition
            accent_color = ThemeColors.ACCENT
            success_color = ThemeColors.SUCCESS

            # Extract RGB components
            ar, ag, ab = int(accent_color[1:3], 16), int(accent_color[3:5], 16), int(accent_color[5:7], 16)
            sr, sg, sb = int(success_color[1:3], 16), int(success_color[3:5], 16), int(success_color[5:7], 16)

            # Smooth color transition (accent to success)
            steps = 15
            for i in range(steps + 1):
                blend = i / steps
                r = int(ar + (sr - ar) * blend)
                g = int(ag + (sg - ag) * blend)
                b = int(ab + (sb - ab) * blend)
                color = f"#{r:02x}{g:02x}{b:02x}"

                self.progress_frame.progress_bar.configure(progress_color=color)
                self.root.update()
                time.sleep(0.02)

            # Pulse effect
            for j in range(3):  # 3 pulses
                # Pulse out (slightly lighter)
                for i in range(5):
                    # Make color slightly lighter
                    factor = 0.9 + (i * 0.05)  # 0.9 to 1.15
                    r = min(255, int(sr * factor))
                    g = min(255, int(sg * factor))
                    b = min(255, int(sb * factor))
                    color = f"#{r:02x}{g:02x}{b:02x}"

                    self.progress_frame.progress_bar.configure(progress_color=color)
                    self.root.update()
                    time.sleep(0.03)

                # Pulse in (back to normal)
                for i in range(5):
                    # Return to original color
                    factor = 1.15 - (i * 0.05)  # 1.15 to 0.9
                    r = min(255, int(sr * factor))
                    g = min(255, int(sg * factor))
                    b = min(255, int(sb * factor))
                    color = f"#{r:02x}{g:02x}{b:02x}"

                    self.progress_frame.progress_bar.configure(progress_color=color)
                    self.root.update()
                    time.sleep(0.03)

            # Transition back to accent color (smooth)
            for i in range(steps + 1):
                blend = i / steps
                r = int(sr + (ar - sr) * blend)
                g = int(sg + (ag - sg) * blend)
                b = int(sb + (ab - sb) * blend)
                color = f"#{r:02x}{g:02x}{b:02x}"

                self.progress_frame.progress_bar.configure(progress_color=color)
                self.root.update()
                time.sleep(0.02)

        # Run animation in a separate thread to avoid UI blocking
        threading.Thread(target=animate, daemon=True).start()