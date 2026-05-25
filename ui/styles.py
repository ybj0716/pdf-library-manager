DARK_STYLE = """
QMainWindow, QDialog {
    background-color: #1e1e2e;
    color: #cdd6f4;
}

QWidget {
    background-color: #1e1e2e;
    color: #cdd6f4;
    font-family: 'Segoe UI', Arial, sans-serif;
    font-size: 13px;
}

/* ── Sidebar ── */
#sidebar {
    background-color: #181825;
    border-right: 1px solid #313244;
    min-width: 180px;
    max-width: 240px;
}

/* ── Tree Widget ── */
QTreeWidget {
    background-color: #181825;
    border: none;
    color: #cdd6f4;
    padding: 4px;
}
QTreeWidget::item {
    padding: 6px 8px;
    border-radius: 6px;
}
QTreeWidget::item:selected {
    background-color: #313244;
    color: #89b4fa;
}
QTreeWidget::item:hover {
    background-color: #2a2a3e;
}
QTreeWidget::branch {
    background: transparent;
}

/* ── Table ── */
QTableWidget {
    background-color: #1e1e2e;
    alternate-background-color: #24243e;
    border: none;
    gridline-color: #313244;
    color: #cdd6f4;
    selection-background-color: #45475a;
}
QTableWidget::item {
    padding: 8px 12px;
    border: none;
}
QTableWidget::item:selected {
    background-color: #45475a;
    color: #cdd6f4;
}
QHeaderView::section {
    background-color: #181825;
    color: #89b4fa;
    padding: 8px 12px;
    border: none;
    border-bottom: 2px solid #313244;
    font-weight: bold;
    font-size: 12px;
}
QHeaderView::section:hover {
    background-color: #24243e;
}

/* ── Search Bar ── */
QLineEdit {
    background-color: #313244;
    border: 1px solid #45475a;
    border-radius: 8px;
    padding: 8px 14px;
    color: #cdd6f4;
    font-size: 13px;
}
QLineEdit:focus {
    border-color: #89b4fa;
}
QLineEdit::placeholder {
    color: #6c7086;
}

/* ── Buttons ── */
QPushButton {
    background-color: #313244;
    color: #cdd6f4;
    border: 1px solid #45475a;
    border-radius: 8px;
    padding: 8px 18px;
    font-size: 13px;
}
QPushButton:hover {
    background-color: #45475a;
    border-color: #89b4fa;
}
QPushButton:pressed {
    background-color: #585b70;
}
QPushButton#primaryBtn {
    background-color: #89b4fa;
    color: #1e1e2e;
    border: none;
    font-weight: bold;
}
QPushButton#primaryBtn:hover {
    background-color: #b4befe;
}
QPushButton#dangerBtn {
    background-color: #f38ba8;
    color: #1e1e2e;
    border: none;
    font-weight: bold;
}
QPushButton#dangerBtn:hover {
    background-color: #eba0ac;
}

/* ── Toolbar ── */
QToolBar {
    background-color: #181825;
    border-bottom: 1px solid #313244;
    spacing: 8px;
    padding: 6px 12px;
}
QToolButton {
    background-color: transparent;
    color: #cdd6f4;
    border: none;
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 13px;
}
QToolButton:hover {
    background-color: #313244;
}

/* ── Status Bar ── */
QStatusBar {
    background-color: #181825;
    color: #a6adc8;
    border-top: 1px solid #313244;
    font-size: 12px;
    padding: 4px 12px;
}

/* ── Scroll Bars ── */
QScrollBar:vertical {
    background: #181825;
    width: 8px;
    border-radius: 4px;
}
QScrollBar::handle:vertical {
    background: #45475a;
    border-radius: 4px;
    min-height: 20px;
}
QScrollBar::handle:vertical:hover {
    background: #585b70;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar:horizontal {
    background: #181825;
    height: 8px;
    border-radius: 4px;
}
QScrollBar::handle:horizontal {
    background: #45475a;
    border-radius: 4px;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }

/* ── Detail Panel ── */
#detailPanel {
    background-color: #181825;
    border-left: 1px solid #313244;
}
#detailTitle {
    font-size: 15px;
    font-weight: bold;
    color: #cdd6f4;
    padding: 8px 4px;
}
#detailLabel {
    color: #89b4fa;
    font-size: 12px;
    font-weight: bold;
}
#detailValue {
    color: #cdd6f4;
    font-size: 12px;
}
QTextEdit {
    background-color: #24243e;
    border: 1px solid #313244;
    border-radius: 8px;
    color: #cdd6f4;
    padding: 8px;
    font-size: 12px;
}

/* ── Drop Zone ── */
#dropZone {
    background-color: #24243e;
    border: 2px dashed #45475a;
    border-radius: 12px;
    color: #6c7086;
    font-size: 14px;
}
#dropZone[drag=true] {
    border-color: #89b4fa;
    background-color: #2a2a4e;
    color: #89b4fa;
}

/* ── ComboBox ── */
QComboBox {
    background-color: #313244;
    border: 1px solid #45475a;
    border-radius: 8px;
    padding: 6px 12px;
    color: #cdd6f4;
    min-width: 120px;
}
QComboBox:hover { border-color: #89b4fa; }
QComboBox QAbstractItemView {
    background-color: #313244;
    color: #cdd6f4;
    selection-background-color: #45475a;
    border: 1px solid #45475a;
    border-radius: 4px;
}
QComboBox::drop-down {
    border: none;
    padding-right: 8px;
}

/* ── Labels ── */
QLabel#sectionHeader {
    color: #6c7086;
    font-size: 11px;
    font-weight: bold;
    padding: 8px 8px 4px 8px;
    letter-spacing: 1px;
}

/* ── Progress ── */
QProgressBar {
    background-color: #313244;
    border-radius: 6px;
    height: 8px;
    text-align: center;
    color: transparent;
}
QProgressBar::chunk {
    background-color: #89b4fa;
    border-radius: 6px;
}

/* ── Tab Widget ── */
QTabWidget::pane {
    background-color: #1e1e2e;
    border: 1px solid #313244;
    border-radius: 8px;
}
QTabBar::tab {
    background-color: #181825;
    color: #6c7086;
    padding: 8px 18px;
    border: none;
    border-radius: 6px 6px 0 0;
    margin-right: 2px;
}
QTabBar::tab:selected {
    background-color: #313244;
    color: #89b4fa;
    font-weight: bold;
}

/* ── Splitter ── */
QSplitter::handle {
    background-color: #313244;
}
QSplitter::handle:horizontal { width: 1px; }
QSplitter::handle:vertical { height: 1px; }

/* ── Group Box ── */
QGroupBox {
    border: 1px solid #313244;
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 8px;
    color: #89b4fa;
    font-weight: bold;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 6px;
    left: 12px;
}

/* ── Checkboxes ── */
QCheckBox {
    color: #cdd6f4;
    spacing: 8px;
}
QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border-radius: 4px;
    border: 1px solid #45475a;
    background-color: #313244;
}
QCheckBox::indicator:checked {
    background-color: #89b4fa;
    border-color: #89b4fa;
}

/* ── Tooltip ── */
QToolTip {
    background-color: #313244;
    color: #cdd6f4;
    border: 1px solid #45475a;
    border-radius: 6px;
    padding: 6px;
}
"""
