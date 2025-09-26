import os
from PySide6.QtCore import Qt, QRect, QEvent, QPoint
from PySide6.QtGui import QGuiApplication, QIcon, QColor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QListWidget,
    QListWidgetItem, QDialog, QGraphicsDropShadowEffect, QAbstractItemView
)

from processor import ClipboardStore
from utils import resource_path
from config import Config

PRIMARY = "#4169e1"
HOVER   = "#7000e0"
TITLE   = "#ffffff"
CLOSEC  = "#FF0000"
MINC    = "#FFD600"
MAXC    = "#00C853"

RESIZE_MARGIN = 8

def _drop_shadow(widget):
    eff = QGraphicsDropShadowEffect(widget)
    eff.setBlurRadius(28)
    eff.setOffset(0, 3)
    eff.setColor(QColor(0, 0, 0, int(255 * 0.18)))
    widget.setGraphicsEffect(eff)
    return eff

def _build_qss(compact: bool) -> str:
    glass_grad = (
        "qlineargradient(x1:0,y1:0,x2:0,y2:1,"
        "stop:0 rgba(255,255,255,50), stop:0.5 rgba(200,220,255,25), stop:1 rgba(255,255,255,8))"
    )
    glass_bg = "none" if compact else glass_grad
    return f"""
        QWidget#bgRoot {{ background-color: rgba(255,255,255,0); border-radius:18px; }}
        QWidget#glassRoot {{
            background-color: rgba(5,5,51,200);
            border: 3px solid rgba(65,105,225,255);
            border-radius:16px;
            background-image: {glass_bg};
            background-repeat:no-repeat; background-position:0 0;
        }}
        QLabel#titleLabel {{ color:{TITLE}; font-weight:bold; }}
        QListWidget {{
            background: rgba(255,250,250,0.92); color:#000;
            border:1px solid #888; border-radius:6px;
        }}
        QPushButton {{ background:{PRIMARY}; color:#fff; border:none;
            border-radius:8px; padding:6px 10px; }}
        QPushButton:hover {{ background:{HOVER}; }}
        QPushButton#minBtn {{ background:transparent; color:{MINC}; border-radius:6px; }}
        QPushButton#maxBtn {{ background:transparent; color:{MAXC}; border-radius:6px; }}
        QPushButton#closeBtn {{ background:transparent; color:{CLOSEC}; border-radius:6px; }}
        QPushButton#minBtn:hover, QPushButton#maxBtn:hover, QPushButton#closeBtn:hover {{
            background: rgba(153,179,255,0.06);
        }}
        QTextBrowser#readmeText {{
            color:#fffafa; background:#333333; border-radius:10px; padding:8px;
        }}
    """

README_MD = r"""
# SuperCopy ©️2025 KisaragiIchigo

- クリップボードを監視して履歴を自動収集
- 履歴一覧のみでシンプル操作（複数選択→一括コピー）
- ボタンは **一括コピー** と **クリア** のみ
"""

class ReadmeDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("README ©️2025 KisaragiIchigo")
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.resize(850, 600)

        outer = QVBoxLayout(self); outer.setContentsMargins(0,0,0,0)
        bg = QWidget(); bg.setObjectName("bgRoot"); outer.addWidget(bg)
        cardLay = QVBoxLayout(bg); cardLay.setContentsMargins(10,10,10,10)
        card = QWidget(); card.setObjectName("glassRoot"); cardLay.addWidget(card)
        _drop_shadow(card)

        v = QVBoxLayout(card); v.setContentsMargins(16,16,16,16)

        bar = QHBoxLayout()
        title = QLabel("README ©️2025 KisaragiIchigo"); title.setObjectName("titleLabel")
        bar.addWidget(title); bar.addStretch(1)
        btn_close = QPushButton("x"); btn_close.setObjectName("closeBtn"); btn_close.setFixedSize(28,28)
        btn_close.clicked.connect(self.accept)
        bar.addWidget(btn_close)
        v.addLayout(bar)

        from PySide6.QtWidgets import QTextBrowser
        viewer = QTextBrowser(); viewer.setObjectName("readmeText")
        viewer.setMarkdown(README_MD); viewer.setOpenExternalLinks(True)
        v.addWidget(viewer, 1)

        self._moving=False; self._drag_offset=QPoint()
        for w in (bg, card): w.installEventFilter(self)
        self.setStyleSheet(_build_qss(compact=False))

    def eventFilter(self, obj, e):
        if e.type()==QEvent.MouseButtonPress and e.button()==Qt.LeftButton:
            self._moving=True; self._drag_offset = e.globalPosition().toPoint() - self.frameGeometry().topLeft(); return True
        if e.type()==QEvent.MouseMove and self._moving and (e.buttons() & Qt.LeftButton):
            self.move(e.globalPosition().toPoint() - self._drag_offset); return True
        if e.type()==QEvent.MouseButtonRelease:
            self._moving=False; return True
        return super().eventFilter(obj,e)

class SuperCopyWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SuperCopy ©️2025 KisaragiIchigo")
        self.resize(700, 300)
        self.setMinimumSize(50, 50)
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        ico = resource_path("supercopy.ico")
        if os.path.exists(ico): self.setWindowIcon(QIcon(ico))

        self.cfg = Config(app_name="SuperCopy")
        self.store = ClipboardStore()

        outer = QVBoxLayout(self); outer.setContentsMargins(0,0,0,0)
        self.bg = QWidget(); self.bg.setObjectName("bgRoot"); outer.addWidget(self.bg)
        bgLay = QVBoxLayout(self.bg); bgLay.setContentsMargins(10,10,10,10)

        self.card = QWidget(); self.card.setObjectName("glassRoot"); bgLay.addWidget(self.card)
        self.shadow = _drop_shadow(self.card)

        v = QVBoxLayout(self.card); v.setContentsMargins(16,16,16,16)

        # タイトルバー
        bar = QHBoxLayout()
        self.title = QLabel("SuperCopy"); self.title.setObjectName("titleLabel")

        self.btn_readme = QPushButton("ReadMe"); self.btn_readme.setFixedHeight(28)
        self.btn_readme.clicked.connect(self._open_readme)

        self.btn_min = QPushButton("_"); self.btn_min.setObjectName("minBtn"); self.btn_min.setFixedSize(28,28)
        self.btn_max = QPushButton("🗖"); self.btn_max.setObjectName("maxBtn"); self.btn_max.setFixedSize(28,28)
        self.btn_close = QPushButton("x"); self.btn_close.setObjectName("closeBtn"); self.btn_close.setFixedSize(28,28)

        self.btn_min.clicked.connect(self.showMinimized)
        self.btn_max.clicked.connect(self._toggle_max_restore)
        self.btn_close.clicked.connect(self.close)

        bar.addWidget(self.title)
        bar.addStretch(1)
        bar.addWidget(self.btn_readme)
        bar.addWidget(self.btn_min)
        bar.addWidget(self.btn_max)
        bar.addWidget(self.btn_close)
        v.addLayout(bar)

        # 履歴リスト（縦スクロール調整）
        self.history_list = QListWidget()
        self.history_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.history_list.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)         # ←スムーズ
        self.history_list.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)                # ←必要時のみ
        self.history_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)             # ←横スク非表示
        self.history_list.setUniformItemSizes(True)                                       # ←大量でも軽い
        v.addWidget(QLabel("履歴一覧"))
        v.addWidget(self.history_list, 1)  # 伸縮して高さを確保（スクロール有効）

        # ボタン行
        btn_row = QHBoxLayout()
        self.btn_copy = QPushButton("一括コピー")
        self.btn_clear = QPushButton("クリア")
        btn_row.addWidget(self.btn_copy); btn_row.addWidget(self.btn_clear)
        v.addLayout(btn_row)

        # イベント
        self.btn_copy.clicked.connect(self._copy_all)
        self.btn_clear.clicked.connect(self._clear_history)

        # クリップボード監視
        self.clip = QGuiApplication.clipboard()
        self.clip.dataChanged.connect(self._on_clip_changed)

        # ドラッグ移動＆リサイズ
        self._moving=False; self._drag_offset=QPoint()
        self.bg.installEventFilter(self)
        self.card.installEventFilter(self)

        # スタイル適用
        self._apply_compact(self.isMaximized())

        # 履歴復元
        for t in self.cfg.data.get("history", []):
            self.store.add(t)
            self.history_list.addItem(t)

    def _apply_compact(self, compact: bool):
        self.setStyleSheet(_build_qss(compact))
        if self.shadow: self.shadow.setEnabled(not compact)
        self.btn_max.setText("❏" if self.isMaximized() else "🗖")

    def changeEvent(self, e):
        if e.type()==QEvent.WindowStateChange:
            self._apply_compact(self.isMaximized())
        return super().changeEvent(e)

    def _toggle_max_restore(self):
        self.showNormal() if self.isMaximized() else self.showMaximized()
        self._apply_compact(self.isMaximized())

    def _open_readme(self):
        dlg = ReadmeDialog(self)
        dlg.move(self.frameGeometry().center() - dlg.rect().center())
        dlg.exec()

    def _on_clip_changed(self):
        txt = self.clip.text()
        if self.store.add(txt):
            self.history_list.addItem(QListWidgetItem(txt))

    def _copy_all(self):
        all_texts = [self.history_list.item(i).text() for i in range(self.history_list.count())]
        QGuiApplication.clipboard().setText("\n".join(all_texts))

    def _clear_history(self):
        self.store.clear()
        self.history_list.clear()

    # ===== ドラッグ移動＆リサイズ =====
    def eventFilter(self, obj, e):
        if obj in (self.bg, self.card):
            if e.type()==QEvent.MouseButtonPress and e.button()==Qt.LeftButton:
                pos = self.mapFromGlobal(e.globalPosition().toPoint())
                edges = self._hit_edges(pos)
                if edges:
                    self._resizing=True; self._resize_edges=edges
                    self._start_geo=self.geometry(); self._start_mouse=e.globalPosition().toPoint()
                else:
                    self._moving=True; self._drag_offset = e.globalPosition().toPoint() - self.frameGeometry().topLeft()
                return True
            if e.type()==QEvent.MouseMove:
                if getattr(self, "_resizing", False):
                    self._resize_to(e.globalPosition().toPoint()); return True
                if self._moving and (e.buttons() & Qt.LeftButton) and not self.isMaximized():
                    self.move(e.globalPosition().toPoint() - self._drag_offset); return True
                self._update_cursor(self._hit_edges(self.mapFromGlobal(e.globalPosition().toPoint())))
            if e.type()==QEvent.MouseButtonRelease:
                self._resizing=False; self._moving=False; return True
        return super().eventFilter(obj,e)

    def _hit_edges(self, pos):
        m=RESIZE_MARGIN; r=self.bg.rect(); edges=""
        if pos.y()<=m: edges+="T"
        if pos.y()>=r.height()-m: edges+="B"
        if pos.x()<=m: edges+="L"
        if pos.x()>=r.width()-m: edges+="R"
        return edges

    def _update_cursor(self, edges):
        if edges in ("TL","BR"): self.setCursor(Qt.SizeFDiagCursor)
        elif edges in ("TR","BL"): self.setCursor(Qt.SizeBDiagCursor)
        elif edges in ("L","R"): self.setCursor(Qt.SizeHorCursor)
        elif edges in ("T","B"): self.setCursor(Qt.SizeVerCursor)
        else: self.setCursor(Qt.ArrowCursor)

    def _resize_to(self, gpos):
        dx = gpos.x() - self._start_mouse.x()
        dy = gpos.y() - self._start_mouse.y()
        geo = self._start_geo; x,y,w,h = geo.x(),geo.y(),geo.width(),geo.height()
        minw, minh = self.minimumSize().width(), self.minimumSize().height()
        if "L" in self._resize_edges:
            new_w = max(minw, w - dx); x += (w - new_w); w = new_w
        if "R" in self._resize_edges:
            w = max(minw, w + dx)
        if "T" in self._resize_edges:
            new_h = max(minh, h - dy); y += (h - new_h); h = new_h
        if "B" in self._resize_edges:
            h = max(minh, h + dy)
        self.setGeometry(x,y,w,h)

    def closeEvent(self, e):
        self._save_history()
        return super().closeEvent(e)

    def _save_history(self):
        texts = [self.history_list.item(i).text() for i in range(self.history_list.count())]
        self.cfg.data["history"] = texts
        self.cfg.save()
