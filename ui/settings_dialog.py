"""settings_dialog.py"""
import json
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel,
    QCheckBox, QLineEdit, QPushButton, QFileDialog, QTableWidget,
    QTableWidgetItem, QHeaderView, QMessageBox, QWidget
)
from PyQt6.QtCore import Qt
from core import database as db


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("설정")
        self.setMinimumSize(560, 520)
        self._build_ui()
        self._load_settings()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(20, 20, 20, 20)

        # ── Watch Folder ──────────────────────────────────────────────────────
        watch_group = QGroupBox("📂  자동 감시 폴더")
        wl = QVBoxLayout(watch_group)
        row = QHBoxLayout()
        self.watch_path_edit = QLineEdit()
        self.watch_path_edit.setPlaceholderText("감시할 폴더 경로...")
        browse_btn = QPushButton("찾아보기")
        browse_btn.clicked.connect(self._browse_watch)
        row.addWidget(self.watch_path_edit)
        row.addWidget(browse_btn)
        wl.addLayout(row)
        layout.addWidget(watch_group)

        # ── Classification Rules ──────────────────────────────────────────────
        cls_group = QGroupBox("🏷️  분류 기준")
        cl = QVBoxLayout(cls_group)
        self.chk_year = QCheckBox("연도별 분류")
        self.chk_journal = QCheckBox("저널/학술지별 분류")
        self.chk_keywords = QCheckBox("키워드별 분류")
        cl.addWidget(self.chk_year)
        cl.addWidget(self.chk_journal)
        cl.addWidget(self.chk_keywords)
        layout.addWidget(cls_group)

        # ── Custom Rules ──────────────────────────────────────────────────────
        custom_group = QGroupBox("⚙️  커스텀 키워드 → 카테고리 규칙")
        cul = QVBoxLayout(custom_group)

        self.rules_table = QTableWidget(0, 2)
        self.rules_table.setHorizontalHeaderLabels(["키워드 (포함 시)", "분류 카테고리"])
        self.rules_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.rules_table.setMaximumHeight(160)
        cul.addWidget(self.rules_table)

        btn_row = QHBoxLayout()
        add_rule_btn = QPushButton("+ 규칙 추가")
        add_rule_btn.clicked.connect(self._add_rule_row)
        del_rule_btn = QPushButton("선택 삭제")
        del_rule_btn.setObjectName("dangerBtn")
        del_rule_btn.clicked.connect(self._del_rule_row)
        btn_row.addWidget(add_rule_btn)
        btn_row.addWidget(del_rule_btn)
        btn_row.addStretch()
        cul.addLayout(btn_row)
        layout.addWidget(custom_group)

        layout.addStretch()

        # ── Buttons ───────────────────────────────────────────────────────────
        btns = QHBoxLayout()
        btns.addStretch()
        cancel_btn = QPushButton("취소")
        cancel_btn.clicked.connect(self.reject)
        save_btn = QPushButton("저장")
        save_btn.setObjectName("primaryBtn")
        save_btn.clicked.connect(self._save)
        btns.addWidget(cancel_btn)
        btns.addWidget(save_btn)
        layout.addLayout(btns)

    def _browse_watch(self):
        path = QFileDialog.getExistingDirectory(self, "감시 폴더 선택")
        if path:
            self.watch_path_edit.setText(path)

    def _add_rule_row(self):
        row = self.rules_table.rowCount()
        self.rules_table.insertRow(row)
        self.rules_table.setItem(row, 0, QTableWidgetItem(""))
        self.rules_table.setItem(row, 1, QTableWidgetItem(""))

    def _del_rule_row(self):
        rows = set(i.row() for i in self.rules_table.selectedItems())
        for row in sorted(rows, reverse=True):
            self.rules_table.removeRow(row)

    def _load_settings(self):
        self.watch_path_edit.setText(db.get_setting('watch_path', ''))

        rules_json = db.get_setting('classification_rules', '{}')
        try:
            rules = json.loads(rules_json)
        except Exception:
            rules = {}

        self.chk_year.setChecked(rules.get('use_year', True))
        self.chk_journal.setChecked(rules.get('use_journal', True))
        self.chk_keywords.setChecked(rules.get('use_keywords', False))

        for r in rules.get('custom_rules', []):
            row = self.rules_table.rowCount()
            self.rules_table.insertRow(row)
            self.rules_table.setItem(row, 0, QTableWidgetItem(r.get('keyword', '')))
            self.rules_table.setItem(row, 1, QTableWidgetItem(r.get('category', '')))

    def _save(self):
        db.set_setting('watch_path', self.watch_path_edit.text().strip())

        custom_rules = []
        for i in range(self.rules_table.rowCount()):
            kw_item = self.rules_table.item(i, 0)
            cat_item = self.rules_table.item(i, 1)
            kw = kw_item.text().strip() if kw_item else ''
            cat = cat_item.text().strip() if cat_item else ''
            if kw and cat:
                custom_rules.append({'keyword': kw, 'category': cat})

        rules = {
            'use_year': self.chk_year.isChecked(),
            'use_journal': self.chk_journal.isChecked(),
            'use_keywords': self.chk_keywords.isChecked(),
            'custom_rules': custom_rules,
        }
        db.set_setting('classification_rules', json.dumps(rules, ensure_ascii=False))
        self.accept()

    def get_watch_path(self) -> str:
        return self.watch_path_edit.text().strip()
