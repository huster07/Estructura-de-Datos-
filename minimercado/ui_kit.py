"""Sistema de diseño: paletas (claro/oscuro), hoja de estilos y componentes reutilizables.

Reglas: 3 tamaños de letra (20 título · 14 texto · 12 leyenda) y un solo radio (10 px).
"""
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QIcon, QPixmap, QPainter
from PySide6.QtWidgets import (QFrame, QLabel, QVBoxLayout, QHBoxLayout, QWidget, QTableWidget,
    QTableWidgetItem, QHeaderView, QPushButton, QDialog, QFormLayout, QDoubleSpinBox, QAbstractItemView)

MONEDA = "Bs"
NAVY = "#0F2A43"

PALETAS = {
    "claro": dict(bg="#EAF1F8", card="#FFFFFF", text="#0F2A43", muted="#64748B", border="#E2E8F0",
                  accent="#38BDF8", accent_hover="#0EA5E9", accent_text="#0F2A43", accent_txt="#0284C7",
                  sidebar="#0F2A43", sidebar_text="#CBD5E1", sidebar_hover="#1B3F63", sel="#E0F2FE",
                  danger="#DC2626", danger_soft="#FEE2E2", ok="#16A34A", ok_soft="#DCFCE7", input="#FFFFFF"),
    "oscuro": dict(bg="#0A1826", card="#11263A", text="#E6EEF5", muted="#8FA6BC", border="#1F3A56",
                   accent="#38BDF8", accent_hover="#7DD3FC", accent_text="#0A1826", accent_txt="#38BDF8",
                   sidebar="#07121D", sidebar_text="#9FB4C9", sidebar_hover="#12304A", sel="#17405F",
                   danger="#F87171", danger_soft="#4A1D24", ok="#4ADE80", ok_soft="#14391F", input="#0D2033"),
}
COL = dict(PALETAS["claro"])   # paleta activa (se modifica en sitio)


def set_modo(modo):
    COL.clear(); COL.update(PALETAS.get(modo, PALETAS["claro"]))


QSS = """
QWidget { color:@text; font-family:"Segoe UI","Inter","Helvetica Neue",Arial,sans-serif; }
QMainWindow { background:@bg; }
QDialog { background:@card; }
QLabel { background:transparent; }
QLabel[role="caption"] { color:@muted; }
QLabel[tone="accent"] { color:@accent_txt; }
QLabel[tone="ok"] { color:@ok; }
QLabel[tone="danger"] { color:@danger; }
QLabel#dlgHeader { background:#0F2A43; color:#FFFFFF; padding:16px 24px; }
QLabel#brand { color:#FFFFFF; padding:8px 8px 16px 8px; }

QFrame#card { background:@card; border:1px solid @border; border-radius:10px; }
QFrame#sidebar { background:@sidebar; }
QFrame#topbar { background:@card; border:none; border-bottom:1px solid @border; }
QFrame#sep { background:@border; border:none; }

QPushButton { background:@accent; color:@accent_text; border:1px solid @accent; border-radius:10px;
              padding:10px 18px; font-weight:600; }
QPushButton:hover { background:@accent_hover; border-color:@accent_hover; }
QPushButton:disabled { background:@border; border-color:@border; color:@muted; }
QPushButton[kind="secondary"] { background:@card; color:@text; border:1px solid @accent; }
QPushButton[kind="secondary"]:hover { background:@sel; border-color:@accent; }
QPushButton[kind="danger"] { background:@card; color:@danger; border:1px solid @danger; }
QPushButton[kind="danger"]:hover { background:@danger_soft; border-color:@danger; }
QPushButton[kind="secondary"]:disabled, QPushButton[kind="danger"]:disabled
    { background:@card; border-color:@border; color:@muted; }
QPushButton#nav { background:transparent; color:@sidebar_text; border:none; text-align:left;
                  padding:12px 14px; font-weight:500; }
QPushButton#nav:hover { background:@sidebar_hover; color:#FFFFFF; }
QPushButton#nav:checked { background:@sidebar_hover; color:#FFFFFF; font-weight:700; }

QLineEdit, QDoubleSpinBox, QComboBox { background:@input; border:1px solid @border; border-radius:10px;
              padding:9px 12px; selection-background-color:@accent; selection-color:@accent_text; }
QLineEdit:focus, QDoubleSpinBox:focus, QComboBox:focus { border:1px solid @accent; }
QLineEdit:disabled, QDoubleSpinBox:disabled { color:@muted; background:@bg; }
QComboBox::drop-down { border:none; width:26px; }
QComboBox QAbstractItemView { background:@card; border:1px solid @border; outline:0;
              selection-background-color:@sel; selection-color:@text; padding:4px; }

QTableWidget { background:@card; border:none; outline:0; }
QTableWidget::item { padding:4px 8px; border-bottom:1px solid @border; }
QTableWidget::item:selected { background:@sel; color:@text; }
QHeaderView::section { background:@card; color:@muted; font-size:12px; font-weight:600; border:none;
              border-bottom:1px solid @border; padding:10px 8px; }
QTableCornerButton::section { background:@card; border:none; }

QScrollBar:vertical { background:transparent; width:10px; margin:0; }
QScrollBar::handle:vertical { background:@border; border-radius:5px; min-height:30px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height:0; }
QScrollBar:horizontal { background:transparent; height:10px; }
QScrollBar::handle:horizontal { background:@border; border-radius:5px; min-width:30px; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width:0; }
QToolTip { background:#0F2A43; color:#FFFFFF; border:none; padding:6px; }
"""


