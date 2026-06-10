#!/usr/bin/env python3
# author: Hadi Cahyadi (cumulus13@gmail.com)
# create in 10 minutes

"""
PyPI Package Information Tool
A beautiful command-line tool to fetch and display PyPI package information.
"""
import os
import sys
from pathlib import Path
import traceback

tprint = None  # type: ignore
LOG_LEVEL = "NO"

exceptions=['pika', 'urllib', 'urllib2', 'urllib3', 'markdown_it', 'markdown', 'subprocess', 'pillow', 'PIL', 'requests', 'pyqt5']

if len(sys.argv) > 1 and any('--debug' == arg for arg in sys.argv):
    print("🐞 Debug mode enabled")
    os.environ["DEBUG"] = "1"
    os.environ['LOGGING'] = "1"
    os.environ.pop('NO_LOGGING', None)
    os.environ['TRACEBACK'] = "1"
    os.environ["LOGGING"] = "1"
    LOG_LEVEL = "DEBUG"
else:
    os.environ['NO_LOGGING'] = "1"

print(f"LOG_LEVEL            [2]: {LOG_LEVEL}")

try:
    from richcolorlog import setup_logging, print_exception as tprint  # type: ignore
    logger = setup_logging(
        name="pypi_info",
        level=LOG_LEVEL,
        exceptions=exceptions
    )
    HAS_RICHCOLORLOG=True
except:
    HAS_RICHCOLORLOG=False
    import logging

    for exc in exceptions:
        logging.getLogger(exc).setLevel(0)
    
    try:
        from .custom_logging import get_logger  # type: ignore
    except ImportError:
        from custom_logging import get_logger  # type: ignore
    
    logger = get_logger('pypi_info', level=getattr(logging, LOG_LEVEL, logging.CRITICAL))

if not tprint:  # type: ignore
    def tprint(*args, **kwargs):
        traceback.print_exc()

def get_config_file():
    config_file = None
    if sys.platform == 'win32':
        config_file_list = [
            Path(os.path.expandvars('%APPDATA%')) / '.pypi_info' / Path('.env'),
            Path(os.path.expandvars('%USERPROFILE%')) / '.pypi_info' / Path('.env'),

            Path(os.path.expandvars('%APPDATA%')) / '.pypi_info' / f"{Path(__file__).stem}.ini",
            Path(os.path.expandvars('%USERPROFILE%')) / '.pypi_info' / f"{Path(__file__).stem}.ini",

            Path(os.path.expandvars('%APPDATA%')) / '.pypi_info' / f"{Path(__file__).stem}.toml",
            Path(os.path.expandvars('%USERPROFILE%')) / '.pypi_info' / f"{Path(__file__).stem}.toml",

            Path(os.path.expandvars('%APPDATA%')) / '.pypi_info' / f"{Path(__file__).stem}.json",
            Path(os.path.expandvars('%USERPROFILE%')) / '.pypi_info' / f"{Path(__file__).stem}.json",

            Path(os.path.expandvars('%APPDATA%')) / '.pypi_info' / f"{Path(__file__).stem}.yml",
            Path(os.path.expandvars('%USERPROFILE%')) / '.pypi_info' / f"{Path(__file__).stem}.yml",
        ]
    else:    
        config_file_list = [
            Path(os.path.expanduser('~')) / '.pypi_info' / Path('.env'),
            Path(os.path.expanduser('~')) / '.config' / '.pypi_info' / Path('.env'),
            Path(os.path.expanduser('~')) / '.config' / Path('.env'),

            Path(os.path.expanduser('~')) / '.pypi_info' / f"{Path(__file__).stem}.ini",
            Path(os.path.expanduser('~')) / '.config' / '.pypi_info' / f"{Path(__file__).stem}.ini",
            Path(os.path.expanduser('~')) / '.config' / f"{Path(__file__).stem}.ini",
            
            Path(os.path.expanduser('~')) / '.pypi_info' / f"{Path(__file__).stem}.toml",
            Path(os.path.expanduser('~')) / '.config' / '.pypi_info' / f"{Path(__file__).stem}.toml",
            Path(os.path.expanduser('~')) / '.config' / f"{Path(__file__).stem}.toml",
            
            Path(os.path.expanduser('~')) / '.pypi_info' / f"{Path(__file__).stem}.json",
            Path(os.path.expanduser('~')) / '.config' / '.pypi_info' / f"{Path(__file__).stem}.json",
            Path(os.path.expanduser('~')) / '.config' / f"{Path(__file__).stem}.json",
            
            Path(os.path.expanduser('~')) / '.pypi_info' / f"{Path(__file__).stem}.yml",
            Path(os.path.expanduser('~')) / '.config' / '.pypi_info' / f"{Path(__file__).stem}.yml",
            Path(os.path.expanduser('~')) / '.config' / f"{Path(__file__).stem}.yml",
        ]
    for cf in config_file_list:
        if cf.is_file():
            config_file = cf
            break
        
    if config_file and not config_file.parent.is_dir():
        config_file.parent.mkdir(parents=True, exist_ok=True)

    config_file = config_file or Path(__file__).parent / Path('.env')

    return config_file

