#!/usr/bin/env python3
# author: Hadi Cahyadi (cumulus13@gmail.com)
# create in 10 minutes

"""
PyPI Package Information Tool
A beautiful command-line tool to fetch and display PyPI package information.
"""

import argparse
import json
import os
import sys
import urllib.request
# import urllib.parse
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
# import tempfile
# import shutil

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.columns import Columns
    from rich.text import Text
    from rich.markdown import Markdown
    from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn
    from rich.tree import Tree
    from rich.align import Align
    from rich_argparse import RichHelpFormatter, _lazy_rich as rr
except ImportError:
    print("❌ Error: rich and rich-argparse packages are required!")
    print("Install with: pip install rich rich-argparse")
    sys.exit(1)

console = Console()

class CustomRichHelpFormatter(RichHelpFormatter):
    """A custom RichHelpFormatter with modified styles."""

    styles: dict[str, rr.StyleType] = {
        "argparse.args": "bold #FFFF00",  # Yellow
        "argparse.groups": "#AA55FF",     # Purple  
        "argparse.help": "bold #00FFFF",  # Cyan
        "argparse.metavar": "bold #FF00FF", # Magenta
        "argparse.syntax": "underline",   # Underlined
        "argparse.text": "white",         # White
        "argparse.prog": "bold #00AAFF italic", # Blue italic
        "argparse.default": "bold",       # Bold
    }

class PyPIClient:
    """Client for interacting with PyPI API."""
    
    BASE_URL = "https://pypi.org/pypi"
    
    def __init__(self):
        self.session_headers = {
            'User-Agent': 'PyPI-Info-Tool/1.0 (https://github.com/user/pypi-info-tool)'
        }
    
    def get_package_info(self, package_name: str) -> Optional[Dict[str, Any]]:
        """Fetch package information from PyPI API."""
        url = f"{self.BASE_URL}/{package_name}/json"
        
        try:
            with console.status(f"[bold blue]🔍 Searching for package '{package_name}'...", spinner="dots"):
                req = urllib.request.Request(url, headers=self.session_headers)
                with urllib.request.urlopen(req, timeout=10) as response:
                    if response.status == 200:
                        return json.loads(response.read().decode('utf-8'))
                    else:
                        return None
        except urllib.error.HTTPError as e:
            if e.code == 404:
                console.print(f"[red]❌ Package '{package_name}' not found on PyPI[/red]")
            else:
                console.print(f"[red]❌ HTTP Error {e.code}: {e.reason}[/red]")
            return None
        except Exception as e:
            console.print(f"[red]❌ Error fetching package info: {str(e)}[/red]")
            return None
    
    def download_package(self, package_name: str, version: str = None, 
                        download_path: str = ".", progress_callback=None) -> bool:
        """Download package from PyPI."""
        package_info = self.get_package_info(package_name)
        if not package_info:
            return False
        
        # Get the version to download
        if version is None or version == "latest":
            version = package_info['info']['version']
        
        # Find the download URL
        releases = package_info.get('releases', {})
        if version not in releases:
            console.print(f"[red]❌ Version {version} not found for {package_name}[/red]")
            return False
        
        files = releases[version]
        if not files:
            console.print(f"[red]❌ No files available for {package_name} {version}[/red]")
            return False
        
        # Prefer wheel files, then source distributions
        download_file = None
        for file_info in files:
            if file_info['packagetype'] == 'bdist_wheel':
                download_file = file_info
                break
        
        if not download_file:
            for file_info in files:
                if file_info['packagetype'] == 'sdist':
                    download_file = file_info
                    break
        
        if not download_file:
            download_file = files[0]  # Fallback to first available
        
        # Download the file
        download_url = download_file['url']
        filename = download_file['filename']
        file_size = download_file.get('size', 0)
        
        download_path = Path(download_path)
        download_path.mkdir(parents=True, exist_ok=True)
        filepath = download_path / filename
        
        try:
            with Progress(
                TextColumn("[bold blue]📥 Downloading"),
                TextColumn("[bold yellow]{task.fields[filename]}"),
                BarColumn(bar_width=40),
                TextColumn("[progress.percentage]{task.percentage:>3.1f}%"),
                TextColumn("[blue]({task.completed:,}/{task.total:,} bytes)"),
                TimeRemainingColumn(),
                console=console,
                transient=False
            ) as progress:
                
                task = progress.add_task(
                    "download", 
                    filename=filename,
                    total=file_size if file_size > 0 else None
                )
                
                req = urllib.request.Request(download_url, headers=self.session_headers)
                with urllib.request.urlopen(req) as response:
                    with open(filepath, 'wb') as f:
                        downloaded = 0
                        while True:
                            chunk = response.read(8192)
                            if not chunk:
                                break
                            f.write(chunk)
                            downloaded += len(chunk)
                            if file_size > 0:
                                progress.update(task, completed=downloaded)
                            elif progress_callback:
                                progress_callback(downloaded)
            
            console.print(f"[green]✅ Downloaded: {filepath}[/green]")
            return True
            
        except Exception as e:
            console.print(f"[red]❌ Download failed: {str(e)}[/red]")
            return False

