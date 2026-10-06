import sqlite3
import sys
from datetime import datetime

from PySide6.QtCore import QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QPainter
from PySide6.QtWidgets import (QApplication, QButtonGroup, QComboBox, QFileDialog, QFormLayout, QFrame,
                               QHBoxLayout, QLabel, QLineEdit, QMainWindow, QPushButton, QStackedWidget,
                               QVBoxLayout, QWidget)

import services as s
import ui_kit as ui
from database import get_conn
from notas import DlgNota
from ui_kit import (COL, Tarjeta, aviso, boton, confirmar, fila, fmt, glyph_icon, item, label,
                    limpiar, panel, pedir, retone, separador, spin, tabla)

DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
DIAS_CORTO = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]


# =====================================================================
#  Dashboard
# =====================================================================
class KPI(QFrame):
    def __init__(self, titulo):
        super().__init__(); self.setObjectName("card")
        l = QVBoxLayout(self); l.setContentsMargins(20, 16, 20, 16); l.setSpacing(4)
        l.addWidget(label(titulo, "caption")); self.v = label("-", "title"); l.addWidget(self.v)

    def set(self, txt, tone=None):
        self.v.setText(txt); retone(self.v, tone)


class BarChart(QWidget):
    def __init__(self):
        super().__init__(); self.datos = []; self.setMinimumHeight(200)

    def set_datos(self, d):
        self.datos = d; self.update()

    def paintEvent(self, _):
        if not self.datos: return
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        f = QFont(self.font()); f.setPixelSize(12); p.setFont(f)
        w, h = self.width(), self.height()
        mx = max(v for _, v in self.datos) or 1
        n = len(self.datos); gap = 18; bw = (w - gap * (n + 1)) / n; base = h - 26; top = 26
        for i, (lab, v) in enumerate(self.datos):
            x = gap + i * (bw + gap); bh = (base - top) * v / mx
            c = QColor(COL["accent"]); c.setAlpha(255 if i == n - 1 else 110)
            p.setPen(Qt.NoPen); p.setBrush(c)
            p.drawRoundedRect(QRectF(x, base - max(bh, 3), bw, max(bh, 3)), 6, 6)
            p.setPen(QColor(COL["muted"]))
            p.drawText(QRectF(x - gap / 2, base + 5, bw + gap, 18), Qt.AlignCenter, lab)
            if v: p.drawText(QRectF(x - gap / 2, base - bh - 22, bw + gap, 18), Qt.AlignCenter, f"{v:,.0f}")


class Dashboard(QWidget):
    def __init__(self, win):
        super().__init__(); self.conn = win.conn
        lay = QVBoxLayout(self); lay.setContentsMargins(0, 0, 0, 0); lay.setSpacing(16)
        r1 = QHBoxLayout(); r1.setSpacing(16)
        self.k_ventas, self.k_tickets = KPI("Ventas de hoy"), KPI("Tickets emitidos")
        self.k_prom, self.k_bajo = KPI("Ticket promedio"), KPI("Productos por agotarse")
        for k in (self.k_ventas, self.k_tickets, self.k_prom, self.k_bajo): r1.addWidget(k)
        lay.addLayout(r1)

        r2 = QHBoxLayout(); r2.setSpacing(16)
        pc, lc = panel("Ventas de los últimos 7 días"); self.chart = BarChart(); lc.addWidget(self.chart)
        r2.addWidget(pc, 2)
        pk, lk = panel("Estado de caja")
        self.c_estado = label("-", "title"); lk.addWidget(self.c_estado)
        self.c_cajero = fila("Cajero"); self.c_desde = fila("Abierta desde")
        self.c_esp = fila("Efectivo esperado", role="h", tone="accent")
        for w in (self.c_cajero, self.c_desde, separador(), self.c_esp): lk.addWidget(w)
        lk.addStretch(); r2.addWidget(pk, 1)
        lay.addLayout(r2, 1)

        r3 = QHBoxLayout(); r3.setSpacing(16)
        pt, lt = panel("Más vendidos hoy"); self.top = tabla(["Producto", "Cantidad"], (0,), (1,)); lt.addWidget(self.top)
        pb, lb = panel("Reponer pronto"); self.bajo = tabla(["Producto", "Stock", "Mínimo"], (0,), (1, 2)); lb.addWidget(self.bajo)
        r3.addWidget(pt, 1); r3.addWidget(pb, 1); lay.addLayout(r3, 1)

    def refresh(self):
        r = s.resumen_dashboard(self.conn)
        self.k_ventas.set(fmt(r["ventas_hoy"]), "accent"); self.k_tickets.set(str(r["tickets"]))
        self.k_prom.set(fmt(r["ticket_prom"]))
        self.k_bajo.set(str(r["stock_bajo"]), "danger" if r["stock_bajo"] else "ok")
        self.chart.set_datos([(DIAS_CORTO[d.weekday()], v) for d, v in s.ventas_ultimos_dias(self.conn)])
        t = s.turno_abierto(self.conn)
        if t:
            self.c_estado.setText("● Abierta"); retone(self.c_estado, "ok")
            self.c_cajero.val.setText(t["cajero"]); self.c_desde.val.setText(t["apertura_local"][5:16])
            self.c_esp.val.setText(fmt(s.resumen_turno(self.conn, t["id"])["esperado"]))
        else:
            self.c_estado.setText("● Cerrada"); retone(self.c_estado, "danger")
            for f in (self.c_cajero, self.c_desde, self.c_esp): f.val.setText("—")
        self.top.setRowCount(0)
        for x in r["top"]:
            i = self.top.rowCount(); self.top.insertRow(i)
            self.top.setItem(i, 0, item(x["nombre"])); self.top.setItem(i, 1, item(f'{x["c"]:g}', True))
        self.bajo.setRowCount(0)
        for p in s.stock_bajo(self.conn)[:12]:
            i = self.bajo.rowCount(); self.bajo.insertRow(i)
            for j, v in enumerate((p["nombre"], f'{p["stock_actual"]:g}', f'{p["stock_minimo"]:g}')):
                self.bajo.setItem(i, j, item(v, j > 0, "danger"))