from envdot import load_env  # type: ignore
load_env(get_config_file())
import argparse
import json
import urllib.request
import urllib.parse

from typing import Dict, Any, List, Optional
from datetime import datetime
import re
HAS_GUI = False
try:
    from .gui_qt5 import main as gui
    HAS_GUI = True
except Exception as e:
    print(f"GUI components could not be imported: {e}: Please install PyQt5 and Pygments for GUI support.")
    try:
        from gui_qt5 import main as gui
        HAS_GUI = True
    except:
        pass

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

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None

from dataclasses import dataclass
import hashlib
import pickle
import time

console = Console()

class CustomRichHelpFormatter(RichHelpFormatter):
    """A custom RichHelpFormatter with modified styles."""
    try:
        styles: Dict[str, rr.StyleType] = {
            "argparse.args": "bold #FFFF00",  # Yellow
            "argparse.groups": "#AA55FF",     # Purple  
            "argparse.help": "bold #00FFFF",  # Cyan
            "argparse.metavar": "bold #FF00FF", # Magenta
            "argparse.syntax": "underline",   # Underlined
            "argparse.text": "white",         # White
            "argparse.prog": "bold #00AAFF italic", # Blue italic
            "argparse.default": "bold",       # Bold
        }
    except Exception as e:  # type: ignore
        styles = {}  # type: ignore

@dataclass
class ConfigManager:
    CACHE_DIR: Path = Path(os.getenv("CACHE_DIR", Path.home() / ".pypi_info" / "cache"))
    CACHE_EXPIRY: int = os.getenv("CACHE_EXPIRY", 3600)  # type: ignore
    REDIS_PREFIX: str = os.getenv("REDIS_PREFIX", "pipr_cache:")
    use_cache: bool = os.getenv("USE_CACHE", True)  # type: ignore
    use_redis: bool = os.getenv("USE_REDIS", True)  # type: ignore
    redis_client: Optional[Any] = None  # type: ignore

Config = ConfigManager()

