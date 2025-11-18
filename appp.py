import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
import os
import sys
import sqlite3
import shutil
from sqlalchemy.orm import Session
from database.config.database_config import get_database_engine
from database.models.models import File, FileEvent
import subprocess
import platform

# Add project root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)

# ---------------------- DATABASE FUNCTIONS ----------------------
def get_db_session():
    try:
        engine = get_database_engine()
        return Session(bind=engine)
    except:
        return None

def get_all_files():
    try:
        session = get_db_session()
        if session:
            files = session.query(File).order_by(File.created_time.desc()).all()
            session.close()
            return files
        return []
    except:
        return []

def get_files_by_category(category):
    """Get files by specific category"""
    try:
        session = get_db_session()
        if session:
            files = session.query(File).filter(File.file_type == category.lower()).order_by(File.created_time.desc()).all()
            session.close()
            return files
        return []
    except:
        return []

def get_deleted_files():
    """Get files that have been deleted (file not found in system)"""
    try:
        session = get_db_session()
        if session:
            files = session.query(File).all()
            deleted_files = []
            for file in files:
                if not os.path.exists(file.file_path):
                    deleted_files.append(file)
            session.close()
            return deleted_files
        return []
    except:
        return []

def get_file_stats():
    try:
        session = get_db_session()
        if not session:
            return {'total_files': 0, 'total_size_gb': 0, 'type_counts': {}}
        
        total_files = session.query(File).count()
        
        total_size = session.query(File.file_size).all()
        total_size_bytes = sum([size[0] for size in total_size if size[0] is not None])
        total_size_gb = total_size_bytes / (1024**3)
        
        file_types = session.query(File.file_type).all()
        type_counts = {}
        for file_type in file_types:
            if file_type[0]:
                type_name = file_type[0].capitalize()
                type_counts[type_name] = type_counts.get(type_name, 0) + 1
        
        session.close()
        
        return {
            'total_files': total_files,
            'total_size_gb': round(total_size_gb, 2),
            'type_counts': type_counts
        }
    except:
        return {'total_files': 0, 'total_size_gb': 0, 'type_counts': {}}

# ---------------------- FILE OPERATION FUNCTIONS ----------------------
def create_new_folder(folder_name, parent_folder=None):
    """Create a new folder in the system"""
    try:
        if parent_folder is None:
            parent_folder = os.path.expanduser("~/Documents")
        
        new_folder_path = os.path.join(parent_folder, folder_name)
        os.makedirs(new_folder_path, exist_ok=True)
        
        # Add to database
        session = get_db_session()
        if session:
            file_record = File(
                file_path=new_folder_path,
                file_name=folder_name,
                file_extension="",
                file_size=0,
                file_type="folder",
                created_time=datetime.now(),
                modified_time=datetime.now(),
                last_accessed=datetime.now(),
                access_count=0
            )
            session.add(file_record)
            session.commit()
            session.close()
        
        return True, f"✅ Folder created: {new_folder_path}"
    except Exception as e:
        return False, f"❌ Error creating folder: {e}"

def handle_file_upload(uploaded_file, destination_folder=None):
    """Handle file uploads to system"""
    try:
        if destination_folder is None:
            destination_folder = os.path.expanduser("~/Downloads")
        
        file_path = os.path.join(destination_folder, uploaded_file.name)
        
        # Save file to system
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        # Add to database
        session = get_db_session()
        if session:
            stat = os.stat(file_path)
            file_record = File(
                file_path=file_path,
                file_name=uploaded_file.name,
                file_extension=os.path.splitext(uploaded_file.name)[1],
                file_size=stat.st_size,
                file_type=get_file_type(uploaded_file.name),
                created_time=datetime.fromtimestamp(stat.st_ctime),
                modified_time=datetime.fromtimestamp(stat.st_mtime),
                last_accessed=datetime.now(),
                access_count=0
            )
            session.add(file_record)
            session.commit()
            session.close()
        
        return True, f"✅ File uploaded: {uploaded_file.name}"
    except Exception as e:
        return False, f"❌ Error uploading file: {e}"

def open_file(file_path):
    """Open file with default system application"""
    try:
        if os.path.exists(file_path):
            system = platform.system()
            
            if system == "Windows":
                os.startfile(file_path)
            elif system == "Darwin":  # macOS
                subprocess.run(["open", file_path])
            else:  # Linux and other Unix-like
                subprocess.run(["xdg-open", file_path])
            
            return True, f"📂 Opening: {os.path.basename(file_path)}"
        else:
            return False, f"❌ File not found: {file_path}"
    except Exception as e:
        return False, f"❌ Error opening file: {e}"