# =====================================================================
#  Punto de venta
# =====================================================================
class POS(QWidget):
    def __init__(self, win):
        super().__init__(); self.win, self.conn, self.carrito = win, win.conn, []
        lay = QHBoxLayout(self); lay.setContentsMargins(0, 0, 0, 0); lay.setSpacing(16)

        izq, li = panel("Productos de la venta")
        self.busca = QLineEdit()
        self.busca.setPlaceholderText("Escanea el código de barras o escribe el nombre y pulsa Enter")
        self.busca.returnPressed.connect(self.buscar); li.addWidget(self.busca)
        self.tbl = tabla(["Producto", "Cantidad", "Precio", "Subtotal"], (0,), (1, 2, 3))
        self.tbl.cellDoubleClicked.connect(lambda *_: self.cambiar_cant()); li.addWidget(self.tbl, 1)
        fb = QHBoxLayout()
        fb.addWidget(boton("Cambiar cantidad", self.cambiar_cant, "secondary"))
        fb.addWidget(boton("Quitar producto", self.quitar, "danger")); fb.addStretch(); li.addLayout(fb)
        lay.addWidget(izq, 1)

        der, ld = panel("Resumen de la venta"); der.setFixedWidth(350)
        self.f_sub = fila("Subtotal", role="h"); ld.addWidget(self.f_sub)
        fd = QHBoxLayout(); fd.addWidget(label("Descuento", "caption")); fd.addStretch()
        self.desc = spin(); self.desc.setFixedWidth(130); self.desc.valueChanged.connect(self.totales)
        fd.addWidget(self.desc); ld.addLayout(fd)
        self.f_imp = fila("Impuesto", role="h"); ld.addWidget(self.f_imp)
        ld.addWidget(separador())
        ft = QHBoxLayout(); ft.addWidget(label("TOTAL", "h")); ft.addStretch()
        self.v_total = label("", "title", "accent"); ft.addWidget(self.v_total); ld.addLayout(ft)
        ld.addWidget(separador())
        ld.addWidget(label("Método de pago", "caption"))
        self.metodo = QComboBox(); self.metodo.addItems(["Efectivo", "Tarjeta", "Transferencia"])
        self.metodo.currentIndexChanged.connect(self.totales); ld.addWidget(self.metodo)
        ld.addWidget(label("Monto recibido", "caption"))
        fr = QHBoxLayout(); self.recibido = spin(); self.recibido.valueChanged.connect(self.totales)
        fr.addWidget(self.recibido, 1); fr.addWidget(boton("Exacto", self.exacto, "secondary")); ld.addLayout(fr)
        self.f_vuelto = fila("Vuelto", role="title"); ld.addWidget(self.f_vuelto)
        ld.addStretch()
        b = boton("Cobrar  ·  F2", self.cobrar); b.setMinimumHeight(52); ld.addWidget(b)
        ld.addWidget(boton("Vaciar venta", self.vaciar, "secondary"))
        lay.addWidget(der)
        self.totales()

    # --- carrito ---
    def buscar(self):
        txt = self.busca.text().strip(); self.busca.clear()
        if not txt: return
        res = s.buscar_productos(self.conn, txt, 20)
        if not res: return aviso(self.win, "Sin resultados", f"No se encontró «{txt}» en el inventario.")
        p = res[0]
        if len(res) > 1 and p["codigo_barras"] != txt:
            cb = QComboBox(); cb.addItems([f'{r["nombre"]}  ·  {fmt(r["precio_venta"])}' for r in res])
            if not pedir(self.win, "Elige el producto", [("Coincidencias", cb)], "Agregar"): return
            p = res[cb.currentIndex()]
        self.agregar(p)

    def agregar(self, p):
        cant = 1.0
        if p["unidad_medida"] in ("kg", "L"):
            sp = spin(9999, 3, 1.0, 0.001)
            if not pedir(self.win, p["nombre"], [(f'Cantidad ({p["unidad_medida"]})', sp)], "Agregar"): return
            cant = sp.value()
        for it in self.carrito:
            if it["producto_id"] == p["id"]:
                it["cantidad"] += cant; break
        else:
            self.carrito.append({"producto_id": p["id"], "nombre": p["nombre"], "cantidad": cant,
                                 "precio": p["precio_venta"]})
        self.refrescar()

    def cambiar_cant(self):
        r = self.tbl.currentRow()
        if r < 0: return
        sp = spin(9999, 3, self.carrito[r]["cantidad"], 0.001)
        if pedir(self.win, "Cambiar cantidad", [(self.carrito[r]["nombre"], sp)], "Aplicar"):
            self.carrito[r]["cantidad"] = sp.value(); self.refrescar()

    def quitar(self):
        r = self.tbl.currentRow()
        if r >= 0: self.carrito.pop(r); self.refrescar()

    def vaciar(self):
        self.carrito.clear(); self.desc.setValue(0); self.recibido.setValue(0); self.refrescar()

    def exacto(self):
        self.recibido.setValue(self.calc()[3])

    # --- cálculos ---
    def tasa(self):
        return float(s.get_ajuste(self.conn, "impuesto", "0") or 0) / 100

    def calc(self):
        sub = sum(i["cantidad"] * i["precio"] for i in self.carrito)
        desc = min(self.desc.value(), sub); imp = round((sub - desc) * self.tasa(), 2)
        return sub, desc, imp, round(sub - desc + imp, 2)

    def refrescar(self):
        self.tbl.setRowCount(0)
        for i in self.carrito:
            r = self.tbl.rowCount(); self.tbl.insertRow(r)
            vals = (i["nombre"], f'{i["cantidad"]:g}', fmt(i["precio"]), fmt(i["cantidad"] * i["precio"]))
            for j, v in enumerate(vals): self.tbl.setItem(r, j, item(v, j > 0))
        self.totales()

    def totales(self):
        sub, desc, imp, total = self.calc()
        self.f_sub.val.setText(fmt(sub)); self.f_imp.cap.setText(f"Impuesto ({self.tasa() * 100:g}%)")
        self.f_imp.val.setText(fmt(imp)); self.v_total.setText(fmt(total))
        if self.metodo.currentText() == "Efectivo":
            self.recibido.setEnabled(True); r = self.recibido.value()
            if r <= 0: self.f_vuelto.val.setText("—"); retone(self.f_vuelto.val, None)
            elif r + 0.005 >= total: self.f_vuelto.val.setText(fmt(r - total)); retone(self.f_vuelto.val, "ok")
            else: self.f_vuelto.val.setText(f"Falta {fmt(total - r)}"); retone(self.f_vuelto.val, "danger")
        else:
            self.recibido.setEnabled(False); self.recibido.blockSignals(True)
            self.recibido.setValue(total); self.recibido.blockSignals(False)
            self.f_vuelto.val.setText(fmt(0)); retone(self.f_vuelto.val, None)

    def refresh(self):
        self.totales()

    # --- cobro ---
    def cobrar(self):
        if not self.carrito: return aviso(self.win, "Venta vacía", "Agrega al menos un producto.")
        if not s.turno_abierto(self.conn):
            return aviso(self.win, "Caja cerrada", "Abre la caja desde el módulo Caja antes de vender.", "danger")
        sub, desc, imp, total = self.calc(); metodo = self.metodo.currentText().lower()
        recibido = self.recibido.value() if metodo == "efectivo" else total
        if metodo == "efectivo" and recibido + 0.005 < total:
            return aviso(self.win, "Monto insuficiente", f"El monto recibido no cubre el total ({fmt(total)}).", "danger")
        try:
            vid, total = s.registrar_venta(self.conn, self.carrito, [{"metodo": metodo, "monto": recibido}],
                                           desc, self.tasa(), recibido=recibido)
        except ValueError as e:
            return aviso(self.win, "No se pudo cobrar", str(e), "danger")
        d = Tarjeta(self.win, "Venta registrada", 400)
        d.body.addWidget(label(fmt(total), "title", "ok"))
        d.body.addWidget(fila("Ticket", f"N° {vid:06d}")); d.body.addWidget(fila("Pago", metodo.capitalize()))
        if metodo == "efectivo":
            d.body.addWidget(fila("Recibido", fmt(recibido)))
            d.body.addWidget(fila("Vuelto", fmt(max(recibido - total, 0)), "h", "ok"))
        d.boton("Nota de compra", lambda: self.win.mostrar_nota(vid), "secondary")
        d.boton("Nueva venta", d.accept, default=True); d.exec()
        self.vaciar(); self.win.refresh_all(); self.busca.setFocus()


