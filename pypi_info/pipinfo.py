#!/usr/bin/env python3
# author: Hadi Cahyadi (cumulus13@gmail.com)
# create in 10 minutes

"""
PyPI Package Information Tool
A beautiful command-line tool to fetch and display PyPI package information.
"""

import argparse
import json
from jsoncolor import jprint
import os
import sys
import urllib.request
import urllib.parse
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
import re

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
    from rich.prompt import Prompt, IntPrompt
    from rich_argparse import RichHelpFormatter, _lazy_rich as rr
    from rich import traceback as rich_traceback
    rich_traceback.install(width=os.get_terminal_size()[0], show_locals=False, theme='fruity', word_wrap=True)
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

class PyPISearchResult:
    """Represents a search result from PyPI."""
    
    def __init__(self, name: str, summary: str, version: str):
        self.name = name
        self.summary = summary or "No description available"
        self.version = version

class PyPIClient:
    """Client for interacting with PyPI API."""
    
    BASE_URL = "https://pypi.org/pypi"
    SEARCH_URL = "https://pypi.org/search/"
    
    def __init__(self):
        self.session_headers = {
            'User-Agent': 'PyPI-Info-Tool/1.0 (https://github.com/user/pypi-info-tool)'
        }
    
    def search_packages(self, query: str, max_results: int = 20) -> List[PyPISearchResult]:
        """Search for packages using multiple approaches."""
        results = []
        
        # Try multiple search strategies
        try:
            # Strategy 1: Try PyPI.org search API (JSON endpoint)
            results = self._search_pypi_json_api(query, max_results)
            if results:
                return results
            
            # Strategy 2: Try PyPI warehouse search
            results = self._search_pypi_warehouse(query, max_results)
            if results:
                return results
            
            # Strategy 3: Try simple.pypi.org listing approach
            results = self._search_simple_pypi(query, max_results)
            if results:
                return results
                
        except Exception as e:
            console.print(f"[yellow]⚠️  Search error: {str(e)}[/yellow]")
        
        return results
    
    def _search_pypi_json_api(self, query: str, max_results: int) -> List[PyPISearchResult]:
        """Search using PyPI's JSON API approach."""
        try:
            # Use PyPI's search endpoint
            search_url = f"https://pypi.org/search/?q={urllib.parse.quote(query)}&o=&c="
            
            with console.status(f"[bold blue]🔍 Searching PyPI for '{query}'...", spinner="dots"):
                req = urllib.request.Request(search_url, headers=self.session_headers)
                with urllib.request.urlopen(req, timeout=15) as response:
                    if response.status == 200:
                        html_content = response.read().decode('utf-8')
                        return self._parse_modern_search_results(html_content, query, max_results)
        except Exception as e:
            pass
        return []
    
    def _search_pypi_warehouse(self, query: str, max_results: int) -> List[PyPISearchResult]:
        """Alternative search using warehouse data."""
        try:
            # Try a different search approach
            search_terms = query.lower().split()
            results = []
            
            # Use a simpler approach - try common package patterns
            common_patterns = [
                query,
                f"python-{query}",
                f"{query}-python",
                f"py{query}",
                f"{query}py",
            ]
            
            for pattern in common_patterns:
                try:
                    package_info = self.get_package_info(pattern)
                    if package_info:
                        info = package_info['info']
                        result = PyPISearchResult(
                            info.get('name', pattern),
                            info.get('summary', 'No description available'),
                            info.get('version', 'unknown')
                        )
                        if result not in [r.name for r in results]:
                            results.append(result)
                except:
                    continue
            
            return results[:max_results]
        except Exception:
            pass
        return []
    
    def _search_simple_pypi(self, query: str, max_results: int) -> List[PyPISearchResult]:
        """Search using a pattern matching approach."""
        try:
            # This is a fallback approach - try to find packages by pattern matching
            # Generate possible package names based on the query
            query_patterns = self._generate_search_patterns(query)
            results = []
            
            with console.status(f"[bold blue]🔍 Trying pattern matching for '{query}'...", spinner="dots"):
                for pattern in query_patterns[:10]:  # Limit attempts
                    try:
                        package_info = self.get_package_info(pattern)
                        if package_info:
                            info = package_info['info']
                            result = PyPISearchResult(
                                info.get('name', pattern),
                                info.get('summary', 'No description available'),
                                info.get('version', 'unknown')
                            )
                            # Check if not already in results
                            if not any(r.name.lower() == result.name.lower() for r in results):
                                results.append(result)
                                if len(results) >= max_results:
                                    break
                    except:
                        continue
            
            return results
        except Exception:
            pass
        return []
    
    def _generate_search_patterns(self, query: str) -> List[str]:
        """Generate possible package name patterns."""
        patterns = []
        query_lower = query.lower()
        
        # Original query
        patterns.append(query_lower)
        
        # Common Python package patterns
        patterns.extend([
            f"python-{query_lower}",
            f"{query_lower}-python",
            f"py-{query_lower}",
            f"py{query_lower}",
            f"{query_lower}py",
            f"{query_lower}-py",
            f"{query_lower}2",
            f"{query_lower}3",
        ])
        
        # Handle partial matches for common packages
        common_packages = {
            'reque': ['requests', 'request', 'python-requests'],
            'moviedb': ['tmdbsimple', 'themoviedb', 'movie-db', 'moviedb', 'python-moviedb'],
            'beautifulsoup': ['beautifulsoup4', 'bs4'],
            'pil': ['pillow', 'PIL'],
            'cv2': ['opencv-python', 'opencv-contrib-python'],
            'skimage': ['scikit-image'],
            'sklearn': ['scikit-learn'],
            'pd': ['pandas'],
            'np': ['numpy'],
        }
        
        if query_lower in common_packages:
            patterns.extend(common_packages[query_lower])
        
        # Try substring matching for popular packages
        popular_packages = [
            'requests', 'beautifulsoup4', 'pandas', 'numpy', 'flask', 'django',
            'fastapi', 'sqlalchemy', 'matplotlib', 'seaborn', 'pillow',
            'opencv-python', 'scikit-learn', 'tensorflow', 'torch', 'scrapy',
            'tmdbsimple', 'imdbpy', 'moviepy', 'pytube'
        ]
        
        for pkg in popular_packages:
            if query_lower in pkg.lower() or any(word in pkg.lower() for word in query_lower.split()):
                patterns.append(pkg)
        
        return list(dict.fromkeys(patterns))  # Remove duplicates while preserving order
    
    def _parse_modern_search_results(self, html_content: str, query: str, max_results: int) -> List[PyPISearchResult]:
        """Parse modern PyPI search results with multiple patterns."""
        results = []
        
        # Try multiple parsing patterns for different PyPI layouts
        patterns = [
            # Pattern 1: Current PyPI layout
            r'<a[^>]*href="/project/([^/]+)/"[^>]*>.*?<span[^>]*class="[^"]*package-snippet__name[^"]*"[^>]*>([^<]+)</span>.*?<p[^>]*class="[^"]*package-snippet__description[^"]*"[^>]*>([^<]*)</p>.*?<span[^>]*class="[^"]*package-snippet__version[^"]*"[^>]*>([^<]+)</span>',
            
            # Pattern 2: Alternative layout
            r'<h3[^>]*class="[^"]*package-snippet__title[^"]*"[^>]*>.*?<a[^>]*href="/project/([^/]+)/"[^>]*>([^<]+)</a>.*?</h3>.*?<p[^>]*class="[^"]*package-snippet__description[^"]*"[^>]*>([^<]*)</p>.*?<span[^>]*class="[^"]*badge[^"]*"[^>]*>([^<]+)</span>',
            
            # Pattern 3: Simplified pattern
            r'href="/project/([^/]+)/"[^>]*>.*?>([^<]+)<.*?description[^>]*>([^<]*)<.*?version[^>]*>([^<]+)<',
        ]
        
        for pattern in patterns:
            try:
                matches = re.findall(pattern, html_content, re.DOTALL | re.IGNORECASE)
                if matches:
                    break
            except:
                continue
        
        if not matches:
            # Fallback: try to find any project links
            project_links = re.findall(r'href="/project/([^/]+)/"', html_content)
            if project_links:
                # Try to get info for found projects
                for project_name in project_links[:max_results]:
                    try:
                        package_info = self.get_package_info(project_name)
                        if package_info:
                            info = package_info['info']
                            results.append(PyPISearchResult(
                                info.get('name', project_name),
                                info.get('summary', 'No description available'),
                                info.get('version', 'unknown')
                            ))
                    except:
                        continue
                return results
        
        # Process matches
        for match in matches[:max_results]:
            if len(match) >= 4:
                project_name, display_name, description, version = match[:4]
                name = project_name.strip()
                summary = description.strip() if description.strip() else "No description available"
                version_clean = version.strip()
                
                # Score relevance
                query_lower = query.lower()
                name_lower = name.lower()
                desc_lower = summary.lower()
                
                # Check if relevant
                if (query_lower in name_lower or 
                    query_lower in desc_lower or 
                    any(word in name_lower for word in query_lower.split()) or
                    any(word in desc_lower for word in query_lower.split())):
                    
                    result = PyPISearchResult(name, summary, version_clean)
                    if not any(r.name.lower() == result.name.lower() for r in results):
                        results.append(result)
        
        # Sort by relevance (exact matches first)
        query_lower = query.lower()
        results.sort(key=lambda x: (
            0 if x.name.lower() == query_lower else
            1 if x.name.lower().startswith(query_lower) else
            2 if query_lower in x.name.lower() else
            3
        ))
        
        return results
    
    def get_package_info(self, package_name: str) -> Optional[Dict[str, Any]]:
        """Fetch package information from PyPI API."""
        url = f"{self.BASE_URL}/{package_name}/json"
        
        try:
            with console.status(f"[bold blue]🔍 Fetching details for '{package_name}'...", spinner="dots"):
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
    
    def find_package(self, query: str) -> Optional[str]:
        """Find package by search query. Returns exact package name or None."""
        # First try exact match
        package_info = self.get_package_info(query)
        if package_info:
            return query
        
        # If exact match fails, search for similar packages
        console.print(f"[yellow]📦 Package '{query}' not found. Searching for similar packages...[/yellow]")
        
        # Try multiple search approaches
        search_results = self.search_packages(query, max_results=30)
        
        # If no results from web search, try our pattern-based approach
        if not search_results:
            console.print(f"[yellow]🔍 Trying alternative search methods...[/yellow]")
            search_results = self._fallback_package_search(query)
        
        if not search_results:
            console.print(f"[red]❌ No packages found matching '{query}'[/red]")
            console.print(f"[dim]💡 Try a different search term or check the spelling[/dim]")
            return None
        
        if len(search_results) == 1:
            console.print(f"[green]✅ Found similar package: {search_results[0].name}[/green]")
            return search_results[0].name
        
        # Multiple results - show selection menu
        return self._show_package_selection(search_results, query)
    
    def _fallback_package_search(self, query: str) -> List[PyPISearchResult]:
        """Fallback search using pattern matching and popular packages."""
        results = []
        
        # Generate search patterns
        patterns = self._generate_search_patterns(query)
        
        console.print(f"[blue]🔍 Checking {len(patterns)} possible package names...[/blue]")
        
        # Try each pattern
        checked = 0
        for pattern in patterns:
            if checked >= 15:  # Limit API calls
                break
                
            try:
                package_info = self.get_package_info(pattern)
                if package_info:
                    info = package_info['info']
                    name = info.get('name', pattern)
                    summary = info.get('summary', 'No description available')
                    version = info.get('version', 'unknown')
                    
                    # Check if not already in results
                    if not any(r.name.lower() == name.lower() for r in results):
                        results.append(PyPISearchResult(name, summary, version))
                        console.print(f"[dim]  ✓ Found: {name}[/dim]")
                
                checked += 1
            except:
                continue
        
        # Also try fuzzy matching with popular packages
        if not results and len(query) > 2:
            results.extend(self._fuzzy_match_popular_packages(query))
        
        return results
    
    def _fuzzy_match_popular_packages(self, query: str) -> List[PyPISearchResult]:
        """Try fuzzy matching with popular packages."""
        popular_packages = [
            # Web frameworks
            'flask', 'django', 'fastapi', 'tornado', 'bottle', 'pyramid',
            # Data science
            'pandas', 'numpy', 'matplotlib', 'seaborn', 'plotly', 'bokeh',
            'scipy', 'scikit-learn', 'tensorflow', 'torch', 'keras',
            # Web scraping
            'requests', 'beautifulsoup4', 'scrapy', 'selenium', 'lxml',
            # Databases
            'sqlalchemy', 'psycopg2', 'pymongo', 'redis', 'sqlite3',
            # Image/Video
            'pillow', 'opencv-python', 'moviepy', 'imageio',
            # APIs and data
            'tmdbsimple', 'imdbpy', 'tweepy', 'pygithub', 'wikipedia',
            # Utilities
            'click', 'colorama', 'tqdm', 'rich', 'tabulate', 'pyyaml',
            # Testing
            'pytest', 'unittest2', 'mock', 'nose',
            # Async
            'asyncio', 'aiohttp', 'uvloop',
        ]
        
        results = []
        query_lower = query.lower()
        
        # Find packages that contain the query or have similar words
        matches = []
        for pkg in popular_packages:
            pkg_lower = pkg.lower()
            # Exact substring match
            if query_lower in pkg_lower:
                matches.append((pkg, 1))
            # Word boundary match
            elif any(word in pkg_lower for word in query_lower.split()):
                matches.append((pkg, 2))
            # Fuzzy match (simple character overlap)
            elif len(set(query_lower) & set(pkg_lower)) >= min(3, len(query_lower) - 1):
                matches.append((pkg, 3))
        
        # Sort by match quality and get info
        matches.sort(key=lambda x: x[1])
        
        for pkg_name, _ in matches[:5]:  # Limit to top 5 matches
            try:
                package_info = self.get_package_info(pkg_name)
                if package_info:
                    info = package_info['info']
                    results.append(PyPISearchResult(
                        info.get('name', pkg_name),
                        info.get('summary', 'No description available'),
                        info.get('version', 'unknown')
                    ))
            except:
                continue
        
        return results
    
    def _show_package_selection(self, results: List[PyPISearchResult], query: str) -> Optional[str]:
        """Show interactive package selection menu."""
        console.print(f"\n[bold yellow]🔍 Found {len(results)} packages matching '{query}':[/bold yellow]\n")
        
        # Create selection table
        table = Table()
        table.add_column("#", style="bold cyan", width=3)
        table.add_column("Package Name", style="bold green", width=25)
        table.add_column("Version", style="bold yellow", width=12)
        table.add_column("Description", style="white")
        
        for i, result in enumerate(results, 1):
            # Truncate long descriptions
            desc = result.summary
            if len(desc) > 80:
                desc = desc[:77] + "..."
            
            table.add_row(
                str(i),
                result.name,
                result.version,
                desc
            )
        
        console.print(table)
        console.print()
        
        try:
            choice = IntPrompt.ask(
                "[bold cyan]Select a package number (or 0 to cancel)",
                default=0,
                show_default=True
            )
            
            if choice == 0:
                console.print("[yellow]⚠️  Selection cancelled[/yellow]")
                return None
            
            if 1 <= choice <= len(results):
                selected_package = results[choice - 1].name
                console.print(f"[green]✅ Selected: {selected_package}[/green]\n")
                return selected_package
            else:
                console.print("[red]❌ Invalid selection[/red]")
                return None
                
        except (KeyboardInterrupt, EOFError):
            console.print("\n[yellow]⚠️  Selection cancelled[/yellow]")
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
    
    def __init__(self):
        self.console = console
    
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
                if len(str(value)) > 50:
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
                display_url = url if len(url) <= 60 else url[:57] + "..."
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
            for item in items[:5]:  # Limit to 5 items per category
                category_node.add(f"[white]{item}")
            if len(items) > 5:
                category_node.add(f"[dim]... and {len(items) - 5} more")
        
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
                    md = Markdown(description[:2000] + ("..." if len(description) > 2000 else ""))
                    self.console.print(Panel(md, title="[bold cyan]📖 Description", border_style="cyan"))
                    self.console.print()
                except:
                    # Fallback to plain text
                    desc_text = description[:1000] + ("..." if len(description) > 1000 else "")
                    self.console.print(Panel(desc_text, title="[bold cyan]📖 Description", border_style="cyan"))
                    self.console.print()
            else:
                desc_text = description[:1000] + ("..." if len(description) > 1000 else "")
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
        
    def display_requirements(self, info: Dict[str, Any], package_name: str):
        try:
            """Display package requirements in a beautiful format."""
            requires_dist = info.get('requires_dist', [])
            requires_python = info.get('requires_python', None)
            
            # Create main requirements panel
            if not requires_dist and not requires_python:
                self.console.print(f"[yellow]📋 No dependencies found for {package_name}[/yellow]")
                return
            
            # Header
            title_text = Text()
            title_text.append("📋 ", style="bold blue")
            title_text.append(f"Requirements for {package_name}", style="bold white")
            
            self.console.print()
            self.console.print(Panel(
                Align.center(title_text),
                title="[bold blue]📋 Package Dependencies[/bold blue]",
                border_style="blue",
                padding=(1, 2)
            ))
            self.console.print()
            
            # Python version requirement
            if requires_python:
                python_table = Table(show_header=False, box=None)
                python_table.add_column("", style="bold yellow", width=20)
                python_table.add_column("", style="bold green")
                python_table.add_row("🐍 Python Version", requires_python)
                
                self.console.print(Panel(
                    python_table, 
                    title="[bold green]🐍 Python Requirements", 
                    border_style="green"
                ))
                self.console.print()
            
            # Parse and categorize dependencies
            if requires_dist:
                deps = self._parse_dependencies(requires_dist)
                
                if deps['core']:
                    self._display_dependency_table(deps['core'], "📦 Core Dependencies", "blue")
                
                if deps['optional']:
                    self._display_dependency_table(deps['optional'], "⚙️  Optional Dependencies", "yellow")
                
                if deps['dev']:
                    self._display_dependency_table(deps['dev'], "🛠️  Development Dependencies", "magenta")
                
                if deps['test']:
                    self._display_dependency_table(deps['test'], "🧪 Testing Dependencies", "cyan")
            
            # Show total count
            total_deps = len(requires_dist) if requires_dist else 0
            self.console.print(f"[dim]💡 Total dependencies: {total_deps}[/dim]")
        except Exception as e:
            console.print_exception()

    def _parse_dependencies(self, requires_dist: List[str]) -> Dict[str, List[Dict]]:
        """Parse and categorize dependencies."""
        deps = {
            'core': [],
            'optional': [],
            'dev': [],
            'test': []
        }
        
        for req in requires_dist:
            if not req:
                continue
            
            # Parse the requirement string
            dep_info = self._parse_single_requirement(req)
            
            # Categorize based on extras or markers
            req_lower = req.lower()
            if any(marker in req_lower for marker in ['extra == "dev"', 'extra == "development"']):
                deps['dev'].append(dep_info)
            elif any(marker in req_lower for marker in ['extra == "test"', 'extra == "testing"']):
                deps['test'].append(dep_info)
            elif 'extra ==' in req_lower:
                deps['optional'].append(dep_info)
            else:
                deps['core'].append(dep_info)
        
        return deps

    def _display_dependency_table(self, deps: List[Dict], title: str, border_color: str):
        """Display a table of dependencies."""
        if not deps:
            return
        
        table = Table(box=None)
        table.add_column("Package", style="bold green", width=25)
        table.add_column("Version", style="bold yellow", width=20)
        table.add_column("Condition", style="cyan")
        
        for dep in deps:
            if not dep:
                continue
            marker = dep.get('marker', '')
            if len(marker) > 40:
                marker = marker[:37] + "..."
            
            table.add_row(
                dep['name'],
                dep['version'],
                marker or "always"
            )
        
        self.console.print(Panel(
            table, 
            title=f"[bold {border_color}]{title} ({len(deps)})[/bold {border_color}]", 
            border_style=border_color
        ))
        self.console.print()
    
    def _parse_single_requirement(self, req: str) -> Dict[str, str]:
        """Parse a single requirement string into name, version, marker."""
        # Split by semicolon to separate package from markers
        parts = req.split(";", 1)
        package_part = parts[0].strip()
        marker_part = parts[1].strip() if len(parts) > 1 else ""

        # Extract package name and version
        version_pattern = r"^([a-zA-Z0-9][a-zA-Z0-9\-_.]*)\s*([><=!~\s].*)?$"
        match = re.match(version_pattern, package_part)
        if match:
            package_name = match.group(1).strip()
            version_spec = match.group(2).strip() if match.group(2) else ""
        else:
            package_name = package_part
            version_spec = ""

        # Clean version spec
        if version_spec:
            version_spec = re.sub(r"\s+", " ", version_spec).strip()

        return {
            "name": package_name,
            "version": version_spec or "any",
            "marker": marker_part,
            "raw": req
        }


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
        prog="pypi-info"
    )
    
    parser.add_argument(
        'package',
        nargs='?',
        help='📦 Package name or search query'
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
        '-s', '--search-only',
        action='store_true',
        help='🔍 Show search results only, don\'t fetch detailed info'
    )
    
    parser.add_argument(
        '-r', '--requirements',
        action='store_true',
        help='📋 Show package requirements/dependencies'
    )
    
    parser.add_argument('-v', '--version', action='version', version=f"[bold #FFFF00]version:[/] [bold #00FFFF]{get_version()}[/]", help="Show version")
    
    args = parser.parse_args()
    
    # Show help if no package specified
    if not args.package:
        parser.print_help()
        return
    
    # Initialize client and display
    client = PyPIClient()
    display = PackageInfoDisplay()
    
    # Handle search-only mode
    if args.search_only:
        console.print(f"\n[bold blue]🔍 Searching PyPI for '{args.package}'...[/bold blue]")
        search_results = client.search_packages(args.package, max_results=50)
        
        if not search_results:
            console.print(f"[red]❌ No packages found matching '{args.package}'[/red]")
            return
        
        # Display search results
        table = Table(title=f"🔍 Search Results for '{args.package}'")
        table.add_column("Package Name", style="bold green", width=30)
        table.add_column("Version", style="bold yellow", width=12)
        table.add_column("Description", style="white")
        
        for result in search_results:
            desc = result.summary
            if len(desc) > 100:
                desc = desc[:97] + "..."
            
            table.add_row(result.name, result.version, desc)
        
        console.print(table)
        return
    
    # Find the package (with smart search)
    console.print(f"\n[bold blue]🔍 Looking for package '{args.package}'...[/bold blue]")
    package_name = client.find_package(args.package)
    
    if not package_name:
        return
    # Get detailed package information
    package_data = client.get_package_info(package_name)
    
    if not package_data:
        console.print(f"[red]❌ Could not fetch details for package '{package_name}'[/red]")
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
    
    if args.requirements:
        # jprint(info)
        display.display_requirements(info, package_name)
        return
    
    # Download package if requested
    if args.download:
        version = args.version_download or "latest"
        console.print(f"\n[bold green]📥 Downloading {package_name} (version: {version})...[/bold green]")
        success = client.download_package(package_name, version, args.path)
        if not success:
            return
        console.print()
    
    # Display package information
    display.display_package_info(package_data, args.last)
    
    # Final message
    console.print(f"[dim]💡 Use --download to download this package, or --help for more options[/dim]")

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
    

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[yellow]⚠️  Operation cancelled by user[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[red]❌ Unexpected error: {str(e)}[/red]")
        sys.exit(1)