#!/usr/bin/env python3
# author: Hadi Cahyadi (cumulus13@gmail.com)
# PyQt5 GUI version of PyPI Package Information Tool

"""
PyPI Package Information Tool - GUI Version
A beautiful PyQt5 interface to fetch and display PyPI package information.
"""

import sys

from ctraceback import CTraceback
sys.excepthook = CTraceback()

with open("debug.log", "w") as f:
    f.write("Script started!\n")
    f.write(f"Args: {sys.argv}\n")


import os
import json
import urllib.request
import urllib.parse
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
import requests
import re
from pydebugger.debug import debug
from pygments.formatters import HtmlFormatter
# Try to import markdown for better rendering
try:
    import markdown
    MARKDOWN_AVAILABLE = True
except ImportError:
    MARKDOWN_AVAILABLE = False

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, 
    QTabWidget, QTextEdit, QLineEdit, QPushButton, QLabel, QTableWidget, 
    QTableWidgetItem, QSplitter, QFrame, QScrollArea, QTreeWidget, 
    QTreeWidgetItem, QHeaderView, QMessageBox, QProgressBar, QStatusBar
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QUrl, QEvent
from PyQt5.QtGui import QFont, QPalette, QColor, QKeySequence, QImage, QTextDocument, QMovie, QIcon, QPixmap
from PyQt5.QtWidgets import QShortcut

from PyQt5.QtWebEngineWidgets import QWebEngineView

from pygments.style import Style
from pygments.token import Token, Keyword, Name, Comment, String, Error, Number, Operator, Generic

class AndromedaStyle(Style):
    background_color = "#262a33"
    default_style = ""
    styles = {
        Comment: 'italic #5c6370',
        Keyword: 'bold #c678dd',
        Name: '#abb2bf',
        Name.Function: '#61afef',
        String: '#98c379',
        Number: '#d19a66',
        Operator: '#56b6c2',
        Error: 'bg:#e06c75 #ffffff'
    }

class HtmlLoaderThread(QThread):
    finished = pyqtSignal(str)

    def __init__(self, info, get_html_func):
        super().__init__()
        self.info = info
        self.get_html_func = get_html_func

    def run(self):
        # Ini jalan di background thread
        html_content = self.get_html_func(self.info)
        self.finished.emit(html_content)

class HtmlLoadWorker(QThread):
    finished = pyqtSignal(str)  # HTML final

    def __init__(self, description_html):
        super().__init__()
        self.description_html = description_html

    def run(self):
        # Di sini kamu bisa melakukan fetch gambar manual kalau mau
        # atau cukup langsung return HTML kalau HtmlViewer sudah handle load sendiri
        self.finished.emit(self.description_html)

class LoadingOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setStyleSheet("background-color: rgba(0, 0, 0, 150);")  # Dim

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)

        self.label = QLabel()
        self.movie = QMovie("loading.gif")  # file gif harus ada
        self.label.setMovie(self.movie)
        layout.addWidget(self.label)

        self.hide()

    def start(self):
        self.show()
        self.movie.start()

    def stop(self):
        self.movie.stop()
        self.hide()

class HtmlViewer(QTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)

    def loadResource(self, type, name):
        if type == QTextDocument.ImageResource:
            url = name.toString()
            try:
                resp = requests.get(url, timeout=5)
                if resp.status_code == 200:
                    img = QImage()
                    img.loadFromData(resp.content)
                    return img
            except Exception as e:
                print("Image load failed:", e)
        return super().loadResource(type, name)

class SearchLineEdit(QLineEdit):
    def __init__(self, parent=None):
        super().__init__(parent)

    def keyPressEvent(self, event):
        main_window = self.window()
        if event.key() in (Qt.Key_Up, Qt.Key_Down) and hasattr(main_window, 'desc_text') and main_window.tab_widget.currentWidget() == main_window.desc_tab and isinstance(main_window.desc_text, QWebEngineView):
            main_window.desc_text.setFocus()
            # Jangan relay event, biarkan QWebEngineView handle sendiri
            return
            # Jika desc_text QTextEdit/HtmlViewer, relay event
        elif event.key() in (Qt.Key_Up, Qt.Key_Down) and hasattr(main_window, 'desc_text') and main_window.tab_widget.currentWidget() == main_window.desc_tab and isinstance(main_window.desc_text, (QTextEdit, HtmlViewer)):
            QApplication.sendEvent(main_window.desc_text, event)
            return
        elif event.key() == Qt.Key_Escape:
            self.window().close()
            return

        super().keyPressEvent(event)

class PyPIClient:
    """Client for interacting with PyPI API."""
    
    BASE_URL = "https://pypi.org/pypi"
    
    def __init__(self):
        self.session_headers = {
            'User-Agent': 'PyPI-Info-Tool-GUI/1.0 (https://github.com/user/pypi-info-tool)'
        }
    
    def get_package_info(self, package_name: str) -> Optional[Dict[str, Any]]:
        """Fetch package information from PyPI API."""
        url = f"{self.BASE_URL}/{package_name}/json"
        
        try:
            req = urllib.request.Request(url, headers=self.session_headers)
            with urllib.request.urlopen(req, timeout=10) as response:
                if response.status == 200:
                    return json.loads(response.read().decode('utf-8'))
                else:
                    return None
        except urllib.error.HTTPError as e:
            if e.code == 404:
                raise Exception(f"Package '{package_name}' not found on PyPI")
            else:
                raise Exception(f"HTTP Error {e.code}: {e.reason}")
        except Exception as e:
            raise Exception(f"Error fetching package info: {str(e)}")

