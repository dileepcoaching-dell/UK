import tkinter as tk
from tkinter import messagebox
import subprocess
import webbrowser
import threading
import os
import sys
import time

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

class Launcher:
    def __init__(self, root):
        self.root = root
        self.root.title("CA Article Toolkit")
        self.root.geometry("440x340")
        self.root.resizable(False, False)
        self.root.configure(bg="#0f172a")

        self.process = None
        self.is_running = False

        # ── Gradient header area
        header = tk.Frame(root, bg="#1e293b", pady=20)
        header.pack(fill="x")

        tk.Label(header, text="UK", font=("Segoe UI", 38, "bold"),
                 fg="#3b82f6", bg="#1e293b").pack()
        tk.Label(header, text="CA Article Toolkit", font=("Segoe UI", 11),
                 fg="#64748b", bg="#1e293b").pack()

        # ── Status pill
        status_frame = tk.Frame(root, bg="#0f172a")
        status_frame.pack(pady=14)
        self.dot = tk.Label(status_frame, text="●", font=("Segoe UI", 12),
                            fg="#64748b", bg="#0f172a")
        self.dot.pack(side="left")
        self.status_label = tk.Label(status_frame, text="  Offline",
                                     font=("Segoe UI", 10), fg="#64748b", bg="#0f172a")
        self.status_label.pack(side="left")

        # ── Start button
        btn_frame = tk.Frame(root, bg="#0f172a")
        btn_frame.pack(pady=8)
        self.start_btn = tk.Button(
            btn_frame, text="▶  Start Toolkit",
            font=("Segoe UI", 13, "bold"),
            bg="#2563eb", fg="white",
            activebackground="#1d4ed8", activeforeground="white",
            relief="flat", cursor="hand2",
            width=22, height=2,
            command=self.toggle_app
        )
        self.start_btn.pack()

        # ── Port info
        self.port_label = tk.Label(root, text="",
                                   font=("Segoe UI", 9), fg="#334155", bg="#0f172a")
        self.port_label.pack(pady=4)

        # ── Footer
        tk.Label(root, text="v1.0  ·  Runs at http://localhost:8501",
                 font=("Segoe UI", 8), fg="#334155", bg="#0f172a").pack(side="bottom", pady=10)

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    # ── Button hover effects
    def _on_enter(self, e):
        if self.is_running:
            self.start_btn.config(bg="#b91c1c")
        else:
            self.start_btn.config(bg="#1d4ed8")

    def _on_leave(self, e):
        if self.is_running:
            self.start_btn.config(bg="#ef4444")
        else:
            self.start_btn.config(bg="#2563eb")

    def toggle_app(self):
        if not self.is_running:
            self.start_app()
        else:
            self.stop_app()

    def start_app(self):
        self.is_running = True
        self.start_btn.config(text="⏳  Starting...", state="disabled", bg="#475569")
        self.status_label.config(text="  Starting Streamlit...", fg="#06b6d4")
        self.dot.config(fg="#06b6d4")
        threading.Thread(target=self.run_streamlit, daemon=True).start()

    def run_streamlit(self):
        try:
            app_path = os.path.join(BASE_DIR, "app.py")
            python_exe = sys.executable  # use same Python that launched this script

            cmd = [
                python_exe, "-m", "streamlit", "run", app_path,
                "--server.port", "8501",
                "--server.headless", "true",
                "--browser.gatherUsageStats", "false"
            ]

            self.process = subprocess.Popen(
                cmd,
                cwd=BASE_DIR,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            )

            # Wait for server to be ready
            time.sleep(4)
            self.root.after(0, self.update_to_running)
            webbrowser.open("http://localhost:8501")

        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Launch Error", f"Failed to start app:\n{str(e)}"))
            self.root.after(0, self.update_to_offline)

    def update_to_running(self):
        self.start_btn.config(text="■  Stop Toolkit", state="normal", bg="#ef4444",
                               activebackground="#b91c1c")
        self.status_label.config(text="  Running on port 8501", fg="#10b981")
        self.dot.config(fg="#10b981")
        self.port_label.config(text="Browser should open automatically", fg="#475569")

    def update_to_offline(self):
        self.is_running = False
        self.start_btn.config(text="▶  Start Toolkit", state="normal", bg="#2563eb",
                               activebackground="#1d4ed8")
        self.status_label.config(text="  Offline", fg="#64748b")
        self.dot.config(fg="#64748b")
        self.port_label.config(text="")

    def stop_app(self):
        if self.process:
            self.process.terminate()
            self.process = None
        self.update_to_offline()

    def on_close(self):
        if self.process:
            self.stop_app()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = Launcher(root)
    root.mainloop()
