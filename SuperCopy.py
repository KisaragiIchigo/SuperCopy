import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont
from gui import SuperCopyWindow

def main():
    app = QApplication(sys.argv)
    app.setFont(QFont("メイリオ", 10))  
    w = SuperCopyWindow()
    w.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
