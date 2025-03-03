import customtkinter as ctk
from typing import Callable, Dict, List
import time
import humanize
import keyring
import json
import threading
from pathlib import Path
import colorsys
import random

class ThemeManager:
    """Manages theme colors with static dark theme (matte black aesthetic)"""
    _current_theme = "dark"  # Static dark theme

    # Dark theme (matte black aesthetic)
    DARK = {
        "BG_PRIMARY": "#0F0F0F",         # Even darker matte black for better contrast
        "BG_SECONDARY": "#202020",       # Slightly lighter black
        "ACCENT": "#007AFF",             # Apple blue
        "ACCENT_LIGHT": "#3D95FF",       # Lighter accent for hover states
        "TEXT_PRIMARY": "#FFFFFF",       # White text
        "TEXT_SECONDARY": "#B0B0B0",     # Light gray text
        "TEXT_TERTIARY": "#7A7A7A",      # Even more subdued text
        "SUCCESS": "#34C759",            # Apple green
        "SUCCESS_LIGHT": "#4BD16A",     # Lighter success color for hover states
        "ERROR": "#FF3B30",              # Apple red
        "WARNING": "#FF9500",              # Apple orange
        "INFO": "#5AC8FA",               # Apple blue (info)
        "PROGRESS_GRADIENT_1": "#0066CC", # Gradient start for progress animation
        "PROGRESS_GRADIENT_2": "#00CCFF", # Gradient end for progress animation
        "CARD_SHADOW": "#0A0A0A",        # Shadow color for cards
        "BORDER": "#333333",             # Border color
        "INPUT_BG": "#151515"            # Input field background
    }

    @classmethod
    def get_theme(cls):
        """Get the current theme name"""
        return cls._current_theme

    @classmethod
    def get_color(cls, color_name):
        """Get a color by name from the theme"""
        return cls.DARK.get(color_name, "#0F0F0F")  # Default to dark background

class ThemeColors:
    """Static theme colors with matte black aesthetic"""
    # Static dark theme colors
    BG_PRIMARY = ThemeManager.get_color("BG_PRIMARY")
    BG_SECONDARY = ThemeManager.get_color("BG_SECONDARY")
    ACCENT = ThemeManager.get_color("ACCENT")
    ACCENT_LIGHT = ThemeManager.get_color("ACCENT_LIGHT")
    TEXT_PRIMARY = ThemeManager.get_color("TEXT_PRIMARY")
    TEXT_SECONDARY = ThemeManager.get_color("TEXT_SECONDARY")
    TEXT_TERTIARY = ThemeManager.get_color("TEXT_TERTIARY")
    SUCCESS = ThemeManager.get_color("SUCCESS")
    SUCCESS_LIGHT = ThemeManager.get_color("SUCCESS_LIGHT")
    ERROR = ThemeManager.get_color("ERROR")
    WARNING = ThemeManager.get_color("WARNING")
    INFO = ThemeManager.get_color("INFO")
    PROGRESS_GRADIENT_1 = ThemeManager.get_color("PROGRESS_GRADIENT_1")
    PROGRESS_GRADIENT_2 = ThemeManager.get_color("PROGRESS_GRADIENT_2")
    CARD_SHADOW = ThemeManager.get_color("CARD_SHADOW")
    BORDER = ThemeManager.get_color("BORDER")
    INPUT_BG = ThemeManager.get_color("INPUT_BG")

class StylishButton(ctk.CTkButton):
    def __init__(self, *args, **kwargs):
        # Extract hover color before passing to super
        self.hover_color = kwargs.pop("hover_color", None)
        self.animation_active = False
        self.animation_lock = threading.Lock()  # Thread safety for animations
        self.is_hovered = False  # Track hover state
        self.click_in_progress = False  # Track click state

        super().__init__(*args, **kwargs)

        # Get the current color
        current_color = self.cget("fg_color")

        # Make buttons darker and more metallic by default
        if "fg_color" not in kwargs:
            # More poppy, darker metallic accent color
            current_color = "#005AC1"  # Darker metallic blue
        elif current_color == ThemeColors.ACCENT:
            current_color = "#005AC1"  # Darker metallic blue
        elif current_color == ThemeColors.SUCCESS:
            current_color = "#0D8C3C"  # Darker metallic green
        elif current_color == ThemeColors.ERROR:
            current_color = "#C52722"  # Darker metallic red
        elif current_color == ThemeColors.WARNING:
            current_color = "#D16802"  # Darker metallic orange

        # Set default hover color if none provided
        if not self.hover_color:
            # If color is a tuple (for light/dark mode), process the dark mode color
            if isinstance(current_color, tuple):
                base_color = current_color[1]  # Dark mode color
            else:
                base_color = current_color

            # Lighten the color for hover with metallic feel
            try:
                # Convert hex to RGB
                r = int(base_color[1:3], 16) / 255.0
                g = int(base_color[3:5], 16) / 255.0
                b = int(base_color[5:7], 16) / 255.0

                # Convert to HSV, adjust brightness, convert back
                h, s, v = colorsys.rgb_to_hsv(r, g, b)
                v = min(v * 1.3, 1.0)  # Increase brightness by 30% for more pop
                s = min(s * 0.9, 1.0)  # Reduce saturation slightly for metallic effect
                r, g, b = colorsys.hsv_to_rgb(h, s, v)

                # Convert back to hex
                hex_color = f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}"
                self.hover_color = hex_color
            except:
                # Fallback if color processing fails
                self.hover_color = ThemeColors.BG_SECONDARY

        self.configure(
            corner_radius=12,  # Perfectly rounded
            font=("SF Pro Display", 13),
            height=36,  # Optimal height
            hover_color=self.hover_color,
            fg_color=current_color,
            text_color=ThemeColors.TEXT_PRIMARY,
            border_width=0
        )

        # Add event bindings for smoother animations
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_click)
        self.bind("<ButtonRelease-1>", self._on_release)

        # Store original properties
        self.original_fg = self.cget("fg_color")
        self.original_text_color = self.cget("text_color")

        # Pre-calculate common colors to avoid recalculation during animations
        self._precalculate_animation_colors()

    def _precalculate_animation_colors(self):
        """Pre-calculate colors for animations to improve performance"""
        try:
            base_color = self.original_fg
            text_color = self.original_text_color

            # Hover colors (pre-calculated for each step with 8 steps)
            self._hover_border_colors = []
            for i in range(9):
                progress = i / 8
                ease = progress * progress * (3.0 - 2.0 * progress)  # Cubic easing
                self._hover_border_colors.append(ease * 1.5)  # Max border width 1.5

            # Text brighten colors
            if isinstance(text_color, str) and text_color.startswith('#'):
                self._hover_text_colors = []
                try:
                    r = int(text_color[1:3], 16)
                    g = int(text_color[3:5], 16)
                    b = int(text_color[5:7], 16)

                    for i in range(9):
                        progress = i / 8
                        ease = progress * progress * (3.0 - 2.0 * progress)  # Cubic easing
                        brightness = 20 * ease
                        r_new = min(255, r + brightness)
                        g_new = min(255, g + brightness)
                        b_new = min(255, b + brightness)

                        self._hover_text_colors.append(f"#{int(r_new):02x}{int(g_new):02x}{int(b_new):02x}")
                except:
                    self._hover_text_colors = [text_color] * 9
            else:
                self._hover_text_colors = [text_color] * 9

            # Click animation colors
            self._click_darker = self._darken_color(base_color, 0.2)
            self._click_brighter = self._lighten_color(base_color, 0.3)

            # Pre-calculate blend steps for click release animation
            self._click_release_colors = []
            for i in range(6):
                blend = 1 - (i / 5)
                color = self._blend_colors(base_color, self._click_brighter, blend)
                self._click_release_colors.append(color)

        except Exception as e:
            print(f"Error pre-calculating button animation colors: {e}")

    def _on_enter(self, event=None):
        """Handle mouse enter event with smooth, optimized animation"""
        with self.animation_lock:
            if self.animation_active or self.is_hovered:
                return

            self.is_hovered = True
            self.animation_active = True

        # Use after() for smoother animations instead of time.sleep()
        def animate_hover(step=0):
            if not self.is_hovered or step >= len(self._hover_border_colors):
                self.animation_active = False
                return

            try:
                # Apply pre-calculated values for optimal performance
                border_width = self._hover_border_colors[step]
                text_color = self._hover_text_colors[step]

                self.configure(
                    border_width=border_width, 
                    border_color=self.hover_color,
                    text_color=text_color
                )

                # Schedule next frame with optimal timing
                self.after(12, lambda: animate_hover(step + 1))
            except Exception as e:
                print(f"Hover animation error: {e}")
                self.animation_active = False
                # Fallback to final state
                self.configure(border_width=1.5, border_color=self.hover_color)

        # Start the animation
        animate_hover()

    def _on_leave(self, event=None):
        """Handle mouse leave event with smooth, optimized animation"""
        self.is_hovered = False

        # Don't run leave animation if click is in progress
        if self.click_in_progress:
            return

        # Use after() for smoother animations
        def animate_leave(step=0, max_steps=5):
            if self.is_hovered or step >= max_steps:
                return

            try:
                # Calculate progress with easing
                progress = 1.0 - (step / max_steps)
                ease = progress * progress  # Quadratic ease-out

                # Update border
                self.configure(border_width=ease * 1.5)

                # Restore text color
                if step == max_steps - 1:
                    self.configure(text_color=self.original_text_color)

                # Schedule next frame
                self.after(10, lambda: animate_leave(step + 1, max_steps))
            except Exception as e:
                print(f"Leave animation error: {e}")
                # Fallback
                self.configure(border_width=0, text_color=self.original_text_color)

        # Start the animation
        animate_leave()

    def _on_click(self, event=None):
        """Handle button click with optimized animation"""
        if self.cget("state") == "disabled":
            return

        self.click_in_progress = True

        try:
            # Immediate feedback - darker color for press effect
            self.configure(fg_color=self._click_darker)
            # Schedule release effect if not manually released
            self.after(200, lambda: self._on_release(None) if self.click_in_progress else None)
        except Exception as e:
            print(f"Click animation error: {e}")

    def _on_release(self, event=None):
        """Handle button release with smooth animation"""
        if not self.click_in_progress:
            return

        self.click_in_progress = False

        try:
            # Flash brighter first
            self.configure(fg_color=self._click_brighter)

            # Then smooth return to original
            def animate_release(step=0):
                if step >= len(self._click_release_colors):
                    # If still hovered after release, reapply hover effect
                    if self.is_hovered:
                        self.configure(
                            border_width=1.5,
                            border_color=self.hover_color,
                            text_color=self._hover_text_colors[-1]
                        )
                    return

                # Apply pre-calculated color
                self.configure(fg_color=self._click_release_colors[step])

                # Schedule next frame
                self.after(16, lambda: animate_release(step + 1))

            # Start the animation with slight delay for the bright flash to be visible
            self.after(40, lambda: animate_release())

        except Exception as e:
            print(f"Release animation error: {e}")
            # Fallback
            self.after(100, lambda: self.configure(fg_color=self.original_fg))

    def _blend_colors(self, color1, color2, blend_factor):
        """Blend two hex colors using the given blend factor (0-1)"""
        try:
            # Convert hex to RGB
            r1, g1, b1 = int(color1[1:3], 16), int(color1[3:5], 16), int(color1[5:7], 16)
            r2, g2, b2 = int(color2[1:3], 16), int(color2[3:5], 16), int(color2[5:7], 16)

            # Linear interpolation
            r = int(r1 + (r2 - r1) * blend_factor)
            g = int(g1 + (g2 - g1) * blend_factor)
            b = int(b1 + (b2 - b1) * blend_factor)

            # Convert back to hex
            return f"#{r:02x}{g:02x}{b:02x}"
        except:
            return color1

    def _darken_color(self, color, amount=0.1):
        """Darken a hex color by the given amount (0-1)"""
        try:
            # Convert hex to RGB
            r, g, b = int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)

            # Darken each component
            r = max(0, int(r * (1 - amount)))
            g = max(0, int(g * (1 - amount)))
            b = max(0, int(b * (1 - amount)))

            # Convert back to hex
            return f"#{r:02x}{g:02x}{b:02x}"
        except:
            return color

    def _lighten_color(self, color, amount=0.1):
        """Lighten a hex color by the given amount (0-1)"""
        try:
            # Convert hex to RGB
            r, g, b = int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)

            # Lighten each component
            r = min(255, int(r + (255 - r) * amount))
            g = min(255, int(g + (255 - g) * amount))
            b = min(255, int(b + (255 - b) * amount))

            # Convert back to hex
            return f"#{r:02x}{g:02x}{b:02x}"
        except:
            return color

