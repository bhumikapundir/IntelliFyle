from sqlalchemy.orm import Session, sessionmaker 
from database.models.models import File, FileEvent 
from database.config.database_config import get_database_engine 
from datetime import datetime 
import os 
import logging
import sys
import time

logger = logging.getLogger(__name__)

# Add ML integration
try:
    ml_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'ml')
    if ml_path not in sys.path:
        sys.path.insert(0, ml_path)
    from ml.auto_organizer import MLOrganizer
    ML_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ ML module not available: {e}")
    ML_AVAILABLE = False

engine = get_database_engine() 
SessionLocal = sessionmaker(bind=engine) 
 
class DatabaseManager: 
    def __init__(self): 
        self.engine = engine 
        self.Session = SessionLocal
        self.ml_organizer = None
        if ML_AVAILABLE:
            self.setup_ml()
    
    def setup_ml(self):
        """Initialize ML organizer"""
        try:
            db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'intellifyle.db')
            self.ml_organizer = MLOrganizer(db_path)
            logger.info("🤖 ML Organizer Ready")
        except Exception as e:
            logger.error(f"ML setup failed: {e}")
            self.ml_organizer = None
    
    def initialize_database(self):
        """Create database tables"""
        try:
            from database.models.models import Base 
            Base.metadata.create_all(self.engine)
            logger.info("✅ Database Tables Created")
            return True
        except Exception as e:
            logger.error(f"❌ Database initialization failed: {e}")
            return False
 
    def add_file(self, file_path, callback=None): 
        """Add file to database with ML processing"""
        session = self.Session() 
        try: 
            # Wait to ensure file is fully created
            time.sleep(0.5)
            
            if os.path.exists(file_path) and os.path.isfile(file_path): 
                stat = os.stat(file_path) 
                
                # Check if file already exists
                existing_file = session.query(File).filter(File.file_path == file_path).first()
                if existing_file:
                    # Update existing file
                    existing_file.modified_time = datetime.fromtimestamp(stat.st_mtime)
                    existing_file.last_accessed = datetime.now()
                    existing_file.file_size = stat.st_size
                    session.commit()
                    self.log_event(file_path, "updated")
                    
                    # ML tracking
                    if self.ml_organizer:
                        self.ml_organizer.track_file_usage(file_path, "modified")
                        
                else:
                    # Create new file record
                    file_record = File( 
                        file_path=file_path, 
                        file_name=os.path.basename(file_path), 
                        file_extension=os.path.splitext(file_path)[1].lower(), 
                        file_size=stat.st_size, 
                        file_type=self.get_file_type(file_path), 
                        created_time=datetime.fromtimestamp(stat.st_ctime), 
                        modified_time=datetime.fromtimestamp(stat.st_mtime), 
                        last_accessed=datetime.now(), 
                        access_count=1 
                    ) 
                    session.add(file_record) 
                    session.commit() 
                    
                    self.log_event(file_path, "created")
                    
                    # ML auto-organization suggestion
                    if self.ml_organizer:
                        category = self.ml_organizer.suggest_organization(file_path)
                        self.ml_organizer.track_file_usage(file_path, "created")
                        logger.info(f"🏷️  ML Suggestion: {os.path.basename(file_path)} → {category}")
                
                if callback:
                    callback("created", file_path)
                    
        except Exception as e: 
            session.rollback() 
            logger.error(f"❌ Error adding file {file_path}: {e}")
        finally: 
            session.close()
 
    def update_file(self, file_path, callback=None): 
        session = self.Session() 
        try: 
            if os.path.exists(file_path): 
                file = session.query(File).filter(File.file_path == file_path).first() 
                if file: 
                    stat = os.stat(file_path) 
                    file.modified_time = datetime.fromtimestamp(stat.st_mtime) 
                    file.file_size = stat.st_size
                    file.last_accessed = datetime.now() 
                    file.access_count += 1
                    session.commit() 
                    
                    self.log_event(file_path, "modified")
                    
                    # ML tracking
                    if self.ml_organizer:
                        self.ml_organizer.track_file_usage(file_path, "modified")
                    
                    if callback:
                        callback("modified", file_path)
                else:
                    # File exists but not in database, add it
                    self.add_file(file_path, callback)
        except Exception as e: 
            session.rollback() 
            logger.error(f"❌ Error updating file {file_path}: {e}")
        finally: 
            session.close() 
 
    def remove_file(self, file_path, callback=None): 
        session = self.Session() 
        try: 
            file = session.query(File).filter(File.file_path == file_path).first() 
            if file: 
                session.delete(file) 
                session.commit() 
                self.log_event(file_path, "deleted")
                if callback:
                    callback("deleted", file_path)
            else:
                logger.warning(f"⚠️ File not found in database: {file_path}")
        except Exception as e: 
            session.rollback() 
            logger.error(f"❌ Error removing file {file_path}: {e}")
        finally: 
            session.close() 
 
    def get_file_type(self, file_path): 
        extension = os.path.splitext(file_path)[1].lower() 
        type_map = {
            '.txt': 'document', '.doc': 'document', '.docx': 'document', 
            '.pdf': 'document', '.pptx': 'document', '.xlsx': 'document',
            '.jpg': 'image', '.jpeg': 'image', '.png': 'image', 
            '.gif': 'image', '.bmp': 'image', '.svg': 'image', '.webp': 'image',
            '.mp4': 'video', '.avi': 'video', '.mov': 'video', 
            '.mkv': 'video', '.wmv': 'video', '.flv': 'video',
            '.mp3': 'audio', '.wav': 'audio', '.m4a': 'audio', 
            '.flac': 'audio', '.aac': 'audio',
            '.zip': 'archive', '.rar': 'archive', '.7z': 'archive',
            '.py': 'other', '.java': 'other', '.js': 'other',  # Changed from 'code' to 'other'
            '.html': 'other', '.css': 'other', '.cpp': 'other', '.c': 'other'
        }
        return type_map.get(extension, 'other')
            
    def log_event(self, file_path, event_type):
        session = self.Session()
        try:
            event = FileEvent(
                file_path=file_path, 
                event_type=event_type,
                timestamp=datetime.now()
            )
            session.add(event)
            session.commit()
        except Exception as e:
            logger.error(f"❌ Error logging event: {e}")
            session.rollback()
        finally:
            session.close()
    
    # ML Features
    def get_file_suggestions(self, limit=5):
        """Get smart file suggestions"""
        if self.ml_organizer:
            return self.ml_organizer.get_suggestions(limit)
        return []
    
    def get_organization_stats(self):
        """Get file organization statistics"""
        if self.ml_organizer:
            return self.ml_organizer.get_organization_stats()
        return {}