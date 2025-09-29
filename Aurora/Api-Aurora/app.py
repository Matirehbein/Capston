from flask import Flask, render_template, request, redirect, url_for, flash
import json
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

#Función para abrir la conexión con la Base de datos
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

# ---------------------------
# Página Principal (Menú)
# ---------------------------
@app.route('/')
def menu_principal():
    return render_template("index_options.html")

@app.route("/index_options")
def index_options():
    return render_template("index_options.html")

# ---------------------------
# CRUD Productos
# ---------------------------

@app.route('/productos')
def crud_productos():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    # Productos
    cur.execute("""
        SELECT p.*, COALESCE(SUM(i.stock),0) as stock
        FROM producto p
        LEFT JOIN variacion_producto v ON v.id_producto = p.id_producto
        LEFT JOIN inventario_sucursal i ON i.id_variacion = v.id_variacion
        GROUP BY p.id_producto
        ORDER BY p.id_producto;
    """)
    productos = cur.fetchall()

    # Sucursales (para el modal de stock)
    cur.execute("SELECT * FROM sucursal ORDER BY id_sucursal;")
    sucursales = cur.fetchall()

    cur.close()
    conn.close()
    return render_template("productos/crud_productos.html", productos=productos, sucursales=sucursales)


# ---------------------------
# CRUD Sucursales
# ---------------------------

@app.route('/sucursales')
def crud_sucursales():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    # Sucursales
    cur.execute("SELECT * FROM sucursal ORDER BY id_sucursal;")
    sucursales = cur.fetchall()

    cur.close()
    conn.close()
    return render_template("sucursales/crud_sucursales.html", sucursales=sucursales)


# ---------------------------
# Rutas de Productos
# ---------------------------

@app.route("/add", methods=["POST"])
def add_producto():
    sku = request.form["sku"]
    nombre = request.form["nombre"]
    precio = request.form["precio"]
    descripcion = request.form.get("descripcion")
    categoria = request.form.get("categoria")
    imagen_url = request.form.get("imagen_url")

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO producto (sku, nombre_producto, precio_producto, descripcion_producto, categoria_producto, imagen_url)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (sku, nombre, precio, descripcion, categoria, imagen_url))
    conn.commit()
    cur.close()
    conn.close()
    flash("Producto agregado con éxito")
    return redirect(url_for("crud_productos"))