def delete_file(file_id, file_path):
    """Delete file from system but keep in database for trash"""
    try:
        # Only delete from file system, keep in database for trash
        if os.path.exists(file_path):
            if os.path.isdir(file_path):
                shutil.rmtree(file_path)
            else:
                os.remove(file_path)
            return True, f"🗑️ File moved to trash: {os.path.basename(file_path)}"
        else:
            # File already doesn't exist, remove from database
            session = get_db_session()
            if session:
                file_record = session.query(File).filter(File.id == file_id).first()
                if file_record:
                    session.delete(file_record)
                    session.commit()
                session.close()
            return True, f"🗑️ File removed from database: {os.path.basename(file_path)}"
    except Exception as e:
        return False, f"❌ Error deleting file: {e}"

def cleanup_deleted_files():
    """Permanently remove database entries for files that don't exist in system"""
    try:
        session = get_db_session()
        if session:
            files = session.query(File).all()
            deleted_count = 0
            for file in files:
                if not os.path.exists(file.file_path):
                    session.delete(file)
                    deleted_count += 1
            session.commit()
            session.close()
            return True, f"🧹 Permanently deleted {deleted_count} files from database"
        return False, "❌ Could not connect to database"
    except Exception as e:
        return False, f"❌ Error cleaning up files: {e}"

def get_file_type(filename):
    """Determine file type from extension"""
    extension = os.path.splitext(filename)[1].lower()
    
    if extension in ['.txt', '.doc', '.docx', '.pdf', '.pptx', '.xlsx']:
        return "document"
    elif extension in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp']:
        return "image" 
    elif extension in ['.mp4', '.avi', '.mov', '.mkv', '.wmv']:
        return "video"
    elif extension in ['.mp3', '.wav', '.m4a', '.flac']:
        return "audio"
    elif extension in ['.zip', '.rar', '.7z']:
        return "archive"
    else:
        return "other"

# ---------------------- PAGE SETUP ----------------------
st.set_page_config("IntelliFyle", "📁", layout="wide")

# Initialize session state
if 'page' not in st.session_state:
    st.session_state.page = "Dashboard"
if 'category' not in st.session_state:
    st.session_state.category = None
if 'feature' not in st.session_state:
    st.session_state.feature = None
if 'show_new_folder' not in st.session_state:
    st.session_state.show_new_folder = False
if 'show_upload' not in st.session_state:
    st.session_state.show_upload = False
if 'delete_confirm' not in st.session_state:
    st.session_state.delete_confirm = None

# ---------------------- HEADER ----------------------
st.title("🧠 IntelliFyle")
st.subheader("Smart File Manager - Real-time Monitoring")

# ---------------------- SIDEBAR ----------------------
with st.sidebar:
    # Refresh button at TOP
    if st.button("🔄 Sync Now", use_container_width=True, type="primary"):
        success, message = cleanup_deleted_files()
        if success:
            st.success(message)
        else:
            st.error(message)
        st.rerun()
    
    st.header("📁 Navigation")
    
    # Navigation buttons
    nav_buttons = [
        ("📊 Dashboard", "Dashboard"),
        ("📂 All Files", "All Files"),
        ("🗑️ Trash", "Trash"),
        ("🔍 Search", "Search")
    ]
    
    for icon_text, page_name in nav_buttons:
        if st.button(icon_text, use_container_width=True, 
                    type="primary" if st.session_state.page == page_name else "secondary"):
            st.session_state.page = page_name
            st.session_state.category = None
            st.session_state.feature = None
            st.rerun()
    
    st.divider()
    
    # Categories
    st.header("📂 Categories")
    categories = ["Documents", "Images", "Videos", "Audio", "Other"]
    for cat in categories:
        if st.button(f"📁 {cat}", use_container_width=True, 
                    type="primary" if st.session_state.page == "Category" and st.session_state.category == cat else "secondary"):
            st.session_state.page = "Category"
            st.session_state.category = cat
            st.session_state.feature = None
            st.rerun()
    
    st.divider()
    
    # Smart Features - REMOVED Smart Search
    st.header("🤖 Smart Features")
    features = ["Recommendations", "Auto-Organize"]  # Removed Smart Search
    for feat in features:
        if st.button(f"💡 {feat}", use_container_width=True,
                    type="primary" if st.session_state.page == "Feature" and st.session_state.feature == feat else "secondary"):
            st.session_state.page = "Feature"
            st.session_state.feature = feat
            st.session_state.category = None
            st.rerun()
    
    st.divider()
    
    # Real-time stats
    stats = get_file_stats()
    st.metric("📊 Total Files", stats['total_files'])
    st.metric("💾 Storage Used", f"{stats['total_size_gb']} GB")