def estilo():
    q = QSS
    for k in sorted(COL, key=len, reverse=True):
        q = q.replace("@" + k, COL[k])
    return q


def fmt(x):
    return f"{MONEDA} {x:,.2f}"


# ---------- Componentes ----------
def retone(w, tone):
    w.setProperty("tone", tone or "")
    w.style().unpolish(w); w.style().polish(w)


def set_role(l, role):
    """Aplica uno de los 3 tamaños de letra: title 20 · h/normal 14 · caption 12."""
    l.setProperty("role", role or "")
    f = l.font(); f.setBold(role in ("title", "h"))
    f.setPixelSize({"title": 20, "caption": 12}.get(role, 14)); l.setFont(f)


def label(texto="", role=None, tone=None, wrap=False):
    l = QLabel(texto); set_role(l, role)
    if tone: l.setProperty("tone", tone)
    l.setWordWrap(wrap)
    return l


def boton(texto, fn=None, kind=None):
    b = QPushButton(texto); b.setCursor(Qt.PointingHandCursor)
    if kind: b.setProperty("kind", kind)
    if fn: b.clicked.connect(lambda *_: fn())
    return b


def spin(maximo=1e7, dec=2, valor=0.0, minimo=0.0):
    w = QDoubleSpinBox(); w.setRange(minimo, maximo); w.setDecimals(dec); w.setValue(valor)
    w.setButtonSymbols(QDoubleSpinBox.NoButtons); w.setGroupSeparatorShown(True)
    return w


def panel(titulo=None, margen=20):
    f = QFrame(); f.setObjectName("card")
    l = QVBoxLayout(f); l.setContentsMargins(margen, margen, margen, margen); l.setSpacing(12)
    if titulo: l.addWidget(label(titulo, "h"))
    return f, l


def separador():
    s = QFrame(); s.setObjectName("sep"); s.setFixedHeight(1); return s


def fila(texto, valor="", role=None, tone=None):
    """Línea 'etiqueta ........ valor'. Devuelve el widget (.cap y .val accesibles)."""
    w = QWidget(); h = QHBoxLayout(w); h.setContentsMargins(0, 0, 0, 0)
    w.cap = label(texto, "caption"); w.val = label(valor, role, tone)
    w.val.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
    h.addWidget(w.cap); h.addStretch(); h.addWidget(w.val)
    return w


