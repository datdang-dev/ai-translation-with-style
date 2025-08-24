"""
Configuration File Watcher

Monitors configuration files for changes and triggers reload callbacks.
Uses polling-based approach for cross-platform compatibility.
"""

import os
import time
import threading
from typing import List, Callable, Dict, Optional
from pathlib import Path


class ConfigFileWatcher:
    """
    Watches configuration files for changes and triggers callbacks.
    
    Uses a polling-based approach for maximum compatibility across platforms.
    """
    
    def __init__(
        self,
        file_paths: List[str],
        on_change_callback: Callable[[str], None],
        poll_interval: float = 1.0
    ):
        """
        Initialize the file watcher.
        
        Args:
            file_paths: List of file paths to watch
            on_change_callback: Callback function called when files change
            poll_interval: Polling interval in seconds
        """
        self.file_paths = [Path(path) for path in file_paths]
        self.on_change_callback = on_change_callback
        self.poll_interval = poll_interval
        
        self._file_stats: Dict[Path, Optional[os.stat_result]] = {}
        self._watching = False
        self._watch_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        
        # Initialize file stats
        self._update_file_stats()
    
    def start_watching(self) -> None:
        """Start watching files for changes."""
        if self._watching:
            return
        
        self._watching = True
        self._stop_event.clear()
        self._watch_thread = threading.Thread(target=self._watch_loop, daemon=True)
        self._watch_thread.start()
    
    def stop_watching(self) -> None:
        """Stop watching files."""
        if not self._watching:
            return
        
        self._watching = False
        self._stop_event.set()
        
        if self._watch_thread and self._watch_thread.is_alive():
            self._watch_thread.join(timeout=5.0)
    
    def _watch_loop(self) -> None:
        """Main watching loop."""
        while self._watching and not self._stop_event.is_set():
            try:
                self._check_for_changes()
            except Exception as e:
                # Log error but continue watching
                print(f"Error checking for file changes: {e}")
            
            # Wait for next check or stop signal
            self._stop_event.wait(timeout=self.poll_interval)
    
    def _check_for_changes(self) -> None:
        """Check if any watched files have changed."""
        for file_path in self.file_paths:
            try:
                current_stat = self._get_file_stat(file_path)
                previous_stat = self._file_stats.get(file_path)
                
                # Check if file has changed
                if self._has_file_changed(previous_stat, current_stat):
                    self._file_stats[file_path] = current_stat
                    
                    try:
                        self.on_change_callback(str(file_path))
                    except Exception as e:
                        print(f"Error in file change callback for {file_path}: {e}")
                
            except Exception as e:
                # File might have been deleted or become inaccessible
                if file_path in self._file_stats:
                    # File was accessible before but not now - trigger callback
                    self._file_stats[file_path] = None
                    try:
                        self.on_change_callback(str(file_path))
                    except Exception as callback_error:
                        print(f"Error in file change callback for {file_path}: {callback_error}")
    
    def _update_file_stats(self) -> None:
        """Update file stats for all watched files."""
        for file_path in self.file_paths:
            self._file_stats[file_path] = self._get_file_stat(file_path)
    
    def _get_file_stat(self, file_path: Path) -> Optional[os.stat_result]:
        """Get file stat, returning None if file doesn't exist or is inaccessible."""
        try:
            return file_path.stat()
        except (OSError, FileNotFoundError):
            return None
    
    def _has_file_changed(
        self,
        previous_stat: Optional[os.stat_result],
        current_stat: Optional[os.stat_result]
    ) -> bool:
        """Check if file has changed based on stat information."""
        
        # If previous state was None and current is not, file was created
        if previous_stat is None and current_stat is not None:
            return True
        
        # If previous state was not None and current is None, file was deleted
        if previous_stat is not None and current_stat is None:
            return True
        
        # If both are None, no change
        if previous_stat is None and current_stat is None:
            return False
        
        # Both exist, check modification time and size
        if previous_stat is not None and current_stat is not None:
            return (
                previous_stat.st_mtime != current_stat.st_mtime or
                previous_stat.st_size != current_stat.st_size
            )
        
        return False
    
    def add_file(self, file_path: str) -> None:
        """Add a new file to watch."""
        path = Path(file_path)
        if path not in self.file_paths:
            self.file_paths.append(path)
            self._file_stats[path] = self._get_file_stat(path)
    
    def remove_file(self, file_path: str) -> None:
        """Remove a file from watching."""
        path = Path(file_path)
        if path in self.file_paths:
            self.file_paths.remove(path)
            self._file_stats.pop(path, None)
    
    def get_watched_files(self) -> List[str]:
        """Get list of currently watched files."""
        return [str(path) for path in self.file_paths]
    
    def get_file_status(self) -> Dict[str, Dict[str, any]]:
        """Get status information for all watched files."""
        status = {}
        
        for file_path in self.file_paths:
            stat_info = self._file_stats.get(file_path)
            
            if stat_info is not None:
                status[str(file_path)] = {
                    'exists': True,
                    'size': stat_info.st_size,
                    'modified': time.ctime(stat_info.st_mtime),
                    'modified_timestamp': stat_info.st_mtime
                }
            else:
                status[str(file_path)] = {
                    'exists': False,
                    'size': None,
                    'modified': None,
                    'modified_timestamp': None
                }
        
        return status
    
    def is_watching(self) -> bool:
        """Check if currently watching files."""
        return self._watching
    
    def __enter__(self):
        """Context manager entry."""
        self.start_watching()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop_watching()