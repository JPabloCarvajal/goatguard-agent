"""
Graphical log viewer for GOATGuard agent.

Displays real-time logs in a dark-themed window using tkinter.
Uses a queue-based approach: a custom logging handler pushes
log records to a thread-safe queue, and the GUI polls it
every 100ms to update the display.

No external dependencies — tkinter ships with Python.
"""

import tkinter as tk
from tkinter import scrolledtext
import logging
import queue
from datetime import datetime


# Colors for each log level
LEVEL_COLORS = {
    "DEBUG":    "#6b7280",
    "INFO":     "#10b981",
    "WARNING":  "#f59e0b",
    "ERROR":    "#ef4444",
    "CRITICAL": "#dc2626",
}


class QueueHandler(logging.Handler):
    """Logging handler that pushes records to a thread-safe queue.

    The GUI thread polls this queue to display logs without
    blocking the agent's capture and transmission threads.
    """

    def __init__(self, log_queue: queue.Queue) -> None:
        super().__init__()
        self.log_queue = log_queue

    def emit(self, record: logging.LogRecord) -> None:
        self.log_queue.put(record)


class AgentGUI:
    """Real-time log viewer window for the GOATGuard agent.

    Dark-themed tkinter window with:
    - Scrolling log area with color-coded levels
    - Status bar showing connection state
    - Packet and metric counters
    """

    def __init__(self) -> None:
        self.log_queue: queue.Queue = queue.Queue()
        self.root = tk.Tk()
        self.root.title("GOATGuard Agent")
        self.root.geometry("900x550")
        self.root.configure(bg="#0a0e17")
        self.root.resizable(True, True)

        # Try to set icon, ignore if it fails
        try:
            self.root.iconbitmap(default="")
        except Exception:
            pass

        self._build_ui()
        self._setup_tags()

    def _build_ui(self) -> None:
        """Build the window layout."""
        # Header
        header = tk.Frame(self.root, bg="#111827", height=50)
        header.pack(fill=tk.X)
        header.pack_propagate(False)

        title = tk.Label(
            header, text="GOATGuard Agent",
            font=("Consolas", 14, "bold"),
            fg="#06b6d4", bg="#111827",
        )
        title.pack(side=tk.LEFT, padx=15, pady=10)

        self.status_label = tk.Label(
            header, text="● STARTING",
            font=("Consolas", 10),
            fg="#f59e0b", bg="#111827",
        )
        self.status_label.pack(side=tk.RIGHT, padx=15, pady=10)

        # Counters bar
        counters = tk.Frame(self.root, bg="#1a2332", height=30)
        counters.pack(fill=tk.X)
        counters.pack_propagate(False)

        self.packets_label = tk.Label(
            counters, text="Packets: 0",
            font=("Consolas", 9), fg="#94a3b8", bg="#1a2332",
        )
        self.packets_label.pack(side=tk.LEFT, padx=15, pady=5)

        self.metrics_label = tk.Label(
            counters, text="Metrics sent: 0",
            font=("Consolas", 9), fg="#94a3b8", bg="#1a2332",
        )
        self.metrics_label.pack(side=tk.LEFT, padx=15, pady=5)

        self.uptime_label = tk.Label(
            counters, text="Uptime: 0s",
            font=("Consolas", 9), fg="#94a3b8", bg="#1a2332",
        )
        self.uptime_label.pack(side=tk.RIGHT, padx=15, pady=5)

        # Log area
        self.log_area = scrolledtext.ScrolledText(
            self.root,
            font=("Consolas", 9),
            bg="#0a0e17", fg="#c9d1d9",
            insertbackground="#c9d1d9",
            selectbackground="#1e3a5f",
            borderwidth=0, padx=10, pady=10,
            state=tk.DISABLED, wrap=tk.WORD,
        )
        self.log_area.pack(fill=tk.BOTH, expand=True)

        # Footer
        footer = tk.Frame(self.root, bg="#111827", height=25)
        footer.pack(fill=tk.X)
        footer.pack_propagate(False)

        footer_text = tk.Label(
            footer, text="GOATGuard Agent v1.0 — UPB Bucaramanga",
            font=("Consolas", 8), fg="#475569", bg="#111827",
        )
        footer_text.pack(side=tk.LEFT, padx=10, pady=3)

    def _setup_tags(self) -> None:
        """Configure text tags for colored log levels."""
        for level, color in LEVEL_COLORS.items():
            self.log_area.tag_config(level, foreground=color)
        self.log_area.tag_config("TIMESTAMP", foreground="#475569")
        self.log_area.tag_config("MODULE", foreground="#6366f1")

    def get_handler(self) -> QueueHandler:
        """Return a logging handler that feeds this GUI.

        Add this handler to the root logger so all agent
        logs appear in the window.
        """
        handler = QueueHandler(self.log_queue)
        handler.setLevel(logging.DEBUG)
        return handler

    def _poll_queue(self) -> None:
        """Check for new log records and display them."""
        while True:
            try:
                record = self.log_queue.get_nowait()
            except queue.Empty:
                break

            self.log_area.configure(state=tk.NORMAL)

            # Timestamp
            ts = datetime.fromtimestamp(record.created).strftime("%H:%M:%S")
            self.log_area.insert(tk.END, f"[{ts}] ", "TIMESTAMP")

            # Level
            level = record.levelname
            self.log_area.insert(tk.END, f"{level:>8} ", level)

            # Module
            module = record.name.split(".")[-1][:15]
            self.log_area.insert(tk.END, f"{module}: ", "MODULE")

            # Message
            self.log_area.insert(tk.END, f"{record.getMessage()}\n")

            self.log_area.configure(state=tk.DISABLED)
            self.log_area.see(tk.END)

        self.root.after(100, self._poll_queue)

    def set_status(self, text: str, color: str = "#10b981") -> None:
        """Update the status indicator."""
        self.status_label.configure(text=f"● {text}", fg=color)

    def update_counters(self, packets: int = 0, metrics: int = 0,
                        uptime: str = "0s") -> None:
        """Update the counter bar values."""
        self.packets_label.configure(text=f"Packets: {packets:,}")
        self.metrics_label.configure(text=f"Metrics sent: {metrics:,}")
        self.uptime_label.configure(text=f"Uptime: {uptime}")

    def run(self, agent_start_func) -> None:
        """Start the GUI and the agent in a background thread.

        Args:
            agent_start_func: Callable that runs the agent.
                              Will be started in a daemon thread.
        """
        import threading

        # Start agent in background thread
        agent_thread = threading.Thread(target=agent_start_func, daemon=True)
        agent_thread.start()

        # Start polling the log queue
        self.root.after(100, self._poll_queue)

        # Run tkinter main loop (blocks until window closes)
        self.root.mainloop()