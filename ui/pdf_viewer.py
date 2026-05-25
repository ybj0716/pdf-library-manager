"""pdf_viewer.py – Built-in PDF viewer with highlight and note annotations"""
import os
import fitz  # PyMuPDF
from PyQt6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QScrollArea,
    QLabel, QPushButton, QToolBar, QSizePolicy, QLineEdit,
    QTextEdit, QSplitter, QFrame, QListWidget, QListWidgetItem,
    QInputDialog, QMessageBox, QToolButton, QButtonGroup,
    QSpinBox, QComboBox, QApplication
)
from PyQt6.QtCore import Qt, QPoint, QRect, QSize, pyqtSignal, QTimer
from PyQt6.QtGui import (
    QPainter, QPen, QBrush, QColor, QPixmap, QImage,
    QCursor, QIcon, QFont, QPalette
)

# ── 상수 ──────────────────────────────────────────────────────────────────────

HIGHLIGHT_COLORS = {
    "🟡 노랑": (1.0, 1.0, 0.0),
    "🟢 초록": (0.2, 1.0, 0.4),
    "🔵 파랑": (0.4, 0.7, 1.0),
    "🩷 분홍": (1.0, 0.4, 0.7),
}

HIGHLIGHT_QT_COLORS = {
    "🟡 노랑": QColor(255, 255, 0, 100),
    "🟢 초록": QColor(50, 255, 100, 100),
    "🔵 파랑": QColor(100, 180, 255, 100),
    "🩷 분홍": QColor(255, 100, 180, 100),
}

class Tool:
    HIGHLIGHT = "highlight"
    NOTE      = "note"
    ERASE     = "erase"
    PAN       = "pan"


# ── 페이지 위젯 ───────────────────────────────────────────────────────────────

class PageWidget(QWidget):
    """PDF 한 페이지를 렌더링하고 형광펜/메모 도구를 처리하는 위젯"""

    note_requested    = pyqtSignal(int, float, float)   # page_idx, pdf_x, pdf_y
    annotation_added  = pyqtSignal()                     # 형광펜/지우개 완료 후

    def __init__(self, page: fitz.Page, page_idx: int, zoom: float = 1.5):
        super().__init__()
        self.fitz_page  = page
        self.page_idx   = page_idx
        self.zoom       = zoom
        self.tool       = Tool.HIGHLIGHT
        self.hl_color   = "🟡 노랑"
        self.pixmap     = None

        self._sel_start: QPoint | None = None
        self._sel_end:   QPoint | None = None
        self._selecting  = False

        self.setMouseTracking(True)
        self._render()

    # ── 렌더링 ────────────────────────────────────────────────────────────────

    def _render(self):
        mat = fitz.Matrix(self.zoom, self.zoom)
        pix = self.fitz_page.get_pixmap(matrix=mat, alpha=False)
        img = QImage(pix.samples, pix.width, pix.height,
                     pix.stride, QImage.Format.Format_RGB888)
        self.pixmap = QPixmap.fromImage(img)
        self.setFixedSize(self.pixmap.size())
        self.update()

    def set_zoom(self, zoom: float):
        self.zoom = zoom
        self._render()

    # ── 페인트 ────────────────────────────────────────────────────────────────

    def paintEvent(self, event):
        p = QPainter(self)
        if self.pixmap:
            p.drawPixmap(0, 0, self.pixmap)

        # 선택 중 미리보기 사각형
        if self._selecting and self._sel_start and self._sel_end:
            rect = QRect(self._sel_start, self._sel_end).normalized()
            if self.tool == Tool.HIGHLIGHT:
                color = HIGHLIGHT_QT_COLORS.get(self.hl_color, QColor(255, 255, 0, 100))
                p.setPen(QPen(color.darker(150), 1))
                p.setBrush(QBrush(color))
            elif self.tool == Tool.ERASE:
                p.setPen(QPen(QColor(255, 80, 80, 200), 1, Qt.PenStyle.DashLine))
                p.setBrush(QBrush(QColor(255, 80, 80, 40)))
            p.drawRect(rect)

    # ── 마우스 이벤트 ─────────────────────────────────────────────────────────

    def mousePressEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            return
        pos = event.position().toPoint()
        if self.tool == Tool.NOTE:
            px, py = pos.x() / self.zoom, pos.y() / self.zoom
            self.note_requested.emit(self.page_idx, px, py)
        else:
            self._sel_start = pos
            self._sel_end   = pos
            self._selecting = True

    def mouseMoveEvent(self, event):
        if self._selecting:
            self._sel_end = event.position().toPoint()
            self.update()

        # 커서 모양
        if self.tool == Tool.HIGHLIGHT:
            self.setCursor(Qt.CursorShape.IBeamCursor)
        elif self.tool == Tool.NOTE:
            self.setCursor(Qt.CursorShape.PointingHandCursor)
        elif self.tool == Tool.ERASE:
            self.setCursor(Qt.CursorShape.CrossCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)

    def mouseReleaseEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton or not self._selecting:
            return
        self._sel_end   = event.position().toPoint()
        self._selecting = False
        self.update()

        if self.tool == Tool.HIGHLIGHT:
            self._apply_highlight()
        elif self.tool == Tool.ERASE:
            self._erase_in_selection()

    # ── 형광펜 적용 ───────────────────────────────────────────────────────────

    def _apply_highlight(self):
        if not self._sel_start or not self._sel_end:
            return
        r = QRect(self._sel_start, self._sel_end).normalized()
        if r.width() < 5 or r.height() < 5:
            return

        x0, y0 = r.left() / self.zoom, r.top() / self.zoom
        x1, y1 = r.right() / self.zoom, r.bottom() / self.zoom
        clip = fitz.Rect(x0, y0, x1, y1)

        words = self.fitz_page.get_text("words", clip=clip)
        if not words:
            return

        quads = [fitz.Rect(w[:4]).quad for w in words]
        annot = self.fitz_page.add_highlight_annot(quads)
        color = HIGHLIGHT_COLORS.get(self.hl_color, (1.0, 1.0, 0.0))
        annot.set_colors(stroke=color)
        annot.update()

        self._render()
        self.annotation_added.emit()

    # ── 지우개 ────────────────────────────────────────────────────────────────

    def _erase_in_selection(self):
        if not self._sel_start or not self._sel_end:
            return
        r = QRect(self._sel_start, self._sel_end).normalized()
        x0, y0 = r.left() / self.zoom, r.top() / self.zoom
        x1, y1 = r.right() / self.zoom, r.bottom() / self.zoom
        erase_rect = fitz.Rect(x0, y0, x1, y1)

        to_delete = [a for a in self.fitz_page.annots()
                     if fitz.Rect(a.rect).intersects(erase_rect)]
        for a in to_delete:
            self.fitz_page.delete_annot(a)

        if to_delete:
            self._render()
            self.annotation_added.emit()


