"""main_window.py – PDF Library Manager main window"""
import os
import json
import subprocess
import sys
from pathlib import Path
from typing import Optional, List

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QLabel, QPushButton, QLineEdit, QTreeWidget, QTreeWidgetItem,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QStatusBar, QToolBar, QTextEdit, QScrollArea, QFrame,
    QMessageBox, QFileDialog, QProgressBar, QDialog, QApplication,
    QSystemTrayIcon, QMenu
)
from PyQt6.QtCore import (
    Qt, QThread, pyqtSignal, QMimeData, QTimer, QSize, QPoint
)
from PyQt6.QtGui import (
    QIcon, QAction, QDragEnterEvent, QDropEvent, QFont, QColor,
    QPalette, QPixmap, QCursor
)

from ui.styles import DARK_STYLE
from ui.settings_dialog import SettingsDialog
from core import database as db
from core.pdf_processor import extract_doi_and_title
from core.metadata_fetcher import fetch_metadata
from core.classifier import classify_paper, suggest_tags
from core.folder_watcher import FolderWatcher


# ── Worker Thread ──────────────────────────────────────────────────────────────

class PDFWorker(QThread):
    progress = pyqtSignal(str)        # status message
    finished = pyqtSignal(dict)       # metadata dict
    error = pyqtSignal(str)           # error message

    def __init__(self, pdf_path: str, rules: dict = None):
        super().__init__()
        self.pdf_path = pdf_path
        self.rules = rules or {}

    def run(self):
        path = self.pdf_path
        name = Path(path).name

        self.progress.emit(f"📄 {name} — DOI/제목 추출 중...")
        doi, title = extract_doi_and_title(path)

        self.progress.emit(f"🔍 {name} — 외부 DB 조회 중 (CrossRef / Semantic Scholar)...")
        metadata = fetch_metadata(doi, title)

        if metadata:
            metadata['filepath'] = path
            metadata['filename'] = name
            metadata.setdefault('tags', ', '.join(suggest_tags(metadata)))
            metadata['category'] = classify_paper(metadata, self.rules)
        else:
            metadata = {
                'filepath': path,
                'filename': name,
                'title': title or Path(path).stem,
                'authors': '',
                'year': None,
                'journal': '',
                'doi': doi or '',
                'abstract': '',
                'keywords': '',
                'tags': '',
                'category': '미분류',
                'metadata_source': '직접 입력 필요',
            }
            self.progress.emit(f"⚠️ {name} — 메타데이터를 찾지 못했습니다.")

        self.finished.emit(metadata)


# ── Drop Zone ──────────────────────────────────────────────────────────────────

class DropZone(QLabel):
    files_dropped = pyqtSignal(list)

    def __init__(self):
        super().__init__()
        self.setObjectName("dropZone")
        self.setText("📂  PDF 파일을 여기에 드래그 & 드롭\n또는 아래 버튼으로 추가")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumHeight(90)
        self.setAcceptDrops(True)
        self._set_normal()

    def _set_normal(self):
        self.setProperty("drag", "false")
        self.setStyleSheet("""
            background-color: #24243e;
            border: 2px dashed #45475a;
            border-radius: 12px;
            color: #6c7086;
            font-size: 14px;
        """)

    def _set_active(self):
        self.setStyleSheet("""
            background-color: #1e2a4e;
            border: 2px dashed #89b4fa;
            border-radius: 12px;
            color: #89b4fa;
            font-size: 14px;
        """)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            pdfs = [u.toLocalFile() for u in event.mimeData().urls()
                    if u.toLocalFile().lower().endswith('.pdf')]
            if pdfs:
                event.acceptProposedAction()
                self._set_active()
                return
        event.ignore()

    def dragLeaveEvent(self, event):
        self._set_normal()

    def dropEvent(self, event: QDropEvent):
        self._set_normal()
        pdfs = [u.toLocalFile() for u in event.mimeData().urls()
                if u.toLocalFile().lower().endswith('.pdf')]
        if pdfs:
            self.files_dropped.emit(pdfs)


# ── Detail Panel ──────────────────────────────────────────────────────────────