# =====================================================================
#  Inventario
# =====================================================================
class Inventario(QWidget):
    TODAS = "Todas las categorías"

    def __init__(self, win):
        super().__init__(); self.win, self.conn, self.ids = win, win.conn, []
        lay = QVBoxLayout(self); lay.setContentsMargins(0, 0, 0, 0)
        card, l = panel(); lay.addWidget(card)
        top = QHBoxLayout(); top.setSpacing(10)
        self.filtro = QLineEdit(); self.filtro.setPlaceholderText("Buscar por nombre o código")
        self.filtro.setMinimumWidth(260); self.filtro.textChanged.connect(self.refresh); top.addWidget(self.filtro, 1)
        self.cat = QComboBox(); self.cat.setMinimumWidth(200); self.cat.currentIndexChanged.connect(self.refresh)
        top.addWidget(self.cat); top.addSpacing(16)
        top.addWidget(boton("Plantilla Excel", self.plantilla, "secondary"))
        top.addWidget(boton("Importar Excel", self.importar, "secondary"))
        top.addWidget(boton("+ Nuevo producto", self.nuevo)); l.addLayout(top)
        self.t = tabla(["Código", "Producto", "Categoría", "Contenido", "Precio", "Stock", "Estado"], (1, 2), (4, 5))
        self.t.cellDoubleClicked.connect(lambda *_: self.editar()); l.addWidget(self.t, 1)
        pie = QHBoxLayout(); self.cuenta = label("", "caption"); pie.addWidget(self.cuenta); pie.addStretch()
        pie.addWidget(boton("Editar", self.editar, "secondary"))
        pie.addWidget(boton("+ Entrada de stock", self.entrada, "secondary"))
        pie.addWidget(boton("Eliminar", self.eliminar, "danger")); l.addLayout(pie)

    def sel(self):
        r = self.t.currentRow()
        if r < 0:
            aviso(self.win, "Selecciona un producto", "Haz clic en una fila de la tabla primero."); return None
        return self.ids[r]

    def refresh(self):
        prods = s.listar_productos(self.conn)
        cats = sorted({p["categoria"].split(" > ")[0] for p in prods if p["categoria"]})
        actual = self.cat.currentText() or self.TODAS
        self.cat.blockSignals(True); self.cat.clear(); self.cat.addItems([self.TODAS] + cats)
        self.cat.setCurrentText(actual if actual in cats else self.TODAS); self.cat.blockSignals(False)
        f, c = self.filtro.text().lower(), self.cat.currentText()
        self.t.setRowCount(0); self.ids = []
        for p in prods:
            if c != self.TODAS and p["categoria"].split(" > ")[0] != c: continue
            if f and f not in (p["nombre"] + (p["codigo_barras"] or "")).lower(): continue
            bajo = p["stock_actual"] <= p["stock_minimo"]
            r = self.t.rowCount(); self.t.insertRow(r); self.ids.append(p["id"])
            cont = f'{p["contenido"]:g} {p["unidad_medida"]}' if p["contenido"] else p["unidad_medida"]
            vals = (p["codigo_barras"] or "—", p["nombre"], p["categoria"] or "—", cont, fmt(p["precio_venta"]),
                    f'{p["stock_actual"]:g}', "Stock bajo" if bajo else "OK")
            for j, v in enumerate(vals):
                self.t.setItem(r, j, item(v, j in (4, 5), "danger" if bajo else ("ok" if j == 6 else None)))
        self.cuenta.setText(f"{len(self.ids)} productos")

    def nuevo(self): self.formulario(None)

    def editar(self):
        pid = self.sel()
        if pid is not None: self.formulario(s.obtener_producto(self.conn, pid))

    def formulario(self, p):
        d = Tarjeta(self.win, "Editar producto" if p else "Nuevo producto", 480)
        cod = QLineEdit((p["codigo_barras"] or "") if p else ""); nom = QLineEdit(p["nombre"] if p else "")
        cat = QComboBox(); cat.setEditable(True); cat.addItems([c[1] for c in s.listar_categorias(self.conn)])
        cat.setCurrentText(p["categoria"] if p else "")
        uni = QComboBox(); uni.addItems(["unidad", "g", "kg", "ml", "L"])
        uni.setCurrentText(p["unidad_medida"] if p else "unidad")
        cont = spin(valor=p["contenido"] if p else 0); pc = spin(valor=p["precio_compra"] if p else 0)
        pv = spin(valor=p["precio_venta"] if p else 0); stock = spin(valor=p["stock_actual"] if p else 0)
        smin = spin(valor=p["stock_minimo"] if p else 5)
        f = QFormLayout(); f.setSpacing(10)
        for et, w in (("Código de barras", cod), ("Nombre", nom), ("Categoría  (Cat. > Subcat.)", cat),
                      ("Unidad", uni), ("Contenido (ej. 500)", cont), ("Precio de compra", pc),
                      ("Precio de venta", pv), ("Stock actual" if p else "Stock inicial", stock),
                      ("Stock mínimo (alerta)", smin)):
            f.addRow(label(et, "caption"), w)
        d.body.addLayout(f)

        def guardar():
            if not nom.text().strip(): return aviso(d, "Falta información", "El nombre es obligatorio.", "danger")
            if pv.value() <= 0: return aviso(d, "Falta información", "El precio de venta debe ser mayor que 0.", "danger")
            try:
                cid = None
                for n in [x.strip() for x in cat.currentText().split(">") if x.strip()]:
                    cid = s.categoria_id(self.conn, n, cid)
                self.conn.commit()
                datos = {"codigo": cod.text().strip(), "nombre": nom.text().strip(), "categoria_id": cid,
                         "unidad": uni.currentText(), "contenido": cont.value(), "precio_compra": pc.value(),
                         "precio_venta": pv.value(), "stock": stock.value(), "stock_minimo": smin.value()}
                if p: s.actualizar_producto(self.conn, p["id"], datos)
                else: s.guardar_producto(self.conn, datos)
            except sqlite3.IntegrityError:
                return aviso(d, "Código repetido", "Ya existe un producto con ese código de barras.", "danger")
            except Exception as e:
                return aviso(d, "Error", str(e), "danger")
            d.accept(); self.win.refresh_all()
        d.boton("Cancelar", d.reject, "secondary"); d.boton("Guardar", guardar, default=True); d.exec()

    def eliminar(self):
        pid = self.sel()
        if pid is None: return
        p = s.obtener_producto(self.conn, pid)
        if confirmar(self.win, "Eliminar producto", f"¿Eliminar «{p['nombre']}» del inventario?\n\n"
                     "Dejará de aparecer y de venderse, pero se conserva el historial de ventas.", "Eliminar", True):
            s.desactivar_producto(self.conn, pid); self.win.refresh_all()

    def entrada(self):
        pid = self.sel()
        if pid is None: return
        p = s.obtener_producto(self.conn, pid); sp = spin(1e6, 3, 1, 0.001)
        if pedir(self.win, "Entrada de mercancía", [(p["nombre"], sp)], "Registrar entrada"):
            s.entrada_stock(self.conn, pid, sp.value()); self.win.refresh_all()

    def plantilla(self):
        ruta, _ = QFileDialog.getSaveFileName(self, "Guardar plantilla", "plantilla_productos.xlsx", "Excel (*.xlsx)")
        if ruta: s.crear_plantilla_excel(ruta)

    def importar(self):
        ruta, _ = QFileDialog.getOpenFileName(self, "Importar productos", "", "Excel (*.xlsx)")
        if not ruta: return
        ok, errs = s.importar_excel(self.conn, ruta)
        txt = f"Productos importados: {ok}" + ("\n\nErrores:\n" + "\n".join(errs[:12]) if errs else "")
        aviso(self.win, "Importación terminada", txt, "danger" if errs else "ok"); self.win.refresh_all()