@app.route("/edit/<int:id>", methods=["POST"])
def edit_producto(id):
    sku = request.form["sku"]
    nombre = request.form["nombre"]
    precio = request.form["precio"]
    descripcion = request.form.get("descripcion")
    categoria = request.form.get("categoria")
    imagen_url = request.form.get("imagen_url")

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE producto
        SET sku = %s, nombre_producto = %s, precio_producto = %s,
            descripcion_producto = %s, categoria_producto = %s, imagen_url = %s
        WHERE id_producto = %s
    """, (sku, nombre, precio, descripcion, categoria, imagen_url, id))
    conn.commit()
    cur.close()
    conn.close()
    flash("Producto actualizado")
    return redirect(url_for("crud_productos"))

@app.route("/delete/<int:id>", methods=["POST"])
def delete_producto(id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM producto WHERE id_producto = %s", (id,))
    conn.commit()
    cur.close()
    conn.close()
    flash("Producto eliminado")
    return redirect(url_for("crud_productos"))

@app.route("/edit_stock/<int:id>", methods=["POST"])
def edit_stock(id):
    id_sucursal = request.form["id_sucursal"]
    stock = request.form["stock"]

    conn = get_db_connection()
    cur = conn.cursor()

    # Asegurar que exista variación para este producto
    cur.execute("SELECT id_variacion FROM variacion_producto WHERE id_producto = %s", (id,))
    variacion = cur.fetchone()
    if not variacion:
        cur.execute("INSERT INTO variacion_producto (id_producto, sku_variacion) VALUES (%s, %s) RETURNING id_variacion", (id, f"VAR-{id}"))
        variacion_id = cur.fetchone()[0]
    else:
        variacion_id = variacion[0]

    # Insertar o actualizar inventario
    cur.execute("""
        INSERT INTO inventario_sucursal (id_sucursal, id_variacion, stock)
        VALUES (%s, %s, %s)
        ON CONFLICT (id_sucursal, id_variacion)
        DO UPDATE SET stock = EXCLUDED.stock
    """, (id_sucursal, variacion_id, stock))

    conn.commit()
    cur.close()
    conn.close()
    flash("Stock actualizado")
    return redirect(url_for("crud_productos"))

# ---------------------------
# Ver stock del Listado de Productos
# ---------------------------

@app.route("/ver_stock/<int:id_producto>")
def ver_stock(id_producto):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    # Traer el producto
    cur.execute("SELECT * FROM producto WHERE id_producto = %s", (id_producto,))
    producto = cur.fetchone()

    # Traer sucursales + stock de este producto
    cur.execute("""
        SELECT s.id_sucursal, s.nombre_sucursal, COALESCE(i.stock, 0) as stock
        FROM sucursal s
        LEFT JOIN inventario_sucursal i 
            ON s.id_sucursal = i.id_sucursal
        LEFT JOIN variacion_producto v
            ON i.id_variacion = v.id_variacion
        WHERE v.id_producto = %s OR v.id_producto IS NULL
        ORDER BY s.id_sucursal
    """, (id_producto,))
    sucursales = cur.fetchall()

    cur.close()
    conn.close()
    return render_template("productos/ver_stock.html", producto=producto, sucursales=sucursales)


# ---------------------------
# Botón "Ver Stock" del CRUD de Productos (Listado de Productos): Guardar Stock en las sucursales.
# ---------------------------

@app.route("/guardar_stock_sucursales/<int:id_producto>", methods=["POST"])
def guardar_stock_sucursales(id_producto):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    # Variación
    cur.execute("SELECT id_variacion FROM variacion_producto WHERE id_producto = %s", (id_producto,))
    variacion_id = cur.fetchone()[0]

    # Stock total del producto
    cur.execute("""
        SELECT COALESCE(SUM(stock),0) as total_stock
        FROM inventario_sucursal
        WHERE id_variacion = %s
    """, (variacion_id,))
    stock_actual = cur.fetchone()[0]

    # Stock definido en producto
    cur.execute("""
    SELECT COALESCE(SUM(i.stock),0)
    FROM producto p
    LEFT JOIN variacion_producto v ON v.id_producto = p.id_producto
    LEFT JOIN inventario_sucursal i ON i.id_variacion = v.id_variacion
    WHERE p.id_producto = %s
                """, (id,))
    stock_total = cur.fetchone()[0]


    # Calcular nuevo total propuesto
    total_nuevo = 0
    for key, val in request.form.items():
        if key.startswith("stock_"):
            total_nuevo += int(val)

    if total_nuevo > stock_max:
        flash(f"No puedes asignar {total_nuevo} unidades. El máximo permitido es {stock_max}.")
        conn.close()
        return redirect(url_for("ver_stock", id_producto=id_producto))

    # Guardar stocks
    for key, val in request.form.items():
        if key.startswith("stock_"):
            id_sucursal = int(key.split("_")[1])
            stock_val = int(val)

            cur.execute("""
                INSERT INTO inventario_sucursal (id_sucursal, id_variacion, stock)
                VALUES (%s, %s, %s)
                ON CONFLICT (id_sucursal, id_variacion)
                DO UPDATE SET stock = EXCLUDED.stock
            """, (id_sucursal, variacion_id, stock_val))

    conn.commit()
    cur.close()
    conn.close()
    flash("Stock por sucursal actualizado correctamente.")
    return redirect(url_for("ver_stock", id_producto=id_producto))

# ---------------------------
# Actualizar Stock en las sucursales (CRUD de Productos)
# ---------------------------

@app.route("/update_stock/<int:id_producto>/<int:id_sucursal>", methods=["POST"])
def update_stock_sucursal(id_producto, id_sucursal):
    nuevo_stock = int(request.form["stock"])

    conn = get_db_connection()
    cur = conn.cursor()

    # Verificar la variación del producto
    cur.execute("SELECT id_variacion FROM variacion_producto WHERE id_producto = %s", (id_producto,))
    variacion = cur.fetchone()
    if not variacion:
        cur.execute("INSERT INTO variacion_producto (id_producto, sku_variacion) VALUES (%s, %s) RETURNING id_variacion",
                    (id_producto, f"VAR-{id_producto}"))
        id_variacion = cur.fetchone()[0]
    else:
        id_variacion = variacion[0]

    # Insertar/Actualizar stock en esta sucursal
    cur.execute("""
        INSERT INTO inventario_sucursal (id_sucursal, id_variacion, stock)
        VALUES (%s, %s, %s)
        ON CONFLICT (id_sucursal, id_variacion)
        DO UPDATE SET stock = EXCLUDED.stock
    """, (id_sucursal, id_variacion, nuevo_stock))

    conn.commit()
    cur.close()
    conn.close()

    flash("Stock actualizado en la sucursal")
    return redirect(url_for("ver_stock", id_producto=id_producto))



# ---------------------------
# Rutas de Sucursales
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
    return redirect(url_for("crud_sucursales"))

@app.route("/editar_sucursal/<int:id_sucursal>", methods=["POST"])
def editar_sucursal(id_sucursal):
    nombre = request.form["nombre_sucursal"]
    region = request.form["region_sucursal"]
    comuna = request.form["comuna_sucursal"]
    direccion = request.form["direccion_sucursal"]
    latitud = request.form.get("latitud_sucursal") or None
    longitud = request.form.get("longitud_sucursal") or None
    horario = request.form.get("horario_json") or "{}"
    telefono = request.form.get("telefono_sucursal") or None

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE sucursal
        SET nombre_sucursal=%s, region_sucursal=%s, comuna_sucursal=%s,
            direccion_sucursal=%s, latitud_sucursal=%s, longitud_sucursal=%s,
            horario_json=%s::jsonb, telefono_sucursal=%s
        WHERE id_sucursal=%s
    """, (nombre, region, comuna, direccion, latitud, longitud, horario, telefono, id_sucursal))
    conn.commit()
    cur.close()
    conn.close()
    flash("Sucursal actualizada con éxito")
    return redirect(url_for("crud_sucursales"))

