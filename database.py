import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "minimercado.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS categorias(
  id INTEGER PRIMARY KEY, nombre TEXT NOT NULL,
  padre_id INTEGER REFERENCES categorias(id),
  UNIQUE(nombre, padre_id));
CREATE TABLE IF NOT EXISTS productos(
  id INTEGER PRIMARY KEY, codigo_barras TEXT UNIQUE, nombre TEXT NOT NULL,
  categoria_id INTEGER REFERENCES categorias(id),
  unidad_medida TEXT DEFAULT 'unidad', contenido REAL DEFAULT 0,
  precio_compra REAL DEFAULT 0, precio_venta REAL NOT NULL,
  stock_actual REAL DEFAULT 0, stock_minimo REAL DEFAULT 5, activo INTEGER DEFAULT 1);
CREATE TABLE IF NOT EXISTS turnos_caja(
  id INTEGER PRIMARY KEY, cajero TEXT, apertura DATETIME DEFAULT CURRENT_TIMESTAMP,
  cierre DATETIME, monto_inicial REAL, monto_contado_cierre REAL,
  estado TEXT DEFAULT 'abierto');
CREATE TABLE IF NOT EXISTS ventas(
  id INTEGER PRIMARY KEY, turno_id INTEGER REFERENCES turnos_caja(id),
  fecha DATETIME DEFAULT CURRENT_TIMESTAMP,
  subtotal REAL, descuento REAL, impuesto REAL, total REAL,
  estado TEXT DEFAULT 'completada', recibido REAL);
CREATE TABLE IF NOT EXISTS venta_detalle(
  id INTEGER PRIMARY KEY, venta_id INTEGER REFERENCES ventas(id),
  producto_id INTEGER REFERENCES productos(id),
  cantidad REAL, precio_unitario REAL, subtotal REAL);
CREATE TABLE IF NOT EXISTS pagos(
  id INTEGER PRIMARY KEY, venta_id INTEGER REFERENCES ventas(id),
  metodo TEXT, monto REAL);
CREATE TABLE IF NOT EXISTS movimientos_inventario(
  id INTEGER PRIMARY KEY, producto_id INTEGER REFERENCES productos(id),
  tipo TEXT, cantidad REAL, motivo TEXT, referencia_id INTEGER,
  fecha DATETIME DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS movimientos_caja(
  id INTEGER PRIMARY KEY, turno_id INTEGER REFERENCES turnos_caja(id),
  tipo TEXT, concepto TEXT, monto REAL,
  fecha DATETIME DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS ajustes(clave TEXT PRIMARY KEY, valor TEXT);
CREATE INDEX IF NOT EXISTS idx_prod_nombre ON productos(nombre);
"""

def get_conn(path=DB_PATH):
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript(SCHEMA)
    _migrar(conn)
    return conn

def _migrar(conn):
    """Actualiza bases creadas con la versión anterior sin perder datos."""
    cols = [r[1] for r in conn.execute("PRAGMA table_info(ventas)")]
    if "recibido" not in cols:
        conn.execute("ALTER TABLE ventas ADD COLUMN recibido REAL")
    conn.commit()
