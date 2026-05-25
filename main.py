"""main.py – PDF Library Manager entry point"""
import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

def main():
    # Enable high-DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("PDF 문헌 관리자")
    app.setApplicationVersion("1.0.0")

    # Import here to avoid circular imports
    from ui.main_window import MainWindow
    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