class PackageInfoDisplay:
    """Display package information in a beautiful format."""
    
    def __init__(self, truncate = True):
        self.console = console
        self.truncate = truncate
    
    def format_size(self, size_bytes: int) -> str:
        """Format file size in human readable format."""
        if size_bytes == 0:
            return "0 B"
        
        size_names = ["B", "KB", "MB", "GB"]
        i = 0
        while size_bytes >= 1024 and i < len(size_names) - 1:
            size_bytes /= 1024.0
            i += 1
        
        return f"{size_bytes:.1f} {size_names[i]}"
    
    def format_date(self, date_str: str) -> str:
        """Format ISO date string to readable format."""
        try:
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            return dt.strftime("%B %d, %Y")
        except:
            return date_str
    
    def create_header_panel(self, info: Dict[str, Any]) -> Panel:
        """Create the main header panel."""
        name = info.get('name', 'Unknown')
        version = info.get('version', 'Unknown')
        summary = info.get('summary', 'No description available')
        
        # Create title with emoji
        title_text = Text()
        title_text.append("📦 ", style="bold blue")
        title_text.append(name, style="bold white")
        title_text.append(f" {version}", style="bold green")
        
        # Summary
        summary_text = Text(summary, style="italic cyan")
        
        content = Align.center(
            Text.assemble(
                title_text, "\n\n",
                summary_text
            )
        )
        
        return Panel(
            content,
            title="[bold blue]📋 Package Information[/bold blue]",
            border_style="blue",
            padding=(1, 2)
        )
    
    def create_basic_info_table(self, info: Dict[str, Any]) -> Table:
        """Create basic information table."""
        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_column("Property", style="bold yellow", width=20)
        table.add_column("Value", style="white")
        
        # Basic info
        basic_fields = [
            ("🏷️  Name", info.get('name', 'N/A')),
            ("🔢 Version", info.get('version', 'N/A')),
            ("👤 Author", info.get('author', 'N/A')),
            ("📧 Author Email", info.get('author_email', 'N/A')),
            ("🏠 Home Page", info.get('home_page', 'N/A')),
            ("🛠️  Maintainer", info.get('maintainer', 'N/A')),
            ("📨 Maintainer Email", info.get('maintainer_email', 'N/A')),
            ("📄 License", info.get('license', 'N/A')),
            ("🐍 Python Requires", info.get('requires_python', 'N/A')),
        ]
        
        for prop, value in basic_fields:
            if value and value != 'N/A':
                # Truncate long values
                if len(str(value)) > 50 and self.truncate:
                    value = str(value)[:47] + "..."
                table.add_row(prop, str(value))
        
        return table
    
    def create_urls_table(self, info: Dict[str, Any]) -> Optional[Table]:
        """Create project URLs table."""
        project_urls = info.get('project_urls', {})
        if not project_urls:
            return None
        
        table = Table(title="🔗 Project URLs", show_header=False, box=None, padding=(0, 1))
        table.add_column("Type", style="bold cyan", width=15)
        table.add_column("URL", style="blue underline")
        
        for url_type, url in project_urls.items():
            if url:
                # Truncate very long URLs
                display_url = url if len(url) <= 60 else url[:57] + "..." if self.truncate else url
                table.add_row(f"🌐 {url_type}", display_url)
        
        return table
    
    def create_classifiers_tree(self, info: Dict[str, Any]) -> Optional[Tree]:
        """Create classifiers tree."""
        classifiers = info.get('classifiers', [])
        if not classifiers:
            return None
        
        tree = Tree("🏷️  [bold yellow]Classifiers")
        
        # Group classifiers by category
        categories = {}
        for classifier in classifiers:
            parts = classifier.split(' :: ')
            if len(parts) >= 2:
                category = parts[0]
                subcategory = ' :: '.join(parts[1:])
                if category not in categories:
                    categories[category] = []
                categories[category].append(subcategory)
        
        for category, items in categories.items():
            category_node = tree.add(f"[bold cyan]{category}")
            if self.truncate:
                for item in items[:5]:  # Limit to 5 items per category
                    category_node.add(f"[white]{item}")
                if len(items) > 5:
                    category_node.add(f"[dim]... and {len(items) - 5} more")
            else:
                for item in items:
                    category_node.add(f"[white]{item}")
        
        return tree
    
    def create_releases_table(self, releases: Dict[str, List], latest_version: str) -> Table:
        """Create releases table showing recent versions."""
        table = Table(title="📦 Recent Releases", box=None)
        table.add_column("Version", style="bold green", width=15)
        table.add_column("Release Date", style="cyan", width=20)
        table.add_column("Files", style="yellow", width=10)
        table.add_column("Size", style="magenta", width=12)
        
        # Sort versions by upload time (newest first)
        version_data = []
        for version, files in releases.items():
            if files:
                upload_time = files[0].get('upload_time_iso_8601', '')
                total_size = sum(f.get('size', 0) for f in files)
                version_data.append((version, upload_time, len(files), total_size))
        
        # Sort by upload time (newest first) and take top 10
        version_data.sort(key=lambda x: x[1], reverse=True)
        
        for i, (version, upload_time, file_count, total_size) in enumerate(version_data[:10]):
            version_display = version
            if version == latest_version:
                version_display = f"{version} [bold red](latest)[/bold red]"
            
            date_display = self.format_date(upload_time) if upload_time else "Unknown"
            size_display = self.format_size(total_size) if total_size > 0 else "Unknown"
            
            table.add_row(
                version_display,
                date_display,
                str(file_count),
                size_display
            )
        
        return table
    
    def display_package_info(self, package_data: Dict[str, Any], show_last_only: bool = False):
        """Display complete package information."""
        info = package_data.get('info', {})
        releases = package_data.get('releases', {})
        
        # Header
        self.console.print()
        self.console.print(self.create_header_panel(info))
        self.console.print()
        
        if show_last_only:
            # Show only latest version info
            latest_version = info.get('version', 'Unknown')
            latest_files = releases.get(latest_version, [])
            
            if latest_files:
                table = Table(title=f"📦 Latest Version ({latest_version})", box=None)
                table.add_column("File", style="bold green")
                table.add_column("Type", style="cyan")
                table.add_column("Size", style="yellow")
                table.add_column("Upload Date", style="magenta")
                
                for file_info in latest_files:
                    table.add_row(
                        file_info.get('filename', 'Unknown'),
                        file_info.get('packagetype', 'Unknown'),
                        self.format_size(file_info.get('size', 0)),
                        self.format_date(file_info.get('upload_time_iso_8601', ''))
                    )
                
                self.console.print(table)
            else:
                self.console.print("[yellow]⚠️  No files found for latest version[/yellow]")
            return
        
        # Create layout columns
        left_column = []
        right_column = []
        
        # Basic info (left column)
        basic_table = self.create_basic_info_table(info)
        left_column.append(Panel(basic_table, title="[bold green]ℹ️  Basic Information", border_style="green"))
        
        # URLs (right column)
        urls_table = self.create_urls_table(info)
        if urls_table:
            right_column.append(Panel(urls_table, title="[bold blue]🔗 Links", border_style="blue"))
        
        # Display two columns
        if left_column and right_column:
            self.console.print(Columns([left_column[0], right_column[0]], equal=True, expand=True))
            self.console.print()
        elif left_column:
            self.console.print(left_column[0])
            self.console.print()
        
        # Classifiers tree
        classifiers_tree = self.create_classifiers_tree(info)
        if classifiers_tree:
            self.console.print(Panel(classifiers_tree, title="[bold yellow]🏷️  Categories", border_style="yellow"))
            self.console.print()
        
        # Description
        description = info.get('description', '').strip()
        if description and len(description) > 100:
            # Try to render as markdown if it looks like markdown
            if any(marker in description for marker in ['#', '*', '`', '```', '[', '](']):
                try:
                    # md = Markdown(description[:2000] + ("..." if len(description) > 2000 else ""))
                    md = Markdown(description)
                    self.console.print(Panel(md, title="[bold cyan]📖 Description", border_style="cyan"))
                    self.console.print()
                except:
                    # Fallback to plain text
                    # desc_text = description[:1000] + ("..." if len(description) > 1000 else "")
                    desc_text = description
                    self.console.print(Panel(desc_text, title="[bold cyan]📖 Description", border_style="cyan"))
                    self.console.print()
            else:
                # desc_text = description[:1000] + ("..." if len(description) > 1000 else "")
                desc_text = description
                self.console.print(Panel(desc_text, title="[bold cyan]📖 Description", border_style="cyan"))
                self.console.print()
        
        # Recent releases
        if releases:
            releases_table = self.create_releases_table(releases, info.get('version', ''))
            self.console.print(releases_table)
            self.console.print()
        
        # Statistics
        total_files = sum(len(files) for files in releases.values())
        total_size = sum(sum(f.get('size', 0) for f in files) for files in releases.values())
        
        stats_table = Table(show_header=False, box=None, padding=(0, 2))
        stats_table.add_column("Metric", style="bold yellow")
        stats_table.add_column("Value", style="bold white")
        
        stats_table.add_row("📊 Total Versions", str(len(releases)))
        stats_table.add_row("📁 Total Files", str(total_files))
        stats_table.add_row("💾 Total Size", self.format_size(total_size))
        
        self.console.print(Panel(stats_table, title="[bold magenta]📈 Statistics", border_style="magenta"))

