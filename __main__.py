import argparse
import sys
from urllib.parse import urlencode

from rich.console import Console
from rich.table import Table

from pip_search.pip_search import config, search

from pip_search import __version__
from pip_search.utils import check_version
from pathlib import Path
import importlib

sys.path.insert(0, str(Path(__file__).parent))
MPATH = str(Path(__file__).parent / 'pipinfo.py')

spec = importlib.util.spec_from_file_location("pipinfo", MPATH)
pipinfo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pipinfo)


def main():
    ap = argparse.ArgumentParser(
        prog="pipinfo", description="Search and Show packages on PyPI"
    )
    ap.add_argument(
        "-s",
        "--sort",
        type=str,
        const="name",
        nargs="?",
        choices=["name", "version", "released"],
        help="sort results by package name, version or \
                        release date (default: %(const)s)",
    )
    ap.add_argument(
        "query",
        nargs="*",
        type=str,
        help="terms to search pypi.org package repository",
    )
    ap.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    ap.add_argument(
        "--date_format",
        type=str,
        default="%d-%m-%Y",
        nargs="?",
        help="format for release date, (default: %(default)s)",
    )
    args = ap.parse_args()
    query = " ".join(args.query)
    result = search(query, opts=args)
    if not args.query:
        ap.print_help()
        sys.exit(1)

    table = Table(
        title=(
            "[not italic]:snake:[/] [bold][magenta]"
            f"{config.api_url}?{urlencode({'q': query})}"
            "[/] [not italic]:snake:[/]"
        )
    )
    table.add_column("No", style="#FF55FF", no_wrap=True)
    table.add_column("Package", style="cyan", no_wrap=True)
    table.add_column("Version", style="bold yellow")
    table.add_column("Released", style="bold green")
    table.add_column("Description", style="bold blue")
    emoji = ":open_file_folder:"
    n = 0
    #zfill = len(str(len(list(result))))
    zfill = 2
    packages = []
    for package in result:
        packages.append(package)
        checked_version = check_version(package.name)
        if checked_version == package.version:
            package.version = f"[bold cyan]{package.version} ==[/]"
        elif checked_version is not False:
            package.version = (
                f"{package.version} > [bold purple]{checked_version}[/]"
            )
        n += 1
        table.add_row(
            str(n).zfill(zfill), 
            f"[link={package.link}]{emoji}[/link] {package.name}",
            package.version,
            package.released_date_str(args.date_format),
            package.description,
        )
        
    console = Console()
    console.print(table)
    
    console.print("[bold #FFFF00]Select package[/], [bold #FF55FF] x|q = exit|quit[/]: ", end = '')
    q = input()
    if q:
        if q.isdigit() and int(q) <= n:
            pipinfo.get(packages[int(q) - 1].name)

if __name__ == "__main__":
    sys.exit(main())
