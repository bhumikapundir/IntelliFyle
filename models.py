from sqlalchemy import Column, Integer, String, DateTime, Text 
from datetime import datetime 
from database.config.database_config import Base 
 
class File(Base): 
    __tablename__ = "files" 
 
    id = Column(Integer, primary_key=True, index=True) 
    file_path = Column(String, unique=True, index=True) 
    file_name = Column(String) 
    file_extension = Column(String) 
    file_size = Column(Integer) 
    file_type = Column(String) 
    created_time = Column(DateTime) 
    modified_time = Column(DateTime) 
    last_accessed = Column(DateTime, default=datetime.now) 
    access_count = Column(Integer, default=0) 
 
class FileEvent(Base): 
    __tablename__ = "file_events" 
 
    id = Column(Integer, primary_key=True, index=True) 
    file_path = Column(String) 
    event_type = Column(String) 
    timestamp = Column(DateTime, default=datetime.now)