


# main.py
import sys
from PySide6.QtWidgets import QApplication

# Đảm bảo bạn import đúng tên class MainWindow từ file app_main.py của bạn
from src.gui.app_main import AscetAgentMainWindow 

def main():
    app = QApplication(sys.argv)
    window = AscetAgentMainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()