# ── 썸네일 위젯 ───────────────────────────────────────────────────────────────

class ThumbnailItem(QLabel):
    clicked_page = pyqtSignal(int)

    def __init__(self, page: fitz.Page, page_idx: int):
        super().__init__()
        self.page_idx = page_idx
        mat = fitz.Matrix(0.2, 0.2)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        img = QImage(pix.samples, pix.width, pix.height,
                     pix.stride, QImage.Format.Format_RGB888)
        self.setPixmap(QPixmap.fromImage(img).scaled(
            120, 160, Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation))
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("""
            QLabel { border: 2px solid #45475a; border-radius: 4px;
                     padding: 4px; background: #24243e; color: #cdd6f4; }
            QLabel:hover { border-color: #89b4fa; }
        """)
        self.setToolTip(f"페이지 {page_idx + 1}")

    def mousePressEvent(self, event):
        self.clicked_page.emit(self.page_idx)

    def set_active(self, active: bool):
        color = "#89b4fa" if active else "#45475a"
        self.setStyleSheet(f"""
            QLabel {{ border: 2px solid {color}; border-radius: 4px;
                      padding: 4px; background: #24243e; color: #cdd6f4; }}
        """)


# ── 메모 패널 ─────────────────────────────────────────────────────────────────

class NotePanel(QWidget):
    def __init__(self):
        super().__init__()
        self.setMaximumWidth(220)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        header = QLabel("📝 메모 목록")
        header.setStyleSheet("color: #89b4fa; font-weight: bold; font-size: 13px;")
        layout.addWidget(header)

        self.note_list = QListWidget()
        self.note_list.setStyleSheet("""
            QListWidget { background: #181825; border: none; color: #cdd6f4; }
            QListWidget::item { padding: 8px; border-bottom: 1px solid #313244;
                                border-radius: 4px; }
            QListWidget::item:selected { background: #313244; }
        """)
        self.note_list.setWordWrap(True)
        layout.addWidget(self.note_list)

    def add_note(self, page_idx: int, text: str):
        item = QListWidgetItem(f"p.{page_idx + 1}  {text}")
        item.setData(Qt.ItemDataRole.UserRole, page_idx)
        self.note_list.addItem(item)

    def clear_notes(self):
        self.note_list.clear()

    def load_from_doc(self, doc: fitz.Document):
        """PDF의 기존 텍스트 주석을 불러옴"""
        self.clear_notes()
        for i, page in enumerate(doc):
            for annot in page.annots(types=[fitz.PDF_ANNOT_TEXT]):
                text = annot.info.get("content", "")
                if text:
                    self.add_note(i, text)


