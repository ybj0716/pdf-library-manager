"""folder_watcher.py – background PDF folder monitoring"""
import time
import threading
from pathlib import Path
from typing import Callable, Optional

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler, FileCreatedEvent
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False


if WATCHDOG_AVAILABLE:
    class _PDFHandler(FileSystemEventHandler):
        def __init__(self, callback: Callable[[str], None]):
            self.callback = callback
            self._seen: set = set()
            self._lock = threading.Lock()

        def on_created(self, event):
            if event.is_directory:
                return
            path = str(event.src_path)
            if not path.lower().endswith('.pdf'):
                return
            with self._lock:
                if path in self._seen:
                    return
                self._seen.add(path)
            # Wait briefly to ensure file write is complete
            threading.Thread(target=self._delayed_call, args=(path,), daemon=True).start()

        def _delayed_call(self, path: str):
            time.sleep(1.5)
            self.callback(path)
            with self._lock:
                self._seen.discard(path)


class FolderWatcher:
    """Watches a folder and fires callback when a new PDF appears."""

    def __init__(self, callback: Callable[[str], None]):
        self.callback = callback
        self._observer: Optional[object] = None
        self.watch_path: Optional[str] = None

    def start(self, path: str) -> bool:
        if not WATCHDOG_AVAILABLE:
            return False
        self.stop()
        p = Path(path)
        if not p.exists():
            return False
        self.watch_path = str(p)
        handler = _PDFHandler(self.callback)
        self._observer = Observer()
        self._observer.schedule(handler, str(p), recursive=False)
        self._observer.start()
        return True

    def stop(self):
        if self._observer is not None:
            try:
                self._observer.stop()
                self._observer.join(timeout=3)
            except Exception:
                pass
            self._observer = None

    def is_running(self) -> bool:
        return (self._observer is not None
                and hasattr(self._observer, 'is_alive')
                and self._observer.is_alive())