class ProgressFrame(ctk.CTkFrame):
    CHUNK_SIZE = 1024 * 1024  # 1MB chunks for better ETA calculation

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.configure(fg_color=ThemeColors.BG_SECONDARY)

        self.progress_var = ctk.DoubleVar(value=0)
        self.speed_var = ctk.StringVar(value="0 B/s")
        self.eta_var = ctk.StringVar(value="Calculating...")
        self.total_var = ctk.StringVar(value="0%")

        # State tracking
        self.is_paused = False
        self.is_pausing = False
        self.pause_animation = None
        self.normal_progress_color = ThemeColors.SUCCESS # Green for syncing/resuming
        self.paused_progress_color = ThemeColors.WARNING  # Yellow when paused (instead of grey)
        self.pausing_progress_color = ThemeColors.WARNING

        # Header with title and status
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent", height=30)
        self.header_frame.pack(fill="x", pady=(10, 0), padx=20)

        # Title on left
        self.title_label = ctk.CTkLabel(
            self.header_frame,
            text="Upload Progress",
            font=("SF Pro Display", 13, "bold"),
            text_color=ThemeColors.TEXT_PRIMARY
        )
        self.title_label.pack(side="left")

        # Status indicator on right
        self.status_indicator = ctk.CTkLabel(
            self.header_frame,
            text="",
            font=("SF Pro Display", 12),
            text_color=ThemeColors.TEXT_SECONDARY
        )
        self.status_indicator.pack(side="right")

        # Progress bar with percentage display - improved container
        self.progress_container = ctk.CTkFrame(self, fg_color="transparent")
        self.progress_container.pack(fill="x", pady=(12, 5), padx=25)  # Increased padding

        # Create a centered frame to better position the progress bar
        self.progress_centered_frame = ctk.CTkFrame(self.progress_container, fg_color="transparent")
        self.progress_centered_frame.pack(fill="x", pady=0, padx=0)

        # Configure grid for shifted right positioning
        self.progress_centered_frame.grid_columnconfigure(0, weight=12)  # Left filler (increased weight for right shift)
        self.progress_centered_frame.grid_columnconfigure(1, weight=0)   # Progress bar
        self.progress_centered_frame.grid_columnconfigure(2, weight=0)   # Percentage
        self.progress_centered_frame.grid_columnconfigure(3, weight=8)   # Right filler (decreased weight for right shift)

        # Enhanced progress bar with better dimensions and visual polish
        self.progress_bar = ctk.CTkProgressBar(
            self.progress_centered_frame, 
            variable=self.progress_var,
            width=400,  # Better width for centering
            progress_color=self.normal_progress_color,
            corner_radius=12,
            height=16,  # Taller for better visibility
            border_width=1,  # Subtle border
            border_color=ThemeColors.BG_SECONDARY,  # Subtle border color
            fg_color=self._blend_colors(ThemeColors.BG_PRIMARY, "#000000", 0.3)  # Slightly darker background for contrast
        )
        self.progress_bar.grid(row=0, column=1, padx=(0, 0), sticky="ew")

        # Percentage label with improved styling - shifted right with more padding
        self.total_label = ctk.CTkLabel(
            self.progress_centered_frame,
            textvariable=self.total_var,
            font=("SF Pro Display", 15, "bold"),  # Slightly larger font
            text_color=ThemeColors.TEXT_PRIMARY,
            width=60,  # Fixed width to prevent layout shifts
            anchor="w"  # Left-align text in the label
        )
        self.total_label.grid(row=0, column=2, padx=(20, 0), sticky="e")  # Increased padding for more right shift

        # Stats frame for speed and ETA - rebuilt for perfect centering
        self.stats_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.stats_frame.pack(fill="x", pady=(5, 15), padx=20)

        # Configure grid with 3 columns for perfect centering
        self.stats_frame.grid_columnconfigure(0, weight=1)  # Left side (speed)
        self.stats_frame.grid_columnconfigure(1, weight=0)  # Center spacer
        self.stats_frame.grid_columnconfigure(2, weight=1)  # Right side (ETA)

        # Speed with icon (left aligned in left column)
        self.speed_frame = ctk.CTkFrame(self.stats_frame, fg_color="transparent")
        self.speed_frame.grid(row=0, column=0, sticky="w")

        self.speed_icon = ctk.CTkLabel(
            self.speed_frame,
            text="↑",  # Upload icon
            font=("SF Pro Display", 12, "bold"),
            text_color=ThemeColors.ACCENT,
            width=20,  # Fixed width for consistent spacing
            anchor="e"  # Right-align the icon
        )
        self.speed_icon.pack(side="left", padx=(0, 3))

        self.speed_label = ctk.CTkLabel(
            self.speed_frame,
            textvariable=self.speed_var,
            font=("SF Pro Display", 12),
            text_color=ThemeColors.TEXT_SECONDARY,
            anchor="w"  # Left-align the text
        )
        self.speed_label.pack(side="left")

        # Center spacer (invisible) - maintains perfect centering
        self.center_spacer = ctk.CTkFrame(
            self.stats_frame, 
            fg_color="transparent",
            width=20,
            height=1
        )
        self.center_spacer.grid(row=0, column=1)

        # ETA with icon (right aligned in right column)
        self.eta_frame = ctk.CTkFrame(self.stats_frame, fg_color="transparent")
        self.eta_frame.grid(row=0, column=2, sticky="e")

        self.eta_icon = ctk.CTkLabel(
            self.eta_frame,
            text="⏱️",  # Clock icon
            font=("SF Pro Display", 12),
            text_color=ThemeColors.TEXT_SECONDARY,
            width=20,  # Fixed width for consistent spacing
            anchor="e"  # Right-align the icon
        )
        self.eta_icon.pack(side="left", padx=(0, 3))

        self.eta_label = ctk.CTkLabel(
            self.eta_frame,
            textvariable=self.eta_var,
            font=("SF Pro Display", 12),
            text_color=ThemeColors.TEXT_SECONDARY,
            anchor="w"  # Left-align the text
        )
        self.eta_label.pack(side="left")

        # Initialize progress bar to 0
        self.progress_bar.set(0)
        self._last_update = time.time()
        self._speed_samples = []

        # Add shimmer effect to progress bar on init
        self._shimmer_effect()

    def _shimmer_effect(self):
        """Add a subtle shimmer effect to the progress bar when at 0%"""
        # Only apply effect if progress is at 0
        if self.progress_var.get() == 0 and not self.is_paused:
            # Create a quick shimmer animation
            start_color = self.normal_progress_color
            highlight_color = ThemeColors.ACCENT_LIGHT

            # Define animation
            def animate(step=0, direction=1):
                # Calculate the blend factor
                if direction > 0:  # Moving forward
                    blend = step / 10
                else:  # Moving back
                    blend = 1 - (step / 10)

                # Calculate the color
                color = self._blend_colors(start_color, highlight_color, blend)
                self.progress_bar.configure(progress_color=color)

                # Continue animation
                next_step = step + 1
                if next_step >= 10:
                    direction = -1
                    next_step = 0

                # Only continue if progress is still 0
                if self.progress_var.get() == 0 and not self.is_paused:
                    self.after(100, lambda: animate(next_step, direction))
                else:
                    # Reset to normal color
                    self.progress_bar.configure(progress_color=self.normal_progress_color)

            # Start animation
            animate()

    def indicate_pausing(self):
        """Visual indicator that we're in the process of pausing - WITH ENHANCED ANIMATIONS"""
        if self.pause_animation:
            self.after_cancel(self.pause_animation)

        # Set state immediately so other components can check it
        self.is_pausing = True
        self.is_paused = False

        # Update status text immediately for visual feedback with more eye-catching color
        self.status_indicator.configure(text="PAUSING", text_color=ThemeColors.WARNING)

        # Change progress bar color immediately for immediate visual feedback
        self.progress_bar.configure(progress_color=ThemeColors.WARNING)

        # Force immediate UI update and make sure it's processed
        self.update_idletasks()
        self.update()

        # Create a more dramatic initial flash to guarantee user sees state change
        def initial_attention_flash():
            try:
                # Quick flash sequence to draw attention - guaranteed to execute
                colors = [ThemeColors.WARNING, "#FFC857", ThemeColors.WARNING]
                for color in colors:
                    self.progress_bar.configure(progress_color=color)
                    self.progress_bar.update()
                    time.sleep(0.1)  # Short delay for quick visual feedback

                # Then start the ongoing pulse animation - Match repeat count with stopping animation (100)
                self._pulse_progress_bar(ThemeColors.ACCENT, ThemeColors.WARNING, repeat=100, steps=12, duration=80)
            except Exception as e:
                print(f"Initial pause flash error: {e}")
                # Fallback to ensure at least some visual feedback
                self.progress_bar.configure(progress_color=ThemeColors.WARNING)

        # Run the initial flash in a separate thread so it's guaranteed to execute
        threading.Thread(target=initial_attention_flash, daemon=True).start()

        # Update speed and ETA with animated "Pausing..." text
        def animate_pause_text():
            try:
                # Continuously cycle the dots animation while in pausing state
                # Keep running for at least 100 cycles to match stopping animation duration
                cycle_count = 0
                max_cycles = 100

                while (self.is_pausing and not self.is_paused) and cycle_count < max_cycles:
                    for dots in ["Pausing.", "Pausing..", "Pausing..."]:
                        if not self.is_pausing or self.is_paused:
                            break
                        self.speed_var.set(dots)
                        self.eta_var.set("Waiting for uploads...")
                        time.sleep(0.25)  # Slightly slower for better visibility
                        cycle_count += 1

                        # Break out if we've run for long enough
                        if cycle_count >= max_cycles:
                            break
            except Exception as e:
                print(f"Pause text animation error: {e}")

        # Start the text animation in a separate thread to avoid blocking
        threading.Thread(target=animate_pause_text, daemon=True).start()

        # Update speed icon with more obvious blinking animation
        self._animate_speed_icon_for_pause()

    def _animate_speed_icon_for_pause(self):
        """Create a blinking animation for the speed icon during pause transition"""
        try:
            # Only start if we're still in pausing state
            if not self.is_pausing or self.is_paused:
                return

            # Get current icon and color
            current_icon = self.speed_icon.cget("text")
            warning_color = ThemeColors.WARNING
            accent_color = ThemeColors.ACCENT

            # Create a more obvious continuous blinking animation
            def blink_icon():
                try:
                    # Continue blinking as long as we're in pausing state
                    blink_count = 0
                    while self.is_pausing and not self.is_paused and blink_count < 100:
                        # Alternate between icons and colors
                        if blink_count % 2 == 0:
                            self.speed_icon.configure(text="↑", text_color=accent_color)
                        else:
                            self.speed_icon.configure(text="⏸", text_color=warning_color)

                        # Force update to make changes visible
                        self.speed_icon.update_idletasks()

                        # Wait between blinks
                        time.sleep(0.25)  # Slower blink is more visible
                        blink_count += 1

                    # Ensure we end with pause icon if we're still pausing
                    if self.is_pausing or self.is_paused:
                        self.speed_icon.configure(text="⏸", text_color=warning_color)

                except Exception as e:
                    print(f"Icon blink error: {e}")
                    # Fallback - set to pause icon
                    self.speed_icon.configure(text="⏸", text_color=warning_color)

            # Run icon blinking in a separate thread
            threading.Thread(target=blink_icon, daemon=True).start()

        except Exception as e:
            print(f"Speed icon pause animation error: {e}")
            # Fallback - set to pause icon
            self.speed_icon.configure(text="⏸", text_color=warning_color)

    def indicate_paused(self, callback=None):
        """Transition to PAUSED state after PAUSING animations complete"""
        # Cancel any ongoing animations first
        if self.pause_animation:
            self.after_cancel(self.pause_animation)

        # Store callback for when animation completes
        self._pause_animation_callback = callback

        # First update state flags so other components cancheck
        self.is_pausing = False
        self.is_paused = True

        # Perform the full transition animation with proper visual feedback
        def execute_pause_transition():
            try:
                # Step 1: Final warning blink before settling
                for i in range(3):
                    # Alternate between accent and warning for final blinks
                    colors = [ThemeColors.WARNING, "#505050", ThemeColors.WARNING]
                    for j, color in enumerate(colors):
                        # Skip animation if state changed
                        if not self.is_paused:
                            break

                        # Apply color
                        self.progress_bar.configure(progress_color=color)
                        self.update_idletasks()
                        time.sleep(0.1)

                # Step 2: Final transition to paused state
                # Get final color
                end_color = self.paused_progress_color

                # Update all elements for consistency - this is the final state
                self.progress_bar.configure(progress_color=end_color)
                self.status_indicator.configure(text="PAUSED", text_color=end_color)
                self.speed_icon.configure(text="⏸", text_color=end_color)
                self.speed_var.set("Paused")
                self.eta_var.set("Paused")

                # Force update to ensure UI is consistent
                self.update_idletasks()

                # Run callback if provided
                if hasattr(self, '_pause_animation_callback') and self._pause_animation_callback:
                    callback_fn = self._pause_animation_callback
                    delattr(self, '_pause_animation_callback')
                    callback_fn()
            except Exception as e:
                # Failsafe to ensure we at least get to PAUSED state
                print(f"Pause transition error: {e}")
                try:
                    self.status_indicator.configure(text="PAUSED", text_color=self.paused_progress_color)
                    self.progress_bar.configure(progress_color=self.paused_progress_color)
                    self.speed_var.set("Paused")
                    self.eta_var.set("Paused")
                except:
                    pass

                # Run callback even if animation failed
                if hasattr(self, '_pause_animation_callback') and self._pause_animation_callback:
                    try:
                        self._pause_animation_callback()
                    except:
                        pass

        # Run the transition in a separate thread
        threading.Thread(target=execute_pause_transition, daemon=True).start()

    def indicate_stopping(self):
        """Visual indicator that we're in the process of stopping - WITH ENHANCED ANIMATIONS"""
        # Cancel any ongoing animations
        if self.pause_animation:
            self.after_cancel(self.pause_animation)

        # Set state flags
        self.is_stopping = True
        self.is_stopped = False

        # Update status text immediately for visual feedback
        self.status_indicator.configure(text="STOPPING", text_color=ThemeColors.ERROR)

        # PERSSISTENT ANIMATION: Create a continuous blinking effect between accent and error colors
        # This animation will continue until explicitly cancelled when fully stopped
        self._pulse_progress_bar(ThemeColors.ACCENT, ThemeColors.ERROR, repeat=100, steps=12, duration=80)

        # Update stats immediately for feedback
        self.speed_var.set("Stopping...")
        self.eta_var.set("Waiting for uploads...")

        # Animate the speed icon with blinking
        self._animate_speed_icon_for_stop()

    def _animate_speed_icon_for_stop(self):
        """Create a blinking animation for the speed icon during stop transition"""
        try:
            # Only start if we're still in stopping state
            if not self.is_stopping or self.is_stopped:
                return

            # Get current icon and color
            current_icon = self.speed_icon.cget("text")
            error_color = ThemeColors.ERROR
            accent_color = ThemeColors.ACCENT

            # Create alternating colors for the icon
            icons = ["↑", "⏹", "↑", "⏹", "⏹"]
            colors = [accent_color, error_color, accent_color, error_color, error_color]

            # Schedule icon updates with proper timing
            for i in range(len(icons)):
                self.after(i * 300, lambda idx=i: self.speed_icon.configure(
                    text=icons[idx],
                    text_color=colors[idx]
                ) if self.is_stopping and not self.is_stopped else None)
        except Exception as e:
            print(f"Speed icon stop animation error: {e}")

    def _animate_icon_transition(self, from_icon, to_icon, target_color):
        """Smooth icon transition with better performance"""
        try:
            # Get current color
            current_color = self.speed_icon.cget("text_color")

            # Immediate feedback - change icon text first
            self.speed_icon.configure(text=from_icon)

            # Schedule the transition to final state after a tiny delay
            self.after(50, lambda: self.speed_icon.configure(text=to_icon, text_color=target_color))
        except Exception as e:
            print(f"Icon transition error: {e}")
            # Fallback
            try:
                self.speed_icon.configure(text=to_icon, text_color=target_color)
            except:
                pass

    def indicate_stopped(self, callback=None):
        """Transition to STOPPED state after STOPPING animations complete"""
        # Cancel any ongoing animations
        if self.pause_animation:
            self.after_cancel(self.pause_animation)

        # Store callback for when animation completes
        self._stop_animation_callback = callback

        # First update state flags so other components can check
        self.is_stopping = False
        self.is_stopped = True

        # Perform the full transition animation with proper visual feedback
        def execute_stop_transition():
            try:
                # Step 1: Final error blinks before settling
                for i in range(3):
                    # Alternate between accent and error for final blinks
                    colors = [ThemeColors.ERROR, "#501010", ThemeColors.ERROR]
                    for j, color in enumerate(colors):
                        # Skip animation if state changed
                        if not self.is_stopped:
                            break

                        # Apply color
                        self.progress_bar.configure(progress_color=color)
                        self.update_idletasks()
                        time.sleep(0.1)

                # Step 2: Final transition to stopped state
                # Get final color
                end_color = ThemeColors.ERROR

                # Update all elements for consistency - this is the final state
                self.progress_bar.configure(progress_color=end_color)
                self.status_indicator.configure(text="STOPPED", text_color=end_color)
                self.speed_icon.configure(text="⏹", text_color=end_color)
                self.speed_var.set("Stopped")
                self.eta_var.set("Click START for new upload")

                # Force update to ensure UI is consistent
                self.update_idletasks()

                # Run callback if provided
                if hasattr(self, '_stop_animation_callback') and self._stop_animation_callback:
                    callback_fn = self._stop_animation_callback
                    delattr(self, '_stop_animation_callback')
                    callback_fn()
            except Exception as e:
                # Failsafe to ensure we at least get to STOPPED state
                print(f"Stop transition error: {e}")
                try:
                    self.status_indicator.configure(text="STOPPED", text_color=ThemeColors.ERROR)
                    self.progress_bar.configure(progress_color=ThemeColors.ERROR)
                    self.speed_var.set("Stopped")
                    self.eta_var.set("Click START for new upload")
                except:
                    pass

                # Run callback even if animation failed
                if hasattr(self, '_stop_animation_callback') and self._stop_animation_callback:
                    try:
                        self._stop_animation_callback()
                    except:
                        pass

        # Run the transition in a separate thread
        threading.Thread(target=execute_stop_transition, daemon=True).start()

    def indicate_resumed(self):
        """Visual indicator for resuming uploads with smooth animation"""
        if self.pause_animation:
            self.after_cancel(self.pause_animation)

        # Update state immediately
        self.is_paused = False
        self.is_pausing = False

        # Immediate feedback - progress bar color
        self.progress_bar.configure(progress_color=self.normal_progress_color)

        # Update status with subtle animation
        self._animate_status_transition("RESUMING", "SYNCING", ThemeColors.SUCCESS)

        # Update speed icon with quick animation
        self._animate_icon_to_active()

        # Reset speed and ETA with subtle fade
        self._animate_stats_to_active()

    def _animate_status_transition(self, first_text, final_text, color):
        """Smooth two-step status text transition"""
        # Immediate first step
        self.status_indicator.configure(text=first_text, text_color=color)

        # Final text after a short delay
        self.after(300, lambda: self.status_indicator.configure(text=final_text))

    def _animate_icon_to_active(self):
        """Smooth transition of speed icon to active state"""
        try:
            # Get target color
            target_color = ThemeColors.ACCENT

            # Immediate feedback - change icon
            self.speed_icon.configure(text="↑")

            # Smooth color transition
            current_color = self.speed_icon.cget("text_color")

            # Single-step quick animation for better responsiveness
            self.after(50, lambda: self.speed_icon.configure(text_color=target_color))
        except Exception as e:
            print(f"Icon animation error: {e}")
            # Fallback
            self.speed_icon.configure(text="↑", text_color=ThemeColors.ACCENT)

    def _animate_stats_to_active(self):
        """Reset speed and ETA displays for active state"""
        # Simply reset to initial state text
        # Calculating actual values will be handled by progress updates
        self.speed_var.set("Calculating...")
        self.eta_var.set("Calculating...")

    def indicate_error(self):
        """Visual indicator of an error condition"""
        if self.pause_animation:
            self.after_cancel(self.pause_animation)

        # Set error state
        self.status_indicator.configure(text="ERROR", text_color=ThemeColors.ERROR)
        self.progress_bar.configure(progress_color=ThemeColors.ERROR)

        # Flash the progress bar to indicate error
        self._flash_progress_bar(ThemeColors.ERROR, ThemeColors.ERROR, steps=5, duration=120)

        # Update stats
        self.speed_var.set("Error occurred")
        self.eta_var.set("Check logs for details")

    def reset(self):
        """Reset the progress frame to initial state"""
        if self.pause_animation:
            self.after_cancel(self.pause_animation)

        # Reset progress bar to 0
        self.progress_var.set(0)
        self.total_var.set("0%")
        self.speed_var.set("0 B/s")
        self.eta_var.set("Calculating...")

        # Reset progress bar colors and status
        self.progress_bar.configure(progress_color=self.normal_progress_color)
        self.status_indicator.configure(text="", text_color=ThemeColors.TEXT_PRIMARY)

        # Reset state flags
        self.is_paused = False
        self.is_pausing = False
        if hasattr(self, 'is_stopping'):
            self.is_stopping = False
        if hasattr(self, 'is_stopped'):
            self.is_stopped = False

        # Reset speed icon
        self.speed_icon.configure(text="↑", text_color=ThemeColors.ACCENT)

        # Force update
        self.update_idletasks()

        # Add shimmer effect to progress bar on reset
        self._shimmer_effect()

    def indicate_resumed(self):
        """Visual indicator that uploads are resumed"""
        if self.pause_animation:
            self.after_cancel(self.pause_animation)

        self.is_pausing = False
        self.is_paused = False

        # Restore normal progress bar
        self.progress_bar.configure(progress_color=self.normal_progress_color)
        self.status_indicator.configure(text="ACTIVE", text_color=ThemeColors.SUCCESS)

        # Restore speed icon
        self.speed_icon.configure(text="↑", text_color=ThemeColors.ACCENT)

        # Brief flash of green to indicate resumed
        self._flash_progress_bar(ThemeColors.SUCCESS, self.normal_progress_color)

    def indicate_network_recovery(self):
        """Visual indicator of network recovery with smoother animation"""
        if self.pause_animation:
            self.after_cancel(self.pause_animation)

        self.status_indicator.configure(text="NETWORK RECOVERED", text_color=ThemeColors.SUCCESS)

        # Create a more distinct and smoother animation for network recovery
        def animate_recovery():
            try:
                # Save original progress value
                original_progress = self.progress_var.get()

                # First pulse the progress bar with a gradient
                colors = [
                    ThemeColors.SUCCESS,  # Start with success color
                    "#50D070",            # Slightly different green
                    "#66F088",            # Brighter green for peak
                    "#50D070",            # Back to mid green
                    ThemeColors.SUCCESS,  # End with success color
                    self.normal_progress_color, # Return to normal
                ]

                # Smooth pulse through colors
                for i, color in enumerate(colors):
                    # More frames for smoother animation
                    if i < len(colors)-1:
                        target_color = colors[i+1]
                        steps = 8
                        for j in range(steps):
                            blend = j/steps
                            # Use cubic easing for smoother transitions
                            ease = blend * blend * (3.0 - 2.0 * blend)
                            current = self._blend_colors(color, target_color, ease)
                            self.progress_bar.configure(progress_color=current)
                            time.sleep(0.02)  # Faster for responsiveness

                # Dynamic connectivity animation in the status text with smoother transitions
                icons = ["⟳", "↻", "⟲", "↺", "⟳"]
                for i, icon in enumerate(icons):
                    self.status_indicator.configure(text=f"{icon} NETWORK RECOVERED")
                    # Use cubic easing for icon timing
                    sleep_time = 0.1 if i in [0, len(icons)-1] else 0.07
                    time.sleep(sleep_time)

                # Playful checkmark animation
                self.status_indicator.configure(text="✓ NETWORK RECOVERED")

                # Ripple effect through the progress bar for visual feedback
                orig_color = self.progress_bar.cget("progress_color")
                # Create light band that moves across progress bar
                for i in range(10):
                    highlight_color = self._blend_colors(orig_color, "#FFFFFF", 0.2)
                    self.progress_bar.configure(progress_color=highlight_color)
                    time.sleep(0.04)
                    self.progress_bar.configure(progress_color=orig_color)
                    time.sleep(0.04)

                # Remove recovery indicator after a while with fade
                time.sleep(2)
                fade_steps = 5
                for i in range(fade_steps):
                    opacity = 1.0 - (i / fade_steps)
                    if i < fade_steps - 1:
                        self.status_indicator.configure(
                            text=f"{'✓ NETWORK RECOVERED' if i < fade_steps/2 else 'RESUMING SYNC'}",
                            text_color=self._blend_colors(ThemeColors.SUCCESS, ThemeColors.ACCENT, i/fade_steps)
                        )
                    else:
                        self.status_indicator.configure(text="SYNCING", text_color=ThemeColors.SUCCESS)
                    time.sleep(0.1)

            except Exception as e:
                print(f"Recovery animation error: {e}")
                # Failsafe
                self.status_indicator.configure(text="SYNCING", text_color=ThemeColors.SUCCESS)
                self.progress_bar.configure(progress_color=self.normal_progress_color)

        threading.Thread(target=animate_recovery, daemon=True).start()

    def indicate_activity(self):
        """Indicate activity like retrying or processing"""
        if self.pause_animation:
            self.after_cancel(self.pause_animation)

        self.status_indicator.configure(text="PROCESSING", text_color=ThemeColors.ACCENT)

        # Brief activity animation
        self._pulse_progress_bar(ThemeColors.ACCENT, "#4488FF", repeat=2)

    def _flash_progress_bar(self, flash_color, final_color, steps=10, duration=50):
        """Flash the progress bar with a color and return to normal"""
        # Single flash
        def animate(step=0):
            if step >= steps * 2:
                self.progress_bar.configure(progress_color=final_color)
                return

            if step < steps:
                # Fade to flash color
                blend = step / steps
                self.progress_bar.configure(progress_color=self._blend_colors(self.normal_progress_color, flash_color, blend))
            else:
                # Fade back to normal
                blend = (steps * 2 - step) / steps
                self.progress_bar.configure(progress_color=self._blend_colors(self.normal_progress_color, flash_color, blend))

            self.pause_animation = self.after(duration, lambda: animate(step + 1))

        animate()

    def _pulse_progress_bar(self, color1, color2, repeat=5, steps=12, duration=50):
        """Create a pulsing effect between two colors with better state tracking"""
        # Create unique animation ID to avoid conflicts
        animation_id = f"pulse_{random.randint(1000, 9999)}"

        def animate(step=0, repeat_count=0):
            # First check if animation should be stopped
            # For pause: check if we're no longer pausing
            # For stop: check if we're no longer stopping
            should_stop = False

            if hasattr(self, 'is_pausing') and hasattr(self, 'is_paused'):
                if self.is_paused and not self.is_pausing:
                    should_stop = True

            if hasattr(self, 'is_stopping') and hasattr(self, 'is_stopped'):
                if self.is_stopped and not self.is_stopping:
                    should_stop = True

            # Stop if max repeats reached or animation should be stopped
            if repeat_count >= repeat or should_stop:
                # Don't change color here - let the final state handler do it
                self.pause_animation = None
                return

            # Calculate color for this step (oscillating between the two colors)
            progress = (step % steps) / steps

            # Make the animation more pronounced - use linear progress for more visible transitions
            # Don't use easing for blink effects as it reduces visibility

            if step % (steps * 2) < steps:
                # Fade from color1 to color2 - more linear for better visibility
                self.progress_bar.configure(progress_color=self._blend_colors(color1, color2, progress))
            else:
                # Fade from color2 to color1 - more linear for better visibility
                self.progress_bar.configure(progress_color=self._blend_colors(color2, color1, progress))

            # Make sure UI updates are processed immediately
            self.progress_bar.update_idletasks()

            # Update counters for next step
            next_step = step + 1
            next_repeat = repeat_count + (1 if next_step % (steps * 2) == 0 else 0)

            # Schedule next animation frame with consistent timing for blink effects
            # Avoid jitter for more consistent blinking
            frame_duration = duration

            # Store the animation ID so it can be cancelled later
            self.pause_animation = self.after(frame_duration, lambda: animate(next_step, next_repeat))

        # Start the animation
        animate()

    def _blend_colors(self, color1, color2, blend_factor):
        """Blend two hex colors using the given blend factor (0-1)"""
        try:
            # Convert hex to RGB
            r1, g1, b1 = int(color1[1:3], 16), int(color1[3:5], 16), int(color1[5:7], 16)
            r2, g2, b2 = int(color2[1:3], 16), int(color2[3:5], 16), int(color2[5:7], 16)

            # Linear interpolation
            r = int(r1 + (r2 - r1) * blend_factor)
            g = int(g1 + (g2 - g1) * blend_factor)
            b = int(b1 + (b2 - b1) * blend_factor)

            # Convert back to hex
            return f"#{r:02x}{g:02x}{b:02x}"
        except:
            return color1

    def update_progress(self, current: int, total: int, speed: float):
        """Update progress bar with current status"""
        if total <= 0 or self.is_paused:
            return

        # Calculate progress percentage
        progress = (current / total) * 100
        self.progress_var.set(progress / 100.0)  # Progress bar expects value between 0 and 1
        self.total_var.set(f"{progress:.1f}%")

        # Calculate and update speed with moving average
        avg_speed = self._calculate_moving_average_speed(speed)
        speed_str = humanize.naturalsize(avg_speed, binary=True) + "/s"
        self.speed_var.set(f"{speed_str}")

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
            self.eta_var.set(f"{eta_str}")
        else:
            self.eta_var.set("Calculating...")

        # Update status indicator if needed
        if not self.is_paused and not self.is_pausing and self.status_indicator.cget("text") == "":
            self.status_indicator.configure(text="ACTIVE", text_color=ThemeColors.SUCCESS)

        # Force immediate update of the UI
        self.progress_bar.update()
        self.update_idletasks()

    def _calculate_moving_average_speed(self, current_speed: float) -> float:
        """Calculate moving average of speed over the last few samples"""
        self._speed_samples.append(current_speed)
        if len(self._speed_samples) > 5:  # Keep last 5 samples
            self._speed_samples.pop(0)
        return sum(self._speed_samples) / len(self._speed_samples)