class DetailPanel(QWidget):
    tag_edited = pyqtSignal(int, str)
    notes_edited = pyqtSignal(int, str)

    def __init__(self):
        super().__init__()
        self.setObjectName("detailPanel")
        self._paper_id: Optional[int] = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget()
        cl = QVBoxLayout(content)
        cl.setSpacing(10)
        cl.setContentsMargins(0, 0, 8, 0)

        # Title
        self.lbl_title = QLabel("문헌을 선택하세요")
        self.lbl_title.setObjectName("detailTitle")
        self.lbl_title.setWordWrap(True)
        cl.addWidget(self.lbl_title)

        # Meta fields
        self.fields_widget = QWidget()
        fl = QVBoxLayout(self.fields_widget)
        fl.setSpacing(6)
        fl.setContentsMargins(0, 0, 0, 0)
        self.meta_labels: dict = {}
        for key, display in [
            ('authors', '👤 저자'),
            ('year', '📅 연도'),
            ('journal', '📰 저널'),
            ('doi', '🔗 DOI'),
            ('category', '🗂️ 분류'),
            ('metadata_source', '🌐 출처'),
        ]:
            row = QHBoxLayout()
            lbl = QLabel(display)
            lbl.setObjectName("detailLabel")
            lbl.setFixedWidth(100)
            val = QLabel("—")
            val.setObjectName("detailValue")
            val.setWordWrap(True)
            val.setTextInteractionFlags(
                Qt.TextInteractionFlag.TextSelectableByMouse |
                Qt.TextInteractionFlag.LinksAccessibleByMouse
            )
            row.addWidget(lbl)
            row.addWidget(val, 1)
            fl.addLayout(row)
            self.meta_labels[key] = val
        cl.addWidget(self.fields_widget)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("background-color: #313244; height: 1px;")
        cl.addWidget(sep)

        # Tags
        tag_lbl = QLabel("🏷️ 태그")
        tag_lbl.setObjectName("detailLabel")
        cl.addWidget(tag_lbl)
        self.tag_edit = QLineEdit()
        self.tag_edit.setPlaceholderText("쉼표로 구분 (예: NVH, FEM, tire)")
        self.tag_edit.editingFinished.connect(self._on_tag_edited)
        cl.addWidget(self.tag_edit)

        # Abstract
        abs_lbl = QLabel("📋 초록")
        abs_lbl.setObjectName("detailLabel")
        cl.addWidget(abs_lbl)
        self.abstract_edit = QTextEdit()
        self.abstract_edit.setReadOnly(True)
        self.abstract_edit.setMaximumHeight(160)
        cl.addWidget(self.abstract_edit)

        # Keywords
        kw_lbl = QLabel("🔑 키워드")
        kw_lbl.setObjectName("detailLabel")
        cl.addWidget(kw_lbl)
        self.kw_label = QLabel("—")
        self.kw_label.setObjectName("detailValue")
        self.kw_label.setWordWrap(True)
        cl.addWidget(self.kw_label)

        cl.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)

        # Action buttons
        btn_row = QHBoxLayout()
        self.viewer_btn = QPushButton("📖 뷰어로 열기")
        self.viewer_btn.setObjectName("primaryBtn")
        self.viewer_btn.clicked.connect(self._open_in_viewer)
        self.viewer_btn.setEnabled(False)
        self.open_btn = QPushButton("📂 폴더 열기")
        self.open_btn.clicked.connect(self._open_file)
        self.open_btn.setEnabled(False)
        btn_row.addWidget(self.viewer_btn)
        btn_row.addWidget(self.open_btn)
        layout.addLayout(btn_row)

    def show_paper(self, paper: dict):
        self._paper_id = paper.get('id')
        self.lbl_title.setText(paper.get('title') or paper.get('filename') or '제목 없음')

        for key, lbl in self.meta_labels.items():
            val = paper.get(key)
            lbl.setText(str(val) if val else '—')

        self.tag_edit.setText(paper.get('tags') or '')
        self.abstract_edit.setPlainText(paper.get('abstract') or '초록 없음')
        self.kw_label.setText(paper.get('keywords') or '—')
        exists = bool(paper.get('filepath') and Path(paper['filepath']).exists())
        self.open_btn.setEnabled(exists)
        self.viewer_btn.setEnabled(exists)
        self._filepath = paper.get('filepath', '')

    def clear(self):
        self._paper_id = None
        self.lbl_title.setText("문헌을 선택하세요")
        for lbl in self.meta_labels.values():
            lbl.setText('—')
        self.tag_edit.clear()
        self.abstract_edit.clear()
        self.kw_label.setText('—')
        self.open_btn.setEnabled(False)
        self.viewer_btn.setEnabled(False)
        self._filepath = ''

    def _on_tag_edited(self):
        if self._paper_id is not None:
            self.tag_edited.emit(self._paper_id, self.tag_edit.text())

    def _open_in_viewer(self):
        if hasattr(self, '_filepath') and self._filepath:
            from ui.pdf_viewer import PDFViewer
            title = self.lbl_title.text()
            viewer = PDFViewer(self._filepath, title, parent=self)
            viewer.exec()

    def _open_file(self):
        if hasattr(self, '_filepath') and self._filepath:
            p = Path(self._filepath)
            if p.exists():
                folder = str(p.parent)
                if sys.platform == 'win32':
                    os.startfile(folder)
                else:
                    subprocess.Popen(['xdg-open', folder])


