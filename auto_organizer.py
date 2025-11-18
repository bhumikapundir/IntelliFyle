import os
import shutil
import sqlite3
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class MLOrganizer:
    def __init__(self, db_path=None):
        self.organized_folder = os.path.join(os.path.expanduser("~"), "Organized_Files")
        self.categories = ["Documents", "Images", "Videos", "Audio", "Spreadsheets", "Code", "Archives", "Other"]
        self.db_path = db_path
        
        # Setup folders
        self.setup_folders()
        logger.info("ML Organizer Ready - Rules-based categorization")
    
    def setup_folders(self):
        """Create organized folders"""
        os.makedirs(self.organized_folder, exist_ok=True)
        for category in self.categories:
            os.makedirs(os.path.join(self.organized_folder, category), exist_ok=True)
    
    def predict_category(self, filename):
        """Predict category using file extension (rules-based)"""
        return self.get_category_from_extension(filename)
    
    def get_category_from_extension(self, filename):
        """Simple rules-based categorization"""
        extension = os.path.splitext(filename)[1].lower()
        
        category_map = {
            # Documents
            '.pdf': 'Documents', '.doc': 'Documents', '.docx': 'Documents', 
            '.txt': 'Documents', '.rtf': 'Documents', '.odt': 'Documents',
            '.ppt': 'Documents', '.pptx': 'Documents',
            
            # Images
            '.jpg': 'Images', '.jpeg': 'Images', '.png': 'Images', 
            '.gif': 'Images', '.bmp': 'Images', '.svg': 'Images', 
            '.webp': 'Images', '.tiff': 'Images', '.ico': 'Images',
            
            # Videos
            '.mp4': 'Videos', '.avi': 'Videos', '.mov': 'Videos', 
            '.mkv': 'Videos', '.wmv': 'Videos', '.flv': 'Videos',
            '.webm': 'Videos', '.m4v': 'Videos', '.mpg': 'Videos',
            
            # Audio
            '.mp3': 'Audio', '.wav': 'Audio', '.m4a': 'Audio', 
            '.flac': 'Audio', '.aac': 'Audio', '.ogg': 'Audio',
            '.wma': 'Audio',
            
            # Spreadsheets
            '.xlsx': 'Spreadsheets', '.xls': 'Spreadsheets', 
            '.csv': 'Spreadsheets', '.ods': 'Spreadsheets',
            
            # Code
            '.py': 'Code', '.java': 'Code', '.js': 'Code', 
            '.html': 'Code', '.css': 'Code', '.cpp': 'Code', 
            '.c': 'Code', '.php': 'Code', '.rb': 'Code',
            '.json': 'Code', '.xml': 'Code',
            
            # Archives
            '.zip': 'Archives', '.rar': 'Archives', '.7z': 'Archives',
            '.tar': 'Archives', '.gz': 'Archives',
        }
        return category_map.get(extension, 'Other')
    
    def suggest_organization(self, file_path):
        """Suggest organization without actually moving files"""
        if not os.path.exists(file_path):
            return None
        
        filename = os.path.basename(file_path)
        predicted_category = self.predict_category(filename)
        
        logger.info(f"SUGGESTION: {filename} -> {predicted_category}")
        return predicted_category
    
    def organize_file(self, file_path):
        """Move file to organized folder - ONLY if user confirms"""
        if not os.path.exists(file_path):
            return False
        
        filename = os.path.basename(file_path)
        predicted_category = self.predict_category(filename)
        
        dest_folder = os.path.join(self.organized_folder, predicted_category)
        dest_path = os.path.join(dest_folder, filename)
        
        try:
            # Don't move if already in organized folder
            if self.organized_folder in file_path:
                return True
                
            os.makedirs(dest_folder, exist_ok=True)
            
            # Only move if file doesn't exist in destination
            if not os.path.exists(dest_path):
                shutil.move(file_path, dest_path)
                logger.info(f"MOVED: {filename} -> {predicted_category}")
                
                # Track real user action
                self.track_file_usage(dest_path, "organized")
                return True
            else:
                logger.warning(f"File already exists in destination: {filename}")
                return False
                
        except Exception as e:
            logger.error(f"Error moving {filename}: {e}")
            return False
    
    def track_file_usage(self, file_path, action_type):
        """Track real user file interactions"""
        if not self.db_path:
            return
            
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS file_usage (
                    id INTEGER PRIMARY KEY,
                    file_path TEXT,
                    file_name TEXT,
                    action_type TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            filename = os.path.basename(file_path)
            cursor.execute(
                "INSERT INTO file_usage (file_path, file_name, action_type) VALUES (?, ?, ?)",
                (file_path, filename, action_type)
            )
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error tracking file: {e}")
    
    def get_suggestions(self, limit=5):
        """Suggest files based on REAL user usage"""
        if not self.db_path:
            return []
            
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check if table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='file_usage'")
            if not cursor.fetchone():
                conn.close()
                return []
            
            # Get files user actually used
            cursor.execute('''
                SELECT file_name, COUNT(*) as usage_count
                FROM file_usage 
                GROUP BY file_name 
                ORDER BY usage_count DESC 
                LIMIT ?
            ''', (limit,))
            
            suggestions = []
            for file_name, usage_count in cursor.fetchall():
                suggestions.append({
                    'file': file_name,
                    'usage_count': usage_count,
                    'reason': f'You used this {usage_count} times'
                })
            
            conn.close()
            return suggestions
            
        except Exception as e:
            logger.error(f"Error getting suggestions: {e}")
            return []
    
    def get_organization_stats(self):
        """Show real organized files"""
        stats = {}
        for category in self.categories:
            category_path = os.path.join(self.organized_folder, category)
            if os.path.exists(category_path):
                file_count = len([f for f in os.listdir(category_path) 
                                if os.path.isfile(os.path.join(category_path, f))])
                stats[category] = file_count
        return stats