class LogFrame(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.configure(fg_color=ThemeColors.BG_SECONDARY)

        # Top bar with title and clear button
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.pack(fill="x", padx=15, pady=(15, 0))

        title_label = ctk.CTkLabel(
            self.header_frame,
            text="Activity Log",
            font=("SF Pro Display", 14, "bold"),
            text_color=ThemeColors.TEXT_PRIMARY
        )
        title_label.pack(side="left")

        self.clear_button = StylishButton(
            self.header_frame,
            text="🧹 Clear Log",
            font=("SF Pro Display", 12),
            fg_color="transparent",
            hover_color=ThemeColors.BG_PRIMARY,
            text_color=ThemeColors.TEXT_SECONDARY,
            width=100,
            height=28,
            command=self.clear
        )
        self.clear_button.pack(side="right")

        # Enhanced log text widget with improved styling
        self.log_text = ctk.CTkTextbox(
            self,
            width=600,
            height=200,
            font=("SF Pro Mono", 12),
            fg_color=ThemeColors.BG_PRIMARY,
            text_color=ThemeColors.TEXT_PRIMARY,
            corner_radius=12,
            border_width=1,
            border_color="#333333"
        )
        self.log_text.pack(expand=True, fill="both", padx=15, pady=10)

        # Add padding for better readability
        self.log_text.configure(padx=8, pady=8)

        # Configure basic tags for different message types
        self.log_text.tag_config("timestamp", foreground=ThemeColors.TEXT_TERTIARY)
        self.log_text.tag_config("info_icon", foreground=ThemeColors.INFO)
        self.log_text.tag_config("success_icon", foreground=ThemeColors.SUCCESS)
        self.log_text.tag_config("error_icon", foreground=ThemeColors.ERROR)
        self.log_text.tag_config("warning_icon", foreground=ThemeColors.WARNING)

        # Message text color tags
        self.log_text.tag_config("info_text", foreground=ThemeColors.INFO)
        self.log_text.tag_config("success_text", foreground=ThemeColors.SUCCESS)
        self.log_text.tag_config("error_text", foreground=ThemeColors.ERROR)
        self.log_text.tag_config("warning_text", foreground=ThemeColors.WARNING)

    def log(self, message: str, level: str = "info"):
        """Add a log entry with consistent, simplified colors and improved message handling"""
        # Get current timestamp with milliseconds for uniqueness
        timestamp = time.strftime("%H:%M:%S")

        # Add milliseconds to ensure uniqueness for simultaneous uploads
        ms = int((time.time() % 1) * 1000)
        unique_timestamp = f"{timestamp}.{ms:03d}"

        # Determine icon based on log level
        icons = {
            "info": "ℹ️",
            "success": "✅",
            "error": "❌",
            "warning": "⚠️",
            "debug": "🔍"
        }
        icon = icons.get(level, "•")

        # Ensure log text is editable
        self.log_text.configure(state="normal")

        # Add timestamp with consistent color (now with unique milliseconds)
        self.log_text.insert("end", f"[{unique_timestamp}] ", "timestamp")

        # Add icon with color based on level
        self.log_text.insert("end", f"{icon} ", f"{level}_icon")

        # Add message with color based on level
        if level == "info":
            self.log_text.insert("end", message, "info_text")
        elif level == "success":
            self.log_text.insert("end", message, "success_text")
        elif level == "error":
            self.log_text.insert("end", message, "error_text")
        elif level == "warning":
            self.log_text.insert("end", message, "warning_text")
        else:
            # Default to info color for unknown levels
            self.log_text.insert("end", message, "info_text")

        # Add newline
        self.log_text.insert("end", "\n")

        # Make log text read-only again
        self.log_text.configure(state="disabled")

        # Scroll to the end
        self.log_text.see("end")

        # Animate the clear button if log has many entries
        line_count = int(float(self.log_text.index('end-1c').split('.')[0]))
        if line_count > 50 and not hasattr(self, '_clear_button_animated'):
            self._animate_clear_button()
            self._clear_button_animated = True

    def _animate_clear_button(self):
        """Animate the clear button to draw attention when logs are getting long"""
        original_fg = self.clear_button.cget("fg_color")
        original_text = self.clear_button.cget("text_color")

        def pulse(count=0):
            if count >= 6:  # Pulse 3 times (6 color changes)
                self.clear_button.configure(fg_color=original_fg, text_color=original_text)
                return

            if count % 2 == 0:
                self.clear_button.configure(fg_color=ThemeColors.WARNING, text_color=ThemeColors.TEXT_PRIMARY)
            else:
                self.clear_button.configure(fg_color=original_fg, text_color=original_text)

            self.after(300, lambda: pulse(count + 1))

        pulse()

    def clear(self):
        """Clear the log content"""
        try:
            # Clear all text
            self.log_text.configure(state="normal")
            self.log_text.delete("1.0", "end")

            # Add success message
            self.log("Log cleared ✓", "success")
            self.log_text.configure(state="disabled")

            # Visual feedback on button
            original_fg = self.clear_button.cget("fg_color")
            original_text = self.clear_button.cget("text_color")
            self.clear_button.configure(fg_color=ThemeColors.SUCCESS, text="✓ Cleared")

            # Reset button after delay
            def reset_button():
                time.sleep(1.0)
                self.clear_button.configure(fg_color=original_fg, text_color=original_text, text="🧹 Clear Log")

            threading.Thread(target=reset_button, daemon=True).start()

            # Reset the clear button animation flag
            if hasattr(self, '_clear_button_animated'):
                delattr(self, '_clear_button_animated')

        except Exception as e:
            print(f"Error clearing log: {str(e)}")
            # Simple fallback with no animations
            try:
                self.log_text.configure(state="normal")
                self.log_text.delete("1.0", "end")
                self.log("Log cleared ✓", "success")
                self.log_text.configure(state="disabled")
                self.clear_button.configure(text="🧹 Clear Log")
            except:
                pass

class StylishEntry(ctk.CTkEntry):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Save original colors for animation
        self.original_fg = kwargs.get("fg_color", ThemeColors.BG_PRIMARY)
        self.original_border = kwargs.get("border_color", ThemeColors.BG_SECONDARY)

        self.configure(
            corner_radius=10,
            height=34,
            font=("SF Pro Display", 13),
            fg_color=self.original_fg,
            text_color=ThemeColors.TEXT_PRIMARY,
            border_color=self.original_border,
            border_width=1
        )

        # Add focus animations
        self.bind("<FocusIn>", self._on_focus_in)
        self.bind("<FocusOut>", self._on_focus_out)

    def _on_focus_in(self, event):
        """Handle focus in event with subtle animation"""
        self.configure(border_color=ThemeColors.ACCENT, border_width=2)

    def _on_focus_out(self, event):
        """Handle focus out event"""
        self.configure(border_color=self.original_border, border_width=1)


class ControlPanel(ctk.CTkFrame):
    def __init__(self, master, callbacks: Dict[str, Callable], **kwargs):
        super().__init__(master, **kwargs)
        self.configure(fg_color="transparent")
        self.callbacks = callbacks

        # Create a grid layout with perfect alignment
        self.grid_columnconfigure(0, weight=0)  # Label column
        self.grid_columnconfigure(1, weight=1)  # Input field column
        self.grid_columnconfigure(2, weight=0)  # Button column

        # Refined dimensions for better visual balance
        label_width = 140
        field_width = 360
        button_width = 125
        row_padding = 8  # Slightly increased for better spacing

        # Server URL Configuration - Row 0
        url_label = ctk.CTkLabel(
            self,
            text="Server URL",
            font=("SF Pro Display", 13, "bold"),
            text_color=ThemeColors.TEXT_SECONDARY,
            width=label_width,
            anchor="e"  # Right-aligned text
        )
        url_label.grid(row=0, column=0, padx=(10, 10), pady=row_padding, sticky="e")

        self.server_url = StylishEntry(self, width=field_width)
        self.server_url.grid(row=0, column=1, padx=(0, 10), pady=row_padding, sticky="ew")
        self.server_url.insert(0, "https://eu2.folderfort.com/api/v1")  # Default value

        self.save_server_btn = StylishButton(
            self,
            text="Save URL",
            command=self.save_server_url,
            fg_color=ThemeColors.ACCENT,
            hover_color=ThemeColors.ACCENT_LIGHT,
            width=button_width
        )
        self.save_server_btn.grid(row=0, column=2, padx=(0, 10), pady=row_padding)
        self._create_tooltip(self.save_server_btn, "Save server URL securely")

        # API Configuration - Row 1
        api_label = ctk.CTkLabel(
            self,
            text="API Token",
            font=("SF Pro Display", 13, "bold"),
            text_color=ThemeColors.TEXT_SECONDARY,
            width=label_width,
            anchor="e"
        )
        api_label.grid(row=1, column=0, padx=(10, 10), pady=row_padding, sticky="e")

        self.api_token = StylishEntry(self, width=field_width, show="•")
        self.api_token.grid(row=1, column=1, padx=(0, 10), pady=row_padding, sticky="ew")

        self.save_token_btn = StylishButton(
            self,
            text="Save Token",
            command=self.save_token,
            fg_color=ThemeColors.ACCENT,
            hover_color=ThemeColors.ACCENT_LIGHT,
            width=button_width
        )
        self.save_token_btn.grid(row=1, column=2, padx=(0, 10), pady=row_padding)
        self._create_tooltip(self.save_token_btn, "Save API token securely")

        # Load saved values if they exist
        self.load_saved_values()

        # Folder Selection - Row 2
        folder_label = ctk.CTkLabel(
            self,
            text="Local Folder",
            font=("SF Pro Display", 13, "bold"),
            text_color=ThemeColors.TEXT_SECONDARY,
            width=label_width,
            anchor="e"
        )
        folder_label.grid(row=2, column=0, padx=(10, 10), pady=row_padding, sticky="e")

        self.folder_path = StylishEntry(self, width=field_width)
        self.folder_path.grid(row=2, column=1, padx=(0, 10), pady=row_padding, sticky="ew")

        browse_btn = StylishButton(
            self,
            text="Browse",
            command=self.callbacks.get("browse", lambda: None),
            fg_color=ThemeColors.ACCENT,
            hover_color=ThemeColors.ACCENT_LIGHT,
            width=button_width
        )
        browse_btn.grid(row=2, column=2, padx=(0, 10), pady=row_padding)
        self._create_tooltip(browse_btn, "Select local folder to sync")

        # Cloud Destination Folder - Row 3
        cloud_label = ctk.CTkLabel(
            self,
            text="Cloud Destination",
            font=("SF Pro Display", 13, "bold"),
            text_color=ThemeColors.TEXT_SECONDARY,
            width=label_width,
            anchor="e"
        )
        cloud_label.grid(row=3, column=0, padx=(10, 10), pady=row_padding, sticky="e")

        self.cloud_folder = ctk.CTkComboBox(
            self,
            width=field_width,
            font=("SF Pro Display", 13),
            fg_color=ThemeColors.BG_PRIMARY,
            text_color=ThemeColors.TEXT_PRIMARY,
            dropdown_fg_color=ThemeColors.BG_SECONDARY,
            button_color=ThemeColors.ACCENT,
            button_hover_color=ThemeColors.BG_SECONDARY,
            border_color=ThemeColors.BG_SECONDARY,
            values=["Loading folders..."]
        )
        self.cloud_folder.grid(row=3, column=1, padx=(0, 10), pady=row_padding, sticky="ew")

        refresh_btn = StylishButton(
            self,
            text="↻ Refresh",
            command=self.callbacks.get("refresh_folders", lambda: None),
            fg_color=ThemeColors.ACCENT,
            hover_color=ThemeColors.ACCENT_LIGHT,
            width=button_width
        )
        refresh_btn.grid(row=3, column=2, padx=(0, 10), pady=row_padding)
        self._create_tooltip(refresh_btn, "Refresh cloud folder list")

        # Control Buttons - Row 4
        self.button_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.button_frame.grid(row=4, column=0, columnspan=3, pady=10, padx=10, sticky="ew")

        # Container for button grid with some padding
        button_container = ctk.CTkFrame(self.button_frame, fg_color="transparent")
        button_container.pack(padx=15)

        # Define buttons with more attractive styling and consistent icons
        button_configs = [
            {
                "text": "Start",
                "callback": "start",
                "fg_color": ThemeColors.SUCCESS,
                "hover_color": ThemeColors.SUCCESS_LIGHT,
                "tooltip": "Begin synchronization",
                "icon": "▶"
            },
            {
                "text": "Pause",
                "callback": "pause",
                "fg_color": ThemeColors.WARNING,
                "hover_color": "#FFA52E",
                "tooltip": "Pause current sync",
                "icon": "⏸"
            },
            {
                "text": "Resume",
                "callback": "resume",
                "fg_color": ThemeColors.SUCCESS,
                "hover_color": ThemeColors.SUCCESS_LIGHT,
                "tooltip": "Resume paused sync",
                "icon": "⏯"
            },
            {
                "text": "Stop",
                "callback": "stop",
                "fg_color": ThemeColors.ERROR,
                "hover_color": "#FF5B52",
                "tooltip": "Stop synchronization (requires confirmation)",
                "icon": "⏹"
            },
            {
                "text": "Retry Failed",
                "callback": "retry",
                "fg_color": ThemeColors.ACCENT,
                "hover_color": ThemeColors.ACCENT_LIGHT,
                "tooltip": "Retry failed uploads",
                "icon": "↻"
            }
        ]

        # Place buttons in container with equal spacing
        for i, config in enumerate(button_configs):
            # Create a frame for icon and button
            btn_frame = ctk.CTkFrame(button_container, fg_color="transparent")
            btn_frame.grid(row=0, column=i, padx=5, sticky="ew")

            # Create the button with its icon
            btn_text = f"{config['icon']} {config['text']}"
            btn = StylishButton(
                btn_frame,
                text=btn_text,
                command=self.callbacks.get(config["callback"], lambda: None),
                fg_color=config["fg_color"],
                hover_color=config["hover_color"],
                width=button_width  # Fixed width for consistent appearance
            )
            btn.pack(fill="both", expand=True)

            # Create tooltip functionality
            self._create_tooltip(btn, config["tooltip"])

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
            original_text = self.save_token_btn.cget("text_color")
            self.save_token_btn.configure(fg_color=ThemeColors.SUCCESS, text="✓ Saved")

            # Reset button after delay
            def reset_button():
                time.sleep(1.5)
                self.save_token_btn.configure(fg_color=original_color, text_color=original_text, text="Save Token")

            threading.Thread(target=reset_button, daemon=True).start()
            self.show_message("Token saved securely")
        else:
            self.show_message("Please enter a token first", "error")

    def save_server_url(self):
        url = self.server_url.get().strip()
        if url:
            keyring.set_password("FolderFortSync", "server_url", url)

            # Visual feedback animation
            original_color = self.save_server_btn.cget("fg_color")
            original_text = self.save_server_btn.cget("text_color")
            self.save_server_btn.configure(fg_color=ThemeColors.SUCCESS, text="✓ Saved")

            # Reset button after delay
            def reset_button():
                time.sleep(1.5)
                self.save_server_btn.configure(fg_color=original_color, text_color=original_text, text="Save URL")

            threading.Thread(target=reset_button, daemon=True).start()
            self.show_message("Server URL saved securely")
        else:
            self.show_message("Please enter a server URL first", "error")

    def load_saved_values(self):
        try:
            # Load saved token
            saved_token = keyring.get_password("FolderFortSync", "api_token")
            if saved_token:
                self.api_token.delete(0, "end")
                self.api_token.insert(0, saved_token)

            # Load saved server URL
            saved_url = keyring.get_password("FolderFortSync", "server_url")
            if saved_url:
                self.server_url.delete(0, "end")
                self.server_url.insert(0, saved_url)
        except Exception as e:
            print(f"Error loading saved values: {str(e)}")
            pass

    def show_message(self, message: str, level: str = "info"):
        if self.callbacks.get("show_message"):
            self.callbacks["show_message"](message, level)

    def get_api_token(self) -> str:
        return self.api_token.get().strip()

    def get_server_url(self) -> str:
        return self.server_url.get().strip()

    def get_folder_path(self) -> str:
        return self.folder_path.get().strip()

    def update_button_states(self, paused=False):
        """Update button states based on sync status"""
        try:
            for child in self.button_frame.winfo_children():
                for grandchild in child.winfo_children():
                    if isinstance(grandchild, StylishButton):
                        # Enable/disable buttons based on status
                        if "Pause" in grandchild.cget("text"):
                            grandchild.configure(state="disabled" if paused else "normal")
                        elif "Resume" in grandchild.cget("text"):
                            grandchild.configure(state="normal" if paused else "disabled")
        except Exception as e:
            print(f"Error updating button states: {str(e)}")

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
                    border_color="#404040"
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


def play_completion_animation(progress_frame):
    """Play a smooth completion animation with fade-out effect instead of movement"""
    def animate():
        try:
            # Define colors for smooth transition with more vibrant options
            accent_color = ThemeColors.ACCENT
            success_color = ThemeColors.SUCCESS
            highlight_color = "#6AFF9F"  # Even brighter green for extra pop
            golden_color = "#FFD700"     # Gold for achievement feeling

            # Make sure the status shows COMPLETED
            progress_frame.status_indicator.configure(text="COMPLETED", text_color=ThemeColors.SUCCESS)

            # Save current progress value for restoration
            current_progress = progress_frame.progress_var.get()

            # Celebration flash animation (multiple colors)
            celebration_colors = [highlight_color, success_color, golden_color, success_color]
            for color in celebration_colors:
                progress_frame.progress_bar.configure(progress_color=color)
                progress_frame.update()
                time.sleep(0.08)  # Slightly slower for more impact

            # Instead of bouncing the progress bar (which can look jittery),
            # use a simpler pulsing effect with color changes
            pulse_colors = [success_color, highlight_color, golden_color, success_color]
            for color in pulse_colors:
                # Just change the color for a subtle pulse effect
                progress_frame.progress_bar.configure(progress_color=color)
                progress_frame.update_idletasks()
                time.sleep(0.06)

            # Ensure progress is exactly at 100%
            progress_frame.progress_var.set(1.0)

            # Glow effect - simplified to prevent visual artifacts
            glow_colors = [success_color, highlight_color, golden_color, highlight_color, success_color]
            for color in glow_colors:
                progress_frame.progress_bar.configure(progress_color=color)
                progress_frame.update_idletasks()
                time.sleep(0.06)

            # Final celebration pulse with checkmark in status
            progress_frame.status_indicator.configure(text="✓ COMPLETED", text_color=ThemeColors.SUCCESS)

            # Final transition back to accent color with simple fade
            progress_frame.progress_bar.configure(progress_color=accent_color)
            progress_frame.update()

            # Ensure speed and ETA show completion
            progress_frame.speed_var.set("Complete")
            progress_frame.eta_var.set("Complete")

            # Restore the progress value (although it should be 100% already)
            progress_frame.progress_var.set(1.0)

        except Exception as e:
            print(f"Completion animation error: {str(e)}")
            # Restore to default state if animation fails
            try:
                progress_frame.progress_bar.configure(progress_color=ThemeColors.ACCENT)
                progress_frame.status_indicator.configure(text="COMPLETED", text_color=ThemeColors.SUCCESS)
            except:
                pass

    # Helper function for color blending
    def blend_colors(color1, color2, blend_factor):
        try:
            # Convert hex to RGB
            r1, g1, b1 = int(color1[1:3], 16), int(color1[3:5], 16), int(color1[5:7], 16)
            r2, g2, b2 = int(color2[1:3], 16), int(color2[3:5], 16), int(color2[5:7], 16)

            # Linear interpolation with bounds checking
            r = max(0, min(255, int(r1 + (r2 - r1) * blend_factor)))
            g = max(0, min(255, int(g1 + (g2 - g1) * blend_factor)))
            b = max(0, min(255, int(b1 + (b2 - b1) * blend_factor)))

            # Convert back to hex
            return f"#{r:02x}{g:02x}{b:02x}"
        except:
            # Fallback to original color on error
            return color1

    # Run animation in a separate thread to avoid UI blocking
    threading.Thread(target=animate, daemon=True).start()

# Color mapping for log highlighting (defined at module level for reuse)
color_map = {
    "info": ThemeColors.INFO,     # Cyan for normal messages
    "success": ThemeColors.SUCCESS,  # Green for success/checkmark
    "error": ThemeColors.ERROR,      # Red for errors
    "warning": ThemeColors.WARNING,  # Yellow for warnings
    "debug": ThemeColors.INFO        # Cyan for debug
}

def _animate_reset_button_exit(self):
        """Button exit with fade animation but NO transparency"""
        try:
            if not hasattr(self, 'reset_button') or not self.reset_button.winfo_exists():
                return
                
            # Get original position before animation
            if not hasattr(self, '_reset_button_orig_position'):
                self._reset_button_orig_position = {
                    'relx': 0.5,  # Center position
                    'rely': 0.85  # Position from top
                }
            
            # Use background color for fading instead of transparency
            bg_color = ThemeColors.BG_PRIMARY
            
            # Quick fade out animation using background colors (not transparency)
            steps = 5
            for i in range(1, steps + 1):
                # Calculate progress
                progress = i / steps
                
                # Blend from original color to background color - not using transparency
                if i < steps:
                    fg_blend = self._blend_colors(ThemeColors.ACCENT, bg_color, progress)
                    text_blend = self._blend_colors(ThemeColors.TEXT_PRIMARY, bg_color, progress)
                    
                    # Apply colors (no transparency)
                    self.reset_button.configure(
                        fg_color=fg_blend,
                        text_color=text_blend
                    )
                    
                    # Small horizontal slide
                    new_x = self._reset_button_orig_position['relx'] + (progress * 0.3)
                    self.reset_button.place(
                        relx=new_x,
                        rely=self._reset_button_orig_position['rely'],
                        anchor="center"
                    )
                    
                    # Update UI between steps
                    self.reset_button.update_idletasks()
                    time.sleep(0.02)
            
            # Final cleanup
            self._safely_destroy_reset_button()
            
            # Clean up position data
            if hasattr(self, '_reset_button_orig_position'):
                delattr(self, '_reset_button_orig_position')
            
        except Exception as e:
            print(f"Error removing reset button: {e}")
            # Fallback
            self._safely_destroy_reset_button()

def _fade_in_new_upload_button(self):
        """Button fade-in animation without using transparency"""
        try:
            if not hasattr(self, 'new_upload_button') or not self.new_upload_button.winfo_exists():
                return

            # Original target colors
            original_fg = ThemeColors.SUCCESS
            original_text = ThemeColors.TEXT_PRIMARY
            
            # Start with background color (not transparent)
            bg_color = ThemeColors.BG_PRIMARY
            self.new_upload_button.configure(
                fg_color=bg_color,
                text_color=bg_color
            )
            
            # Animate from background color to target color - no transparency
            steps = 5
            for i in range(1, steps + 1):
                # Calculate progress
                progress = i / steps
                
                # Blend from background to target color
                fg_blend = self._blend_colors(bg_color, original_fg, progress)
                text_blend = self._blend_colors(bg_color, original_text, progress)
                
                # Apply colors
                self.new_upload_button.configure(
                    fg_color=fg_blend,
                    text_color=text_blend
                )
                
                # Update UI between steps
                self.new_upload_button.update_idletasks()
                time.sleep(0.03)
            
            # Ensure final state matches target
            self.new_upload_button.configure(
                fg_color=original_fg,
                text_color=original_text
            )
            
        except Exception as e:
            print(f"Error showing button: {e}")
            # Fallback
            self.new_upload_button.configure(
                fg_color=ThemeColors.SUCCESS,
                text_color=ThemeColors.TEXT_PRIMARY
            )

def _animate_new_upload_button_exit(self):
        """Button exit animation without using transparency"""
        try:
            if not hasattr(self, 'new_upload_button') or not self.new_upload_button.winfo_exists():
                return
                
            # Get original position before animation
            if not hasattr(self, '_upload_button_orig_position'):
                self._upload_button_orig_position = {
                    'relx': 0.5,  # Center position
                    'rely': 0.85  # Position from top
                }
            
            # Use background color for fading instead of transparency
            bg_color = ThemeColors.BG_PRIMARY
            
            # Quick fade out animation using background colors (not transparency)
            steps = 5
            for i in range(1, steps + 1):
                # Calculate progress
                progress = i / steps
                
                # Blend from original color to background color - not using transparency
                if i < steps:
                    fg_blend = self._blend_colors(ThemeColors.SUCCESS, bg_color, progress)
                    text_blend = self._blend_colors(ThemeColors.TEXT_PRIMARY, bg_color, progress)
                    
                    # Apply colors (no transparency)
                    self.new_upload_button.configure(
                        fg_color=fg_blend,
                        text_color=text_blend
                    )
                    
                    # Small horizontal slide
                    new_x = self._upload_button_orig_position['relx'] + (progress * 0.3)
                    self.new_upload_button.place(
                        relx=new_x,
                        rely=self._upload_button_orig_position['rely'],
                        anchor="center"
                    )
                    
                    # Update UI between steps
                    self.new_upload_button.update_idletasks()
                    time.sleep(0.02)
            
            # Final cleanup
            self._safely_destroy_upload_button()
            
            # Clean up position data
            if hasattr(self, '_upload_button_orig_position'):
                delattr(self, '_upload_button_orig_position')
            
        except Exception as e:
            print(f"Error removing upload button: {e}")
            # Fallback
            self._safely_destroy_upload_button()

def _fade_in_reset_button(self):
        """Button fade-in animation without using transparency"""
        try:
            if not hasattr(self, 'reset_button') or not self.reset_button.winfo_exists():
                return

            # Original target colors
            original_fg = ThemeColors.ACCENT
            original_text = ThemeColors.TEXT_PRIMARY
            
            # Start with background color (not transparent)
            bg_color = ThemeColors.BG_PRIMARY
            self.reset_button.configure(
                fg_color=bg_color,
                text_color=bg_color
            )
            
            # Animate from background color to target color - no transparency
            steps = 5
            for i in range(1, steps + 1):
                # Calculate progress
                progress = i / steps
                
                # Blend from background to target color
                fg_blend = self._blend_colors(bg_color, original_fg, progress)
                text_blend = self._blend_colors(bg_color, original_text, progress)
                
                # Apply colors
                self.reset_button.configure(
                    fg_color=fg_blend,
                    text_color=text_blend
                )
                
                # Update UI between steps
                self.reset_button.update_idletasks()
                time.sleep(0.03)
            
            # Ensure final state matches target
            self.reset_button.configure(
                fg_color=original_fg,
                text_color=original_text
            )
            
        except Exception as e:
            print(f"Error showing button: {e}")
            # Fallback
            self.reset_button.configure(
                fg_color=ThemeColors.ACCENT,
                text_color=ThemeColors.TEXT_PRIMARY
            )
            