# ── Main Window ───────────────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("📚 PDF 문헌 관리자")
        self.resize(1280, 800)
        self.setAcceptDrops(True)

        db.init_db()
        self._workers: List[PDFWorker] = []
        self._current_papers: List[dict] = []
        self._processing_queue: List[str] = []

        self._watcher = FolderWatcher(self._on_new_pdf_detected)
        self._build_ui()
        self._build_tray()
        self._refresh_sidebar()
        self._refresh_table()
        self._start_watcher_if_configured()

    # ── UI Build ──────────────────────────────────────────────────────────────

    def _build_ui(self):
        self.setStyleSheet(DARK_STYLE)
        self._build_toolbar()

        # Central layout
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Drop zone + toolbar row
        top_bar = QWidget()
        top_bar.setStyleSheet("background-color: #181825; border-bottom: 1px solid #313244;")
        tbl = QHBoxLayout(top_bar)
        tbl.setContentsMargins(16, 10, 16, 10)
        tbl.setSpacing(12)

        self.drop_zone = DropZone()
        self.drop_zone.files_dropped.connect(self._handle_dropped_files)
        tbl.addWidget(self.drop_zone, 2)

        right_btns = QVBoxLayout()
        add_btn = QPushButton("➕  PDF 추가")
        add_btn.setObjectName("primaryBtn")
        add_btn.setFixedHeight(36)
        add_btn.clicked.connect(self._browse_pdf)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setVisible(False)
        self.progress_bar.setFixedHeight(6)

        self.progress_lbl = QLabel("")
        self.progress_lbl.setStyleSheet("color: #89b4fa; font-size: 11px;")
        self.progress_lbl.setVisible(False)

        right_btns.addWidget(add_btn)
        right_btns.addWidget(self.progress_bar)
        right_btns.addWidget(self.progress_lbl)
        tbl.addLayout(right_btns)
        main_layout.addWidget(top_bar)

        # Main splitter: sidebar | table+detail
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.main_splitter.setHandleWidth(1)

        # ── Left Sidebar ──
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setMinimumWidth(160)
        sidebar.setMaximumWidth(240)
        sl = QVBoxLayout(sidebar)
        sl.setContentsMargins(0, 0, 0, 0)
        sl.setSpacing(0)

        # Search
        search_widget = QWidget()
        search_widget.setStyleSheet("padding: 10px 10px 6px 10px;")
        swl = QVBoxLayout(search_widget)
        swl.setContentsMargins(0, 0, 0, 0)
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("🔍 검색...")
        self.search_edit.textChanged.connect(self._on_search)
        swl.addWidget(self.search_edit)
        sl.addWidget(search_widget)

        # Tree
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setIndentation(14)
        self.tree.itemClicked.connect(self._on_tree_clicked)
        sl.addWidget(self.tree)

        self.main_splitter.addWidget(sidebar)

        # ── Right Area ──
        right_area = QWidget()
        rl = QVBoxLayout(right_area)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(0)

        # Table + detail splitter
        self.right_splitter = QSplitter(Qt.Orientation.Horizontal)

        # Paper table
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["제목", "저자", "연도", "저널", "분류", "태그"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(2, 60)
        hh.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setSortingEnabled(True)
        self.table.itemSelectionChanged.connect(self._on_row_selected)
        self.table.itemDoubleClicked.connect(self._on_row_double_clicked)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._on_table_context_menu)

        # Detail panel
        self.detail = DetailPanel()
        self.detail.setMinimumWidth(260)
        self.detail.setMaximumWidth(380)
        self.detail.tag_edited.connect(self._on_tag_saved)

        self.right_splitter.addWidget(self.table)
        self.right_splitter.addWidget(self.detail)
        self.right_splitter.setStretchFactor(0, 3)
        self.right_splitter.setStretchFactor(1, 1)

        rl.addWidget(self.right_splitter)
        self.main_splitter.addWidget(right_area)
        self.main_splitter.setStretchFactor(0, 0)
        self.main_splitter.setStretchFactor(1, 1)

        main_layout.addWidget(self.main_splitter)

        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self._watcher_lbl = QLabel("⚫ 감시 비활성")
        self._watcher_lbl.setStyleSheet("color: #6c7086;")
        self.status_bar.addPermanentWidget(self._watcher_lbl)
        self.status_bar.showMessage("준비")

    def _build_toolbar(self):
        tb = QToolBar("Main")
        tb.setMovable(False)
        tb.setIconSize(QSize(18, 18))
        self.addToolBar(tb)

        refresh_action = QAction("🔄 새로고침", self)
        refresh_action.triggered.connect(self._refresh_table)
        tb.addAction(refresh_action)

        tb.addSeparator()

        settings_action = QAction("⚙️ 설정", self)
        settings_action.triggered.connect(self._open_settings)
        tb.addAction(settings_action)

        tb.addSeparator()

        stats_action = QAction("📊 통계", self)
        stats_action.triggered.connect(self._show_stats)
        tb.addAction(stats_action)

    def _build_tray(self):
        self.tray = QSystemTrayIcon(self)
        # Simple colored icon
        pix = QPixmap(16, 16)
        pix.fill(QColor("#89b4fa"))
        self.tray.setIcon(QIcon(pix))
        self.tray.setToolTip("PDF 문헌 관리자")

        tray_menu = QMenu()
        show_action = QAction("창 열기", self)
        show_action.triggered.connect(self.show)
        quit_action = QAction("종료", self)
        quit_action.triggered.connect(QApplication.quit)
        tray_menu.addAction(show_action)
        tray_menu.addSeparator()
        tray_menu.addAction(quit_action)
        self.tray.setContextMenu(tray_menu)
        self.tray.activated.connect(self._on_tray_activated)
        self.tray.show()

    # ── Data Methods ──────────────────────────────────────────────────────────

    def _get_rules(self) -> dict:
        try:
            return json.loads(db.get_setting('classification_rules', '{}'))
        except Exception:
            return {}

    def _refresh_sidebar(self):
        self.tree.clear()

        # All
        all_item = QTreeWidgetItem(["📚  전체 문헌"])
        all_item.setData(0, Qt.ItemDataRole.UserRole, ('all', ''))
        self.tree.addTopLevelItem(all_item)

        # Categories
        cats = db.get_categories()
        if cats:
            cat_root = QTreeWidgetItem(["🗂️  분류"])
            cat_root.setData(0, Qt.ItemDataRole.UserRole, ('all', ''))
            for cat in cats:
                child = QTreeWidgetItem([f"  {cat}"])
                child.setData(0, Qt.ItemDataRole.UserRole, ('category', cat))
                cat_root.addChild(child)
            cat_root.setExpanded(True)
            self.tree.addTopLevelItem(cat_root)

        # Tags
        tags = db.get_all_tags()
        if tags:
            tag_root = QTreeWidgetItem(["🏷️  태그"])
            tag_root.setData(0, Qt.ItemDataRole.UserRole, ('all', ''))
            for tag in tags[:30]:
                child = QTreeWidgetItem([f"  {tag}"])
                child.setData(0, Qt.ItemDataRole.UserRole, ('tag', tag))
                tag_root.addChild(child)
            tag_root.setExpanded(False)
            self.tree.addTopLevelItem(tag_root)

        self.tree.topLevelItem(0).setSelected(True)

    def _refresh_table(self, category: str = "", tag: str = ""):
        search = self.search_edit.text()
        papers = db.get_all_papers(search=search, category=category, tag=tag)
        self._current_papers = papers

        self.table.setSortingEnabled(False)
        self.table.setRowCount(0)
        for paper in papers:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setRowHeight(row, 36)

            title_item = QTableWidgetItem(paper.get('title') or paper.get('filename') or '')
            title_item.setData(Qt.ItemDataRole.UserRole, paper.get('id'))
            self.table.setItem(row, 0, title_item)
            self.table.setItem(row, 1, QTableWidgetItem(
                (paper.get('authors') or '')[:50]))
            year_val = paper.get('year')
            self.table.setItem(row, 2, QTableWidgetItem(
                str(year_val) if year_val else ''))
            self.table.setItem(row, 3, QTableWidgetItem(
                (paper.get('journal') or '')[:40]))
            self.table.setItem(row, 4, QTableWidgetItem(
                (paper.get('category') or '')))
            self.table.setItem(row, 5, QTableWidgetItem(
                (paper.get('tags') or '')))

        self.table.setSortingEnabled(True)
        stats = db.get_stats()
        self.status_bar.showMessage(
            f"총 {stats['total']}개 문헌 | 메타데이터 보유: {stats['with_metadata']}개"
        )

    # ── PDF Processing ────────────────────────────────────────────────────────

    def _browse_pdf(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, "PDF 파일 선택", "", "PDF 파일 (*.pdf);;모든 파일 (*)"
        )
        if paths:
            self._process_pdfs(paths)

    def _handle_dropped_files(self, paths: list):
        self._process_pdfs(paths)

    def _on_new_pdf_detected(self, path: str):
        """Called from watcher thread — schedule on main thread."""
        QTimer.singleShot(0, lambda: self._process_pdfs([path]))

    def _process_pdfs(self, paths: list):
        self._processing_queue.extend(paths)
        if not self.progress_bar.isVisible():
            self._process_next()

    def _process_next(self):
        if not self._processing_queue:
            self.progress_bar.setVisible(False)
            self.progress_lbl.setVisible(False)
            self._refresh_sidebar()
            self._refresh_table()
            return

        path = self._processing_queue.pop(0)
        self.progress_bar.setVisible(True)
        self.progress_lbl.setVisible(True)

        worker = PDFWorker(path, self._get_rules())
        worker.progress.connect(self._on_worker_progress)
        worker.finished.connect(self._on_worker_finished)
        worker.error.connect(self._on_worker_error)
        self._workers.append(worker)
        worker.start()

    def _on_worker_progress(self, msg: str):
        self.progress_lbl.setText(msg)
        self.progress_lbl.setVisible(True)

    def _on_worker_finished(self, metadata: dict):
        db.add_paper(metadata)
        remaining = len(self._processing_queue)
        if remaining == 0:
            self.progress_lbl.setText(f"✅ 완료: {metadata.get('title') or metadata.get('filename')}")
        else:
            self.progress_lbl.setText(f"남은 파일: {remaining}개")
        QTimer.singleShot(500, self._process_next)

    def _on_worker_error(self, msg: str):
        self.status_bar.showMessage(f"오류: {msg}", 5000)
        QTimer.singleShot(500, self._process_next)

    # ── Interactions ──────────────────────────────────────────────────────────

    def _on_search(self, text: str):
        self._refresh_table()

    def _on_tree_clicked(self, item: QTreeWidgetItem, col: int):
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            self._refresh_table()
            return
        kind, value = data
        if kind == 'category':
            self._refresh_table(category=value)
        elif kind == 'tag':
            self._refresh_table(tag=value)
        else:
            self._refresh_table()

    def _on_row_double_clicked(self, item):
        row = self.table.currentRow()
        if row < 0:
            return
        paper_id = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        paper = db.get_paper(paper_id)
        if paper and paper.get('filepath') and Path(paper['filepath']).exists():
            self._open_viewer(paper)

    def _open_viewer(self, paper: dict):
        from ui.pdf_viewer import PDFViewer
        viewer = PDFViewer(paper['filepath'],
                           paper.get('title') or paper.get('filename', ''),
                           parent=self)
        viewer.exec()

    def _on_row_selected(self):
        rows = self.table.selectedItems()
        if not rows:
            self.detail.clear()
            return
        row = self.table.currentRow()
        paper_id = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        if paper_id is None:
            return
        paper = db.get_paper(paper_id)
        if paper:
            self.detail.show_paper(paper)

    def _on_tag_saved(self, paper_id: int, tags: str):
        db.update_paper(paper_id, {'tags': tags})
        self._refresh_table()
        self._refresh_sidebar()

    def _on_table_context_menu(self, pos: QPoint):
        row = self.table.rowAt(pos.y())
        if row < 0:
            return
        paper_id = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        menu = QMenu(self)
        view_action   = menu.addAction("📖 뷰어로 열기")
        open_action   = menu.addAction("📂 폴더 열기")
        refetch_action = menu.addAction("🔄 메타데이터 다시 가져오기")
        menu.addSeparator()
        delete_action = menu.addAction("🗑️ 삭제")

        action = menu.exec(self.table.viewport().mapToGlobal(pos))
        if action == view_action:
            paper = db.get_paper(paper_id)
            if paper and Path(paper.get('filepath','')).exists():
                self._open_viewer(paper)
        elif action == delete_action:
            reply = QMessageBox.question(
                self, "삭제 확인", "이 문헌을 라이브러리에서 삭제할까요?\n(파일은 삭제되지 않습니다)",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                db.delete_paper(paper_id)
                self.detail.clear()
                self._refresh_table()
                self._refresh_sidebar()
        elif action == open_action:
            paper = db.get_paper(paper_id)
            if paper:
                p = Path(paper['filepath'])
                if p.exists():
                    folder = str(p.parent)
                    if sys.platform == 'win32':
                        os.startfile(folder)
                    else:
                        subprocess.Popen(['xdg-open', folder])
        elif action == refetch_action:
            paper = db.get_paper(paper_id)
            if paper:
                self._process_pdfs([paper['filepath']])

    # ── Settings & Watcher ────────────────────────────────────────────────────

    def _open_settings(self):
        dlg = SettingsDialog(self)
        if dlg.exec():
            self._start_watcher_if_configured()
            self._refresh_table()

    def _start_watcher_if_configured(self):
        watch_path = db.get_setting('watch_path', '')
        if watch_path and Path(watch_path).exists():
            ok = self._watcher.start(watch_path)
            if ok:
                self._watcher_lbl.setText(f"🟢 감시 중: {watch_path}")
                self._watcher_lbl.setStyleSheet("color: #a6e3a1;")
            else:
                self._watcher_lbl.setText("⚠️ 감시 시작 실패 (watchdog 필요)")
                self._watcher_lbl.setStyleSheet("color: #fab387;")
        else:
            self._watcher.stop()
            self._watcher_lbl.setText("⚫ 감시 비활성")
            self._watcher_lbl.setStyleSheet("color: #6c7086;")

    # ── Stats ─────────────────────────────────────────────────────────────────

    def _show_stats(self):
        stats = db.get_stats()
        cats = db.get_categories()
        tags = db.get_all_tags()
        msg = (
            f"📚 총 문헌 수: {stats['total']}개\n"
            f"✅ 메타데이터 보유: {stats['with_metadata']}개\n"
            f"🗂️ 분류 수: {len(cats)}개\n"
            f"🏷️ 태그 수: {len(tags)}개\n"
        )
        QMessageBox.information(self, "라이브러리 통계", msg)

    # ── Tray & Close ──────────────────────────────────────────────────────────

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show()
            self.activateWindow()

    def closeEvent(self, event):
        # Minimize to tray instead of closing
        event.ignore()
        self.hide()
        self.tray.showMessage(
            "PDF 관리자", "백그라운드에서 계속 실행됩니다.",
            QSystemTrayIcon.MessageIcon.Information, 2000
        )

    # ── Drag & Drop on main window ────────────────────────────────────────────

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            pdfs = [u.toLocalFile() for u in event.mimeData().urls()
                    if u.toLocalFile().lower().endswith('.pdf')]
            if pdfs:
                event.acceptProposedAction()
                return
        event.ignore()

    def dropEvent(self, event: QDropEvent):
        pdfs = [u.toLocalFile() for u in event.mimeData().urls()
                if u.toLocalFile().lower().endswith('.pdf')]
        if pdfs:
            self._handle_dropped_files(pdfs)