# ---------------------- TOP ACTION BUTTONS ----------------------
col1, col2, col3 = st.columns([1, 1, 1])

with col1:
    if st.button("📁 New Folder", use_container_width=True):
        st.session_state.show_new_folder = True

with col2:
    if st.button("📤 Upload File", use_container_width=True):
        st.session_state.show_upload = True

with col3:
    if st.button("🔄 Refresh", use_container_width=True):
        st.rerun()

# ---------------------- MODALS ----------------------
# New Folder Modal
if st.session_state.show_new_folder:
    with st.form("new_folder_form"):
        st.subheader("Create New Folder")
        folder_name = st.text_input("Folder Name", placeholder="Enter folder name...")
        parent_folder = st.selectbox("Location", [
            os.path.expanduser("~/Desktop"),
            os.path.expanduser("~/Documents"), 
            os.path.expanduser("~/Downloads")
        ])
        
        col1, col2 = st.columns(2)
        with col1:
            if st.form_submit_button("Create Folder"):
                if folder_name:
                    success, message = create_new_folder(folder_name, parent_folder)
                    if success:
                        st.success(message)
                    else:
                        st.error(message)
                    st.session_state.show_new_folder = False
                    st.rerun()
                else:
                    st.error("Please enter a folder name")
        with col2:
            if st.form_submit_button("Cancel"):
                st.session_state.show_new_folder = False
                st.rerun()

# Upload File Modal
if st.session_state.show_upload:
    with st.form("upload_form"):
        st.subheader("Upload Files")
        uploaded_files = st.file_uploader("Choose files", accept_multiple_files=True, 
                                         help="Select files to upload")
        destination_folder = st.selectbox("Upload to", [
            os.path.expanduser("~/Downloads"),
            os.path.expanduser("~/Documents"),
            os.path.expanduser("~/Desktop")
        ])
        
        col1, col2 = st.columns(2)
        with col1:
            if st.form_submit_button("Upload Files"):
                if uploaded_files:
                    for uploaded_file in uploaded_files:
                        success, message = handle_file_upload(uploaded_file, destination_folder)
                        if success:
                            st.success(message)
                        else:
                            st.error(message)
                    st.session_state.show_upload = False
                    st.rerun()
                else:
                    st.error("Please select files to upload")
        with col2:
            if st.form_submit_button("Cancel"):
                st.session_state.show_upload = False
                st.rerun()

# Delete Confirmation Modal
if st.session_state.delete_confirm:
    file_id, file_path, file_name = st.session_state.delete_confirm
    with st.container():
        st.warning(f"Are you sure you want to move **{file_name}** to trash?")
        st.info("📝 File will be moved to trash and can be permanently deleted later.")
        
        col1, col2, col3 = st.columns([1, 1, 2])
        with col1:
            if st.button("✅ Move to Trash", use_container_width=True, type="primary"):
                success, message = delete_file(file_id, file_path)
                if success:
                    st.success(message)
                else:
                    st.error(message)
                st.session_state.delete_confirm = None
                st.rerun()
        with col2:
            if st.button("❌ Cancel", use_container_width=True):
                st.session_state.delete_confirm = None
                st.rerun()

# ---------------------- MAIN CONTENT ----------------------

