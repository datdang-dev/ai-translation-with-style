#!/usr/bin/env python3
"""
Translation Job Monitor GUI
Provides real-time monitoring of translation jobs with individual log windows
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox
import threading
import asyncio
import json
import os
import sys
import queue
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass

# Add current directory to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from gui_batch_orchestrator import GUIBatchOrchestrator, GUIJobStatus

@dataclass
class JobMonitorWindow:
    """Represents a job monitoring window"""
    window: tk.Toplevel
    text_widget: scrolledtext.ScrolledText
    status_label: ttk.Label
    progress_var: tk.StringVar
    job_id: str

class TranslationMonitorGUI:
    """Main GUI application for monitoring translation jobs"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Translation Job Monitor")
        self.root.geometry("1000x700")
        
        # Job management
        self.orchestrator: Optional[GUIBatchOrchestrator] = None
        self.job_windows: Dict[str, JobMonitorWindow] = {}
        self.job_queue = queue.Queue()
        self.log_queues: Dict[str, queue.Queue] = {}
        
        # Setup GUI
        self.setup_gui()
        self.setup_menu()
        
        # Start background thread for job monitoring
        self.monitoring_thread = threading.Thread(target=self.monitor_jobs, daemon=True)
        self.monitoring_thread.start()
        
        # Update GUI periodically
        self.update_gui()
        
    def setup_gui(self):
        """Setup the main GUI layout"""
        # Main frame
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Top control panel
        control_frame = ttk.LabelFrame(main_frame, text="Job Control", padding=10)
        control_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Configuration section
        config_frame = ttk.Frame(control_frame)
        config_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(config_frame, text="Config File:").pack(side=tk.LEFT)
        self.config_var = tk.StringVar(value="config/preset_translation.json")
        self.config_entry = ttk.Entry(config_frame, textvariable=self.config_var, width=50)
        self.config_entry.pack(side=tk.LEFT, padx=(5, 5))
        ttk.Button(config_frame, text="Browse", command=self.browse_config).pack(side=tk.LEFT)
        
        # Input/Output directories
        io_frame = ttk.Frame(control_frame)
        io_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(io_frame, text="Input Dir:").grid(row=0, column=0, sticky=tk.W)
        self.input_dir_var = tk.StringVar(value="testing_playground")
        ttk.Entry(io_frame, textvariable=self.input_dir_var, width=40).grid(row=0, column=1, padx=(5, 5), sticky=tk.EW)
        ttk.Button(io_frame, text="Browse", command=self.browse_input_dir).grid(row=0, column=2)
        
        ttk.Label(io_frame, text="Output Dir:").grid(row=1, column=0, sticky=tk.W)
        self.output_dir_var = tk.StringVar(value="testing_playground/batch_output")
        ttk.Entry(io_frame, textvariable=self.output_dir_var, width=40).grid(row=1, column=1, padx=(5, 5), sticky=tk.EW)
        ttk.Button(io_frame, text="Browse", command=self.browse_output_dir).grid(row=1, column=2)
        
        io_frame.columnconfigure(1, weight=1)
        
        # Settings
        settings_frame = ttk.Frame(control_frame)
        settings_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(settings_frame, text="File Pattern:").pack(side=tk.LEFT)
        self.pattern_var = tk.StringVar(value="chunk_*.json")
        ttk.Entry(settings_frame, textvariable=self.pattern_var, width=20).pack(side=tk.LEFT, padx=(5, 15))
        
        ttk.Label(settings_frame, text="Max Concurrent:").pack(side=tk.LEFT)
        self.max_concurrent_var = tk.StringVar(value="3")
        ttk.Entry(settings_frame, textvariable=self.max_concurrent_var, width=5).pack(side=tk.LEFT, padx=(5, 15))
        
        ttk.Label(settings_frame, text="Job Delay (s):").pack(side=tk.LEFT)
        self.job_delay_var = tk.StringVar(value="10.0")
        ttk.Entry(settings_frame, textvariable=self.job_delay_var, width=8).pack(side=tk.LEFT, padx=(5, 15))
        
        # Action buttons
        button_frame = ttk.Frame(control_frame)
        button_frame.pack(fill=tk.X)
        
        self.start_button = ttk.Button(button_frame, text="Start Batch Translation", command=self.start_batch_translation)
        self.start_button.pack(side=tk.LEFT, padx=(0, 10))
        
        self.stop_button = ttk.Button(button_frame, text="Stop All Jobs", command=self.stop_all_jobs, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(button_frame, text="Clear Completed", command=self.clear_completed_jobs).pack(side=tk.LEFT, padx=(0, 10))
        
        # Job list
        job_frame = ttk.LabelFrame(main_frame, text="Translation Jobs", padding=10)
        job_frame.pack(fill=tk.BOTH, expand=True)
        
        # Treeview for job list
        columns = ("Status", "Input File", "Output File", "Start Time", "Duration", "Progress")
        self.job_tree = ttk.Treeview(job_frame, columns=columns, show="tree headings", height=15)
        
        # Configure columns
        self.job_tree.heading("#0", text="Job ID")
        self.job_tree.column("#0", width=100)
        
        for col in columns:
            self.job_tree.heading(col, text=col)
            if col == "Status":
                self.job_tree.column(col, width=100)
            elif col in ["Start Time", "Duration", "Progress"]:
                self.job_tree.column(col, width=120)
            else:
                self.job_tree.column(col, width=200)
        
        # Scrollbar for treeview
        tree_scroll = ttk.Scrollbar(job_frame, orient=tk.VERTICAL, command=self.job_tree.yview)
        self.job_tree.configure(yscrollcommand=tree_scroll.set)
        
        self.job_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Context menu for jobs
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="Open Log Window", command=self.open_job_log)
        self.context_menu.add_command(label="View Details", command=self.view_job_details)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Export Logs", command=self.export_job_logs)
        self.context_menu.add_command(label="Cancel Job", command=self.cancel_job)
        
        self.job_tree.bind("<Button-3>", self.show_context_menu)
        self.job_tree.bind("<Double-1>", self.open_job_log)
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.pack(fill=tk.X, pady=(10, 0))
        
    def setup_menu(self):
        """Setup application menu"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Load Configuration", command=self.load_configuration)
        file_menu.add_command(label="Save Configuration", command=self.save_configuration)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        
        # View menu
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="View", menu=view_menu)
        view_menu.add_command(label="Refresh Jobs", command=self.refresh_job_list)
        view_menu.add_command(label="Open All Log Windows", command=self.open_all_log_windows)
        view_menu.add_command(label="Close All Log Windows", command=self.close_all_log_windows)
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self.show_about)
        
    def browse_config(self):
        """Browse for configuration file"""
        filename = filedialog.askopenfilename(
            title="Select Configuration File",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if filename:
            self.config_var.set(filename)
            
    def browse_input_dir(self):
        """Browse for input directory"""
        dirname = filedialog.askdirectory(title="Select Input Directory")
        if dirname:
            self.input_dir_var.set(dirname)
            
    def browse_output_dir(self):
        """Browse for output directory"""
        dirname = filedialog.askdirectory(title="Select Output Directory")
        if dirname:
            self.output_dir_var.set(dirname)
            
    def start_batch_translation(self):
        """Start batch translation process"""
        try:
            # Validate inputs
            config_path = self.config_var.get()
            input_dir = self.input_dir_var.get()
            output_dir = self.output_dir_var.get()
            pattern = self.pattern_var.get()
            max_concurrent = int(self.max_concurrent_var.get())
            job_delay = float(self.job_delay_var.get())
            
            if not os.path.exists(config_path):
                messagebox.showerror("Error", f"Configuration file not found: {config_path}")
                return
                
            if not os.path.exists(input_dir):
                messagebox.showerror("Error", f"Input directory not found: {input_dir}")
                return
                
            # Create output directory if it doesn't exist
            os.makedirs(output_dir, exist_ok=True)
            
            # Initialize orchestrator
            self.orchestrator = GUIBatchOrchestrator(
                config_path=config_path,
                max_concurrent=max_concurrent,
                job_delay=job_delay
            )
            
            # Setup callbacks for real-time updates
            self.orchestrator.add_status_callback(self.on_job_status_update)
            
            # Start translation in separate thread
            translation_thread = threading.Thread(
                target=self.run_batch_translation,
                args=(input_dir, output_dir, pattern),
                daemon=True
            )
            translation_thread.start()
            
            # Update UI state
            self.start_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)
            self.status_var.set("Starting batch translation...")
            
        except ValueError as e:
            messagebox.showerror("Error", f"Invalid input values: {e}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start batch translation: {e}")
            
    def run_batch_translation(self, input_dir: str, output_dir: str, pattern: str):
        """Run batch translation in background thread"""
        try:
            # Create new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Run the translation with GUI monitoring
            summary = loop.run_until_complete(
                self.orchestrator.run_from_directory_with_gui(input_dir, output_dir, pattern)
            )
            
            # Update status
            self.job_queue.put(("batch_complete", summary))
            
        except Exception as e:
            self.job_queue.put(("batch_error", str(e)))
        finally:
            loop.close()
            
    def stop_all_jobs(self):
        """Stop all running jobs"""
        if self.orchestrator:
            self.orchestrator.cancel_all_jobs()
        self.status_var.set("Stopping all jobs...")
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        
    def clear_completed_jobs(self):
        """Clear completed jobs from the list"""
        if self.orchestrator:
            # Get jobs that will be cleared
            jobs_to_clear = []
            for job_id, job in self.orchestrator.gui_jobs.items():
                if job.status in ["completed", "failed", "cancelled"]:
                    jobs_to_clear.append(job_id)
                    
            # Close associated log windows
            for job_id in jobs_to_clear:
                if job_id in self.job_windows:
                    self.job_windows[job_id].window.destroy()
                    del self.job_windows[job_id]
                    
            # Clear from orchestrator
            self.orchestrator.clear_completed_jobs()
            
            # Update GUI
            remaining_jobs = list(self.orchestrator.gui_jobs.values())
            self.update_job_list_gui(remaining_jobs)
        else:
            # Fallback to manual clearing
            for item in self.job_tree.get_children():
                status = self.job_tree.item(item)["values"][0]
                if status in ["completed", "failed", "cancelled"]:
                    job_id = self.job_tree.item(item)["text"]
                    self.job_tree.delete(item)
                    # Close associated log window
                    if job_id in self.job_windows:
                        self.job_windows[job_id].window.destroy()
                        del self.job_windows[job_id]
                    
    def show_context_menu(self, event):
        """Show context menu for job tree"""
        item = self.job_tree.identify_row(event.y)
        if item:
            self.job_tree.selection_set(item)
            self.context_menu.post(event.x_root, event.y_root)
            
    def open_job_log(self, event=None):
        """Open log window for selected job"""
        selection = self.job_tree.selection()
        if not selection:
            return
            
        job_id = self.job_tree.item(selection[0])["text"]
        
        if job_id in self.job_windows:
            # Bring existing window to front
            self.job_windows[job_id].window.lift()
            return
            
        # Create new log window
        log_window = tk.Toplevel(self.root)
        log_window.title(f"Job Log - {job_id}")
        log_window.geometry("800x600")
        
        # Status frame
        status_frame = ttk.Frame(log_window)
        status_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(status_frame, text="Status:").pack(side=tk.LEFT)
        status_var = tk.StringVar(value="Unknown")
        status_label = ttk.Label(status_frame, textvariable=status_var, font=("Arial", 10, "bold"))
        status_label.pack(side=tk.LEFT, padx=(5, 20))
        
        progress_var = tk.StringVar(value="")
        ttk.Label(status_frame, textvariable=progress_var).pack(side=tk.LEFT)
        
        # Log text area
        log_frame = ttk.Frame(log_window)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        text_widget = scrolledtext.ScrolledText(
            log_frame,
            wrap=tk.WORD,
            font=("Consolas", 10),
            bg="black",
            fg="green"
        )
        text_widget.pack(fill=tk.BOTH, expand=True)
        
        # Store window reference
        self.job_windows[job_id] = JobMonitorWindow(
            window=log_window,
            text_widget=text_widget,
            status_label=status_label,
            progress_var=progress_var,
            job_id=job_id
        )
        
        # Preload existing logs if available
        if self.orchestrator:
            job = self.orchestrator.get_job_by_id(job_id)
            if job and getattr(job, "log_messages", None):
                for message in job.log_messages:
                    text_widget.insert(tk.END, message + "\n")
                text_widget.see(tk.END)
        
        # Create log queue for this job
        if job_id not in self.log_queues:
            self.log_queues[job_id] = queue.Queue()
        
        # Setup real-time logging callback
        if self.orchestrator:
            def log_callback(message):
                try:
                    self.log_queues[job_id].put(message)
                except:
                    pass
                    
            self.orchestrator.add_log_callback(job_id, log_callback)
        
        # Handle window close
        def on_close():
            if job_id in self.job_windows:
                del self.job_windows[job_id]
            if self.orchestrator:
                self.orchestrator.remove_log_callback(job_id)
            log_window.destroy()
        
        log_window.protocol("WM_DELETE_WINDOW", on_close)
        
    def view_job_details(self):
        """View detailed information about selected job"""
        selection = self.job_tree.selection()
        if not selection:
            return
            
        item = selection[0]
        job_id = self.job_tree.item(item)["text"]
        
        if self.orchestrator:
            job = self.orchestrator.get_job_by_id(job_id)
            if job:
                details = f"""Job Details:
        