class RedisManager:    
    
    def __init__(self) -> None:
        """Initialize Redis connection"""
        if not REDIS_AVAILABLE:
            logger.warning("Redis not available, falling back to file cache")
            Config.use_redis = False
            return
        
        try:
            redis_config = self.get_redis_config()
            logger.debug(f"Connecting to Redis: {redis_config.get('host')}:{redis_config.get('port')}/{redis_config.get('db')}")
            
            Config.redis_client = redis.Redis(  # type: ignore
                decode_responses=True,
                **redis_config
            )
            
            Config.redis_client.ping()
            logger.info(f"Redis connected: {redis_config.get('host')}:{redis_config.get('port')}/{redis_config.get('db')}")
            
        except redis.ConnectionError as e:  # type: ignore
            logger.warning(f"Redis connection failed: {e}, falling back to file cache")
            logger.exception(e)  # type: ignore
            Config.redis_client = None
            Config.use_redis = False
        except Exception as e:
            logger.warning(f"Redis initialization failed: {e}, falling back to file cache")
            logger.exception(e)  # type: ignore
            Config.redis_client = None
            Config.use_redis = False

    def get_redis_config(self) -> Dict[str, Any]:
        """Get Redis configuration from config file or environment"""
        config = {
            'host': os.getenv('PYPI_INFO_REDIS_HOST', '127.0.0.1'),
            'port': int(os.getenv('PYPI_INFO_REDIS_PORT', '6379')),
            'db': int(os.getenv('PYPI_INFO_REDIS_DB', '0')),
            'password': os.getenv('PYPI_INFO_REDIS_PASSWORD', ''),
            'socket_timeout': int(os.getenv('PYPI_INFO_REDIS_TIMEOUT', '5')),
            'socket_connect_timeout': int(os.getenv('PYPI_INFO_REDIS_CONNECT_TIMEOUT', '5')),
        }
        
        redis_url = os.getenv('PYPI_INFO_REDIS_URL', '')
        if redis_url:
            try:
                import re
                pattern = r'redis://(?:([^@]+)@)?([^:]+):(\d+)/(\d+)'
                match = re.match(pattern, redis_url)
                if match:
                    password, host, port, db = match.groups()
                    config['host'] = host
                    config['port'] = int(port)
                    config['db'] = int(db)
                    if password:
                        config['password'] = password
                    logger.debug(f"Parsed Redis URL: {host}:{port}/{db}")
            except Exception as e:
                logger.warning(f"Failed to parse Redis URL: {e}")
        
        if not config['password']:
            config.pop('password', None)
        
        return config

    def _get_redis_key(self, cache_key: str) -> str:
        """Get Redis key with prefix"""
        return f"{Config.REDIS_PREFIX}{cache_key}"

    def _get_from_redis(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Retrieve data from Redis cache"""
        logger.alert(f"Config.use_redis: {Config.use_redis}")
        logger.alert(f"Config.redis_client: {Config.redis_client}")

        if not Config.use_redis or not Config.redis_client:
            return None
        
        redis_key = None

        try:
            redis_key = self._get_redis_key(cache_key)
            data_str = Config.redis_client.get(redis_key)
            
            if data_str:
                data = json.loads(data_str)  # type: ignore
                logger.debug(f"Redis cache hit: {cache_key}")
                return data
            
            logger.debug(f"Redis cache miss: {cache_key}")
            return None
            
        except redis.RedisError as e:  # type: ignore
            logger.exception(f"Redis get error: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.exception(f"Redis data decode error: {e}")
            try:
                if redis_key: Config.redis_client.delete(redis_key)  # type: ignore
            except:
                pass
            return None
        except Exception as e:
            logger.exception(f"Redis error: {e}")
            return None

    def _save_to_redis(self, cache_key: str, data: Dict[str, Any]) -> None:
        """Save data to Redis cache"""
        if not Config.use_redis or not Config.redis_client:
            return
        
        try:
            redis_key = self._get_redis_key(cache_key)
            data_str = json.dumps(data)
            
            Config.redis_client.setex(
                redis_key,
                Config.CACHE_EXPIRY,
                data_str
            )
            logger.debug(f"Redis cached: {cache_key} (TTL: {Config.CACHE_EXPIRY}s)")
            
        except redis.RedisError as e:  # type: ignore
            logger.warning(f"Redis set error: {e}")
        except Exception as e:
            logger.warning(f"Redis save error: {e}")

class CacheManager:

    def _get_cache_path(self, cache_key: str) -> Path:
        """Get cache file path for a given key"""
        key_hash = hashlib.md5(cache_key.encode()).hexdigest()
        return Config.CACHE_DIR / f"{key_hash}.cache"

    def _get_from_cache(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Retrieve data from file cache if valid"""
        if not Config.use_cache:
            return None
        
        cache_path = self._get_cache_path(cache_key)
        
        if not cache_path.exists():
            return None
        
        try:
            cache_age = time.time() - cache_path.stat().st_mtime
            if cache_age > Config.CACHE_EXPIRY:
                logger.debug(f"File cache expired for: {cache_key}")
                cache_path.unlink()
                return None
            
            with open(cache_path, 'rb') as f:
                data = pickle.load(f)
            
            logger.debug(f"File cache hit for: {cache_key} (age: {cache_age:.1f}s)")
            return data
            
        except Exception as e:
            logger.warning(f"File cache read error: {e}")
            if cache_path.exists():
                cache_path.unlink()
            return None

    def _save_to_cache(self, cache_key: str, data: Dict[str, Any]) -> None:
        """Save data to file cache"""
        if not Config.use_cache:
            return
        
        cache_path = self._get_cache_path(cache_key)
        
        try:
            with open(cache_path, 'wb') as f:
                pickle.dump(data, f)
            logger.debug(f"File cached: {cache_key}")
        except Exception as e:
            logger.warning(f"File cache write error: {e}")
    
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

        self.redis_manager = RedisManager()
        self.cache_manager = CacheManager()
    
    def search_packages(self, query: str, max_results: int = 20) -> List[PyPISearchResult]:
        """Search for packages using multiple approaches."""
        results = []

        try:
            results = self._search_pypi_json_api(query, max_results)
            if results:
                return results
            
            results = self._search_pypi_warehouse(query, max_results)
            if results:
                return results
            
            results = self._search_simple_pypi(query, max_results)
            if results:
                return results
                
        except Exception as e:
            console.print(f"[yellow]⚠️  Search error: {str(e)}[/yellow]")
        
        return results
    
    def _search_pypi_json_api(self, query: str, max_results: int) -> List[PyPISearchResult]:
        """Search using PyPI's JSON API approach."""

        package_name = re.sub(r'\s+', '_', query.strip().lower())
        cache_key = f"package_search:{package_name}"
        logger.info(f"cache_key: {cache_key}")
        logger.info(f"Config.use_redis: {Config.use_redis}")

        html_content = ""

        if cache_key and Config.use_redis:
            cached_data = self.redis_manager._get_from_redis(cache_key)
            logger.alert(f"cached_data: {cached_data}")  # type: ignore
            if cached_data:
                html_content = cached_data.get("data")
        
        elif cache_key and Config.use_cache:
            cached_data = self.cache_manager._get_from_cache(cache_key)
            logger.fatal(f"cached_data: {cached_data}")
            if cached_data:
                if Config.use_redis:
                    redis_manager._save_to_redis(cache_key, cached_data)  # type: ignore
                html_content = cached_data.get("data")
        else:
            try:
                search_url = f"https://pypi.org/search/?q={urllib.parse.quote(query)}&o=&c="
                
                with console.status(f"[bold blue]🔍 Searching PyPI for '{query}'...", spinner="dots"):
                    req = urllib.request.Request(search_url, headers=self.session_headers)
                    with urllib.request.urlopen(req, timeout=15) as response:
                        if response.status == 200:
                            html_content = response.read().decode('utf-8')
                            
            except Exception as e:
                pass

        if cache_key and html_content:  # type: ignore
            if Config.use_cache:
                self.cache_manager._save_to_cache(cache_key, {"data": html_content})  # type: ignore
            if Config.use_redis:
                self.redis_manager._save_to_redis(cache_key, {"data": html_content})  # type: ignore
        
        return self._parse_modern_search_results(html_content, query, max_results)  # type: ignore
    
    def _search_pypi_warehouse(self, query: str, max_results: int) -> List[PyPISearchResult]:
        """Alternative search using warehouse data."""
        try:
            results = []
            
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
            query_patterns = self._generate_search_patterns(query)
            results = []
            
            with console.status(f"[bold blue]🔍 Trying pattern matching for '{query}'...", spinner="dots"):
                for pattern in query_patterns[:10]:
                    try:
                        package_info = self.get_package_info(pattern)
                        if package_info:
                            info = package_info['info']
                            result = PyPISearchResult(
                                info.get('name', pattern),
                                info.get('summary', 'No description available'),
                                info.get('version', 'unknown')
                            )
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
        
        patterns.append(query_lower)
        
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
        
        popular_packages = [
            'requests', 'beautifulsoup4', 'pandas', 'numpy', 'flask', 'django',
            'fastapi', 'sqlalchemy', 'matplotlib', 'seaborn', 'pillow',
            'opencv-python', 'scikit-learn', 'tensorflow', 'torch', 'scrapy',
            'tmdbsimple', 'imdbpy', 'moviepy', 'pytube'
        ]
        
        for pkg in popular_packages:
            if query_lower in pkg.lower() or any(word in pkg.lower() for word in query_lower.split()):
                patterns.append(pkg)
        
        return list(dict.fromkeys(patterns))
    
    def _parse_modern_search_results(self, html_content: str, query: str, max_results: int) -> List[PyPISearchResult]:
        """Parse modern PyPI search results with multiple patterns."""
        results = []
        
        patterns = [
            r'<a[^>]*href="/project/([^/]+)/"[^>]*>.*?<span[^>]*class="[^"]*package-snippet__name[^"]*"[^>]*>([^<]+)</span>.*?<p[^>]*class="[^"]*package-snippet__description[^"]*"[^>]*>([^<]*)</p>.*?<span[^>]*class="[^"]*package-snippet__version[^"]*"[^>]*>([^<]+)</span>',
            r'<h3[^>]*class="[^"]*package-snippet__title[^"]*"[^>]*>.*?<a[^>]*href="/project/([^/]+)/"[^>]*>([^<]+)</a>.*?</h3>.*?<p[^>]*class="[^"]*package-snippet__description[^"]*"[^>]*>([^<]*)</p>.*?<span[^>]*class="[^"]*badge[^"]*"[^>]*>([^<]+)</span>',
            r'href="/project/([^/]+)/"[^>]*>.*?>([^<]+)<.*?description[^>]*>([^<]*)<.*?version[^>]*>([^<]+)<',
        ]
        
        matches = None

        for pattern in patterns:
            try:
                matches = re.findall(pattern, html_content, re.DOTALL | re.IGNORECASE)
                if matches:
                    break
            except:
                continue
        
        if not matches:  # type: ignore
            project_links = re.findall(r'href="/project/([^/]+)/"', html_content)
            if project_links:
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
        
        for match in matches[:max_results]:  # type: ignore
            if len(match) >= 4:
                project_name, display_name, description, version = match[:4]
                name = project_name.strip()
                summary = description.strip() if description.strip() else "No description available"
                version_clean = version.strip()
                
                query_lower = query.lower()
                name_lower = name.lower()
                desc_lower = summary.lower()
                
                if (query_lower in name_lower or 
                    query_lower in desc_lower or 
                    any(word in name_lower for word in query_lower.split()) or
                    any(word in desc_lower for word in query_lower.split())):
                    
                    result = PyPISearchResult(name, summary, version_clean)
                    if not any(r.name.lower() == result.name.lower() for r in results):
                        results.append(result)
        
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
        
        cache_key = f"package_info:{package_name}"
        logger.info(f"cache_key: {cache_key}")
        logger.info(f"Config.use_redis: {Config.use_redis}")

        if cache_key and Config.use_redis:
            cached_data = self.redis_manager._get_from_redis(cache_key)
            logger.alert(f"cached_data: {cached_data}")  # type: ignore
            if cached_data:
                return cached_data
        
        if cache_key and Config.use_cache:
            cached_data = self.cache_manager._get_from_cache(cache_key)
            logger.fatal(f"cached_data: {cached_data}")
            if cached_data:
                if Config.use_redis:
                    redis_manager._save_to_redis(cache_key, cached_data)  # type: ignore
                return cached_data
        
        try:
            with console.status(f"[bold blue]🔍 Fetching details for '{package_name}'...", spinner="dots"):
                req = urllib.request.Request(url, headers=self.session_headers)
                with urllib.request.urlopen(req, timeout=10) as response:
                    if response.status == 200:
                        data = json.loads(response.read().decode('utf-8'))
                        if Config.use_redis:
                            self.redis_manager._save_to_redis(cache_key, data)
                        if Config.use_cache:
                            self.cache_manager._save_to_cache(cache_key, data)
                        return data
                    else:
                        return None
        except urllib.error.HTTPError as e:  # type: ignore
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
        package_info = self.get_package_info(query)
        if package_info:
            return query
        
        console.print(f"[yellow]📦 Package '{query}' not found. Searching for similar packages...[/yellow]")
        
        search_results = self.search_packages(query, max_results=30)
        
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
        
        return self._show_package_selection(search_results, query)
    
    def _fallback_package_search(self, query: str) -> List[PyPISearchResult]:
        """Fallback search using pattern matching and popular packages."""
        results = []
        
        patterns = self._generate_search_patterns(query)
        
        with console.status(f"[blue]🔍 Checking {len(patterns)} possible package names ...[/blue]", spinner="point"):
        
            checked = 0
            for pattern in patterns:
                if checked >= 15:
                    break
                    
                try:
                    package_info = self.get_package_info(pattern)
                    if package_info:
                        info = package_info['info']
                        name = info.get('name', pattern)
                        summary = info.get('summary', 'No description available')
                        version = info.get('version', 'unknown')
                        
                        if not any(r.name.lower() == name.lower() for r in results):
                            results.append(PyPISearchResult(name, summary, version))
                            console.print(f"[dim]  ✓ Found: {name}[/dim]")
                    
                    checked += 1
                except:
                    continue
        
        if not results and len(query) > 2:
            results.extend(self._fuzzy_match_popular_packages(query))
        
        return results
    
    def _fuzzy_match_popular_packages(self, query: str) -> List[PyPISearchResult]:
        """Try fuzzy matching with popular packages."""
        popular_packages = [
            'flask', 'django', 'fastapi', 'tornado', 'bottle', 'pyramid',
            'pandas', 'numpy', 'matplotlib', 'seaborn', 'plotly', 'bokeh',
            'scipy', 'scikit-learn', 'tensorflow', 'torch', 'keras',
            'requests', 'beautifulsoup4', 'scrapy', 'selenium', 'lxml',
            'sqlalchemy', 'psycopg2', 'pymongo', 'redis', 'sqlite3',
            'pillow', 'opencv-python', 'moviepy', 'imageio',
            'tmdbsimple', 'imdbpy', 'tweepy', 'pygithub', 'wikipedia',
            'click', 'colorama', 'tqdm', 'rich', 'tabulate', 'pyyaml',
            'pytest', 'unittest2', 'mock', 'nose',
            'asyncio', 'aiohttp', 'uvloop',
        ]
        
        results = []
        query_lower = query.lower()
        
        matches = []
        for pkg in popular_packages:
            pkg_lower = pkg.lower()
            if query_lower in pkg_lower:
                matches.append((pkg, 1))
            elif any(word in pkg_lower for word in query_lower.split()):
                matches.append((pkg, 2))
            elif len(set(query_lower) & set(pkg_lower)) >= min(3, len(query_lower) - 1):
                matches.append((pkg, 3))
        
        matches.sort(key=lambda x: x[1])
        
        for pkg_name, _ in matches[:5]:
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
        
        table = Table()
        table.add_column("#", style="bold cyan", width=3)
        table.add_column("Package Name", style="bold green", width=25)
        table.add_column("Version", style="bold yellow", width=12)
        table.add_column("Description", style="white")
        
        for i, result in enumerate(results, 1):
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
                sys.exit(0)
            
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
        
        if version is None or version == "latest":
            version = package_info['info']['version']
        
        releases = package_info.get('releases', {})
        if version not in releases:
            console.print(f"[red]❌ Version {version} not found for {package_name}[/red]")
            return False
        
        files = releases[version]
        if not files:
            console.print(f"[red]❌ No files available for {package_name} {version}[/red]")
            return False
        
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
            download_file = files[0]
        
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
            size_bytes /= 1024.0  # type: ignore
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
        
        title_text = Text()
        title_text.append("📦 ", style="bold blue")
        title_text.append(name, style="bold white")
        title_text.append(f" {version}", style="bold green")
        
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
                display_url = url if len(url) <= 60 else url[:57] + "..."
                table.add_row(f"🌐 {url_type}", display_url)
        
        return table
    
    def create_classifiers_tree(self, info: Dict[str, Any]) -> Optional[Tree]:
        """Create classifiers tree."""
        classifiers = info.get('classifiers', [])
        if not classifiers:
            return None
        
        tree = Tree("🏷️  [bold yellow]Classifiers")
        
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
            for item in items[:5]:
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
        
        version_data = []
        for version, files in releases.items():
            if files:
                upload_time = files[0].get('upload_time_iso_8601', '')
                total_size = sum(f.get('size', 0) for f in files)
                version_data.append((version, upload_time, len(files), total_size))
        
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

    # ------------------------------------------------------------------ #
    #  NEW METHOD: display_all_versions                                    #
    # ------------------------------------------------------------------ #
    def display_all_versions(self, package_data: Dict[str, Any]):
        """Display every available version of a package in a full table."""
        info     = package_data.get('info', {})
        releases = package_data.get('releases', {})
        latest   = info.get('version', '')
        name     = info.get('name', 'Unknown')

        if not releases:
            self.console.print("[yellow]⚠️  No releases found for this package[/yellow]")
            return

        # Build list sorted newest-first by upload time
        version_data = []
        for version, files in releases.items():
            upload_time = ''
            total_size  = 0
            file_types  = set()
            if files:
                upload_time = files[0].get('upload_time_iso_8601', '')
                total_size  = sum(f.get('size', 0) for f in files)
                file_types  = {f.get('packagetype', '') for f in files}
            version_data.append((version, upload_time, len(files), total_size, file_types))

        version_data.sort(key=lambda x: x[1], reverse=True)

        table = Table(
            title=(
                f"📦 All Versions — [bold white]{name}[/bold white]  "
                f"([bold green]{len(version_data)}[/bold green] total)"
            ),
            box=None,
            show_lines=False,
        )
        table.add_column("#",            style="dim",        width=5,  justify="right")
        table.add_column("Version",      style="bold green", width=18)
        table.add_column("Release Date", style="cyan",       width=22)
        table.add_column("Files",        style="yellow",     width=7,  justify="right")
        table.add_column("Size",         style="magenta",    width=12, justify="right")
        table.add_column("Types",        style="bold blue")

        for idx, (version, upload_time, file_count, total_size, file_types) in \
                enumerate(version_data, start=1):

            if version == latest:
                ver_display = f"[bold white]{version}[/bold white] [bold red]◀ latest[/bold red]"
            else:
                ver_display = version

            date_display = self.format_date(upload_time) if upload_time else "[dim]Unknown[/dim]"
            size_display = self.format_size(total_size)  if total_size  else "[dim]—[/dim]"

            type_labels = []
            if 'bdist_wheel' in file_types:
                type_labels.append("[green]wheel[/green]")
            if 'sdist' in file_types:
                type_labels.append("[yellow]sdist[/yellow]")
            for t in sorted(file_types - {'bdist_wheel', 'sdist'}):
                type_labels.append(f"[dim]{t}[/dim]")
            types_display = "  ".join(type_labels) if type_labels else "[dim]—[/dim]"

            table.add_row(
                str(idx),
                ver_display,
                date_display,
                str(file_count),
                size_display,
                types_display,
            )

        self.console.print()
        self.console.print(table)
        self.console.print()
        self.console.print(
            "[dim]💡 Use [bold]-v <version>[/bold] with [bold]--download[/bold] "
            "to download a specific version[/dim]"
        )

    def display_package_info(self, package_data: Dict[str, Any], show_last_only: bool = False, show_full: bool = False):
        """Display complete package information."""
        info = package_data.get('info', {})
        releases = package_data.get('releases', {})
        
        self.console.print()
        self.console.print(self.create_header_panel(info))
        self.console.print()
        
        if show_last_only:
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
        
        left_column = []
        right_column = []
        
        basic_table = self.create_basic_info_table(info)
        left_column.append(Panel(basic_table, title="[bold green]ℹ️  Basic Information", border_style="green"))
        
        urls_table = self.create_urls_table(info)
        if urls_table:
            right_column.append(Panel(urls_table, title="[bold blue]🔗 Links", border_style="blue"))
        
        if left_column and right_column:
            self.console.print(Columns([left_column[0], right_column[0]], equal=True, expand=True))
            self.console.print()
        elif left_column:
            self.console.print(left_column[0])
            self.console.print()
        
        classifiers_tree = self.create_classifiers_tree(info)
        if classifiers_tree:
            self.console.print(Panel(classifiers_tree, title="[bold yellow]🏷️  Categories", border_style="yellow"))
            self.console.print()
        
        description = info.get('description', '').strip()
        if description and len(description) > 100:
            if any(marker in description for marker in ['#', '*', '`', '```', '[', '](']):
                try:
                    if show_full:
                        md = Markdown(description)
                    else:
                        md = Markdown(description[:2000] + ("..." if len(description) > 2000 else ""))
                    self.console.print(Panel(md, title="[bold cyan]📖 Description", border_style="cyan"))
                    self.console.print()
                except:
                    desc_text = description[:1000] + ("..." if len(description) > 1000 else "")
                    self.console.print(Panel(desc_text, title="[bold cyan]📖 Description", border_style="cyan"))
                    self.console.print()
            else:
                desc_text = description[:1000] + ("..." if len(description) > 1000 else "")
                self.console.print(Panel(desc_text, title="[bold cyan]📖 Description", border_style="cyan"))
                self.console.print()
        
        if releases:
            releases_table = self.create_releases_table(releases, info.get('version', ''))
            self.console.print(releases_table)
            self.console.print()
        
        total_files = sum(len(files) for files in releases.values())
        total_size  = sum(sum(f.get('size', 0) for f in files) for files in releases.values())
        
        stats_table = Table(show_header=False, box=None, padding=(0, 2))
        stats_table.add_column("Metric", style="bold yellow")
        stats_table.add_column("Value",  style="bold white")
        
        stats_table.add_row("📊 Total Versions", str(len(releases)))
        stats_table.add_row("📁 Total Files",    str(total_files))
        stats_table.add_row("💾 Total Size",     self.format_size(total_size))
        
        self.console.print(Panel(stats_table, title="[bold magenta]📈 Statistics", border_style="magenta"))

    def display_requirements(self, info: Dict[str, Any], package_name: str, export: bool = False, export_name: str|None = None):
        try:
            """Display package requirements in a beautiful format."""
            requires_dist   = info.get('requires_dist', [])
            requires_python = info.get('requires_python', None)

            if not requires_dist and not requires_python:
                self.console.print(f"[yellow]📋 No dependencies found for {package_name}[/yellow]")
                return
            
            if export:
                with open(os.path.join(os.getcwd(), export_name or 'requirements.txt'), 'w') as f_req:
                    f_req.write("\n".join(requires_dist))
                    self.console.print(f"✅ [bold #FFFF00]success export requirements to[/] [bold #00FFFF]{f_req.name}[/]")

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

        if not requires_dist:
            return deps
        
        for req in requires_dist:
            if not req:
                continue
            
            dep_info = self._parse_single_requirement(req)
            
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
        table.add_column("Package",   style="bold green",  width=25)
        table.add_column("Version",   style="bold yellow", width=20)
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
        parts        = req.split(";", 1)
        package_part = parts[0].strip()
        marker_part  = parts[1].strip() if len(parts) > 1 else ""

        version_pattern = r"^([a-zA-Z0-9][a-zA-Z0-9\-_.]*)\s*([><=!~\s].*)?$"
        match = re.match(version_pattern, package_part)
        if match:
            package_name = match.group(1).strip()
            version_spec = match.group(2).strip() if match.group(2) else ""
        else:
            package_name = package_part
            version_spec = ""

        if version_spec:
            version_spec = re.sub(r"\s+", " ", version_spec).strip()

        return {
            "name":    package_name,
            "version": version_spec or "any",
            "marker":  marker_part,
            "raw":     req
        }

def get_download_path(path=None, package_name=None):
    path = os.getenv('DOWNLOAD_PATH', path or os.getcwd())
    if package_name:
        path = os.path.join(path, package_name)
        os.makedirs(path, exist_ok=True)
    return path

def get_version():
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
        prog="pipinfo/pypi-info/pip-info/pypi-info"
    )
    
    parser.add_argument(
        'package',
        nargs='*',
        help='📦 Packages name or search query'
    )
    
    parser.add_argument(
        '-l', '--last',
        action='store_true',
        help='🔍 Show only the latest version information'
    )

    # ------------------------------------------------------------------ #
    #  NEW FLAG: --all-versions / -A                                       #
    # ------------------------------------------------------------------ #
    parser.add_argument(
        '-A', '--all-versions',
        action='store_true',
        dest='all_versions',
        help='📋 Show all available versions of the package'
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
        '-v', '--version-download',
        help='🔢 Specific version to download (default: latest)'
    )
    
    parser.add_argument(
        '-a', '--author',
        action='store_true',
        help='👤 Show author information'
    )
    
    parser.add_argument(
        '-H', '--home',
        action='store_true',
        help='🏠 Show home page URL'
    )
    
    parser.add_argument(
        '-t', '--tags',
        action='store_true',
        help='🏷️  Show package classifiers/tags'
    )
    
    parser.add_argument(
        '-u', '--urls',
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

    parser.add_argument(
        '-e', '--export',
        action='store_true',
        help='💢 Export requirements/description to txt/md file'
    )

    parser.add_argument(
        '-E', '--export-name',
        help='🐜 Export name / Save as name'
    )

    parser.add_argument(
        '-g', '--gui',
        action='store_true',
        help='🖥️  Launch GUI (if available)'
    )

    parser.add_argument(
        '-f', '--full',
        action='store_true',
        help='🚿 Show all'
    )
    
    parser.add_argument(
        '-V', '--version',
        action='version',
        version=f"[bold #FFFF00]version:[/] [bold #00FFFF]{get_version()}[/]",
        help="Show version"
    )
    
    args = parser.parse_args()
    
    if not args.package:
        parser.print_help()
        return

    if args.gui and HAS_GUI:
        gui(args.package[0])
        sys.exit(0)
    elif args.gui and not HAS_GUI:
        console.print("[red]❌ GUI dependencies not installed. Please install 'pyqt5' and 'pygments' to use the GUI mode.[/red]")

    client  = PyPIClient()
    display = PackageInfoDisplay()
    
    # Handle search-only mode
    if args.search_only:
        for i, pack in enumerate(args.package):
            console.print(f"\n[bold blue]🔍 Searching PyPI for '{pack}'...[/bold blue]")
            search_results = client.search_packages(pack, max_results=50)
            
            if not search_results:
                console.print(f"[red]❌ No packages found matching '{pack}'[/red]")
                return
            
            table = Table(title=f"🔍 Search Results for '{pack}'")
            table.add_column("Package Name", style="bold green", width=30)
            table.add_column("Version",      style="bold yellow", width=12)
            table.add_column("Description",  style="white")
            
            for result in search_results:
                desc = result.summary
                if len(desc) > 100:
                    desc = desc[:97] + "..."
                table.add_row(result.name, result.version, desc)
            
            console.print(table)
            if i == len(args.package) - 1:
                return
    
    for i, pack in enumerate(args.package):
        console.print(f"\n[bold blue]🔍 Looking for package '{pack}'...[/bold blue]")
        package_name = client.find_package(pack)

        package_data = client.get_package_info(package_name)
        
        if not package_data:
            console.print(f"[red]❌ Could not fetch details for package '{package_name}'[/red]")
        
        info = package_data.get('info', {})
    
        if args.author:
            author       = info.get('author', 'N/A')
            author_email = info.get('author_email', 'N/A')
            console.print(f"[bold yellow]👤 Author:[/bold yellow] {author}")
            if author_email != 'N/A':
                console.print(f"[bold yellow]📧 Email:[/bold yellow] {author_email}")
            if i == len(args.package) - 1:
                return
        
        if args.home:
            home_page = info.get('home_page') or info.get('project_urls', {}).get('Homepage', 'N/A')
            console.print(f"[bold yellow]🏠 Home Page:[/bold yellow] {home_page}")
            if i == len(args.package) - 1:
                return
        
        if args.tags:
            classifiers = info.get('classifiers', [])
            if classifiers:
                console.print("[bold yellow]🏷️  Package Tags/Classifiers:[/bold yellow]")
                for classifier in classifiers:
                    console.print(f"  • {classifier}")
            else:
                console.print("[yellow]No classifiers found[/yellow]")
            if i == len(args.package) - 1:
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

        # ------------------------------------------------------------------ #
        #  Handle --all-versions                                               #
        # ------------------------------------------------------------------ #
        if args.all_versions:
            display.display_all_versions(package_data)
            if i == len(args.package) - 1:
                return
        
        if args.requirements:
            display.display_requirements(info, package_name, args.export, args.export_name)  # type: ignore
            if i == len(args.package) - 1:
                return
        
        if args.download:
            version = args.version_download or "latest"
            console.print(f"\n[bold green]📥 Downloading {package_name} (version: {version})...[/bold green]")
            success = client.download_package(
                package_name, version,
                get_download_path(
                    args.path,
                    package_name if os.getenv('DOWNLOAD_IN_SUBFOLDER', '1') in ['1', 'true', 'True'] else None
                )
            )
            if not success:
                console.print(f"\n:cross_mark: [white on red]Failed to download '{package_name}'[/]")
            console.print()
            if i == len(args.package) - 1:
                return
        
        if not args.requirements and not args.download and not args.author \
                and not args.home and not args.urls and not args.all_versions:
            display.display_package_info(package_data, args.last, args.full)  # type: ignore

        print("=" * os.get_terminal_size()[0])
        
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