# ── 메인 뷰어 ─────────────────────────────────────────────────────────────────

class PDFViewer(QDialog):
    def __init__(self, filepath: str, title: str = "", parent=None):
        super().__init__(parent)
        self.filepath   = filepath
        self.doc        = fitz.open(filepath)
        self.total_pages = len(self.doc)
        self.current_page = 0
        self.zoom       = 1.5
        self.tool       = Tool.HIGHLIGHT
        self.hl_color   = "🟡 노랑"
        self._modified  = False
        self._pages: list[PageWidget] = []

        self.setWindowTitle(f"📄 {title or os.path.basename(filepath)}")
        self.resize(1100, 800)
        self._build_ui()
        self._load_pages()

    # ── UI 구성 ───────────────────────────────────────────────────────────────

    def _build_ui(self):
        self.setStyleSheet("""
            QDialog { background-color: #1e1e2e; color: #cdd6f4; }
            QWidget { background-color: #1e1e2e; color: #cdd6f4; }
            QPushButton {
                background: #313244; color: #cdd6f4;
                border: 1px solid #45475a; border-radius: 6px;
                padding: 6px 14px; font-size: 13px;
            }
            QPushButton:hover { background: #45475a; border-color: #89b4fa; }
            QPushButton:checked { background: #89b4fa; color: #1e1e2e;
                                  border-color: #89b4fa; font-weight: bold; }
            QToolBar { background: #181825; border-bottom: 1px solid #313244;
                       spacing: 6px; padding: 6px 10px; }
            QLabel#pageLabel { color: #a6adc8; font-size: 13px; }
            QScrollArea { border: none; }
            QComboBox { background: #313244; border: 1px solid #45475a;
                        border-radius: 6px; padding: 4px 10px; color: #cdd6f4; }
            QSpinBox  { background: #313244; border: 1px solid #45475a;
                        border-radius: 6px; padding: 4px 8px; color: #cdd6f4; }
            QSplitter::handle { background: #313244; }
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ── 툴바 ──────────────────────────────────────────────────────────────
        toolbar = QWidget()
        toolbar.setStyleSheet("background: #181825; border-bottom: 1px solid #313244;")
        tbl = QHBoxLayout(toolbar)
        tbl.setContentsMargins(12, 8, 12, 8)
        tbl.setSpacing(8)

        # 도구 버튼
        self.btn_highlight = QPushButton("🖊 형광펜")
        self.btn_highlight.setCheckable(True)
        self.btn_highlight.setChecked(True)
        self.btn_note      = QPushButton("📌 메모")
        self.btn_note.setCheckable(True)
        self.btn_erase     = QPushButton("🧹 지우개")
        self.btn_erase.setCheckable(True)

        tool_group = QButtonGroup(self)
        tool_group.setExclusive(True)
        for btn in (self.btn_highlight, self.btn_note, self.btn_erase):
            tool_group.addButton(btn)
            tbl.addWidget(btn)

        self.btn_highlight.clicked.connect(lambda: self._set_tool(Tool.HIGHLIGHT))
        self.btn_note.clicked.connect(lambda: self._set_tool(Tool.NOTE))
        self.btn_erase.clicked.connect(lambda: self._set_tool(Tool.ERASE))

        # 색상 선택
        sep1 = QFrame(); sep1.setFrameShape(QFrame.Shape.VLine)
        sep1.setStyleSheet("color: #313244;")
        tbl.addWidget(sep1)

        color_lbl = QLabel("색상:")
        color_lbl.setStyleSheet("color: #a6adc8;")
        tbl.addWidget(color_lbl)

        self.color_combo = QComboBox()
        for name in HIGHLIGHT_COLORS:
            self.color_combo.addItem(name)
        self.color_combo.currentTextChanged.connect(self._set_color)
        tbl.addWidget(self.color_combo)

        tbl.addStretch()

        # 저장 버튼
        save_btn = QPushButton("💾 저장")
        save_btn.setStyleSheet("""
            QPushButton { background: #89b4fa; color: #1e1e2e;
                          border: none; font-weight: bold;
                          border-radius: 6px; padding: 6px 18px; }
            QPushButton:hover { background: #b4befe; }
        """)
        save_btn.clicked.connect(self._save)
        tbl.addWidget(save_btn)

        # 줌
        sep2 = QFrame(); sep2.setFrameShape(QFrame.Shape.VLine)
        sep2.setStyleSheet("color: #313244;")
        tbl.addWidget(sep2)

        zoom_out = QPushButton("🔍−")
        zoom_out.setFixedWidth(40)
        zoom_out.clicked.connect(self._zoom_out)
        self.zoom_lbl = QLabel("150%")
        self.zoom_lbl.setStyleSheet("color: #a6adc8; min-width: 40px;")
        self.zoom_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        zoom_in = QPushButton("🔍+")
        zoom_in.setFixedWidth(40)
        zoom_in.clicked.connect(self._zoom_in)
        tbl.addWidget(zoom_out)
        tbl.addWidget(self.zoom_lbl)
        tbl.addWidget(zoom_in)

        main_layout.addWidget(toolbar)

        # ── 본문 영역 ─────────────────────────────────────────────────────────
        body_splitter = QSplitter(Qt.Orientation.Horizontal)

        # 왼쪽: 썸네일
        self.thumb_area = QScrollArea()
        self.thumb_area.setWidgetResizable(True)
        self.thumb_area.setFixedWidth(140)
        self.thumb_area.setStyleSheet("background: #181825; border: none;")
        thumb_container = QWidget()
        self.thumb_layout = QVBoxLayout(thumb_container)
        self.thumb_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.thumb_layout.setSpacing(6)
        self.thumb_layout.setContentsMargins(8, 8, 8, 8)
        self.thumb_area.setWidget(thumb_container)
        body_splitter.addWidget(self.thumb_area)

        # 가운데: 페이지 스크롤
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("background: #2a2a3e; border: none;")
        scroll_content = QWidget()
        scroll_content.setStyleSheet("background: #2a2a3e;")
        self.pages_layout = QVBoxLayout(scroll_content)
        self.pages_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
        self.pages_layout.setSpacing(16)
        self.pages_layout.setContentsMargins(24, 24, 24, 24)
        self.scroll.setWidget(scroll_content)
        body_splitter.addWidget(self.scroll)

        # 오른쪽: 메모 패널
        self.note_panel = NotePanel()
        body_splitter.addWidget(self.note_panel)

        body_splitter.setStretchFactor(0, 0)
        body_splitter.setStretchFactor(1, 1)
        body_splitter.setStretchFactor(2, 0)
        main_layout.addWidget(body_splitter)

        # ── 하단 네비게이션 ───────────────────────────────────────────────────
        nav_bar = QWidget()
        nav_bar.setStyleSheet("background: #181825; border-top: 1px solid #313244;")
        nav_layout = QHBoxLayout(nav_bar)
        nav_layout.setContentsMargins(16, 8, 16, 8)

        prev_btn = QPushButton("◀ 이전")
        prev_btn.clicked.connect(self._prev_page)
        self.page_spin = QSpinBox()
        self.page_spin.setMinimum(1)
        self.page_spin.setMaximum(self.total_pages)
        self.page_spin.valueChanged.connect(self._go_to_page)
        self.total_lbl = QLabel(f"/ {self.total_pages} 페이지")
        self.total_lbl.setObjectName("pageLabel")
        next_btn = QPushButton("다음 ▶")
        next_btn.clicked.connect(self._next_page)

        nav_layout.addStretch()
        nav_layout.addWidget(prev_btn)
        nav_layout.addWidget(self.page_spin)
        nav_layout.addWidget(self.total_lbl)
        nav_layout.addWidget(next_btn)
        nav_layout.addStretch()
        main_layout.addWidget(nav_bar)

    # ── 페이지 로드 ───────────────────────────────────────────────────────────

    def _load_pages(self):
        self._thumbs: list[ThumbnailItem] = []
        self._pages = []

        for i in range(self.total_pages):
            fitz_page = self.doc[i]

            # 썸네일
            thumb = ThumbnailItem(fitz_page, i)
            thumb.clicked_page.connect(self._go_to_page_idx)
            self.thumb_layout.addWidget(thumb)
            self._thumbs.append(thumb)

            # 페이지 위젯
            pw = PageWidget(fitz_page, i, self.zoom)
            pw.tool     = self.tool
            pw.hl_color = self.hl_color
            pw.note_requested.connect(self._on_note_requested)
            pw.annotation_added.connect(self._on_annotation_added)
            self.pages_layout.addWidget(pw)
            self._pages.append(pw)

            # 페이지 번호 라벨
            lbl = QLabel(f"— {i + 1} —")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet("color: #585b70; font-size: 11px;")
            self.pages_layout.addWidget(lbl)

        # 기존 메모 불러오기
        self.note_panel.load_from_doc(self.doc)

        if self._thumbs:
            self._thumbs[0].set_active(True)

    # ── 도구 / 색상 ───────────────────────────────────────────────────────────

    def _set_tool(self, tool: str):
        self.tool = tool
        for pw in self._pages:
            pw.tool = tool

    def _set_color(self, color: str):
        self.hl_color = color
        for pw in self._pages:
            pw.hl_color = color

    # ── 메모 ─────────────────────────────────────────────────────────────────

    def _on_note_requested(self, page_idx: int, pdf_x: float, pdf_y: float):
        text, ok = QInputDialog.getMultiLineText(
            self, "메모 추가", f"페이지 {page_idx + 1}에 메모를 입력하세요:")
        if ok and text.strip():
            point = fitz.Point(pdf_x, pdf_y)
            annot = self.doc[page_idx].add_text_annot(point, text.strip())
            annot.update()
            self.note_panel.add_note(page_idx, text.strip())
            self._pages[page_idx]._render()
            self._modified = True

    def _on_annotation_added(self):
        self._modified = True

    # ── 저장 ─────────────────────────────────────────────────────────────────

    def _save(self):
        try:
            self.doc.save(self.filepath, incremental=True,
                          encryption=fitz.PDF_ENCRYPT_KEEP)
            self._modified = False
            QMessageBox.information(self, "저장 완료",
                                    "형광펜과 메모가 PDF에 저장되었습니다.")
        except Exception as e:
            # incremental save 실패 시 새 파일로 저장
            try:
                tmp = self.filepath + ".tmp"
                self.doc.save(tmp)
                import shutil
                shutil.move(tmp, self.filepath)
                self._modified = False
                QMessageBox.information(self, "저장 완료",
                                        "형광펜과 메모가 PDF에 저장되었습니다.")
            except Exception as e2:
                QMessageBox.warning(self, "저장 실패", str(e2))

    # ── 줌 ───────────────────────────────────────────────────────────────────

    def _zoom_in(self):
        levels = [0.75, 1.0, 1.25, 1.5, 1.75, 2.0, 2.5, 3.0]
        idx = min(range(len(levels)), key=lambda i: abs(levels[i] - self.zoom))
        if idx < len(levels) - 1:
            self._set_zoom(levels[idx + 1])

    def _zoom_out(self):
        levels = [0.75, 1.0, 1.25, 1.5, 1.75, 2.0, 2.5, 3.0]
        idx = min(range(len(levels)), key=lambda i: abs(levels[i] - self.zoom))
        if idx > 0:
            self._set_zoom(levels[idx - 1])

    def _set_zoom(self, zoom: float):
        self.zoom = zoom
        self.zoom_lbl.setText(f"{int(zoom * 100)}%")
        for pw in self._pages:
            pw.set_zoom(zoom)

    # ── 페이지 이동 ───────────────────────────────────────────────────────────

    def _go_to_page(self, page_num: int):
        self._go_to_page_idx(page_num - 1)

    def _go_to_page_idx(self, idx: int):
        if idx < 0 or idx >= self.total_pages:
            return
        if self._thumbs:
            self._thumbs[self.current_page].set_active(False)
            self._thumbs[idx].set_active(True)
        self.current_page = idx
        self.page_spin.blockSignals(True)
        self.page_spin.setValue(idx + 1)
        self.page_spin.blockSignals(False)

        # 해당 페이지로 스크롤
        if idx < len(self._pages):
            pw = self._pages[idx]
            self.scroll.ensureWidgetVisible(pw, 0, 50)

    def _prev_page(self):
        if self.current_page > 0:
            self._go_to_page_idx(self.current_page - 1)

    def _next_page(self):
        if self.current_page < self.total_pages - 1:
            self._go_to_page_idx(self.current_page + 1)

    # ── 닫기 ─────────────────────────────────────────────────────────────────

    def closeEvent(self, event):
        if self._modified:
            reply = QMessageBox.question(
                self, "저장하지 않은 변경사항",
                "형광펜/메모가 저장되지 않았습니다. 저장하고 닫을까요?",
                QMessageBox.StandardButton.Save |
                QMessageBox.StandardButton.Discard |
                QMessageBox.StandardButton.Cancel
            )
            if reply == QMessageBox.StandardButton.Save:
                self._save()
                event.accept()
            elif reply == QMessageBox.StandardButton.Discard:
                event.accept()
            else:
                event.ignore()
                return
        self.doc.close()
        event.accept()