def get_version():
    """
    Get the version of the ddf module.
    Version is taken from the __version__.py file if it exists.
    The content of __version__.py should be:
    version = "0.33"
    """
    try:
        version_file = Path(__file__).parent / "__version__.py"
        if version_file.is_file():
            with open(version_file, "r") as f:
                for line in f:
                    if line.strip().startswith("version"):
                        parts = line.split("=")
                        if len(parts) == 2:
                            return parts[1].strip().strip('"').strip("'")
    except Exception as e:
        if os.getenv('TRACEBACK') and os.getenv('TRACEBACK') in ['1', 'true', 'True']:
            console.print_exception(show_locals=False)
        else:
            console.log(f"[white on red]ERROR:[/] [white on blue]{e}[/]")

    return "UNKNOWN VERSION"
    

def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="🐍 PyPI Package Information Tool - Get detailed info about Python packages",
        formatter_class=CustomRichHelpFormatter,
        prog="pipinfo"
    )
    
    parser.add_argument(
        'package',
        nargs='?',
        help='📦 Package name to search for'
    )
    
    parser.add_argument(
        '-l', '--last',
        action='store_true',
        help='🔍 Show only the latest version information'
    )
    
    parser.add_argument(
        '-d', '--download',
        action='store_true',
        help='📥 Download the package with progress bar'
    )
    
    parser.add_argument(
        '-p', '--path',
        default='.',
        help='📁 Directory path to save downloaded files (default: current directory)'
    )
    
    parser.add_argument(
        '--version-download',
        help='🔢 Specific version to download (default: latest)'
    )
    
    parser.add_argument(
        '--author',
        action='store_true',
        help='👤 Show author information'
    )
    
    parser.add_argument(
        '--home',
        action='store_true',
        help='🏠 Show home page URL'
    )
    
    parser.add_argument(
        '--tags',
        action='store_true',
        help='🏷️  Show package classifiers/tags'
    )
    
    parser.add_argument(
        '--urls',
        action='store_true',
        help='🔗 Show all project URLs'
    )
    
    parser.add_argument(
        '-f',
        '--full',
        action='store_false',
        help='🖥️  Show full package information (ignore truncation)'
    )
    
    parser.add_argument('-v', '--version', action='version', version=f"[bold #FFFF00]version:[/] [bold #00FFFF]{get_version()}[/]", help="Show version")
    
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)
        
    args = parser.parse_args()
    
    # Show help if no package specified
    if not args.package:
        parser.print_help()
        return
    # Initialize client and display
    client = PyPIClient()
    display = PackageInfoDisplay(args.full)
    
    # Get package information
    console.print(f"\n[bold blue]🔍 Searching PyPI for '{args.package}'...[/bold blue]")
    package_data = client.get_package_info(args.package)
    
    if not package_data:
        console.print(f"[red]❌ Could not find package '{args.package}' on PyPI[/red]")
        return
    
    info = package_data.get('info', {})
    
    # Handle specific info requests
    if args.author:
        author = info.get('author', 'N/A')
        author_email = info.get('author_email', 'N/A')
        console.print(f"[bold yellow]👤 Author:[/bold yellow] {author}")
        if author_email != 'N/A':
            console.print(f"[bold yellow]📧 Email:[/bold yellow] {author_email}")
        return
    
    if args.home:
        home_page = info.get('home_page') or info.get('project_urls', {}).get('Homepage', 'N/A')
        console.print(f"[bold yellow]🏠 Home Page:[/bold yellow] {home_page}")
        return
    
    if args.tags:
        classifiers = info.get('classifiers', [])
        if classifiers:
            console.print("[bold yellow]🏷️  Package Tags/Classifiers:[/bold yellow]")
            for classifier in classifiers:
                console.print(f"  • {classifier}")
        else:
            console.print("[yellow]No classifiers found[/yellow]")
        return
    
    if args.urls:
        project_urls = info.get('project_urls', {})
        if project_urls:
            console.print("[bold yellow]🔗 Project URLs:[/bold yellow]")
            for url_type, url in project_urls.items():
                console.print(f"  🌐 [cyan]{url_type}:[/cyan] {url}")
        else:
            console.print("[yellow]No project URLs found[/yellow]")
        return
    
    # Download package if requested
    if args.download:
        version = args.version_download or "latest"
        console.print(f"\n[bold green]📥 Downloading {args.package} (version: {version})...[/bold green]")
        success = client.download_package(args.package, version, args.path)
        if not success:
            return
        console.print()
    
    # Display package information
    display.display_package_info(package_data, args.last)
    
    # Final message
    console.print(f"[dim]💡 Use --download to download this package, or --help for more options[/dim]")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[yellow]⚠️  Operation cancelled by user[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[red]❌ Unexpected error: {str(e)}[/red]")
        sys.exit(1)