# =====================================================================
#  Ventas (historial)
# =====================================================================
class Ventas(QWidget):
    def __init__(self, win):
        super().__init__(); self.win, self.conn, self.ids = win, win.conn, []
        lay = QVBoxLayout(self); lay.setContentsMargins(0, 0, 0, 0)
        card, l = panel(); lay.addWidget(card)
        self.t = tabla(["N°", "Fecha y hora", "Cajero", "Pago", "Total", "Estado"], (1, 2), (4,))
        self.t.cellDoubleClicked.connect(lambda *_: self.ver()); l.addWidget(self.t, 1)
        pie = QHBoxLayout(); pie.addStretch()
        pie.addWidget(boton("Anular venta", self.anular, "danger"))
        pie.addWidget(boton("Ver nota de compra", self.ver)); l.addLayout(pie)

    def refresh(self):
        self.t.setRowCount(0); self.ids = []
        for v in s.listar_ventas(self.conn):
            r = self.t.rowCount(); self.t.insertRow(r); self.ids.append(v["id"])
            f = datetime.strptime(v["fecha_local"], "%Y-%m-%d %H:%M:%S")
            anulada = v["estado"] == "anulada"
            vals = (f'{v["id"]:06d}', f"{f:%d/%m/%Y  %H:%M}", v["cajero"], (v["metodos"] or "").replace(",", ", "),
                    fmt(v["total"]), "Anulada" if anulada else "Completada")
            for j, x in enumerate(vals):
                self.t.setItem(r, j, item(x, j == 4, "danger" if anulada else ("ok" if j == 5 else None)))

    def _sel(self):
        r = self.t.currentRow()
        if r < 0: aviso(self.win, "Selecciona una venta", "Haz clic en una fila de la tabla primero."); return None
        return self.ids[r]

    def ver(self):
        v = self._sel()
        if v: self.win.mostrar_nota(v)

    def anular(self):
        v = self._sel()
        if v and confirmar(self.win, "Anular venta", f"¿Anular la venta N° {v:06d}?\n\n"
                           "El stock de los productos será devuelto al inventario.", "Anular venta", True):
            try: s.anular_venta(self.conn, v)
            except ValueError as e: return aviso(self.win, "No se pudo anular", str(e), "danger")
            self.win.refresh_all()


