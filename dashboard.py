import time
import os
from rich.console import Console
from rich.table import Table
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.text import Text
from rich import box

console = Console()

class Dashboard:
    def __init__(self, db_manager):
        self.db_manager = db_manager
        self.recent_events = []
        self.start_time = time.time()
        self.monitored_folders = [
            "~/Desktop", "~/Documents", "~/Downloads", 
            "~/Pictures", "~/Videos"
        ]
        
    def add_event(self, event_type, file_path):
        """Add new event to recent events list"""
        event = {
            'timestamp': time.strftime("%H:%M:%S"),
            'type': event_type,
            'file': os.path.basename(file_path),
            'full_path': file_path
        }
        self.recent_events.insert(0, event)
        # Keep only last 15 events
        self.recent_events = self.recent_events[:15]
        
    def get_stats(self):
        """Get current statistics"""
        try:
            stats = self.db_manager.get_file_stats()
        except Exception as e:
            # Fallback if stats fail
            stats = {
                'total_files': 0,
                'file_types': {},
                'total_size': 0
            }
            
        uptime = time.time() - self.start_time
        hours, remainder = divmod(uptime, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        return {
            'total_files': stats.get('total_files', 0),
            'file_types': stats.get('file_types', {}),
            'total_size': stats.get('total_size', 0),
            'uptime': f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}",
            'recent_events': len(self.recent_events)
        }
    
    def create_layout(self):
        """Create the dashboard layout"""
        layout = Layout()
        
        # Split the main layout
        layout.split_column(
            Layout(self.create_header(), name="header", size=3),
            Layout(name="main"),
            Layout(self.create_footer(), name="footer", size=3)
        )
        
        # Split the main area
        layout["main"].split_row(
            Layout(self.create_stats_panel(), name="stats"),
            Layout(self.create_events_panel(), name="events")
        )
        
        return layout
    
    def create_header(self):
        """Create header panel"""
        header_text = Text()
        header_text.append("🔍 IntelliFyle - Smart File Manager", style="bold blue")
        header_text.append("\nReal-time File System Monitoring Dashboard")
        
        return Panel(header_text, style="bold white", box=box.DOUBLE)
    
    def create_stats_panel(self):
        """Create statistics panel"""
        stats = self.get_stats()
        
        stats_table = Table(show_header=False, box=box.ROUNDED, show_edge=True)
        stats_table.add_column("Metric", style="cyan", width=20)
        stats_table.add_column("Value", style="green", width=15)
        
        stats_table.add_row("Total Files", f"{stats['total_files']:,}")
        stats_table.add_row("Total Size", f"{stats['total_size'] / (1024*1024):.2f} MB")
        stats_table.add_row("Uptime", stats['uptime'])
        stats_table.add_row("Recent Events", str(stats['recent_events']))
        
        # File type breakdown
        if stats['file_types']:
            stats_table.add_row("", "")  # Empty row as separator
            stats_table.add_row("[bold]File Types:[/bold]", "")
            for file_type, count in stats['file_types'].items():
                stats_table.add_row(f"  {file_type.title()}", str(count))
        else:
            stats_table.add_row("", "")  # Empty row as separator
            stats_table.add_row("[bold]File Types:[/bold]", "No files yet")
        
        return Panel(stats_table, title="📊 Statistics", border_style="green")
    
    def create_events_panel(self):
        """Create recent events panel"""
        events_table = Table(show_header=True, header_style="bold yellow", box=box.ROUNDED)
        events_table.add_column("Time", style="cyan", width=8)
        events_table.add_column("Event", style="magenta", width=10)
        events_table.add_column("File", style="white", width=40)
        
        if self.recent_events:
            for event in self.recent_events:
                # Color code event types
                event_color = {
                    'created': 'green',
                    'modified': 'blue', 
                    'deleted': 'red',
                    'moved': 'yellow'
                }.get(event['type'], 'white')
                
                events_table.add_row(
                    event['timestamp'],
                    f"[{event_color}]{event['type'].upper()}[/{event_color}]",
                    event['file']
                )
        else:
            events_table.add_row("--:--:--", "WAITING", "No events yet...")
            
        return Panel(events_table, title="🔄 Recent Events", border_style="blue")
    
    def create_footer(self):
        """Create footer panel"""
        folders_text = " | ".join(self.monitored_folders)
        footer_text = Text()
        footer_text.append("📁 Monitored Folders: ", style="bold")
        footer_text.append(folders_text)
        footer_text.append("\nPress Ctrl+C to stop monitoring", style="italic dim")
        
        return Panel(footer_text, style="dim", box=box.SQUARE)
    
    def update_display(self):
        """Update and return the complete layout"""
        return self.create_layout()