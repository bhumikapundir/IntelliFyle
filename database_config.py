from sqlalchemy import create_engine 
from sqlalchemy.ext.declarative import declarative_base 
import os 
 
Base = declarative_base() 
 
def get_database_engine(): 
    current_dir = os.path.dirname(__file__)
    project_root = os.path.abspath(os.path.join(current_dir, '..', '..'))
    db_path = os.path.join(project_root, 'intellifyle.db') 
    engine = create_engine(f'sqlite:///{db_path}') 
    return engine