# =====================================================================
#  Caja y arqueo
# =====================================================================
class DlgArqueo(Tarjeta):
    def __init__(self, parent, conn, r):
        super().__init__(parent, "Cierre de caja y arqueo", 460)
        self.conn, self.r, self.resultado = conn, r, None
        for k, v in r["por_metodo"].items(): self.body.addWidget(fila(f"Ventas · {k.capitalize()}", fmt(v)))
        self.body.addWidget(fila("Efectivo inicial", fmt(r["turno"]["monto_inicial"])))
        self.body.addWidget(fila("Ingresos de caja", fmt(r["ingresos"])))
        self.body.addWidget(fila("Egresos (proveedores / gastos)", fmt(r["egresos"])))
        self.body.addWidget(separador())
        self.body.addWidget(fila("Efectivo esperado en caja", fmt(r["esperado"]), "h", "accent"))
        self.body.addWidget(label("Efectivo contado", "caption"))
        self.sp = spin(); self.sp.valueChanged.connect(self.calc); self.body.addWidget(self.sp)
        self.diff = label("Ingresa el efectivo contado", "h"); self.body.addWidget(self.diff)
        self.boton("Cancelar", self.reject, "secondary")
        self.b_ok = self.boton("Confirmar cierre", self.confirmar, default=True); self.b_ok.setEnabled(False)
        self.sp.setFocus()

    @staticmethod
    def estado(d):
        if abs(d) < 0.01: return "Caja cuadrada ✓", "ok"
        return (f"Sobrante de {fmt(d)}", "accent") if d > 0 else (f"Faltante de {fmt(-d)}", "danger")

    def calc(self):
        txt, tone = self.estado(self.sp.value() - self.r["esperado"])
        self.diff.setText(txt); ui.set_role(self.diff, "title"); retone(self.diff, tone)
        self.b_ok.setEnabled(True)

    def confirmar(self):
        contado = self.sp.value()
        try: res = s.cerrar_turno(self.conn, contado)
        except ValueError as e: return aviso(self, "Error", str(e), "danger")
        try: ruta = s.hacer_backup(self.conn)
        except Exception: ruta = None
        txt, tone = self.estado(res["diferencia"]); self.resultado = txt
        limpiar(self.body); limpiar(self.pie); self.pie.addStretch()
        self.body.addWidget(label(txt, "title", tone))
        self.body.addWidget(fila("Ventas totales", fmt(res["total_ventas"])))
        self.body.addWidget(fila("Esperado en efectivo", fmt(res["esperado"])))
        self.body.addWidget(fila("Contado", fmt(contado)))
        self.body.addWidget(separador())
        resp = label("✓ Copia de seguridad guardada" if ruta else "No se pudo crear la copia de seguridad",
                     "caption", "ok" if ruta else "danger")
        if ruta: resp.setToolTip(str(ruta))
        self.body.addWidget(resp); self.boton("Listo", self.accept, default=True)


