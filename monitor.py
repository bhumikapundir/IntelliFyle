import os
import sys
import logging
import time
from watchdog.observers import Observer 
from watchdog.events import FileSystemEventHandler 

# Setup imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.operations.database_operations import DatabaseManager 

logger = logging.getLogger(__name__)

class FileMonitor(FileSystemEventHandler): 
    def __init__(self, callback=None): 
        self.db_manager = DatabaseManager()
        self.callback = callback
        self.processed_events = set()
 
    def on_created(self, event): 
        if not event.is_directory: 
            # Add delay to ensure file is fully written
            time.sleep(1)  # Increased from 0.5 to 1 second
            file_path = os.path.abspath(event.src_path)
            event_key = f"created_{file_path}_{time.time()}"  # Added timestamp to make unique
            
            # Avoid duplicate processing with longer timeout
            if event_key not in self.processed_events:
                self.processed_events.add(event_key)
                print(f"🤖 Processing: {os.path.basename(file_path)}")
                self.db_manager.add_file(file_path, self.callback)
                
                # Clean old events to prevent memory issues
                if len(self.processed_events) > 1000:
                    self.processed_events.clear()
 
    def on_modified(self, event): 
        if not event.is_directory: 
            file_path = os.path.abspath(event.src_path)
            event_key = f"modified_{file_path}_{time.time()}"
            
            # Avoid duplicate processing
            if event_key not in self.processed_events:
                self.processed_events.add(event_key)
                self.db_manager.update_file(file_path, self.callback)
                
                # Clean old events to prevent memory issues
                if len(self.processed_events) > 1000:
                    self.processed_events.clear()
 
    def on_deleted(self, event): 
        if not event.is_directory: 
            file_path = os.path.abspath(event.src_path)
            event_key = f"deleted_{file_path}_{time.time()}"
            
            if event_key not in self.processed_events:
                self.processed_events.add(event_key)
                self.db_manager.remove_file(file_path, self.callback)
                
                # Clean old events to prevent memory issues
                if len(self.processed_events) > 1000:
                    self.processed_events.clear()
 
    def on_moved(self, event): 
        if not event.is_directory: 
            src_path = os.path.abspath(event.src_path)
            dest_path = os.path.abspath(event.dest_path)
            
            event_key = f"moved_{src_path}_{dest_path}_{time.time()}"
            
            if event_key not in self.processed_events:
                self.processed_events.add(event_key)
                
                # Remove old path, add new path
                self.db_manager.remove_file(src_path, self.callback) 
                time.sleep(0.5)  # Small delay
                self.db_manager.add_file(dest_path, self.callback)
                
                # Clean old events to prevent memory issues
                if len(self.processed_events) > 1000:
                    self.processed_events.clear()

def start_monitoring(callback=None): 
    db_manager = DatabaseManager() 
    db_manager.initialize_database() 
 
    # Watch these folders
    folders_to_watch = [ 
        os.path.expanduser("~/Desktop"), 
        os.path.expanduser("~/Documents"), 
        os.path.expanduser("~/Downloads"), 
        os.path.expanduser("~/Pictures"), 
        os.path.expanduser("~/Videos") 
    ] 
 
    observer = Observer() 
    event_handler = FileMonitor(callback) 
 
    for folder in folders_to_watch: 
        if os.path.exists(folder): 
            observer.schedule(event_handler, folder, recursive=True) 
            logger.info(f"👁️ Monitoring: {folder}")
        else:
            logger.warning(f"⚠️ Folder not found: {folder}")
 
    observer.start() 
    return observer