#!/usr/bin/env python3

# File: pypi_info/__init__.py
# Author: Hadi Cahyadi <cumulus13@gmail.com>
# Date: 2026-01-03
# Description: 
# License: MIT

__all__ = ["PyPIClient", "PackageInfoDisplay", "get_version"]

try:
	from .gui_qt5 import AndromedaStyle, HtmlLoaderThread, HtmlLoadWorker, LoadingOverlay, HtmlViewer, SearchLineEdit, PackageInfoWorker, PyPIInfoGUI  # type: ignore 
	__all__.extend(["AndromedaStyle", "HtmlLoaderThread", "HtmlLoadWorker", "LoadingOverlay", "HtmlViewer", "SearchLineEdit", "PackageInfoWorker", "PyPIInfoGUI"])
except Exception as e:
	print("GUI components could not be imported [__init__]:", e)

from .pipinfo import PyPIClient, PackageInfoDisplay, get_version