class Caja(QWidget):
    def __init__(self, win):
        super().__init__(); self.win, self.conn = win, win.conn
        lay = QHBoxLayout(self); lay.setContentsMargins(0, 0, 0, 0); lay.setSpacing(16)
        izq, li = panel("Turno de caja"); self.estado = label("", "title"); li.addWidget(self.estado)
        self.f = {k: fila(k) for k in ("Cajero", "Apertura", "Efectivo inicial", "Ventas en efectivo",
                                       "Ventas con tarjeta", "Ventas por transferencia", "Ingresos", "Egresos")}
        for w in self.f.values(): li.addWidget(w)
        li.addWidget(separador())
        self.f_esp = fila("Efectivo esperado", role="title", tone="accent"); li.addWidget(self.f_esp)
        self.l_cierre = label("", "caption", wrap=True); li.addWidget(self.l_cierre); li.addStretch()
        self.b_abrir = boton("Abrir caja", self.abrir); li.addWidget(self.b_abrir)
        fm = QHBoxLayout()
        self.b_egr = boton("Registrar egreso", lambda: self.mov("egreso"), "secondary")
        self.b_ing = boton("Registrar ingreso", lambda: self.mov("ingreso"), "secondary")
        fm.addWidget(self.b_egr); fm.addWidget(self.b_ing); li.addLayout(fm)
        self.b_cerrar = boton("Cerrar caja y arqueo", self.cerrar, "secondary"); li.addWidget(self.b_cerrar)
        lay.addWidget(izq, 1)
        der, ld = panel("Movimientos del turno")
        self.t = tabla(["Hora", "Tipo", "Concepto", "Monto"], (2,), (3,)); ld.addWidget(self.t); lay.addWidget(der, 1)

    def refresh(self):
        t = s.turno_abierto(self.conn)
        for b in (self.b_egr, self.b_ing, self.b_cerrar): b.setEnabled(bool(t))
        self.b_abrir.setEnabled(not t); self.t.setRowCount(0)
        if not t:
            self.estado.setText("● Caja cerrada"); retone(self.estado, "danger")
            for w in (*self.f.values(), self.f_esp): w.val.setText("—")
            return
        r = s.resumen_turno(self.conn, t["id"]); pm = r["por_metodo"]
        self.estado.setText(f'● Turno #{t["id"]} abierto'); retone(self.estado, "ok")
        vals = {"Cajero": t["cajero"], "Apertura": t["apertura_local"], "Efectivo inicial": fmt(t["monto_inicial"]),
                "Ventas en efectivo": fmt(pm.get("efectivo", 0)), "Ventas con tarjeta": fmt(pm.get("tarjeta", 0)),
                "Ventas por transferencia": fmt(pm.get("transferencia", 0)), "Ingresos": fmt(r["ingresos"]),
                "Egresos": fmt(r["egresos"])}
        for k, v in vals.items(): self.f[k].val.setText(v)
        self.f_esp.val.setText(fmt(r["esperado"]))
        for m in s.listar_movimientos_caja(self.conn, t["id"]):
            i = self.t.rowCount(); self.t.insertRow(i)
            for j, v in enumerate((m["hora"], m["tipo"].capitalize(), m["concepto"], fmt(m["monto"]))):
                self.t.setItem(i, j, item(v, j == 3, "danger" if (m["tipo"] == "egreso" and j == 3) else None))

    def abrir(self):
        nombre = QLineEdit(s.get_ajuste(self.conn, "cajero", "Cajero")); monto = spin()
        if not pedir(self.win, "Apertura de caja", [("Cajero", nombre), ("Efectivo inicial en caja", monto)],
                     "Abrir caja"): return
        try:
            s.abrir_turno(self.conn, monto.value(), nombre.text().strip() or "Cajero")
            s.set_ajuste(self.conn, "cajero", nombre.text().strip() or "Cajero"); self.l_cierre.setText("")
        except ValueError as e: aviso(self.win, "Aviso", str(e), "danger")
        self.win.refresh_all()

    def mov(self, tipo):
        c = QLineEdit(); m = spin()
        c.setPlaceholderText("Ej. Pago a proveedor de bebidas" if tipo == "egreso" else "Ej. Aporte de efectivo")
        if not pedir(self.win, f"Registrar {tipo}", [("Concepto", c), ("Monto", m)], "Registrar"): return
        if not c.text().strip() or m.value() <= 0:
            return aviso(self.win, "Datos incompletos", "Indica el concepto y un monto mayor que 0.", "danger")
        try: s.registrar_movimiento_caja(self.conn, tipo, c.text().strip(), m.value())
        except ValueError as e: aviso(self.win, "Aviso", str(e), "danger")
        self.win.refresh_all()

    def cerrar(self):
        t = s.turno_abierto(self.conn)
        if not t: return
        d = DlgArqueo(self.win, self.conn, s.resumen_turno(self.conn, t["id"])); d.exec()
        if d.resultado: self.l_cierre.setText(f"Último cierre: {d.resultado}")
        self.win.refresh_all()


