import os
import sys
import time
import logging
import threading
import subprocess
from datetime import datetime

# Setup project path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('intellifyle.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)  # Use stdout for better unicode support
    ]
)
logger = logging.getLogger(__name__)

class IntelliFyleSystem:
    def __init__(self):
        self.db_manager = None
        self.observer = None
        self.running = False
        self.frontend_process = None
        self.ml_organizer = None
    
    def start_system(self):
        """Start the complete IntelliFyle system"""
        try:
            print("🚀 Starting IntelliFyle - Smart File Manager")
            print("📁 Monitoring: Desktop, Documents, Downloads, Pictures, Videos")
            print("🤖 ML Features: Auto-Organization & Smart Suggestions")
            print("🌐 Web Interface: http://localhost:8501")
            print("⏹️  Press Ctrl+C to stop\n")
            
            # Initialize database first
            from database.operations.database_operations import DatabaseManager
            self.db_manager = DatabaseManager()
            self.db_manager.initialize_database()
            print("✅ Database Ready")
            
            # Initialize ML organizer
            self.setup_ml_organizer()
            
            # Start file monitoring
            from monitor.monitor import start_monitoring
            self.observer = start_monitoring(self.file_event_callback)
            print("✅ File Monitoring Active")
            
            # Start frontend
            print("🔄 Starting Web Interface...")
            self.start_frontend()
            
            print("✅ System Fully Operational")
            print("\n📊 Real-time updates will appear here:")
            print("- New files will be categorized automatically")
            print("- File modifications will be tracked")
            print("- ML suggestions will be generated")
            
            # Keep main thread alive
            while self.running:
                time.sleep(1)
                
        except KeyboardInterrupt:
            self.stop_system()
        except Exception as e:
            logger.error(f"❌ Error starting system: {e}")
            self.stop_system()
    
    def setup_ml_organizer(self):
        """Initialize ML organizer"""
        try:
            from ml.auto_organizer import MLOrganizer
            db_path = os.path.join(os.path.dirname(__file__), 'intellifyle.db')
            self.ml_organizer = MLOrganizer(db_path)
            print("✅ ML Organizer Ready")
        except Exception as e:
            print(f"⚠️ ML Organizer not available: {e}")
            self.ml_organizer = None
    
    def file_event_callback(self, event_type, file_path):
        """Handle file events with real-time processing"""
        try:
            filename = os.path.basename(file_path)
            
            if event_type == 'created':
                print(f"📄 NEW: {filename}")
                # Auto-categorize new files
                if self.ml_organizer:
                    category = self.ml_organizer.suggest_organization(file_path)
                    print(f"   🏷️  Suggested Category: {category}")
                    
            elif event_type == 'modified':
                print(f"✏️  UPDATED: {filename}")
                
            elif event_type == 'deleted':
                print(f"🗑️  DELETED: {filename}")
                
            elif event_type == 'moved':
                print(f"📦 MOVED: {filename}")
                
            # Update frontend in real-time (if possible)
            self.trigger_frontend_refresh()
            
        except Exception as e:
            logger.error(f"Error in file event callback: {e}")
    
    def trigger_frontend_refresh(self):
        """Trigger frontend refresh by updating a flag file"""
        try:
            refresh_file = os.path.join(os.path.dirname(__file__), 'refresh.flag')
            with open(refresh_file, 'w') as f:
                f.write(str(time.time()))
        except:
            pass  # Silent fail
    
    def start_frontend(self):
        """Start the Streamlit frontend in a subprocess"""
        try:
            frontend_script = os.path.join(os.path.dirname(__file__), 'ui', 'appp.py')
            
            if not os.path.exists(frontend_script):
                raise FileNotFoundError(f"Frontend script not found: {frontend_script}")
            
            # Start Streamlit as a subprocess with browser auto-open
            self.frontend_process = subprocess.Popen([
                sys.executable, '-m', 'streamlit', 'run', frontend_script,
                '--server.port', '8501',
                '--server.headless', 'false',  # Changed to false to allow browser opening
                '--browser.serverAddress', 'localhost',
                '--server.fileWatcherType', 'none'
            ])
            
            print("✅ Web Interface Started at http://localhost:8501")
            print("📱 Browser should open automatically...")
            
            # Wait a bit for frontend to start
            time.sleep(5)
            
        except Exception as e:
            print(f"❌ Frontend error: {e}")
            print("💡 You can manually start the frontend with: streamlit run ui/appp.py")
    
    def stop_system(self):
        """Stop the system gracefully"""
        print("\n🛑 Shutting down IntelliFyle...")
        self.running = False
        
        # Stop frontend
        if self.frontend_process:
            self.frontend_process.terminate()
            try:
                self.frontend_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.frontend_process.kill()
            print("✅ Frontend Stopped")
        
        # Stop file monitoring
        if self.observer:
            self.observer.stop()
            self.observer.join()
            print("✅ File Monitoring Stopped")
        
        print("✅ System Stopped")

def main():
    # Check if required folders exist
    required_folders = ['monitor', 'database', 'database/config', 'database/models', 
                       'database/operations', 'ml', 'ui']
    
    for folder in required_folders:
        if not os.path.exists(folder):
            os.makedirs(folder)
            print(f"📁 Created folder: {folder}")
    
    system = IntelliFyleSystem()
    system.start_system()

if __name__ == "__main__":
    main()