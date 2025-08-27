# from gui_qt5 import PyPIInfoGUI
# from PyQt5.QtWidgets import QApplication
# import sys

# app = QApplication(sys.argv)
# win = PyPIInfoGUI(default_package="flask")
# win.show()
# sys.exit(app.exec_())

from gui_qt5 import main

# Jalankan GUI dengan default package berbeda
main(default_package="requests")
