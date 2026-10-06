import os, tempfile
from database import get_conn
import services as s
d = tempfile.mkdtemp(); conn = get_conn(os.path.join(d, "t.db"))
s.crear_plantilla_excel(f"{d}/p.xlsx")
print("import:", s.importar_excel(conn, f"{d}/p.xlsx", f"{d}/bk"))
p = s.buscar_productos(conn, "7750001")[0]
try: s.registrar_venta(conn, [{"producto_id": p["id"], "cantidad": 1, "precio": 12}], [{"metodo":"efectivo","monto":12}])
except ValueError as e: print("sin caja ->", e)
s.abrir_turno(conn, 100)
vid, tot = s.registrar_venta(conn, [{"producto_id": p["id"], "cantidad": 20, "precio": 12}],
                             [{"metodo":"efectivo","monto":100},{"metodo":"tarjeta","monto":140}], descuento=0)
print("venta", vid, tot, "stock:", s.buscar_productos(conn,"7750001")[0]["stock_actual"])
try: s.registrar_venta(conn, [{"producto_id": p["id"], "cantidad": 99, "precio": 12}], [{"metodo":"efectivo","monto":9999}])
except ValueError as e: print("rollback ->", e)
s.registrar_movimiento_caja(conn, "egreso", "Proveedor", 30)
print("stock bajo:", [r["nombre"] for r in s.stock_bajo(conn)])
print("cierre:", {k: v for k, v in s.cerrar_turno(conn, 170).items() if k != "turno"})
print("dash:", {k: v for k, v in s.resumen_dashboard(conn).items() if k != "top"})
print("backup:", s.hacer_backup(conn, f"{d}/bk"))