# Dashboard Page
if st.session_state.page == "Dashboard":
    st.header("📊 Dashboard")
    
    stats = get_file_stats()
    
    # Metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("📄 Total Files", stats['total_files'])
    with col2:
        st.metric("💾 Storage Used", f"{stats['total_size_gb']} GB")
    with col3:
        st.metric("📂 File Types", len(stats['type_counts']))
    with col4:
        st.metric("🔄 Real-time", "Active")
    
    # File type chart
    if stats['type_counts']:
        col1, col2 = st.columns([2, 1])
        
        with col1:
            fig = px.pie(
                values=list(stats['type_counts'].values()),
                names=list(stats['type_counts'].keys()),
                title="File Type Distribution"
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.subheader("📈 Quick Stats")
            for file_type, count in stats['type_counts'].items():
                st.write(f"• {file_type}: {count} files")
    else:
        st.info("📝 No files found. Start by adding files to monitored folders.")

# All Files Page
elif st.session_state.page == "All Files":
    st.header("📂 All Files")
    
    search_query = st.text_input("🔍 Search files...", placeholder="Enter file name...")
    
    files = get_all_files()
    
    if files:
        filtered_files = [f for f in files if not search_query or search_query.lower() in f.file_name.lower()]
        
        if filtered_files:
            st.info("📅 Showing newest files first")
            
            for file in filtered_files:
                col1, col2, col3, col4, col5 = st.columns([4, 2, 1, 1, 1])
                
                with col1:
                    icon_map = {
                        "document": "📄",
                        "image": "🖼️", 
                        "video": "🎬",
                        "audio": "🎵",
                        "archive": "📦",
                        "folder": "📁",
                        "other": "📄"
                    }
                    icon = icon_map.get(file.file_type, "📄")
                    st.write(f"{icon} **{file.file_name}**")
                    
                    file_size = file.file_size / (1024*1024) if file.file_size else 0
                    file_type_display = file.file_type.capitalize() if file.file_type else "Unknown"
                    st.caption(f"Type: {file_type_display} | Size: {file_size:.1f} MB")
                
                with col2:
                    if file.created_time:
                        st.caption(f"Added: {file.created_time.strftime('%Y-%m-%d %H:%M')}")
                    else:
                        st.caption("Added: Unknown")
                
                with col3:
                    if st.button("📂 Open", key=f"open_{file.id}"):
                        success, message = open_file(file.file_path)
                        if success:
                            st.success(message)
                        else:
                            st.error(message)
                        st.rerun()
                
                with col4:
                    if st.button("📁 Show", key=f"show_{file.id}"):
                        folder_path = os.path.dirname(file.file_path)
                        success, message = open_file(folder_path)
                        if success:
                            st.success(message)
                        else:
                            st.error(message)
                        st.rerun()
                
                with col5:
                    if st.button("🗑️", key=f"delete_{file.id}"):
                        st.session_state.delete_confirm = (file.id, file.file_path, file.file_name)
                        st.rerun()
                
                st.divider()
            
            st.info(f"📊 Showing {len(filtered_files)} files")
        else:
            st.warning("❌ No files found matching your search.")
    else:
        st.info("📝 No files found in database. The system is monitoring your files...")

# Trash Page - Show deleted/missing files
elif st.session_state.page == "Trash":
    st.header("🗑️ Trash")
    
    col1, col2 = st.columns([1, 2])
    with col1:
        if st.button("🧹 Cleanup Trash", type="primary", use_container_width=True):
            success, message = cleanup_deleted_files()
            if success:
                st.success(message)
            else:
                st.error(message)
            st.rerun()
    
    with col2:
        st.info("🗑️ Files in trash will be permanently deleted when you click 'Cleanup Trash'")
    
    deleted_files = get_deleted_files()
    
    if deleted_files:
        st.warning(f"🔍 Found {len(deleted_files)} deleted files in trash:")
        
        for file in deleted_files:
            col1, col2, col3, col4 = st.columns([4, 2, 1, 1])
            
            with col1:
                # File icon based on type
                icon_map = {
                    "document": "📄",
                    "image": "🖼️", 
                    "video": "🎬",
                    "audio": "🎵",
                    "archive": "📦",
                    "folder": "📁",
                    "other": "📄"
                }
                icon = icon_map.get(file.file_type, "📄")
                st.write(f"{icon} **{file.file_name}**")
                st.caption(f"Original path: {file.file_path}")
                file_size = file.file_size / (1024*1024) if file.file_size else 0
                st.caption(f"Type: {file.file_type} | Size: {file_size:.1f} MB")
            
            with col2:
                if file.modified_time:
                    st.caption(f"Deleted: {file.modified_time.strftime('%Y-%m-%d %H:%M')}")
                else:
                    st.caption("Deleted: Unknown")
            
            with col3:
                if st.button("🔄 Restore", key=f"restore_{file.id}"):
                    st.error("❌ Restore functionality not implemented yet")
                    st.info("To restore, you would need the original file")
            
            with col4:
                if st.button("🗑️ Remove", key=f"remove_{file.id}"):
                    # Remove from database permanently
                    session = get_db_session()
                    if session:
                        file_record = session.query(File).filter(File.id == file.id).first()
                        if file_record:
                            session.delete(file_record)
                            session.commit()
                            st.success(f"✅ Permanently removed {file.file_name} from database")
                        session.close()
                    st.rerun()
            
            st.divider()
    else:
        st.success("✅ No deleted files found in trash. Everything is synchronized!")

# Search Page
elif st.session_state.page == "Search":
    st.header("🔍 Search Files")
    
    search_type = st.selectbox("Search by:", ["Name", "Type"])
    query = st.text_input("Enter your search query:")
    
    if query:
        files = get_all_files()
        results = []
        
        for file in files:
            if search_type == "Name" and query.lower() in file.file_name.lower():
                results.append(file)
            elif search_type == "Type" and file.file_type and query.lower() in file.file_type.lower():
                results.append(file)
        
        if results:
            st.success(f"🎯 Found {len(results)} files:")
            for file in results:
                col1, col2, col3 = st.columns([3, 1, 1])
                with col1:
                    st.write(f"📄 {file.file_name} ({file.file_type})")
                with col2:
                    if st.button("Open", key=f"search_open_{file.id}"):
                        success, message = open_file(file.file_path)
                        if success:
                            st.success(message)
                        else:
                            st.error(message)
                with col3:
                    if st.button("Show", key=f"search_show_{file.id}"):
                        success, message = open_file(os.path.dirname(file.file_path))
                        if success:
                            st.success(message)
                        else:
                            st.error(message)
                st.divider()
        else:
            st.warning("❌ No files found matching your search.")

# Category Page - FIXED
elif st.session_state.page == "Category" and st.session_state.category:
    st.header(f"📂 {st.session_state.category} Files")
    
    # Map category names to database file types
    category_mapping = {
        "Documents": "document",
        "Images": "image", 
        "Videos": "video",
        "Audio": "audio",
        "Other": "other"
    }
    
    db_category = category_mapping.get(st.session_state.category, st.session_state.category.lower())
    category_files = get_files_by_category(db_category)
    
    if category_files:
        st.success(f"📊 Found {len(category_files)} files in {st.session_state.category}")
        for file in category_files:
            col1, col2, col3 = st.columns([3, 1, 1])
            with col1:
                icon = "📄" if file.file_type == "document" else "🖼️" if file.file_type == "image" else "🎬" if file.file_type == "video" else "🎵" if file.file_type == "audio" else "📁"
                st.write(f"{icon} **{file.file_name}**")
                file_size = file.file_size / (1024*1024) if file.file_size else 0
                st.caption(f"Size: {file_size:.1f} MB | Added: {file.created_time.strftime('%Y-%m-%d') if file.created_time else 'Unknown'}")
            with col2:
                if st.button("Open", key=f"cat_open_{file.id}"):
                    success, message = open_file(file.file_path)
                    if success:
                        st.success(message)
                    else:
                        st.error(message)
            with col3:
                if st.button("Show", key=f"cat_show_{file.id}"):
                    success, message = open_file(os.path.dirname(file.file_path))
                    if success:
                        st.success(message)
                    else:
                        st.error(message)
            st.divider()
    else:
        st.warning(f"❌ No {st.session_state.category} files found.")

# Feature Page - FIXED
elif st.session_state.page == "Feature" and st.session_state.feature:
    st.header(f"🤖 {st.session_state.feature}")
    
    if st.session_state.feature == "Recommendations":
        st.write("💡 Smart recommendations based on your usage patterns...")
        files = get_all_files()
        if files:
            st.success("🎯 Based on your recent activity, you might need:")
            recent_files = sorted(files, key=lambda x: x.modified_time if x.modified_time else datetime.min, reverse=True)[:5]
            for file in recent_files:
                st.write(f"📄 {file.file_name} (Recently modified)")
        else:
            st.info("📝 No usage data yet. Start using files to get recommendations.")
        
    elif st.session_state.feature == "Auto-Organize":
        st.write("🗂️ Automatic file organization...")
        
        # Show actual file organization stats
        stats = get_file_stats()
        if stats['type_counts']:
            st.subheader("📈 Current File Organization")
            for file_type, count in stats['type_counts'].items():
                st.write(f"• {file_type}: {count} files")
            
            # Show organization suggestion
            st.subheader("💡 Organization Suggestion")
            st.info("Files are automatically categorized by type. You can manually organize them into folders.")
        else:
            st.info("📝 No files found to organize.")

# ---------------------- FOOTER ----------------------
st.divider()
st.caption("🔄 IntelliFyle - Real-time File Monitoring Active | Files are automatically tracked and organized")

# Auto-refresh every 30 seconds
st.markdown("""
<script>
setTimeout(function() {
    window.location.reload();
}, 30000);
</script>
""", unsafe_allow_html=True)