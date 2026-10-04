# pypi-info

A command-line tool that fetches and displays PyPI package information in a readable, colourful terminal layout (built with [rich](https://github.com/Textualize/rich)).

Look up a package, list every version, show dependencies, download a release, search PyPI, or check a whole `requirements.txt` for packages that exist.

[![Example Usage](https://github.com/cumulus13/pipinfo/raw/refs/heads/master/example_usage.gif)](https://github.com/cumulus13/pipinfo/raw/refs/heads/master/example_usage.gif)

## Features

- Package overview: name, version, author, license, Python requirement, project URLs, classifiers, description (rendered as Markdown), recent releases and statistics
- `--all-versions`: every release with date, file count, size and file types (wheel / sdist)
- `--requirements`: dependencies grouped into core, optional, dev and test, with version specifiers and environment markers; can export them to a file
- `--download`: download a wheel (falls back to sdist) with a progress bar, for the latest or a specific version
- `--check FILE`: check that every package in a requirements file exists on PyPI, with live per-package status and a summary table
- Fuzzy lookup: if a name is not found, pipinfo searches PyPI, guesses common name patterns and lets you pick from a list
- Caching: file cache (default) and optional Redis cache
- Optional PyQt5 GUI

## Requirements

- Python 3.10 or newer (the code uses `str | None` type hints)
- Required packages:
  - `rich`
  - `rich-argparse`
  - `envdot` (loads the config file / `.env`)
- Optional packages:
  - `redis` for the Redis cache
  - `richcolorlog` for coloured logging (otherwise `custom_logging.py` must be importable, see below)
  - `PyQt5` and `Pygments` for the GUI (`gui_qt5.py` must be importable)

### Important: `--check` needs the rich fork

`--check` uses `console.status(..., spinner_position='right', persist='half')`. Those two arguments are not in upstream rich. They exist in the author's fork:

<https://github.com/cumulus13/rich>

With stock rich, `-c` fails with `Console.status() got an unexpected keyword argument 'spinner_position'`. All other features work with stock rich.

`persist` accepts:

| Value | Behaviour |
|-------|-----------|
| `all` | keep every updated status text |
| `half` | keep only the first and the last status text |

## Installation

From source:

```bash
git clone https://github.com/cumulus13/pipinfo
cd pipinfo
pip install rich rich-argparse envdot
# optional
pip install redis richcolorlog PyQt5 pygments
```

With pip:
```bash
$ pip install pypi-info
```

If `richcolorlog` is not installed, the script falls back to `custom_logging.get_logger(name, level=...)`. Provide a `custom_logging.py` next to the script, for example:

```python
import logging

def get_logger(name, level=logging.CRITICAL):
    return logging.getLogger(name)
```

Run it as `python pipinfo.py ...`, or install it as a command named `pipinfo`.

## Usage

```
pipinfo [options] [package ...]
```

At least one package or `--check FILE` is required; otherwise help is shown.

Alias names for pipinfo: pypinfo, pypi-info

### Examples

```bash
# Full overview
pipinfo requests

# Only the latest release files
pipinfo requests --last

# Every available version
pipinfo django --all-versions

# Dependencies, and export them to requirements.txt
pipinfo celery -r
pipinfo celery -r -e
pipinfo celery -r -e -E celery-deps.txt

# Download latest wheel to ./downloads/requests/
pipinfo requests -d -p downloads

# Download a specific version
pipinfo requests -d -v 2.31.0

# Quick facts
pipinfo rich --author
pipinfo rich --home
pipinfo rich --tags
pipinfo rich --urls

# Search PyPI (also happens automatically if the exact name does not exist)
pipinfo "movie db" --search-only

# Several packages at once
pipinfo rich click typer

# Check a requirements file
pipinfo -c requirements.txt
pipinfo -c requirements.txt --verbose
```

## Options

| Option | Description |
|--------|-------------|
| `package ...` | One or more package names or search queries |
| `-c FILE`, `--check FILE` | Check that each package in a requirements file exists on PyPI |
| `-l`, `--last` | Show only the files of the latest version |
| `-A`, `--all-versions` | Show all available versions of the package |
| `-d`, `--download` | Download the package with a progress bar |
| `-p PATH`, `--path PATH` | Directory to save downloads (default: current directory) |
| `-v VERSION`, `--version-download VERSION` | Version to download (default: latest) |
| `-a`, `--author` | Show author information |
| `-H`, `--home` | Show the home page URL |
| `-t`, `--tags` | Show classifiers / tags |
| `-u`, `--urls` | Show all project URLs |
| `-s`, `--search-only` | Show search results only, without fetching details |
| `-r`, `--requirements` | Show dependencies |
| `-e`, `--export` | With `-r`: write the raw dependency list to a file (`requirements.txt` by default) |
| `-E NAME`, `--export-name NAME` | File name for `--export` |
| `-g`, `--gui` | Launch the GUI, if its dependencies are installed |
| `-f`, `--full` | Show the full description instead of the first 2000 characters |
| `-V`, `--version` | Show the pipinfo version (read from `__version__.py` next to the script) |
| `--debug` | Enable debug logging and tracebacks |
| `--verbose` | With `-c`: show HTTP status, size, timing and retry reasons for each package |
| `--retries N` | With `-c`: attempts per package on network or server errors (default `3`) |
| `--timeout S` | With `-c`: per-request timeout in seconds (default `30`) |

## Checking a requirements file (`-c`)

```bash
pipinfo -c requirements.txt
```

While running, each package shows a live status line, which is replaced with the result:

```
❓ check 'requests'
✅ check 'requests' EXIST
❌ check 'not-a-real-pkg' NOT FOUND
⚠️  check 'celery' ERROR HTTP 503 Service Unavailable
```

When all packages have been checked, a summary table is printed:

```
              📋 Check Results from requirements.txt
┏━━━┳━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━┓
┃ # ┃ Package Name   ┃ Status       ┃ Latest Version ┃
┡━━━╇━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━┩
│ 1 │ requests       │ ✅ EXIST     │ 2.34.2         │
│ 2 │ not-a-real-pkg │ ❌ NOT FOUND │ -              │
│ 3 │ celery         │ ⚠️  ERROR    │ -              │
└───┴────────────────┴──────────────┴────────────────┘
```

### Result states

| State | Meaning |
|-------|---------|
| EXIST | PyPI answered with the package JSON; the latest version is shown |
| NOT FOUND | PyPI answered HTTP 404. This is the only case reported as missing |
| ERROR | The check failed (timeout, DNS, connection reset, HTTP 429/5xx, invalid JSON). The package is **not** necessarily missing |

Network errors and HTTP 429/500/502/503/504 are retried with a short backoff (`--retries`, `--timeout`). Use `--verbose` to see why a package failed.

### How the file is parsed

One requirement per line. Package names are extracted and de-duplicated (case-insensitive). The following are handled or skipped:

- Version specifiers and extras: `requests==2.0`, `rich[extra]>=13`, `pkg!=1.0`
- Environment markers: `rich ; python_version > "3"`
- Inline comments: `flask  # web`, and full-line comments
- Skipped: option lines (`-r other.txt`, `-e .`, `--index-url ...`), local paths, `git+...` and `http(s)://` URLs
- A UTF-8 BOM at the start of the file is tolerated

`-r other.txt` includes are not followed.

### Exit codes (`-c` without positional packages)

| Code | Meaning |
|------|---------|
| `0` | All packages exist |
| `1` | At least one package was not found |
| `2` | At least one package could not be checked (error) |

This makes it usable in CI. If you also pass packages on the command line, pipinfo continues with the normal lookup after printing the table.

## Lookup, search and fuzzy matching

If the exact name does not exist, pipinfo:

1. searches `pypi.org/search` and parses the results,
2. tries common name patterns (`python-X`, `X-python`, `pyX`, `Xpy`, ...),
3. falls back to fuzzy matching against a list of popular packages.

If several candidates are found, an interactive numbered list lets you pick one (`0` cancels).

## Downloads

- Prefers a wheel, then an sdist, then the first available file.
- Files are saved in `<path>/<package-name>/` by default. Set `DOWNLOAD_IN_SUBFOLDER=0` to save directly in `<path>`.
- The `DOWNLOAD_PATH` environment variable, if set, overrides `-p`.

## Configuration

pipinfo loads its configuration with `envdot`. The first existing file from the list below is used; if none exists, a `.env` next to the script is used.

**Linux / macOS**

```
~/.pypi_info/.env
~/.config/.pypi_info/.env
~/.config/.env
~/.pypi_info/<script>.{ini,toml,json,yml}
~/.config/.pypi_info/<script>.{ini,toml,json,yml}
~/.config/<script>.{ini,toml,json,yml}
```

**Windows**

```
%APPDATA%\.pypi_info\.env
%USERPROFILE%\.pypi_info\.env
%APPDATA%\.pypi_info\<script>.{ini,toml,json,yml}
%USERPROFILE%\.pypi_info\<script>.{ini,toml,json,yml}
```

`<script>` is the script file name without extension (for example `pipinfo`).

### Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `USE_CACHE` | `true` | Enable the file cache |
| `CACHE_DIR` | `~/.pypi_info/cache` | File cache directory |
| `CACHE_EXPIRY` | `3600` | Cache lifetime in seconds |
| `USE_REDIS` | `true` | Use Redis if available; falls back to the file cache when Redis cannot be reached |
| `REDIS_PREFIX` | `pipr_cache:` | Prefix for Redis keys |
| `PYPI_INFO_REDIS_HOST` | `127.0.0.1` | Redis host |
| `PYPI_INFO_REDIS_PORT` | `6379` | Redis port |
| `PYPI_INFO_REDIS_DB` | `0` | Redis database |
| `PYPI_INFO_REDIS_PASSWORD` | empty | Redis password |
| `PYPI_INFO_REDIS_TIMEOUT` | `5` | Redis socket timeout (s) |
| `PYPI_INFO_REDIS_CONNECT_TIMEOUT` | `5` | Redis connect timeout (s) |
| `PYPI_INFO_REDIS_URL` | empty | `redis://[password@]host:port/db`; overrides host, port, db and password |
| `DOWNLOAD_PATH` | current dir | Download directory (overrides `-p`) |
| `DOWNLOAD_IN_SUBFOLDER` | `1` | Save into a per-package subfolder |
| `TRACEBACK` | unset | `1` / `true` prints full tracebacks for some errors |

Boolean values accept `1`, `true`, `yes`, `on` (case-insensitive) as true; anything else is false.

Example `.env`:

```env
USE_CACHE=true
CACHE_EXPIRY=7200
USE_REDIS=true
PYPI_INFO_REDIS_HOST=127.0.0.1
PYPI_INFO_REDIS_PORT=6379
DOWNLOAD_IN_SUBFOLDER=1
```

### Notes on caching

- The file cache stores package JSON and search pages. Entries older than `CACHE_EXPIRY` are removed when read.
- Only fresh network results are written back to the cache, so a cache hit does not extend its own lifetime.
- `--check` always queries PyPI directly and does not read the cache.
- The file cache uses `pickle`; only point `CACHE_DIR` at a directory you control.

## Troubleshooting

**`Console.status() got an unexpected keyword argument 'spinner_position'`**
You are using stock rich. Install the fork (see [above](#important---check-needs-the-rich-fork)) to use `-c`.

**A package shows ERROR in `--check`**
It could not be checked, it is not necessarily missing. Re-run with `--verbose` to see the reason, and try a higher `--timeout` or `--retries`.

**`unrecognized arguments: --debug`**
You are running an older version. `--debug` is registered in current versions.

**Output crashes when piped or in CI**
Older versions called `os.get_terminal_size()`. Current versions use `shutil.get_terminal_size()`.

**GUI does not start**
Install `PyQt5` and `pygments`, and make sure `gui_qt5.py` is importable. The reason for the failed import is printed when you pass `-g`.

**Logging import error**
Without `richcolorlog`, a `custom_logging.py` that provides `get_logger` must be next to the script.

## Known limitations

- With several packages, `-a`, `-H` and `-t` print their output for each package but only stop after the last one, so the full overview is also printed for earlier packages. `-u` stops after the first package.
- `--check` does not follow `-r other.txt` includes and ignores URL and path requirements.
- A package name that PyPI normalizes differently is still found (PyPI redirects), but the name shown in the table is the one written in your file.

## License

[MIT](LICENSE)

## 👤 Author
        
[Hadi Cahyadi](mailto:cumulus13@gmail.com)
    

[![Buy Me a Coffee](https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png)](https://www.buymeacoffee.com/cumulus13)

[![Donate via Ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/cumulus13)
 
[Support me on Patreon](https://www.patreon.com/cumulus13)