@app.route("/eliminar_sucursal/<int:id_sucursal>", methods=["POST"])
def eliminar_sucursal(id_sucursal):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM sucursal WHERE id_sucursal = %s", (id_sucursal,))
    conn.commit()
    cur.close()
    conn.close()
    flash("Sucursal eliminada con éxito")
    return redirect(url_for("crud_sucursales"))

# ===========================
# CRUD Sucursales: Botón de ver Stock por Sucursales
# ===========================

@app.route("/stock_sucursales")
def stock_sucursales():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    # Traer solo sucursales
    cur.execute("SELECT id_sucursal, nombre_sucursal FROM sucursal ORDER BY id_sucursal;")
    sucursales = cur.fetchall()

    cur.close()
    conn.close()
    return render_template("sucursales/stock_sucursales.html", sucursales=sucursales)


# ===========================
# CRUD Sucursales: Ruta para el detalle por Sucursal
# ===========================

@app.route("/stock_sucursal/<int:id_sucursal>")
def detalle_sucursal(id_sucursal):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    # Traer sucursal
    cur.execute("SELECT * FROM sucursal WHERE id_sucursal = %s", (id_sucursal,))
    sucursal = cur.fetchone()

    # Traer productos con stock en esta sucursal
    cur.execute("""
        SELECT p.id_producto, p.nombre_producto, p.imagen_url, p.precio_producto,
               COALESCE(i.stock, 0) as stock
        FROM producto p
        LEFT JOIN variacion_producto v ON v.id_producto = p.id_producto
        LEFT JOIN inventario_sucursal i ON i.id_variacion = v.id_variacion AND i.id_sucursal = %s
        ORDER BY p.id_producto;
    """, (id_sucursal,))
    productos = cur.fetchall()

    cur.close()
    conn.close()
    return render_template("sucursales/detalle_sucursal.html", sucursal=sucursal, productos=productos)




# ===========================
# RUN
# ===========================
if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
