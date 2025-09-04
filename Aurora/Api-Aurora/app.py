from flask import Flask, render_template, request, redirect, url_for, flash
import psycopg2
import psycopg2.extras

app = Flask(__name__)
app.secret_key = "supersecretkey"

# Config PostgreSQL
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

# ---------------------------
# Helpers
# ---------------------------
def get_or_create_default_variacion(conn, id_producto: int) -> int:
    """
    Obtiene la variación por defecto para un producto.
    Si no existe, la crea (campos talla/color nulos, sku_variacion = 'VAR-{sku}').
    Retorna id_variacion.
    """
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute(
            "SELECT id_variacion FROM variacion_producto WHERE id_producto = %s LIMIT 1;",
            (id_producto,)
        )
        row = cur.fetchone()
        if row:
            return row["id_variacion"]

        # Necesitamos el sku del producto para construir sku_variacion
        cur.execute(
            "SELECT sku FROM producto WHERE id_producto = %s;",
            (id_producto,)
        )
        prod = cur.fetchone()
        sku = prod["sku"] if prod and "sku" in prod else f"SKU_{id_producto}"
        sku_var = f"VAR-{sku}"

        cur.execute(
            """
            INSERT INTO variacion_producto (id_producto, talla, color, sku_variacion)
            VALUES (%s, NULL, NULL, %s)
            RETURNING id_variacion;
            """,
            (id_producto, sku_var)
        )
        new_id = cur.fetchone()[0]
        return new_id

# ===========================
# RUTAS
# ===========================
@app.route("/")
def index():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    # Productos con stock total (suma de todas las sucursales)
    cur.execute("""
        SELECT
            p.id_producto,
            p.nombre_producto,
            p.precio_producto,
            COALESCE(SUM(inv.stock), 0) AS stock_total
        FROM producto p
        LEFT JOIN variacion_producto vp ON vp.id_producto = p.id_producto
        LEFT JOIN inventario_sucursal inv ON inv.id_variacion = vp.id_variacion
        GROUP BY p.id_producto
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
    try:
        with conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                # Crea producto
                sku = f"SKU_{nombre}"
                cur.execute("""
                    INSERT INTO producto (sku, nombre_producto, precio_producto)
                    VALUES (%s, %s, %s)
                    RETURNING id_producto;
                """, (sku, nombre, precio))
                id_producto = cur.fetchone()[0]

                # Crea variación por defecto para satisfacer FK de inventario_sucursal
                get_or_create_default_variacion(conn, id_producto)

        flash("Producto agregado con éxito")
    finally:
        conn.close()

    return redirect(url_for("index"))

@app.route("/edit/<int:id>", methods=["POST"])
def edit_producto(id):
    nombre = request.form["nombre"]
    precio = request.form["precio"]

    conn = get_db_connection()
    with conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE producto
                SET nombre_producto = %s, precio_producto = %s
                WHERE id_producto = %s
            """, (nombre, precio, id))
    conn.close()
    flash("Producto actualizado")
    return redirect(url_for("index"))

@app.route("/delete/<int:id>", methods=["POST"])
def delete_producto(id):
    conn = get_db_connection()
    with conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM producto WHERE id_producto = %s", (id,))
    conn.close()
    flash("Producto eliminado")
    return redirect(url_for("index"))

# ---------------------------
# Stock (por sucursal)
# ---------------------------
@app.route("/stock/add", methods=["POST"])
def add_stock():
    """
    Incrementa stock para un producto en una sucursal.
    Crea registro en inventario_sucursal si no existe.
    Requiere: product_id, sucursal_id, cantidad (>0)
    """
    product_id = int(request.form["product_id"])
    sucursal_id = int(request.form["sucursal_id"])
    cantidad = int(request.form["cantidad"])

    if cantidad <= 0:
        flash("La cantidad debe ser mayor a 0.")
        return redirect(url_for("index"))

    conn = get_db_connection()
    try:
        with conn:
            id_variacion = get_or_create_default_variacion(conn, product_id)
            with conn.cursor() as cur:
                # Upsert sumando
                cur.execute("""
                    INSERT INTO inventario_sucursal (id_sucursal, id_variacion, stock)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (id_sucursal, id_variacion)
                    DO UPDATE SET stock = inventario_sucursal.stock + EXCLUDED.stock;
                """, (sucursal_id, id_variacion, cantidad))
        flash("Stock agregado correctamente")
    finally:
        conn.close()

    return redirect(url_for("index"))

@app.route("/stock/set", methods=["POST"])
def set_stock():
    """
    Fija (sobrescribe) el stock para un producto en una sucursal.
    Requiere: product_id, sucursal_id, cantidad (>=0)
    """
    product_id = int(request.form["product_id"])
    sucursal_id = int(request.form["sucursal_id"])
    cantidad = int(request.form["cantidad"])

    if cantidad < 0:
        flash("La cantidad no puede ser negativa.")
        return redirect(url_for("index"))

    conn = get_db_connection()
    try:
        with conn:
            id_variacion = get_or_create_default_variacion(conn, product_id)
            with conn.cursor() as cur:
                # Upsert fijando
                cur.execute("""
                    INSERT INTO inventario_sucursal (id_sucursal, id_variacion, stock)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (id_sucursal, id_variacion)
                    DO UPDATE SET stock = EXCLUDED.stock;
                """, (sucursal_id, id_variacion, cantidad))
        flash("Stock actualizado correctamente")
    finally:
        conn.close()

    return redirect(url_for("index"))

@app.route("/stock/delete", methods=["POST"])
def delete_stock():
    """
    Elimina el registro de stock (id_sucursal + variación por defecto del producto).
    Requiere: product_id, sucursal_id
    """
    product_id = int(request.form["product_id"])
    sucursal_id = int(request.form["sucursal_id"])

    conn = get_db_connection()
    try:
        with conn:
            id_variacion = get_or_create_default_variacion(conn, product_id)
            with conn.cursor() as cur:
                cur.execute("""
                    DELETE FROM inventario_sucursal
                    WHERE id_sucursal = %s AND id_variacion = %s;
                """, (sucursal_id, id_variacion))
        flash("Registro de stock eliminado")
    finally:
        conn.close()

    return redirect(url_for("index"))

# ---------------------------
# Sucursales (ya lo tenías)
# ---------------------------
@app.route("/add_sucursal", methods=["POST"])
def add_sucursal():
    nombre = request.form["nombre"]
    region = request.form["region"]
    comuna = request.form["comuna"]
    direccion = request.form["direccion"]
    latitud = request.form.get("latitud") or None
    longitud = request.form.get("longitud") or None
    horario = request.form.get("horario") or "{}"
    telefono = request.form.get("telefono") or None

    conn = get_db_connection()
    with conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO sucursal 
                (nombre_sucursal, region_sucursal, comuna_sucursal, direccion_sucursal, latitud_sucursal, longitud_sucursal, horario_json, telefono_sucursal)
                VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb, %s)
            """, (nombre, region, comuna, direccion, latitud, longitud, horario, telefono))
    conn.close()
    flash("Sucursal agregada con éxito")
    return redirect(url_for("index"))

# ===========================
# RUN
# ===========================
if __name__ == "__main__":
    app.run(host="127.0.0.1", port=3000, debug=True)
