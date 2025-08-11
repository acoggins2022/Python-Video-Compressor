import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import threading
import queue
import re

# Import the core compression logic from the other file.
from compressor_logic import compress_video

class CompressorApp(tk.Tk):
    """
    A user-friendly GUI for compressing video files using FFmpeg.
    """
    def __init__(self):
        super().__init__()

        # --- Window Setup ---
        self.title("Video Compressor")
        self.minsize(550, 560)
        self.resizable(True, True)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # --- Class Variables ---
        self.input_path_display = tk.StringVar()
        self.output_path_display = tk.StringVar()
        self.full_input_path = ""
        self.full_output_path = ""

        self.status_text = tk.StringVar(value="Welcome! Select a video to start.")
        self.crf_display_value = tk.IntVar(value=26)
        self.progress_var = tk.DoubleVar()
        self.progress_queue = queue.Queue()

        # --- UI Creation ---
        self.create_widgets()
        self.check_status_updates()

    def create_widgets(self):
        """Create and arrange all the GUI elements in the window."""
        main_frame = ttk.Frame(self, padding="15")
        main_frame.grid(row=0, column=0, sticky="nsew")
        main_frame.grid_columnconfigure(0, weight=1)

        # --- File Selection ---
        file_frame = ttk.LabelFrame(main_frame, text="File Paths", padding="10")
        file_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        file_frame.grid_columnconfigure(0, weight=1)

        ttk.Button(file_frame, text="Select Input Video", command=self.select_input).grid(row=0, column=0, sticky="ew", pady=5)
        ttk.Label(file_frame, textvariable=self.input_path_display, foreground="gray").grid(row=1, column=0, sticky="ew", padx=5)

        ttk.Button(file_frame, text="Select Output Location", command=self.select_output).grid(row=2, column=0, sticky="ew", pady=5)
        ttk.Label(file_frame, textvariable=self.output_path_display, foreground="gray").grid(row=3, column=0, sticky="ew", padx=5)

        # --- Compression Settings ---
        settings_frame = ttk.LabelFrame(main_frame, text="Compression Settings", padding="10")
        settings_frame.grid(row=1, column=0, sticky="ew")
        settings_frame.grid_columnconfigure(1, weight=1)

        # CRF Slider
        ttk.Label(settings_frame, text="Video Quality (CRF):").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        crf_controls_frame = ttk.Frame(settings_frame)
        crf_controls_frame.grid(row=0, column=1, sticky="ew", padx=5)
        crf_controls_frame.columnconfigure(0, weight=1)
        
        self.crf_slider = ttk.Scale(
            crf_controls_frame, from_=16, to=34, orient=tk.HORIZONTAL, value=26, command=self.update_crf_label
        )
        self.crf_slider.grid(row=0, column=0, sticky="ew")
        ttk.Label(crf_controls_frame, textvariable=self.crf_display_value, width=3).grid(row=0, column=1, padx=(5,0))
        
        ttk.Label(
            settings_frame, text="Default: 26. Higher value = smaller file, lower quality.", 
            foreground="gray", font=("TkDefaultFont", 8)
        ).grid(row=1, column=0, columnspan=2, sticky="w", padx=5, pady=(0, 10))

        # Preset Dropdown
        ttk.Label(settings_frame, text="Speed vs. Size Preset:").grid(row=2, column=0, sticky="w", padx=5, pady=5)
        self.preset_combo = ttk.Combobox(settings_frame, values=['ultrafast', 'fast', 'medium', 'slow', 'slower'], state="readonly")
        self.preset_combo.set('medium')
        self.preset_combo.grid(row=2, column=1, sticky="ew", padx=5)

        # Resolution Dropdown
        ttk.Label(settings_frame, text="Video Height:").grid(row=3, column=0, sticky="w", padx=5, pady=5)
        resolution_options = ['Keep Original', '360p', '480p', '720p', '1080p', '1440p', '2160p']
        self.res_combo = ttk.Combobox(settings_frame, values=resolution_options, state="readonly")
        self.res_combo.set('Keep Original')
        self.res_combo.grid(row=3, column=1, sticky="ew", padx=5)
        
        ttk.Label(
            settings_frame, text="Note: Upscaling is not supported. Higher selections will default to original.", 
            foreground="gray", font=("TkDefaultFont", 8)
        ).grid(row=4, column=0, columnspan=2, sticky="w", padx=5, pady=(0, 10))

        # Audio Bitrate Dropdown
        ttk.Label(settings_frame, text="Audio Quality:").grid(row=5, column=0, sticky="w", padx=5, pady=5)
        audio_options = ['64k', '96k', '128k', '192k', '256k']
        self.audio_combo = ttk.Combobox(settings_frame, values=audio_options, state="readonly")
        self.audio_combo.set('96k')
        self.audio_combo.grid(row=5, column=1, sticky="ew", padx=5)
        
        # --- Action Button & Progress Bar ---
        self.start_button = ttk.Button(main_frame, text="Start Compression", command=self.start_compression_thread)
        self.start_button.grid(row=2, column=0, sticky="ew", ipady=5, pady=10)

        self.progressbar = ttk.Progressbar(main_frame, variable=self.progress_var, maximum=100)
        self.progressbar.grid(row=3, column=0, sticky="ew", pady=5)

        # --- Status Bar ---
        status_bar = ttk.Label(self, textvariable=self.status_text, relief=tk.SUNKEN, anchor=tk.W, padding="5")
        status_bar.grid(row=1, column=0, sticky="ew")

    def select_input(self):
        """Handle the 'Select Input' button click."""
        path = filedialog.askopenfilename(filetypes=[("Video Files", "*.mp4 *.mkv *.mov *.avi *.wmv"), ("All files", "*.*")])
        if path:
            self.full_input_path = path
            self.input_path_display.set(f"Input: {os.path.basename(path)}")
            
            base_name = os.path.splitext(os.path.basename(path))[0]
            output_dir = os.path.dirname(path)
            self.full_output_path = os.path.join(output_dir, f"{base_name}_compressed.mp4")
            self.output_path_display.set(self.full_output_path)

    def select_output(self):
        """Handle the 'Select Output' button click."""
        suggested_name = os.path.basename(self.full_output_path) if self.full_output_path else ""
        suggested_dir = os.path.dirname(self.full_output_path) if self.full_output_path else os.path.expanduser("~")
        path = filedialog.asksaveasfilename(defaultextension=".mp4", initialfile=suggested_name, initialdir=suggested_dir, filetypes=[("MP4 files", "*.mp4")])
        if path:
            self.full_output_path = path
            self.output_path_display.set(path)

    def update_crf_label(self, value):
        """Rounds the slider value and updates the display label."""
        self.crf_display_value.set(round(float(value)))

    def start_compression_thread(self):
        """
        Validates settings and starts the compression in a separate thread.
        """
        input_file = self.full_input_path
        output_file = self.full_output_path

        if not input_file or not output_file:
            messagebox.showerror("Error", "Please select both an input and output file.")
            return

        res_selection = self.res_combo.get()
        if res_selection == 'Keep Original':
            target_height = 0
        else:
            match = re.search(r'\d+', res_selection)
            target_height = int(match.group()) if match else 0

        settings = {
            'crf': self.crf_display_value.get(),
            'preset': self.preset_combo.get(),
            'target_height': target_height,
            'audio_bitrate': self.audio_combo.get()
        }
        
        self.start_button.config(state=tk.DISABLED)
        self.progress_var.set(0)
        
        thread = threading.Thread(
            target=compress_video,
            args=(input_file, output_file, settings, self.progress_queue.put),
            daemon=True
        )
        thread.start()

    def check_status_updates(self):
        """
        Checks the queue for messages from the worker thread and updates the GUI.
        """
        try:
            data = self.progress_queue.get_nowait()
            
            status = data.get('status')
            message = data.get('message')
            
            if message:
                self.status_text.set(message)
            
            if status == 'progress':
                self.progress_var.set(data.get('value', 0))
            elif status == 'success':
                self.progress_var.set(100)
                self.start_button.config(state=tk.NORMAL)
            elif status == 'error':
                self.progress_var.set(0)
                self.start_button.config(state=tk.NORMAL)

        except queue.Empty:
            pass
        
        self.after(100, self.check_status_updates)

if __name__ == "__main__":
    app = CompressorApp()
    app.mainloop()