# =====================================================================
#  Ventana principal
# =====================================================================
class Main(QMainWindow):
    def __init__(self):
        super().__init__(); self.resize(1280, 780); self.setMinimumSize(1100, 680)
        self.conn = get_conn()
        ui.set_modo(s.get_ajuste(self.conn, "tema", "claro")); ui.MONEDA = s.get_ajuste(self.conn, "moneda", "Bs")
        central = QWidget(); self.setCentralWidget(central)
        root = QHBoxLayout(central); root.setContentsMargins(0, 0, 0, 0); root.setSpacing(0)

        # Sidebar
        sb = QFrame(); sb.setObjectName("sidebar"); sb.setFixedWidth(230)
        ls = QVBoxLayout(sb); ls.setContentsMargins(14, 18, 14, 18); ls.setSpacing(4)
        self.brand = QLabel(); self.brand.setObjectName("brand"); ui.set_role(self.brand, "title"); ls.addWidget(self.brand)
        self.pages = [Dashboard(self), POS(self), Inventario(self), Ventas(self), Caja(self)]
        self.nombres = ["Dashboard", "Punto de venta", "Inventario", "Ventas", "Caja"]
        grupo = QButtonGroup(self); self.nav = []
        for i, (g, n) in enumerate(zip(["▦", "$", "▤", "☰", "▣"], self.nombres)):
            b = QPushButton("  " + n); b.setObjectName("nav"); b.setCheckable(True); b.setCursor(Qt.PointingHandCursor)
            b.setIcon(glyph_icon(g, COL["accent"])); b.clicked.connect(lambda _, i=i: self.ir(i))
            grupo.addButton(b); ls.addWidget(b); self.nav.append(b)
        ls.addStretch()
        for g, n, fn in (("◐", "Cambiar tema", self.toggle_tema), ("⚙", "Ajustes", self.ajustes)):
            b = QPushButton("  " + n); b.setObjectName("nav"); b.setCursor(Qt.PointingHandCursor)
            b.setIcon(glyph_icon(g, COL["accent"])); b.clicked.connect(lambda *_, fn=fn: fn()); ls.addWidget(b)
        root.addWidget(sb)

        # Topbar + canvas
        der = QVBoxLayout(); der.setSpacing(0); root.addLayout(der, 1)
        tb = QFrame(); tb.setObjectName("topbar"); tb.setFixedHeight(68)
        lt = QHBoxLayout(tb); lt.setContentsMargins(28, 0, 28, 0)
        self.titulo = label("", "title"); lt.addWidget(self.titulo); lt.addStretch()
        self.reloj = label("", "caption"); lt.addWidget(self.reloj); lt.addSpacing(24)
        self.usuario = label("", "h"); lt.addWidget(self.usuario); der.addWidget(tb)
        self.stack = QStackedWidget(); wrap = QWidget(); lw = QVBoxLayout(wrap); lw.setContentsMargins(28, 24, 28, 24)
        for p in self.pages: self.stack.addWidget(p)
        lw.addWidget(self.stack); der.addWidget(wrap, 1)

        self.timer = QTimer(self); self.timer.timeout.connect(self.tick); self.timer.start(1000)
        self.ir(1 if s.turno_abierto(self.conn) else 0)

    def tick(self):
        n = datetime.now()
        self.reloj.setText(f"{DIAS[n.weekday()].capitalize()} {n.day:02d} {MESES[n.month - 1]} {n.year}  ·  {n:%H:%M:%S}")

    def ir(self, i):
        self.nav[i].setChecked(True); self.stack.setCurrentIndex(i); self.titulo.setText(self.nombres[i])
        self.refresh_all(); self.tick()
        if i == 1: self.pages[1].busca.setFocus()

    def refresh_all(self):
        neg = s.get_ajuste(self.conn, "negocio", "Minimercado")
        self.brand.setText(neg); self.setWindowTitle(f"{neg} · Inventario y POS")
        for p in self.pages: p.refresh()
        t = s.turno_abierto(self.conn)
        self.usuario.setText(f"●  {t['cajero']}" if t else "●  Sin turno abierto")
        retone(self.usuario, "ok" if t else "danger")

    def mostrar_nota(self, venta_id):
        neg = s.get_ajuste(self.conn, "negocio", "Minimercado")
        DlgNota(self, s.obtener_venta(self.conn, venta_id), neg).exec()

    def toggle_tema(self):
        nuevo = "oscuro" if s.get_ajuste(self.conn, "tema", "claro") == "claro" else "claro"
        s.set_ajuste(self.conn, "tema", nuevo); ui.set_modo(nuevo)
        QApplication.instance().setStyleSheet(ui.estilo()); self.refresh_all()

    def ajustes(self):
        neg = QLineEdit(s.get_ajuste(self.conn, "negocio", "Minimercado"))
        imp = spin(100, 2, float(s.get_ajuste(self.conn, "impuesto", "0") or 0))
        mon = QLineEdit(ui.MONEDA)
        if pedir(self, "Ajustes del negocio", [("Nombre del negocio", neg), ("Impuesto (%)", imp),
                                               ("Símbolo de moneda", mon)]):
            s.set_ajuste(self.conn, "negocio", neg.text().strip() or "Minimercado")
            s.set_ajuste(self.conn, "impuesto", imp.value())
            s.set_ajuste(self.conn, "moneda", mon.text().strip() or "Bs")
            ui.MONEDA = mon.text().strip() or "Bs"; self.refresh_all()

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_F2 and self.stack.currentIndex() == 1: self.pages[1].cobrar()
        else: super().keyPressEvent(e)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    base = app.font(); base.setPixelSize(14); app.setFont(base)   # tamaño de texto base
    w = Main(); app.setStyleSheet(ui.estilo()); w.show(); sys.exit(app.exec())