Job ID: {job.job_id}
Status: {job.status}
Input File: {job.input_path}
Output File: {job.output_path}
Progress: {job.progress:.1%}
Current Step: {job.current_step or 'N/A'}
Completed Steps: {job.completed_steps}/{job.total_steps}
Start Time: {datetime.fromtimestamp(job.start_time).strftime("%Y-%m-%d %H:%M:%S") if job.start_time else 'N/A'}
End Time: {datetime.fromtimestamp(job.end_time).strftime("%Y-%m-%d %H:%M:%S") if job.end_time else 'N/A'}
Duration: {f"{job.end_time - job.start_time:.2f} seconds" if job.start_time and job.end_time else 'N/A'}
Error: {job.error or 'None'}
Log Messages: {len(job.log_messages)} entries
"""
            else:
                details = "Job not found in orchestrator"
        else:
            values = self.job_tree.item(item)["values"]
            details = f"""Job Details:
        
Job ID: {job_id}
Status: {values[0]}
Input File: {values[1]}
Output File: {values[2]}
Start Time: {values[3]}
Duration: {values[4]}
Progress: {values[5]}
"""
        
        messagebox.showinfo("Job Details", details)
        
    def export_job_logs(self):
        """Export logs for selected job"""
        selection = self.job_tree.selection()
        if not selection:
            return
            
        job_id = self.job_tree.item(selection[0])["text"]
        
        if not self.orchestrator:
            messagebox.showerror("Error", "No orchestrator available")
            return
            
        filename = filedialog.asksaveasfilename(
            title="Export Job Logs",
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            initialname=f"{job_id}_logs.txt"
        )
        
        if filename:
            if self.orchestrator.export_job_logs(job_id, filename):
                messagebox.showinfo("Success", f"Logs exported to {filename}")
            else:
                messagebox.showerror("Error", "Failed to export logs")
                
    def cancel_job(self):
        """Cancel selected job"""
        selection = self.job_tree.selection()
        if not selection:
            return
            
        job_id = self.job_tree.item(selection[0])["text"]
        
        if self.orchestrator:
            job = self.orchestrator.get_job_by_id(job_id)
            if job and job.status in ["pending", "processing"]:
                result = messagebox.askyesno("Cancel Job", f"Are you sure you want to cancel job {job_id}?")
                if result:
                    self.orchestrator.update_job_status(job_id, status="cancelled")
                    messagebox.showinfo("Job Cancelled", f"Job {job_id} has been cancelled")
            else:
                messagebox.showinfo("Cannot Cancel", f"Job {job_id} cannot be cancelled (status: {job.status if job else 'unknown'})")
        else:
            messagebox.showerror("Error", "No orchestrator available")
        
    def open_all_log_windows(self):
        """Open log windows for all jobs"""
        for item in self.job_tree.get_children():
            self.job_tree.selection_set(item)
            self.open_job_log()
            
    def close_all_log_windows(self):
        """Close all log windows"""
        for job_id, job_window in list(self.job_windows.items()):
            job_window.window.destroy()
        self.job_windows.clear()
        
    def refresh_job_list(self):
        """Refresh the job list"""
        if self.orchestrator and hasattr(self.orchestrator, 'gui_jobs'):
            jobs = list(self.orchestrator.gui_jobs.values())
            self.update_job_list_gui(jobs)
            
    def load_configuration(self):
        """Load configuration from file"""
        filename = filedialog.askopenfilename(
            title="Load Configuration",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if filename:
            try:
                with open(filename, 'r') as f:
                    config = json.load(f)
                    
                # Update GUI with loaded configuration
                self.config_var.set(config.get('config_path', ''))
                self.input_dir_var.set(config.get('input_dir', ''))
                self.output_dir_var.set(config.get('output_dir', ''))
                self.pattern_var.set(config.get('pattern', 'chunk_*.json'))
                self.max_concurrent_var.set(str(config.get('max_concurrent', 3)))
                self.job_delay_var.set(str(config.get('job_delay', 10.0)))
                
                messagebox.showinfo("Success", "Configuration loaded successfully")
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load configuration: {e}")
                
    def save_configuration(self):
        """Save current configuration to file"""
        filename = filedialog.asksaveasfilename(
            title="Save Configuration",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if filename:
            try:
                config = {
                    'config_path': self.config_var.get(),
                    'input_dir': self.input_dir_var.get(),
                    'output_dir': self.output_dir_var.get(),
                    'pattern': self.pattern_var.get(),
                    'max_concurrent': int(self.max_concurrent_var.get()),
                    'job_delay': float(self.job_delay_var.get())
                }
                
                with open(filename, 'w') as f:
                    json.dump(config, f, indent=2)
                    
                messagebox.showinfo("Success", "Configuration saved successfully")
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save configuration: {e}")
                
    def show_about(self):
        """Show about dialog"""
        about_text = """Translation Job Monitor GUI
        