def tabla(cols, anchas=(0,), der=()):
    t = QTableWidget(0, len(cols)); t.setHorizontalHeaderLabels(cols)
    t.setShowGrid(False); t.setFrameShape(QFrame.NoFrame)
    for i in range(len(cols)):
        t.horizontalHeader().setSectionResizeMode(i, QHeaderView.Stretch if i in anchas else QHeaderView.ResizeToContents)
        if i in der: t.horizontalHeaderItem(i).setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
    t.horizontalHeader().setMinimumSectionSize(90)
    t.horizontalHeader().setHighlightSections(False)
    t.horizontalHeader().setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
    t.verticalHeader().hide(); t.verticalHeader().setDefaultSectionSize(44)
    t.setEditTriggers(QAbstractItemView.NoEditTriggers)
    t.setSelectionBehavior(QAbstractItemView.SelectRows); t.setSelectionMode(QAbstractItemView.SingleSelection)
    t.setFocusPolicy(Qt.NoFocus)
    return t


def item(texto, derecha=False, tone=None):
    it = QTableWidgetItem(str(texto))
    it.setTextAlignment((Qt.AlignRight if derecha else Qt.AlignLeft) | Qt.AlignVCenter)
    if tone == "danger":
        it.setBackground(QColor(COL["danger_soft"])); it.setForeground(QColor(COL["danger"]))
    elif tone == "ok":
        it.setForeground(QColor(COL["ok"]))
    return it


def glyph_icon(ch, color):
    pm = QPixmap(28, 28); pm.fill(Qt.transparent)
    p = QPainter(pm); p.setRenderHint(QPainter.TextAntialiasing)
    p.setFont(QFont("Segoe UI Symbol", 15)); p.setPen(QColor(color))
    p.drawText(pm.rect(), Qt.AlignCenter, ch); p.end()
    return QIcon(pm)


def limpiar(layout):
    while layout.count():
        it = layout.takeAt(0)
        if it.widget(): it.widget().deleteLater()
        elif it.layout(): limpiar(it.layout())


# ---------- Ventanas tipo tarjeta (encabezado azul marino) ----------
class Tarjeta(QDialog):
    def __init__(self, parent, titulo, ancho=440):
        super().__init__(parent)
        self.setWindowTitle(titulo); self.setMinimumWidth(ancho); self.setModal(True)
        raiz = QVBoxLayout(self); raiz.setContentsMargins(0, 0, 0, 0); raiz.setSpacing(0)
        h = QLabel(titulo); h.setObjectName("dlgHeader"); set_role(h, "title"); raiz.addWidget(h)
        self.body = QVBoxLayout(); self.body.setSpacing(12); self.body.setContentsMargins(24, 20, 24, 12)
        c = QWidget(); c.setLayout(self.body); raiz.addWidget(c)
        self.pie = QHBoxLayout(); self.pie.setContentsMargins(24, 8, 24, 20); self.pie.setSpacing(10)
        self.pie.addStretch()
        p = QWidget(); p.setLayout(self.pie); raiz.addWidget(p)

    def boton(self, texto, fn, kind=None, default=False):
        b = boton(texto, fn, kind); self.pie.addWidget(b)
        if default: b.setDefault(True)
        return b


def aviso(parent, titulo, texto, tone=None):
    d = Tarjeta(parent, titulo); d.body.addWidget(label(texto, tone=tone, wrap=True))
    d.boton("Entendido", d.accept, default=True); d.exec()


def confirmar(parent, titulo, texto, ok="Confirmar", peligro=False):
    d = Tarjeta(parent, titulo); d.body.addWidget(label(texto, wrap=True))
    d.boton("Cancelar", d.reject, "secondary")
    d.boton(ok, d.accept, "danger" if peligro else None, default=True)
    return d.exec() == QDialog.Accepted


def pedir(parent, titulo, campos, ok="Guardar", texto=None):
    """campos: [(etiqueta, widget)]. Devuelve True si el usuario aceptó."""
    d = Tarjeta(parent, titulo)
    if texto: d.body.addWidget(label(texto, "caption", wrap=True))
    f = QFormLayout(); f.setSpacing(10); f.setLabelAlignment(Qt.AlignLeft)
    for et, w in campos: f.addRow(label(et, "caption"), w)
    d.body.addLayout(f)
    d.boton("Cancelar", d.reject, "secondary"); d.boton(ok, d.accept, default=True)
    if campos: campos[0][1].setFocus()
    return d.exec() == QDialog.Accepted
