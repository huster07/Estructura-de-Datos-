"""Nota de compra (NO es factura): vista previa, impresión y PDF."""
import html
from datetime import datetime
from PySide6.QtCore import QMarginsF
from PySide6.QtGui import QPageLayout, QPageSize, QTextDocument
from PySide6.QtPrintSupport import QPrintDialog, QPrinter
from PySide6.QtWidgets import QFileDialog, QTextBrowser
import ui_kit as ui
from ui_kit import Tarjeta, label

PAPEL = QPageSize.A5     # cambia a A6 para un formato más pequeño


def nota_html(d, negocio):
    v, items, pagos = d["venta"], d["items"], d["pagos"]
    f = datetime.strptime(v["fecha_local"], "%Y-%m-%d %H:%M:%S")
    m = ui.MONEDA
    filas = ""
    for i in items:
        u = f' {i["unidad_medida"]}' if i["unidad_medida"] in ("kg", "L") else ""
        filas += (f'<tr><td>{html.escape(i["nombre"])}</td><td align="right">{i["cantidad"]:g}{u}</td>'
                  f'<td align="right">{i["precio_unitario"]:,.2f}</td><td align="right">{i["subtotal"]:,.2f}</td></tr>')
    metodo = ", ".join(p["metodo"].capitalize() for p in pagos) or "-"
    efectivo = any(p["metodo"] == "efectivo" for p in pagos)
    recibido = v["recibido"] or v["total"]
    vuelto = max(recibido - v["total"], 0) if efectivo else 0
    def lin(t, val, b=False):
        s = "<b>%s</b>" if b else "%s"
        return f'<tr><td>{s % t}</td><td align="right">{s % val}</td></tr>'
    resumen = lin("Subtotal", f'{m} {v["subtotal"]:,.2f}')
    if v["descuento"]: resumen += lin("Descuento", f'- {m} {v["descuento"]:,.2f}')
    if v["impuesto"]: resumen += lin("Impuesto", f'{m} {v["impuesto"]:,.2f}')
    resumen += lin("TOTAL", f'{m} {v["total"]:,.2f}', True) + lin("Pago", metodo)
    if efectivo: resumen += lin("Recibido", f'{m} {recibido:,.2f}') + lin("Vuelto", f'{m} {vuelto:,.2f}')
    anulada = '<p align="center"><b style="color:#DC2626">*** VENTA ANULADA ***</b></p>' if v["estado"] == "anulada" else ""
    return f"""<div style="color:#0F2A43; font-size:10pt">
<h2 align="center" style="margin:0">{html.escape(negocio)}</h2>
<p align="center" style="margin:2px">NOTA DE COMPRA N° {v["id"]:06d}<br>
Fecha: {f:%d/%m/%Y} &nbsp;&nbsp; Hora: {f:%H:%M:%S}<br>Atendió: {html.escape(v["cajero"] or "-")}</p>{anulada}<hr>
<table width="100%" cellspacing="0" cellpadding="3">
<tr bgcolor="#E0F2FE"><th align="left">Producto</th><th align="right">Cant.</th><th align="right">P. unit.</th><th align="right">Importe</th></tr>
{filas}</table><hr>
<table width="100%" cellspacing="0" cellpadding="2">{resumen}</table><hr>
<p align="center" style="margin:2px">Documento sin validez fiscal<br>¡Gracias por su compra!<br>
<span style="font-size:8pt">Impreso: {datetime.now():%d/%m/%Y %H:%M}</span></p></div>"""


class DlgNota(Tarjeta):
    def __init__(self, parent, datos, negocio):
        v = datos["venta"]
        super().__init__(parent, f'Nota de compra N° {v["id"]:06d}', 520)
        self.numero = v["id"]; self.html = nota_html(datos, negocio)
        f = datetime.strptime(v["fecha_local"], "%Y-%m-%d %H:%M:%S")
        self.body.addWidget(label(f"Vista previa · emitida el {f:%d/%m/%Y} a las {f:%H:%M:%S}", "caption"))
        self.vista = QTextBrowser(); self.vista.setHtml(self.html); self.vista.setMinimumSize(440, 460)
        self.vista.setStyleSheet(f"QTextBrowser{{background:#FFFFFF; color:#0F2A43; border:1px solid "
                                 f"{ui.COL['border']}; border-radius:10px; padding:8px;}}")
        self.body.addWidget(self.vista)
        self.boton("Cerrar", self.reject, "secondary")
        self.boton("Descargar PDF", self.pdf, "secondary")
        self.boton("Imprimir", self.imprimir, default=True)

    def _doc(self):
        d = QTextDocument(); d.setHtml(self.html); return d

    def _printer(self):
        p = QPrinter(QPrinter.HighResolution); p.setPageSize(QPageSize(PAPEL))
        p.setPageMargins(QMarginsF(8, 8, 8, 8), QPageLayout.Millimeter); return p

    def imprimir(self):
        p = self._printer()
        if QPrintDialog(p, self).exec(): self._doc().print_(p)

    def pdf(self):
        ruta, _ = QFileDialog.getSaveFileName(self, "Guardar nota de compra",
                                              f"nota_{self.numero:06d}.pdf", "PDF (*.pdf)")
        if not ruta: return
        p = self._printer(); p.setOutputFormat(QPrinter.PdfFormat); p.setOutputFileName(ruta)
        self._doc().print_(p)
        ui.aviso(self, "PDF guardado", f"La nota se guardó en:\n{ruta}", "ok")