A graphical interface for monitoring batch translation jobs.

Features:
- Real-time job monitoring
- Individual log windows for each job
- Batch job management
- Configuration save/load

Version: 1.0
"""
        messagebox.showinfo("About", about_text)
        
    def monitor_jobs(self):
        """Background thread for monitoring jobs"""
        while True:
            try:
                # Check for job updates
                if not self.job_queue.empty():
                    event_type, data = self.job_queue.get_nowait()
                    
                    if event_type == "batch_complete":
                        self.root.after(0, self.handle_batch_complete, data)
                    elif event_type == "batch_error":
                        self.root.after(0, self.handle_batch_error, data)
                        
                # Update job list if orchestrator is available
                if self.orchestrator and hasattr(self.orchestrator, 'gui_jobs'):
                    jobs = list(self.orchestrator.gui_jobs.values())
                    self.root.after(0, self.update_job_list_gui, jobs)
                    
                time.sleep(1)
                
            except queue.Empty:
                pass
            except Exception as e:
                print(f"Error in monitor_jobs: {e}")
                
    def handle_batch_complete(self, summary):
        """Handle batch completion"""
        self.status_var.set(f"Batch complete - {summary.get('completed', 0)} jobs completed")
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        
        messagebox.showinfo("Batch Complete", 
                          f"Translation completed!\n"
                          f"Completed: {summary.get('completed', 0)}\n"
                          f"Failed: {summary.get('failed', 0)}\n"
                          f"Success Rate: {summary.get('success_rate', 0):.1%}")
        
    def handle_batch_error(self, error_msg):
        """Handle batch error"""
        self.status_var.set(f"Batch error: {error_msg}")
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        messagebox.showerror("Batch Error", f"Translation failed: {error_msg}")
        
    def update_job_list_gui(self, jobs):
        """Update the job list in the GUI using GUIJobStatus objects"""
        # Clear existing items
        for item in self.job_tree.get_children():
            self.job_tree.delete(item)
            
        # Add current jobs
        for job in jobs:
            # Calculate duration
            duration = ""
            if job.start_time:
                if job.end_time:
                    duration = f"{job.end_time - job.start_time:.1f}s"
                else:
                    duration = f"{time.time() - job.start_time:.1f}s"
                    
            # Format start time
            start_time = ""
            if job.start_time:
                start_time = datetime.fromtimestamp(job.start_time).strftime("%H:%M:%S")
                
            # Progress info with percentage
            progress_text = f"{job.progress:.1%}"
            if job.current_step:
                progress_text += f" - {job.current_step}"
            
            values = (
                job.status,
                os.path.basename(job.input_path),
                os.path.basename(job.output_path),
                start_time,
                duration,
                progress_text
            )
            
            item = self.job_tree.insert("", "end", text=job.job_id, values=values)
            
            # Color code by status
            if job.status == "completed":
                self.job_tree.set(item, "Status", "✅ Completed")
            elif job.status == "failed":
                self.job_tree.set(item, "Status", "❌ Failed")
            elif job.status == "processing":
                self.job_tree.set(item, "Status", "🔄 Processing")
            elif job.status == "cancelled":
                self.job_tree.set(item, "Status", "🚫 Cancelled")
            else:
                self.job_tree.set(item, "Status", "⏳ Pending")
                
            # Update log window if exists
            if job.job_id in self.job_windows:
                job_window = self.job_windows[job.job_id]
                status_text = f"Status: {job.status}"
                if job.current_step:
                    status_text += f" - {job.current_step}"
                job_window.progress_var.set(status_text)
                
    def on_job_status_update(self, jobs_dict):
        """Callback for job status updates from orchestrator"""
        # This is called from orchestrator thread, need to schedule GUI update
        jobs = list(jobs_dict.values())
        self.root.after(0, self.update_job_list_gui, jobs)
        
    def update_job_list(self, jobs):
        """Legacy method for backward compatibility"""
        # Convert old-style jobs to GUI format if needed
        if jobs and hasattr(jobs[0], 'job_id'):
            self.update_job_list_gui(jobs)
        else:
            # Handle old BatchJob format
            gui_jobs = []
            for i, job in enumerate(jobs):
                job_id = f"job_{i}"
                gui_job = GUIJobStatus(
                    job_id=job_id,
                    input_path=job.input_path,
                    output_path=job.output_path,
                    status=job.status,
                    error=job.error,
                    start_time=job.start_time,
                    end_time=job.end_time
                )
                gui_jobs.append(gui_job)
            self.update_job_list_gui(gui_jobs)
                    
    def update_gui(self):
        """Periodic GUI update"""
        # Update log windows with queued messages
        for job_id, log_queue in self.log_queues.items():
            if job_id in self.job_windows:
                job_window = self.job_windows[job_id]
                try:
                    while True:
                        message = log_queue.get_nowait()
                        job_window.text_widget.insert(tk.END, message + "\n")
                        job_window.text_widget.see(tk.END)
                except queue.Empty:
                    pass
                    
        # Schedule next update
        self.root.after(1000, self.update_gui)
        
    def run(self):
        """Start the GUI application"""
        self.root.mainloop()


def main():
    """Main function"""
    app = TranslationMonitorGUI()
    app.run()


if __name__ == "__main__":
    main()