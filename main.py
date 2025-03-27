import sys

from PyQt5.QtWidgets import QApplication
from OCRApp import VideoOCRApp

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = VideoOCRApp()
    ex.show()
    sys.exit(app.exec_())