class PackageInfoWorker(QThread):
    """Worker thread for fetching package information."""
    
    info_received = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, package_name: str):
        super().__init__()
        self.package_name = package_name
        self.client = PyPIClient()
    
    def run(self):
        try:
            package_data = self.client.get_package_info(self.package_name)
            if package_data:
                self.info_received.emit(package_data)
            else:
                self.error_occurred.emit(f"No data found for package '{self.package_name}'")
        except Exception as e:
            self.error_occurred.emit(str(e))

class PyPIInfoGUI(QMainWindow):
    """Main GUI window for PyPI package information."""
    
    def __init__(self, default_package = "helpman"):
        super().__init__()
        self.package_data = None
        self.worker = None
        self.use_htmlviewer = False
        self.webengine_mode = False
        self.package_name = "Helpman"
        self.setWindowIcon(QIcon(QPixmap(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'icon.png'))))

        # Always on top dari awal
        self.setWindowFlag(Qt.WindowStaysOnTopHint, True)

        # Buat UI dulu supaya sizeHint final
        self.init_ui()
        self.setup_style()
        self.setup_shortcuts()

        # --- SETEL UKURAN A4 SETELAH UI DIBUAT ---
        screen = QApplication.primaryScreen()
        screen_size = screen.availableGeometry()
        sw, sh = screen_size.width(), screen_size.height()

        # Rasio A4 (tinggi / lebar)
        a4_ratio = 1.414
        target_height = int(sh * 0.9)
        target_width = int(target_height / a4_ratio)

        # Pastikan tidak melebihi lebar layar
        if target_width > sw:
            target_width = int(sw * 0.9)
            target_height = int(target_width * a4_ratio)

        target_width += 200
        # Set ukuran dan center
        self.resize(target_width, target_height)
        self.move((sw - target_width) // 2, (sh - target_height) // 2)

        self.loading_overlay = LoadingOverlay(self)
        self.loading_overlay.resize(self.size())
        self.loading_overlay.hide()
        self.resizeEvent = lambda event: self.loading_overlay.resize(self.size())

        self.search_input.setText(default_package)
        self.search_package()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Up, Qt.Key_Down, Qt.Key_Left, Qt.Key_Right):
            main_window = self.window()
            if (
                hasattr(main_window, 'desc_text')
                and main_window.tab_widget.currentWidget() == main_window.desc_tab
                and isinstance(main_window.desc_text, (QTextEdit, HtmlViewer))
            ):
                QApplication.sendEvent(main_window.desc_text, event)
                return
        elif event.key() == Qt.Key_Escape:
            self.window().close()
            return
        elif event.key() == Qt.Key_Q and not self.search_input.hasFocus():
            self.window().close()
            return

        super().keyPressEvent(event)
        
    def center_on_screen(self):
        qr = self.frameGeometry()
        cp = QApplication.desktop().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())
    
    def init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("PyPI Package Information Tool - GUI")
        self.setGeometry(100, 100, 1200, 800)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout(central_widget)
        
        # Search section
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Package Name:"))
        
        # self.search_input = QLineEdit()
        self.search_input = SearchLineEdit()
        self.search_input.setPlaceholderText("Enter package name (e.g., requests, beautifulsoup4)")
        self.search_input.returnPressed.connect(self.search_package)
        search_layout.addWidget(self.search_input)
        
        self.search_button = QPushButton("Search")
        self.search_button.clicked.connect(self.search_package)
        search_layout.addWidget(self.search_button)
        
        main_layout.addLayout(search_layout)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)
        
        # Tab widget
        self.tab_widget = QTabWidget()
        
        # Tab 1: Description
        self.desc_tab = QWidget()
        desc_layout = QVBoxLayout(self.desc_tab)
        desc_layout.setContentsMargins(0, 0, 0, 0)
        
        self.desc_text = QTextEdit()
        # self.desc_text = HtmlViewer()
        self.desc_text.setReadOnly(True)
        self.desc_text.setLineWrapMode(QTextEdit.WidgetWidth)  # Enable word wrapping
        desc_layout.addWidget(self.desc_text)
        
        self.tab_widget.addTab(self.desc_tab, "&1. Description")
        
        # Tab 2: Basic Info & Links
        self.info_tab = QWidget()
        self.setup_info_tab()
        self.tab_widget.addTab(self.info_tab, "&2. Basic Info")
        
        # Tab 3: Classifiers
        self.classifiers_tab = QWidget()
        self.setup_classifiers_tab()
        self.tab_widget.addTab(self.classifiers_tab, "&3. Classifiers")
        
        # Tab 4: Recent Releases
        self.releases_tab = QWidget()
        self.setup_releases_tab()
        self.tab_widget.addTab(self.releases_tab, "&4. Recent Releases")
        
        main_layout.addWidget(self.tab_widget)
        
        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready - Enter a package name to search")

    # def toggle_htmlviewer(self):
    #     """Toggle between QTextEdit (default) and HtmlViewer for description tab."""
    #     if not self.package_data:
    #         return

    #     desc_layout = self.desc_tab.layout()

    #     # Hapus widget lama
    #     if self.desc_text:
    #         desc_layout.removeWidget(self.desc_text)
    #         self.desc_text.deleteLater()

    #     # Toggle
    #     self.use_htmlviewer = not self.use_htmlviewer

    #     if self.use_htmlviewer:
    #         # Pakai HtmlViewer (gambar bisa tampil)
    #         self.desc_text = HtmlViewer()
    #     else:
    #         # Kembali ke QTextEdit biasa
    #         self.desc_text = QTextEdit()
    #         self.desc_text.setReadOnly(True)

    #     desc_layout.addWidget(self.desc_text)

    #     # Reload konten
    #     info = self.package_data.get('info', {})
    #     html_content = self.get_description_html(info)
    #     self.desc_text.setHtml(html_content)

    #     # Pindah ke tab Description dan fokus
    #     self.tab_widget.setCurrentWidget(self.desc_tab)
    #     self.desc_text.setFocus()

    # def toggle_htmlviewer(self):
    #     """Toggle between QTextEdit (default) and HtmlViewer for description tab."""
    #     if not self.package_data:
    #         return

    #     # Tampilkan overlay loading
    #     self.loading_overlay.start()

    #     # Jalankan proses ganti widget setelah overlay tampil
    #     QTimer.singleShot(50, self._do_toggle_htmlviewer)

    # def _do_toggle_htmlviewer(self):
    #     """Proses sebenarnya mengganti viewer dan load konten."""
    #     desc_layout = self.desc_tab.layout()

    #     # Hapus widget lama
    #     if self.desc_text:
    #         desc_layout.removeWidget(self.desc_text)
    #         self.desc_text.deleteLater()

    #     # Toggle
    #     self.use_htmlviewer = not self.use_htmlviewer

    #     if self.use_htmlviewer:
    #         self.desc_text = HtmlViewer()
    #     else:
    #         self.desc_text = QTextEdit()
    #         self.desc_text.setReadOnly(True)

    #     desc_layout.addWidget(self.desc_text)

    #     # Reload konten
    #     info = self.package_data.get('info', {})
    #     html_content = self.get_description_html(info)
    #     self.desc_text.setHtml(html_content)

    #     # Fokus ke tab Description
    #     self.tab_widget.setCurrentWidget(self.desc_tab)
    #     self.desc_text.setFocus()

    #     # Matikan overlay
    #     self.loading_overlay.stop()

    def toggle_htmlviewer(self):
        """Mulai proses toggle dengan loading overlay."""
        if not self.package_data:
            return

        self.loading_overlay.start()

        # Jalankan thread untuk load HTML di background
        info = self.package_data.get('info', {})
        self.loader_thread = HtmlLoaderThread(info, self.get_description_html)
        self.loader_thread.finished.connect(self._apply_htmlviewer)
        self.loader_thread.start()

    # def _apply_htmlviewer(self, html_content):
    #     desc_layout = self.desc_tab.layout()

    #     if self.desc_text:
    #         desc_layout.removeWidget(self.desc_text)
    #         self.desc_text.deleteLater()

    #     self.use_htmlviewer = not self.use_htmlviewer
    #     if self.use_htmlviewer:
    #         self.desc_text = HtmlViewer()
    #     else:
    #         self.desc_text = QTextEdit()
    #         self.desc_text.setReadOnly(True)

    #     desc_layout.addWidget(self.desc_text)
    #     self.desc_text.setHtml(html_content)

    #     self.tab_widget.setCurrentWidget(self.desc_tab)
    #     self.desc_text.setFocus()

    #     # Matikan overlay setelah UI sudah di-update
    #     self.loading_overlay.stop()

    def _apply_htmlviewer(self, html_content):
        desc_layout = self.desc_tab.layout()

        if self.desc_text:
            desc_layout.removeWidget(self.desc_text)
            self.desc_text.deleteLater()

        self.use_htmlviewer = not self.use_htmlviewer
        if self.use_htmlviewer:
            self.desc_text = HtmlViewer()
        else:
            self.desc_text = QTextEdit()
            self.desc_text.setReadOnly(True)
            
        self.desc_text.setStyleSheet("")  # Kosongkan agar HTML/CSS dari pygments/markdown dipakai
        self.desc_text.setPalette(self.palette())

        desc_layout.addWidget(self.desc_text)
        self.desc_text.setHtml(html_content)

        self.search_input.clearFocus()
        self.tab_widget.setCurrentWidget(self.desc_tab)
        self.desc_text.setFocus(Qt.OtherFocusReason)

        self.loading_overlay.stop()
        
    def get_description_html(self, info: dict) -> str:
        """Generate the HTML for the description tab without applying it."""
        name = info.get('name', 'Unknown')
        version = info.get('version', 'Unknown')
        summary = info.get('summary', 'No description available')
        description = info.get('description', '').strip()
        
        dark_css = """
        <style>
            body { background: #181818; color: #00FFFF; }
            h1, h2, h3, h4, h5, h6 { color: #00FFFF; }
            a { color: #0078AA; }
            code, pre {
                background: #222;
                color: #FFFF00;
                border-radius: 4px;
                padding: 4px;
                max-width: 100%;
                white-space: pre-wrap;
                word-break: break-word;
                overflow-x: auto;
                box-sizing: border-box;
                display: block;
            }
            pre {
                margin: 10px 0;
                padding: 10px;
                max-width: 100%;
                overflow-x: auto;
                white-space: pre-wrap;
                word-break: break-word;
            }
            table { background: #181818; color: #00FFFF; }
            th, td { border: 1px solid #333; }
        </style>
        """

        content = f"""
        <div style='text-align: center; margin-bottom: 20px;'>
            <h1 style='color: #00FFFF; margin-bottom: 5px;'>📦 {name} {version}</h1>
            <p style='color: #AAAAFF; font-style: italic; font-size: 14px;'>{summary}</p>
        </div>
        """
        
        content = dark_css + content

        if description:
            content += "<hr style='border-color: #333333; margin: 20px 0;'>"
            content += "<h3 style='color: #AAAAFF; margin-bottom: 10px;'>📖 Description</h3>"

            if self.is_markdown_content(description):
                if MARKDOWN_AVAILABLE:
                    formatter = HtmlFormatter(style='fruity', noclasses=True)
                    formatter = HtmlFormatter(style='fruity', noclasses=True)
                    responsive_css = """
                    <style>
                        pre, code {
                            max-width: 100%;
                            white-space: pre-wrap;
                            word-break: break-word;
                            overflow-x: auto;
                            box-sizing: border-box;
                            display: block;
                        }
                    </style>
                    """
                    css = f"<style>{formatter.get_style_defs('.codehilite')}</style>" + responsive_css
                    # css = f"<style>{formatter.get_style_defs('.codehilite')}</style>"

                    md = markdown.Markdown(
                        extensions=['fenced_code', 'tables', 'codehilite'],
                        extension_configs={
                            'codehilite': {
                                'guess_lang': True,
                                'pygments_style': 'fruity',
                                'noclasses': True
                            }
                        }
                    )
                    html_desc = md.convert(description)
                    content += css + html_desc
                else:
                    content += self.format_markdown_fallback(description)
            else:
                content += self.format_plain_description(description)

        return content

    def switch_to_htmlviewer(self):
        if not self.package_data:
            return

        info = self.package_data.get('info', {})
        # Tampilkan overlay
        self.loading_overlay.start()

        # Ambil HTML description dulu (tanpa ganti widget)
        html_desc = self.get_description_html(info)  # kamu bisa ambil dari populate_description_tab tapi return HTML

        # Jalankan worker untuk load HTML
        self.worker = HtmlLoadWorker(html_desc)
        self.worker.finished.connect(self.on_html_load_finished)
        self.worker.start()

    def on_html_load_finished(self, html_desc):
        self.loading_overlay.stop()
        desc_layout = self.desc_tab.layout()
        if self.desc_text:
            desc_layout.removeWidget(self.desc_text)
            self.desc_text.deleteLater()

        self.desc_text = HtmlViewer()
        desc_layout.addWidget(self.desc_text)
        self.desc_text.setHtml(html_desc)

        self.tab_widget.setCurrentWidget(self.desc_tab)
        self.desc_text.setFocus()
    
    def setup_info_tab(self):
        """Setup the basic info tab."""
        layout = QVBoxLayout(self.info_tab)
        
        # Splitter for basic info and links
        splitter = QSplitter(Qt.Horizontal)
        
        # Basic info table
        self.basic_info_table = QTableWidget()
        self.basic_info_table.setColumnCount(2)
        # self.basic_info_table.setHorizontalHeaderLabels(["Property", "Value"])
        # self.basic_info_table.horizontalHeader().setStretchLastSection(True)
        # self.basic_info_table.verticalHeader().setVisible(False)
        self.basic_info_table.setColumnCount(2)
        self.basic_info_table.horizontalHeader().setVisible(False)  # Sembunyikan header
        self.basic_info_table.verticalHeader().setVisible(False)

        # Links table
        self.links_table = QTableWidget()
        self.links_table.setColumnCount(2)
        # self.links_table.setHorizontalHeaderLabels(["Type", "URL"])
        # self.links_table.horizontalHeader().setStretchLastSection(True)
        # self.links_table.verticalHeader().setVisible(False)
        self.links_table.setColumnCount(2)
        self.links_table.horizontalHeader().setVisible(False)       # Sembunyikan header
        self.links_table.verticalHeader().setVisible(False)
        
        splitter.addWidget(self.basic_info_table)
        splitter.addWidget(self.links_table)
        splitter.setSizes([500, 500])
        
        layout.addWidget(splitter)
    
    def setup_classifiers_tab(self):
        """Setup the classifiers tab."""
        layout = QVBoxLayout(self.classifiers_tab)
        
        self.classifiers_tree = QTreeWidget()
        self.classifiers_tree.setHeaderLabel("Classifiers")
        layout.addWidget(self.classifiers_tree)
    
    def setup_releases_tab(self):
        """Setup the releases tab."""
        layout = QVBoxLayout(self.releases_tab)
        
        self.releases_table = QTableWidget()
        self.releases_table.setColumnCount(4)
        self.releases_table.setHorizontalHeaderLabels(["Version", "Release Date", "Files", "Size"])
        self.releases_table.horizontalHeader().setStretchLastSection(True)
        self.releases_table.verticalHeader().setVisible(False)
        
        layout.addWidget(self.releases_table)
    
    def setup_style(self):
        """Setup the dark theme with specified colors."""
        # Set application palette for dark theme
        palette = QPalette()
        
        # Background colors
        palette.setColor(QPalette.Window, QColor(0, 0, 0))  # Black background
        palette.setColor(QPalette.WindowText, QColor(0, 255, 255))  # Cyan text
        palette.setColor(QPalette.Base, QColor(20, 20, 20))  # Dark gray for input fields
        palette.setColor(QPalette.AlternateBase, QColor(40, 40, 40))  # Alternate row color
        palette.setColor(QPalette.Text, QColor(0, 255, 255))  # Cyan text in inputs
        palette.setColor(QPalette.Button, QColor(60, 60, 60))  # Button background
        palette.setColor(QPalette.ButtonText, QColor(0, 255, 255))  # Button text
        palette.setColor(QPalette.Highlight, QColor(0, 120, 120))  # Selection highlight
        palette.setColor(QPalette.HighlightedText, QColor(255, 255, 255))  # Selected text
        
        self.setPalette(palette)
        
        # Custom styles for specific elements
        style_sheet = """
            QTabWidget::pane {
                border: 1px solid #333333;
                background-color: black;
            }
            
            QTabWidget::tab-bar {
                alignment: left;
            }
            
            QTabBar::tab {
                background-color: #333333;
                color: #00FFFF;
                padding: 8px 16px;
                margin-right: 2px;
                border: 1px solid #555555;
            }
            
            QTabBar::tab:selected {
                background-color: #555555;
                color: #FFFFFF;
                font-weight: bold;
            }
            
            QTabBar::tab:hover {
                background-color: #444444;
            }
            
            QTableWidget {
                background-color: black;
                color: #00FFFF;
                gridline-color: #333333;
                selection-background-color: #0078AA;
            }
            
            QTableWidget::item {
                padding: 5px;
            }
            
            QHeaderView::section {
                background-color: #333333;
                color: #00FFFF;
                padding: 5px;
                border: 1px solid #555555;
                font-weight: bold;
            }
            
            QTextEdit {
                background-color: black;
                border: 1px solid #333333;
            }
            
            QTreeWidget {
                background-color: black;
                color: #FFAAFF;
                border: 1px solid #333333;
            }
            
            QTreeWidget::item {
                padding: 3px;
            }
            
            QTreeWidget::item:selected {
                background-color: #0078AA;
            }
            
            QLineEdit {
                background-color: #1a1a1a;
                border: 2px solid #333333;
                color: #00FFFF;
                padding: 5px;
                border-radius: 3px;
            }
            
            QLineEdit:focus {
                border-color: #0078AA;
            }
            
            QPushButton {
                background-color: #333333;
                color: #00FFFF;
                border: 2px solid #555555;
                padding: 8px 16px;
                border-radius: 3px;
                font-weight: bold;
            }
            
            QPushButton:hover {
                background-color: #444444;
                border-color: #0078AA;
            }
            
            QPushButton:pressed {
                background-color: #222222;
            }
            
            QProgressBar {
                border: 1px solid #333333;
                background-color: #1a1a1a;
                text-align: center;
                color: #00FFFF;
            }
            
            QProgressBar::chunk {
                background-color: #0078AA;
            }
            
            QStatusBar {
                background-color: #333333;
                color: #00FFFF;
                border-top: 1px solid #555555;
            }
        """
        
        self.setStyleSheet(style_sheet)
        
        # Set font
        font = QFont("Consolas", 10)
        if not font.exactMatch():
            font = QFont("Monaco", 10)
        if not font.exactMatch():
            font = QFont("monospace", 10)
        self.setFont(font)
    
    # def switch_to_htmlviewer(self):
    #     """Ganti desc_text jadi HtmlViewer dan reload description."""
    #     if not self.package_data:
    #         return

    #     # Ganti widget di layout
    #     desc_layout = self.desc_tab.layout()
    #     if self.desc_text:
    #         desc_layout.removeWidget(self.desc_text)
    #         self.desc_text.deleteLater()

    #     self.desc_text = HtmlViewer()
    #     desc_layout.addWidget(self.desc_text)

    #     # Reload konten description
    #     info = self.package_data.get('info', {})
    #     self.populate_description_tab(info)

    #     # Pindah ke tab Description & fokus
    #     self.tab_widget.setCurrentWidget(self.desc_tab)
    #     self.desc_text.setFocus()

    def eventFilter(self, obj, event):
        # Jangan relay event, biarkan widget handle sendiri
        if obj == self.desc_text and event.type() == QEvent.KeyPress:
            # Biarkan QTextEdit/HtmlViewer handle arrow keys
            return False
        return super().eventFilter(obj, event)
    
    def reload_description(self):
        """Reload description content."""
        if not self.package_data:
            return

        info = self.package_data.get('info', {})
        if self.webengine_mode:
            # Jika QWebEngineView, reload HTML
            html_content = self.get_description_html(info)
            self.desc_text.setHtml(html_content)
        else:
            content = self.populate_description_tab(info)
            self._apply_htmlviewer(content)

    def setup_shortcuts(self):
        """Setup keyboard shortcuts."""
        # Tab shortcuts (Alt+1-4)
        for i in range(4):
            shortcut = QShortcut(QKeySequence(f"Alt+{i+1}"), self)
            shortcut.activated.connect(lambda idx=i: self.tab_widget.setCurrentIndex(idx))
        
        # Quit shortcuts (Q and Escape)
        quit_shortcut_q = QShortcut(QKeySequence("Q"), self)
        quit_shortcut_q.activated.connect(self.close)
        
        quit_shortcut_esc = QShortcut(QKeySequence("Escape"), self)
        quit_shortcut_esc.activated.connect(self.close)
        
        # Search shortcut (Ctrl+F) - focus to search input
        search_shortcut = QShortcut(QKeySequence("Ctrl+F"), self)
        search_shortcut.activated.connect(self.focus_search_input)
        
        webengine_shortcut = QShortcut(QKeySequence("Ctrl+Alt+S"), self)
        webengine_shortcut.activated.connect(self.toggle_webengine_desc)
        
        reload_desc_shortcut = QShortcut(QKeySequence("Ctrl+R"), self)
        reload_desc_shortcut.activated.connect(self.reload_description)

    def toggle_webengine_desc(self):
        """Toggle description tab between QWebEngineView and QTextEdit/HtmlViewer."""
        if not self.package_data:
            return

        desc_layout = self.desc_tab.layout()
        if self.desc_text:
            desc_layout.removeWidget(self.desc_text)
            self.desc_text.deleteLater()

        info = self.package_data.get('info', {})
        html_content = self.get_description_html(info)

        if not self.webengine_mode:
            # Switch to QWebEngineView
            self.desc_text = QWebEngineView()
            self.desc_text.setHtml(html_content)
            self.webengine_mode = True
        else:
            # Switch back to QTextEdit/HtmlViewer
            self.desc_text = HtmlViewer() if self.use_htmlviewer else QTextEdit()
            self.desc_text.setReadOnly(True)
            self.desc_text.setHtml(html_content)
            self.reload_description()
            self.webengine_mode = False

        desc_layout.addWidget(self.desc_text)
        self.tab_widget.setCurrentWidget(self.desc_tab)
        self.desc_text.setFocus()
    
    def focus_search_input(self):
        """Focus to search input and select all text."""
        self.search_input.setFocus()
        self.search_input.selectAll()
    
    def search_package(self):
        """Search for package information."""
        self.webengine_mode = False
        package_name = self.search_input.text().strip() or self.package_name
        if not package_name:
            QMessageBox.warning(self, "Warning", "Please enter a package name")
            return
        
        # Clear previous data
        self.clear_all_tabs()
        
        # Show progress
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        self.search_button.setEnabled(False)
        self.status_bar.showMessage(f"Searching for package '{package_name}'...")
        
        # Start worker thread
        self.worker = PackageInfoWorker(package_name)
        self.worker.info_received.connect(self.on_info_received)
        self.worker.error_occurred.connect(self.on_error_occurred)
        self.worker.finished.connect(self.on_search_finished)
        self.worker.start()
    
    def on_info_received(self, package_data: dict):
        """Handle received package information."""
        self.package_data = package_data
        self.populate_all_tabs()
    
    def on_error_occurred(self, error_message: str):
        """Handle search errors."""
        QMessageBox.critical(self, "Error", error_message)
    
    def on_search_finished(self):
        """Handle search completion."""
        self.progress_bar.setVisible(False)
        self.search_button.setEnabled(True)
        if self.package_data:
            pkg_name = self.package_data.get('info', {}).get('name', 'Unknown')
            self.status_bar.showMessage(f"Successfully loaded information for '{pkg_name}'")
        else:
            self.status_bar.showMessage("Search completed")
    
    def clear_all_tabs(self):
        """Clear all tab contents."""
        # Clear description tab sesuai tipe widget
        if isinstance(self.desc_text, (QTextEdit, HtmlViewer)):
            self.desc_text.clear()
        elif isinstance(self.desc_text, QWebEngineView):
            self.desc_text.setHtml("")  # Kosongkan konten web

        self.basic_info_table.setRowCount(0)
        self.links_table.setRowCount(0)
        self.classifiers_tree.clear()
        self.releases_table.setRowCount(0)
    
    def populate_all_tabs(self):
        """Populate all tabs with package information."""
        if not self.package_data:
            return
        
        info = self.package_data.get('info', {})
        releases = self.package_data.get('releases', {})
        
        self.populate_description_tab(info)
        self.populate_basic_info_tab(info)
        self.populate_classifiers_tab(info)
        self.populate_releases_tab(releases, info.get('version', ''))
    
    def populate_description_tab(self, info: dict):
        """Populate the description tab with proper markdown rendering."""
        # Set color for description tab
        self.desc_text.setStyleSheet("QTextEdit { color: #00FFFF; }")
        
        name = info.get('name', 'Unknown')
        version = info.get('version', 'Unknown')
        summary = info.get('summary', 'No description available')
        description = info.get('description', '').strip()
        
        # Create header
        content = f"""
        <div style='text-align: center; margin-bottom: 20px;'>
            <h1 style='color: #00FFFF; margin-bottom: 5px;'>📦 {name} {version}</h1>
            <p style='color: #AAAAFF; font-style: italic; font-size: 14px;'>{summary}</p>
        </div>
        """
        
        if description:
            content += "<hr style='border-color: #333333; margin: 20px 0;'>"
            content += "<h3 style='color: #AAAAFF; margin-bottom: 10px;'>📖 Description</h3>"
            
            # Check if description looks like markdown
            if self.is_markdown_content(description):
                # Try to render as markdown
                if MARKDOWN_AVAILABLE:
                    try:
                        # Convert markdown to HTML
                        # md = markdown.Markdown(extensions=['codehilite', 'fenced_code', 'tables'])
                        # html_desc = md.convert(description)  # Limit size
                        formatter = HtmlFormatter(style='fruity', noclasses=True)
                        # formatter = HtmlFormatter(style=AndromedaStyle, noclasses=True)
                        css = f"<style>{formatter.get_style_defs('.codehilite')}</style>"

                        md = markdown.Markdown(
                            extensions=['fenced_code', 'tables', 'codehilite'],
                            extension_configs={
                                'codehilite': {
                                    'guess_lang': True,
                                    'pygments_style': 'fruity',
                                    'noclasses': True
                                }
                            }
                        )
                        html_desc = md.convert(description)
                        content += css + html_desc
                        
                        # Apply custom styling to markdown elements
                        html_desc = self.style_markdown_html(html_desc)
                        content += f"<div style='color: #00FFFF; line-height: 1.4;'>{html_desc}</div>"
                        
                        # if len(description) > 3000:
                        #     content += "<p style='color: #888888; font-style: italic;'>... (content truncated)</p>"
                    except Exception as e:
                        # Fallback to plain text if markdown fails
                        content += self.format_plain_description(description)
                else:
                    # Markdown not available, format as plain text with some basic formatting
                    content += self.format_markdown_fallback(description)
            else:
                # Plain text description
                content += self.format_plain_description(description)
        
        self.desc_text.setHtml(content)
        return content
    
    def is_markdown_content(self, text: str) -> bool:
        """Check if content appears to be markdown."""
        markdown_indicators = [
            '# ', '## ', '### ',  # Headers
            '```', '`',           # Code blocks/inline code
            '* ', '- ', '+ ',     # Lists
            '[', '](',            # Links
            '**', '__',           # Bold
            '*', '_',             # Italic (but be careful with single chars)
            '|',                  # Tables
            '---', '===',         # Horizontal rules
        ]
        
        # Count markdown indicators
        indicator_count = sum(1 for indicator in markdown_indicators if indicator in text)
        
        # Also check for multiple line breaks (common in markdown)
        has_multiple_breaks = '\n\n' in text
        
        # Consider it markdown if it has multiple indicators or looks structured
        return indicator_count >= 3 or (indicator_count >= 1 and has_multiple_breaks)
    
    def style_markdown_html(self, html: str) -> str:
        """Apply custom CSS styling to markdown HTML elements."""
        # Replace default styling with our custom colors
        styling_replacements = [
            ('<h1>', '<h1 style="color: #00FFFF; margin: 15px 0 10px 0;">'),
            ('<h2>', '<h2 style="color: #00FFFF; margin: 12px 0 8px 0;">'),
            ('<h3>', '<h3 style="color: #AAAAFF; margin: 10px 0 6px 0;">'),
            ('<h4>', '<h4 style="color: #AAAAFF; margin: 8px 0 4px 0;">'),
            ('<h5>', '<h5 style="color: #AAAAFF; margin: 6px 0 3px 0;">'),
            ('<h6>', '<h6 style="color: #AAAAFF; margin: 4px 0 2px 0;">'),
            ('<p>', '<p style="color: #00FFFF; margin: 8px 0; line-height: 1.4;">'),
            ('<li>', '<li style="color: #00FFFF; margin: 2px 0;">'),
            # ('<code>', '<code style="background-color: #333333; color: #FFFF00; padding: 2px 4px; border-radius: 3px;">'),
            ('<code>', '<code style="background-color: #333333; color: #FFFF00; padding: 2px 4px; border-radius: 3px; white-space: pre-wrap; word-wrap: break-word;">'),
            # ('<pre>', '<pre style="background-color: #1a1a1a; color: #00FFFF; padding: 10px; border-radius: 5px; border: 1px solid #333333; overflow-x: auto;">'),
            ('<pre>', '<pre style="background-color: #1a1a1a; color: #00FFFF; padding: 10px; border-radius: 5px; border: 1px solid #333333; white-space: pre-wrap; word-wrap: break-word; overflow-x: hidden;">'),
            ('<blockquote>', '<blockquote style="border-left: 4px solid #0078AA; padding-left: 10px; margin: 10px 0; color: #AAAAFF; font-style: italic;">'),
            ('<a ', '<a style="color: #0078AA; text-decoration: underline;" '),
            ('<table>', '<table style="border-collapse: collapse; margin: 10px 0; color: #00FFFF;">'),
            ('<th>', '<th style="border: 1px solid #333333; padding: 8px; background-color: #333333; color: #FFFF00;">'),
            ('<td>', '<td style="border: 1px solid #333333; padding: 6px;">'),
            ('<hr>', '<hr style="border: none; border-top: 2px solid #333333; margin: 15px 0;">'),
        ]
        
        for old, new in styling_replacements:
            html = html.replace(old, new)
        
        return html
    
    def format_markdown_fallback(self, text: str) -> str:
        """Format markdown-like content without markdown library."""
        # lines = text[:2000].split('\n')  # Limit size
        lines = text.split('\n')  # Limit size
        formatted_lines = []
        
        for line in lines:
            line = line.strip()
            if not line:
                formatted_lines.append('<br>')
                continue
                
            # Headers
            if line.startswith('# '):
                formatted_lines.append(f'<h1 style="color: #00FFFF; margin: 15px 0 10px 0;">{line[2:]}</h1>')
            elif line.startswith('## '):
                formatted_lines.append(f'<h2 style="color: #00FFFF; margin: 12px 0 8px 0;">{line[3:]}</h2>')
            elif line.startswith('### '):
                formatted_lines.append(f'<h3 style="color: #AAAAFF; margin: 10px 0 6px 0;">{line[4:]}</h3>')
            # Code blocks
            elif line.startswith('```'):
                if line == '```':
                    formatted_lines.append('<pre style="background-color: #1a1a1a; color: #00FFFF; padding: 10px; border-radius: 5px;">')
                else:
                    formatted_lines.append('</pre>')
            # Lists
            elif line.startswith('* ') or line.startswith('- ') or line.startswith('+ '):
                formatted_lines.append(f'<li style="color: #00FFFF; margin: 2px 0;">{line[2:]}</li>')
            # Regular text
            else:
                # Handle inline code
                line = re.sub(r'`([^`]+)`', r'<code style="background-color: #333333; color: #FFFF00; padding: 2px 4px;">\1</code>', line)
                # Handle bold
                line = re.sub(r'\*\*([^*]+)\*\*', r'<strong style="color: #FFFF00;">\1</strong>', line)
                # Handle italic
                line = re.sub(r'\*([^*]+)\*', r'<em style="color: #AAAAFF;">\1</em>', line)
                
                formatted_lines.append(f'<p style="color: #00FFFF; margin: 4px 0; line-height: 1.4;">{line}</p>')
        
        result = '\n'.join(formatted_lines)
        # if len(text) > 2000:
        #     result += '<p style="color: #888888; font-style: italic;">... (content truncated)</p>'
            
        return f'<div>{result}</div>'
    
    def format_plain_description(self, text: str) -> str:
        """Format plain text description."""
        # Limit length and convert newlines to HTML
        # desc_text = text[:2000] if len(text) > 2000 else text
        # desc_text = text if len(text) > 2000 else text
        desc_text = text
        desc_html = desc_text.replace('\n', '<br>').replace('\r', '')
        
        # Add truncation notice if needed
        # if len(text) > 2000:
        #     desc_html += '<br><br><em style="color: #888888;">... (content truncated)</em>'
        
        return f'<div style="color: #00FFFF; line-height: 1.4; margin: 10px 0;">{desc_html}</div>'
    
    def populate_basic_info_tab(self, info: dict):
        """Populate the basic info and links tab."""
        # Basic info table
        basic_fields = [
            ("🏷️ Name", info.get('name', 'N/A')),
            ("🔢 Version", info.get('version', 'N/A')),
            ("👤 Author", info.get('author', 'N/A')),
            ("📧 Author Email", info.get('author_email', 'N/A')),
            ("🏠 Home Page", info.get('home_page', 'N/A')),
            ("🛠️ Maintainer", info.get('maintainer', 'N/A')),
            ("📨 Maintainer Email", info.get('maintainer_email', 'N/A')),
            ("📄 License", info.get('license', 'N/A')),
            ("🐍 Python Requires", info.get('requires_python', 'N/A')),
        ]
        
        valid_fields = [(prop, value) for prop, value in basic_fields if value and value != 'N/A']
        self.basic_info_table.setRowCount(len(valid_fields))
        
        for row, (prop, value) in enumerate(valid_fields):
            # Truncate long values
            # if len(str(value)) > 50:
            #     value = str(value)[:47] + "..."
            
            prop_item = QTableWidgetItem(prop)
            prop_item.setForeground(QColor(255, 255, 0))  # Yellow
            
            value_item = QTableWidgetItem(str(value))
            value_item.setForeground(QColor(0, 255, 255))  # Cyan
            
            self.basic_info_table.setItem(row, 0, prop_item)
            self.basic_info_table.setItem(row, 1, value_item)
        
        # Links table
        project_urls = info.get('project_urls', {})
        if project_urls:
            self.links_table.setRowCount(len(project_urls))
            
            for row, (url_type, url) in enumerate(project_urls.items()):
                if url:
                    type_item = QTableWidgetItem(f"🌐 {url_type}")
                    type_item.setForeground(QColor(170, 170, 255))  # Light blue
                    
                    # Truncate very long URLs
                    # display_url = url if len(url) <= 60 else url[:57] + "..."
                    display_url = url
                    url_item = QTableWidgetItem(display_url)
                    url_item.setForeground(QColor(170, 170, 255))  # Light blue
                    
                    self.links_table.setItem(row, 0, type_item)
                    self.links_table.setItem(row, 1, url_item)
        
        # Resize columns to content
        self.basic_info_table.resizeColumnsToContents()
        self.links_table.resizeColumnsToContents()
    
    def populate_classifiers_tab(self, info: dict):
        """Populate the classifiers tab."""
        # Set color for classifiers
        self.classifiers_tree.setStyleSheet("QTreeWidget { color: #FFAAFF; }")
        
        classifiers = info.get('classifiers', [])
        if not classifiers:
            root_item = QTreeWidgetItem(self.classifiers_tree)
            root_item.setText(0, "No classifiers found")
            root_item.setForeground(0, QColor(255, 170, 255))
            return
        
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
            category_item = QTreeWidgetItem(self.classifiers_tree)
            category_item.setText(0, f"📁 {category}")
            category_item.setForeground(0, QColor(255, 170, 255))
            category_item.setExpanded(True)
            
            # for item in items[:10]:  # Limit to 10 items per category
            for item in items:
                item_widget = QTreeWidgetItem(category_item)
                item_widget.setText(0, f"• {item}")
                item_widget.setForeground(0, QColor(255, 170, 255))
            
            # if len(items) > 10:
            #     more_item = QTreeWidgetItem(category_item)
            #     more_item.setText(0, f"... and {len(items) - 10} more")
            #     more_item.setForeground(0, QColor(128, 128, 128))
    
    def populate_releases_tab(self, releases: dict, latest_version: str):
        """Populate the releases tab."""
        # Set color for releases table
        self.releases_table.setStyleSheet("QTableWidget { color: #FFAA00; }")
        
        if not releases:
            return
        
        # Sort versions by upload time (newest first)
        version_data = []
        for version, files in releases.items():
            if files:
                upload_time = files[0].get('upload_time_iso_8601', '')
                total_size = sum(f.get('size', 0) for f in files)
                version_data.append((version, upload_time, len(files), total_size))
        
        # Sort by upload time (newest first) and take top 20
        version_data.sort(key=lambda x: x[1], reverse=True)
        # display_data = version_data[:20]
        display_data = version_data
        
        self.releases_table.setRowCount(len(display_data))
        
        for row, (version, upload_time, file_count, total_size) in enumerate(display_data):
            # Version
            version_item = QTableWidgetItem(version)
            if version == latest_version:
                version_item.setText(f"{version} (latest)")
                version_item.setForeground(QColor(255, 255, 0))  # Yellow for latest
            else:
                version_item.setForeground(QColor(255, 170, 0))  # Orange
            
            # Date
            date_display = self.format_date(upload_time) if upload_time else "Unknown"
            date_item = QTableWidgetItem(date_display)
            date_item.setForeground(QColor(255, 170, 0))  # Orange
            
            # Files count
            files_item = QTableWidgetItem(str(file_count))
            files_item.setForeground(QColor(255, 170, 0))  # Orange
            
            # Size
            size_display = self.format_size(total_size) if total_size > 0 else "Unknown"
            size_item = QTableWidgetItem(size_display)
            size_item.setForeground(QColor(255, 170, 0))  # Orange
            
            self.releases_table.setItem(row, 0, version_item)
            self.releases_table.setItem(row, 1, date_item)
            self.releases_table.setItem(row, 2, files_item)
            self.releases_table.setItem(row, 3, size_item)
        
        # Resize columns to content
        self.releases_table.resizeColumnsToContents()
    
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

def main(default_package="helpman"):
    """Main function to run the GUI application."""
    app = QApplication(sys.argv)

    # Set application properties
    app.setApplicationName("PyPI Info GUI")
    app.setApplicationVersion("1.0")
    app.setOrganizationName("PyPI Tools")

    # Create and show main window
    window = PyPIInfoGUI(default_package=default_package)
    window.show()

    # Run the application
    sys.exit(app.exec_())


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "helpman")
