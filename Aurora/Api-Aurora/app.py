from flask import Flask, render_template, request, redirect, url_for, flash
import psycopg2
import psycopg2.extras
import os

app = Flask(__name__)
app.secret_key = "supersecretkey"

# Configuración PostgreSQL
app.config['PG_HOST'] = "localhost"
app.config['PG_DATABASE'] = "aurora"
app.config['PG_USER'] = "postgres"
app.config['PG_PASSWORD'] = "duoc"

def get_db_connection():
    return psycopg2.connect(
        host=app.config['PG_HOST'],
        database=app.config['PG_DATABASE'],
        user=app.config['PG_USER'],
        password=app.config['PG_PASSWORD']
    )

# ===========================
# RUTAS
# ===========================
@app.route("/")
def index():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    # Productos
    cur.execute("""
        SELECT p.*, COALESCE(i.stock,0) as stock
        FROM producto p
        LEFT JOIN inventario_sucursal i ON i.id_variacion = p.id_producto
        ORDER BY p.id_producto;
    """)
    productos = cur.fetchall()

    # Sucursales
    cur.execute("SELECT * FROM sucursal ORDER BY id_sucursal;")
    sucursales = cur.fetchall()

    cur.close()
    conn.close()
    return render_template("index.html", productos=productos, sucursales=sucursales)

# ---------------------------
# Productos
# ---------------------------
@app.route("/add", methods=["POST"])
def add_producto():
    nombre = request.form["nombre"]
    precio = request.form["precio"]

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO producto (sku, nombre_producto, precio_producto)
        VALUES (%s, %s, %s)
    """, ("SKU_" + nombre, nombre, precio))
    conn.commit()
    cur.close()
    conn.close()
    flash("Producto agregado con éxito")
    return redirect(url_for("index"))

@app.route("/edit/<int:id>", methods=["POST"])
def edit_producto(id):
    nombre = request.form["nombre"]
    precio = request.form["precio"]

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE producto
        SET nombre_producto = %s, precio_producto = %s
        WHERE id_producto = %s
    """, (nombre, precio, id))
    conn.commit()
    cur.close()
    conn.close()
    flash("Producto actualizado")
    return redirect(url_for("index"))

@app.route("/delete/<int:id>", methods=["POST"])
def delete_producto(id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM producto WHERE id_producto = %s", (id,))
    conn.commit()
    cur.close()
    conn.close()
    flash("Producto eliminado")
    return redirect(url_for("index"))

# ---------------------------
# Sucursales
# ---------------------------
@app.route("/add_sucursal", methods=["POST"])
def add_sucursal():
    nombre = request.form["nombre"]
    region = request.form["region"]
    comuna = request.form["comuna"]
    direccion = request.form["direccion"]
    latitud = request.form.get("latitud") or None
    longitud = request.form.get("longitud") or None
    horario = request.form.get("horario") or '{}'
    telefono = request.form.get("telefono") or None

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO sucursal 
        (nombre_sucursal, region_sucursal, comuna_sucursal, direccion_sucursal, latitud_sucursal, longitud_sucursal, horario_json, telefono_sucursal)
        VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb, %s)
    """, (nombre, region, comuna, direccion, latitud, longitud, horario, telefono))
    conn.commit()
    cur.close()
    conn.close()
    flash("Sucursal agregada con éxito")
    return redirect(url_for("index"))

# ===========================
# RUN
# ===========================
if __name__ == "__main__":
    app.run(host="127.0.0.1", port=3000, debug=True)
