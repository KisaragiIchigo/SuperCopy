import os
from PySide6.QtCore import Qt, QRect, QEvent, QPoint
from PySide6.QtGui import QGuiApplication, QIcon, QColor # 説明: QMouseEventはインポートしない(GUISample準拠)
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
        /* 説明: タイトルバーのフォントサイズをルールに合わせて小さく */
        QLabel#titleLabel {{ color:{TITLE}; font-weight:bold; font-size: 8pt; }}
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
        /* 説明: READMEダイアログ内のテキストエリア用スタイル */
        QTextBrowser#readmeText {{
            color:#fffafa; background:#333333; border-radius:10px; padding:8px;
        }}
        /* 説明: READMEダイアログの内部カード用スタイル(ルール準拠) */
        QWidget#textPanel {{
             background-color:#333333; 
             border-radius:10px;
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
        # 説明: ルール通り、最小/最大化ボタンは非表示
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint) 
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.resize(850, 600) # 説明: ルール通りの初期サイズ

        outer = QVBoxLayout(self); outer.setContentsMargins(0,0,0,0)
        bg = QWidget(); bg.setObjectName("bgRoot"); outer.addWidget(bg)
        cardLay = QVBoxLayout(bg); cardLay.setContentsMargins(10,10,10,10)
        card = QWidget(); card.setObjectName("glassRoot"); cardLay.addWidget(card)
        _drop_shadow(card)

        v = QVBoxLayout(card); v.setContentsMargins(16,16,16,16)

        # --- タイトルバー ---
        bar = QHBoxLayout()
        title = QLabel("README ©️2025 KisaragiIchigo"); title.setObjectName("titleLabel")
        bar.addWidget(title); bar.addStretch(1)
        # 説明: 閉じるボタンのみ配置
        btn_close = QPushButton("x"); btn_close.setObjectName("closeBtn"); btn_close.setFixedSize(28,28)
        btn_close.clicked.connect(self.accept)
        bar.addWidget(btn_close)
        v.addLayout(bar)

        # --- テキスト表示エリア ---
        # 説明: ルール準拠のため、内部カード(textPanel)を追加
        text_panel = QWidget(); text_panel.setObjectName("textPanel")
        v.addWidget(text_panel, 1)
        
        text_layout = QVBoxLayout(text_panel); text_layout.setContentsMargins(8,8,8,8)
        from PySide6.QtWidgets import QTextBrowser
        viewer = QTextBrowser(); viewer.setObjectName("readmeText")
        viewer.setMarkdown(README_MD); viewer.setOpenExternalLinks(True)
        text_layout.addWidget(viewer, 1) # 説明: viewerをtext_panelに入れる

        # --- ドラッグ移動 ---
        self._moving=False; self._drag_offset=QPoint()
        # 説明: bgとcardをドラッグ移動の対象にする
        for w in (bg, card, title): w.installEventFilter(self)
        self.setStyleSheet(_build_qss(compact=False))

    def eventFilter(self, obj, e):
        # 説明: ダイアログのドラッグ移動処理
        # ★修正: e.type() をチェックしてから globalPosition を呼ぶ
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
        self.setMinimumSize(50, 50) # 説明: ルール通りの最小サイズ
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        ico = resource_path("supercopy.ico")
        if os.path.exists(ico): self.setWindowIcon(QIcon(ico))

        # 説明: Configは起動時に読み込むけど、履歴の復元はしない
        self.cfg = Config(app_name="SuperCopy") 
        self.store = ClipboardStore()

        outer = QVBoxLayout(self); outer.setContentsMargins(0,0,0,0)
        self.bg = QWidget(); self.bg.setObjectName("bgRoot"); outer.addWidget(self.bg)
        bgLay = QVBoxLayout(self.bg); bgLay.setContentsMargins(10,10,10,10) # 説明: 角丸と影のためのマージン

        self.card = QWidget(); self.card.setObjectName("glassRoot"); bgLay.addWidget(self.card)
        self.shadow = _drop_shadow(self.card)

        v = QVBoxLayout(self.card); v.setContentsMargins(16,16,16,16) # 説明: カード内部のパディング

        # --- タイトルバー ---
        bar = QHBoxLayout()
        self.title = QLabel("SuperCopy"); self.title.setObjectName("titleLabel")

        # 説明: ReadMeボタンをルール通り最小化ボタンの左に配置
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
        bar.addWidget(self.btn_readme) # 説明: ボタン配置順の変更
        bar.addWidget(self.btn_min)
        bar.addWidget(self.btn_max)
        bar.addWidget(self.btn_close)
        v.addLayout(bar)

        # --- 履歴リスト ---
        self.history_list = QListWidget()
        self.history_list.setSelectionMode(QAbstractItemView.ExtendedSelection) # 説明: 複数選択モード
        self.history_list.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.history_list.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.history_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.history_list.setUniformItemSizes(True)
        v.addWidget(QLabel("履歴一覧"))
        v.addWidget(self.history_list, 1)

        # --- ボタン行 ---
        btn_row = QHBoxLayout()
        self.btn_copy = QPushButton("一括コピー")
        self.btn_clear = QPushButton("クリア")
        btn_row.addWidget(self.btn_copy); btn_row.addWidget(self.btn_clear)
        v.addLayout(btn_row)

        # --- イベント接続 ---
        self.btn_copy.clicked.connect(self._copy_all)
        self.btn_clear.clicked.connect(self._clear_history)

        # --- クリップボード監視 ---
        self.clip = QGuiApplication.clipboard()
        self.clip.dataChanged.connect(self._on_clip_changed)

        # --- ドラッグ移動＆リサイズ ---
        self._moving=False; self._drag_offset=QPoint()
        self.bg.installEventFilter(self)
        # 説明: cardもドラッグ移動の対象に追加（タイトルバー部分など）
        self.card.installEventFilter(self)
        self.title.installEventFilter(self) # 説明: タイトルラベルでもドラッグできるように

        # --- スタイル適用 ---
        self._apply_compact(self.isMaximized())

        # 説明: ★履歴復元処理は削除 (起動時は常に空)

    def _apply_compact(self, compact: bool):
        # 説明: 最大化/復元時にスタイルを切り替える
        self.setStyleSheet(_build_qss(compact))
        if self.shadow: self.shadow.setEnabled(not compact) # 説明: 最大化時は影をOFF
        self.btn_max.setText("❏" if self.isMaximized() else "🗖") # 説明: ボタンアイコン切り替え

    def changeEvent(self, e):
        # 説明: ウィンドウ状態の変化（最大化など）を検知
        if e.type()==QEvent.WindowStateChange:
            # self.window_state = self.windowState() # この行は特に使ってないのでコメントアウト
            self._apply_compact(self.isMaximized())
        return super().changeEvent(e)

    def _toggle_max_restore(self):
        # 説明: 最大化/復元をトグル
        self.showNormal() if self.isMaximized() else self.showMaximized()
        # 説明: トグル直後に状態を再適用
        self._apply_compact(self.isMaximized())

    def _open_readme(self):
        dlg = ReadmeDialog(self)
        dlg.move(self.frameGeometry().center() - dlg.rect().center()) # 説明: 親ウィンドウの中央に表示
        dlg.exec()

    def _on_clip_changed(self):
        txt = self.clip.text()
        if self.store.add(txt): # 説明: 重複チェックはstore側
            self.history_list.addItem(QListWidgetItem(txt))

    def _copy_all(self):
        # 説明: ★選択状態にかかわらず、常に全件コピー
        texts_to_copy = [self.history_list.item(i).text() for i in range(self.history_list.count())]
            
        if texts_to_copy:
            # 説明: 対象のテキストを改行で連結してクリップボードへ
            QGuiApplication.clipboard().setText("\n".join(texts_to_copy))

    def _clear_history(self):
        self.store.clear()
        self.history_list.clear()

    # ===== ドラッグ移動＆リサイズ (★修正箇所) =====
    def eventFilter(self, obj, e):
        # 説明: bg(ウィンドウの端)またはcard(タイトルバーなど)が対象
        if obj in (self.bg, self.card, self.title):

            # --- マウスプレス ---
            if e.type()==QEvent.MouseButtonPress and e.button()==Qt.LeftButton:
                # 説明: ★Pressイベント内でのみ globalPosition を呼ぶ
                pos = self.mapFromGlobal(e.globalPosition().toPoint())
                edges = self._hit_edges(pos) if obj is self.bg else ""
                
                if edges:
                    # 説明: 端を掴んだらリサイズ開始
                    self._resizing=True; self._resize_edges=edges
                    self._start_geo=self.geometry(); self._start_mouse=e.globalPosition().toPoint()
                    return True
                elif obj in (self.card, self.title, self.bg): # 説明: 端以外(bg含む)なら移動開始
                    self._moving=True; self._drag_offset = e.globalPosition().toPoint() - self.frameGeometry().topLeft()
                    return True
            
            # --- マウスムーブ ---
            if e.type()==QEvent.MouseMove:
                # 説明: ★Moveイベント内でのみ globalPosition を呼ぶ
                pos = self.mapFromGlobal(e.globalPosition().toPoint())
                edges = self._hit_edges(pos) if obj is self.bg else ""

                if getattr(self, "_resizing", False):
                    self._resize_to(e.globalPosition().toPoint()); return True
                if self._moving and (e.buttons() & Qt.LeftButton) and not self.isMaximized():
                    self.move(e.globalPosition().toPoint() - self._drag_offset); return True
                
                # 説明: bg上でのみカーソル変更 (リサイズ中でない場合)
                if obj is self.bg and not getattr(self, "_resizing", False):
                    self._update_cursor(edges)
                return True # 説明: Moveイベントはここで処理完了
            
            # --- マウスリリース ---
            if e.type()==QEvent.MouseButtonRelease:
                self._resizing=False; self._moving=False
                self._update_cursor("") # 説明: カーソルをリセット
                return True
            
            # --- マウスイベント以外 (ウィンドウから離れた時など) ---
            if e.type() == QEvent.Leave:
                 self._update_cursor("") # 説明: カーソルをリセット
                 return True

        # 説明: 親クラスのイベントフィルタを実行
        return super().eventFilter(obj,e)

    def _hit_edges(self, pos):
        # 説明: リサイズマージン(端)にヒットしたか判定
        m=RESIZE_MARGIN; r=self.bg.rect(); edges=""
        if pos.y()<=m: edges+="T"
        if pos.y()>=r.height()-m: edges+="B"
        if pos.x()<=m: edges+="L"
        if pos.x()>=r.width()-m: edges+="R"
        return edges

    def _update_cursor(self, edges):
        # 説明: ヒットした場所に応じてカーソル形状を変更
        if   edges in ("TL","BR"): self.setCursor(Qt.SizeFDiagCursor)
        elif edges in ("TR","BL"): self.setCursor(Qt.SizeBDiagCursor)
        elif edges in ("L","R"):   self.setCursor(Qt.SizeHorCursor)
        elif edges in ("T","B"):   self.setCursor(Qt.SizeVerCursor)
        else: self.setCursor(Qt.ArrowCursor)

    def _resize_to(self, gpos):
        # 説明: マウス移動量に応じてウィンドウジオメトリを更新
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
        return super().closeEvent(e)

