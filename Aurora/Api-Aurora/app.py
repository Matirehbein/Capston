import re
import os
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, session, send_from_directory, jsonify
import psycopg2
import psycopg2.extras
from psycopg2 import errors
from werkzeug.security import generate_password_hash, check_password_hash
from flask_cors import CORS
import json
import datetime


app = Flask(__name__)
app.secret_key = "supersecretkey"


# Constantes para categorías y tallas
CATEGORIAS_ROPA = ["Abrigos", "Chaquetas", "Parkas", "Polerones", "Poleras", "Ropa interior", "Top", "Traje de baño"]
CATEGORIAS_CALZADO = ["Calzado", "Pantalones"]
TALLAS_ROPA = ["XS", "S", "M", "L", "XL"]
TALLAS_CALZADO = [str(i) for i in range(35, 47)] # Genera tallas del 35 al 46

# ===========================
# SESSION INFO
# ===========================
@app.route("/api/session_info")
def api_session_info():
    """
    Devuelve la información de sesión del usuario logueado.
    Incluye credenciales (cookies) para que el frontend pueda acceder.
    """
    if "user_id" not in session:
        return jsonify({"logged_in": False})

    return jsonify({
        "logged_in": True,
        "id": session.get("user_id"),
        "nombre": session.get("nombre_usuario"),
        "apellido_paterno": session.get("apellido_paterno"),
        "apellido_materno": session.get("apellido_materno"),
        "email": session.get("email_usuario"),
        "rol": session.get("rol_usuario")
    })


# Configuración PostgreSQL
app.config['PG_HOST'] = "localhost"
app.config['PG_DATABASE'] = "aurora"
app.config['PG_USER'] = "postgres"
app.config['PG_PASSWORD'] = "duoc"



# Función para abrir la conexión con la Base de datos
def get_db_connection():
    return psycopg2.connect(
        host=app.config['PG_HOST'],
        database=app.config['PG_DATABASE'],
        user=app.config['PG_USER'],
        password=app.config['PG_PASSWORD']
    )

# Decoradores
def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            flash("⚠️ Debes iniciar sesión.", "warning")
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapper

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "rol_usuario" not in session or session["rol_usuario"] not in ["admin", "soporte"]:
            return redirect(url_for("menu_principal"))
        return f(*args, **kwargs)
    return decorated_function



# ===========================
# RUTAS
# ===========================

BASE_DIR = os.path.abspath(os.path.dirname(__file__))                     # ...\Capstone\Aurora\Api-Aurora
SRC_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "src"))            # ...\Capstone\Aurora\src
PUBLIC_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "Public"))      # ...\Capstone\Aurora\Public
FRONTEND_MAIN_URL = "http://localhost:3000/src/main.html"
CORS(app,
    supports_credentials=True,
    resources={r"/api/*": {"origins": ["http://localhost:3000", "http://127.0.0.1:3000"]}})
# Servir /Public (CSS/JS/Imgs)
@app.route("/Public/<path:filename>")
def public_files(filename):
    return send_from_directory(PUBLIC_DIR, filename)

FRONTEND_ORIGIN = "http://localhost:3000"   # o "http://192.168.100.9:3000"

@app.route("/src/main.html")
def redirect_main_frontend():
    from flask import redirect
    return redirect(f"{FRONTEND_ORIGIN}/src/main.html", code=302)

# Obtengo datos de la BDD para los productos y sucursales
# Esta ruta alimenta las tablas de la interfaz

# 1.- Me conecto a la BDD
# 2.- TRaigo todos los productos y sucursales
# 3.- Renderizo el template "index.html" con los daots
# 4.- Finalmente, el usuario ve la página con el resultado esperado, que es ver la tabla de productos y sucursales

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


# REEMPLAZA ESTA FUNCIÓN COMPLETA en app.py

@app.route('/productos')
@login_required
def crud_productos():
    # 1. Obtener los parámetros de filtrado desde la URL (sin cambios)
    filtro_categoria = request.args.get('filtro_categoria', '')
    filtro_nombre = request.args.get('filtro_nombre', '')
    filtro_sucursal = request.args.get('filtro_sucursal', '')
    q = request.args.get('q', '')

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    # 2. Construir la consulta SQL de forma dinámica
    # La modificación principal está aquí, en cómo se une la tabla de inventario.
    
    params = []
    
    # NUEVO: Se construye la cláusula del JOIN dinámicamente
    join_clause = """
        LEFT JOIN variacion_producto v ON v.id_producto = p.id_producto
        LEFT JOIN inventario_sucursal i ON i.id_variacion = v.id_variacion
    """
    
    # Si se está filtrando por una sucursal, modificamos el JOIN para que solo
    # considere el stock de esa sucursal específica en el cálculo.
    if filtro_sucursal:
        join_clause = """
            LEFT JOIN variacion_producto v ON v.id_producto = p.id_producto
            LEFT JOIN inventario_sucursal i ON i.id_variacion = v.id_variacion AND i.id_sucursal = %s
        """
        params.append(filtro_sucursal)

    base_query = f"""
        SELECT 
            p.id_producto, p.sku, p.nombre_producto, p.precio_producto, 
            p.descripcion_producto, p.categoria_producto, p.imagen_url, 
            COALESCE(SUM(i.stock), 0) as stock
        FROM producto p
        {join_clause}
    """
    
    where_clauses = []
    
    # El resto de los filtros se añaden como cláusulas WHERE
    if filtro_categoria:
        where_clauses.append("p.categoria_producto = %s")
        params.append(filtro_categoria)
    
    if filtro_nombre:
        where_clauses.append("p.nombre_producto = %s")
        params.append(filtro_nombre)

    # NUEVO: El filtro de sucursal ahora se enfoca en asegurar que el producto exista allí.
    # El cálculo de stock ya se maneja en el JOIN.
    if filtro_sucursal:
        where_clauses.append("p.id_producto IN (SELECT v.id_producto FROM inventario_sucursal i JOIN variacion_producto v ON i.id_variacion = v.id_variacion WHERE i.id_sucursal = %s AND i.stock > 0)")
        params.append(filtro_sucursal)

    if q:
        where_clauses.append("(p.id_producto::text ILIKE %s OR p.sku ILIKE %s)")
        params.extend([f"%{q}%", f"%{q}%"])

    final_query = base_query
    if where_clauses:
        final_query += " WHERE " + " AND ".join(where_clauses)
    
    final_query += " GROUP BY p.id_producto ORDER BY p.id_producto;"
    
    cur.execute(final_query, tuple(params))
    productos = cur.fetchall()

    # Obtener datos para los menús desplegables (sin cambios)
    cur.execute("SELECT DISTINCT categoria_producto FROM producto WHERE categoria_producto IS NOT NULL ORDER BY categoria_producto;")
    categorias = [row['categoria_producto'] for row in cur.fetchall()]
    
    nombres_productos_query = "SELECT DISTINCT nombre_producto FROM producto"
    nombres_params = []
    if filtro_categoria:
        nombres_productos_query += " WHERE categoria_producto = %s"
        nombres_params.append(filtro_categoria)
    nombres_productos_query += " ORDER BY nombre_producto;"
    cur.execute(nombres_productos_query, nombres_params)
    nombres_productos = [row['nombre_producto'] for row in cur.fetchall()]

    cur.execute("SELECT * FROM sucursal ORDER BY id_sucursal;")
    sucursales = cur.fetchall()

    cur.close()
    conn.close()

    filtros_activos = {
        'categoria': filtro_categoria,
        'nombre': filtro_nombre,
        'sucursal': filtro_sucursal,
        'q': q
    }

    return render_template(
        "productos/crud_productos.html", 
        productos=productos, 
        sucursales=sucursales,
        categorias=categorias,
        nombres_productos=nombres_productos,
        filtros_activos=filtros_activos
    )

# ---------------------------
# Filtro de Búsqueda CRUD DE PRODUCTO
# ---------------------------
# ===========================
# API PARA FILTROS DINÁMICOS
# ===========================
@app.route("/api/productos/nombres_por_categoria")
@login_required
def api_nombres_por_categoria():
    """
    Devuelve una lista JSON de nombres de productos filtrados por una categoría.
    Si no se proporciona categoría, devuelve todos los nombres distintos.
    """
    categoria = request.args.get('categoria', '')
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        if categoria:
            # Si se especifica una categoría, filtra por ella
            cur.execute("""
                SELECT DISTINCT nombre_producto FROM producto 
                WHERE categoria_producto = %s 
                ORDER BY nombre_producto;
            """, (categoria,))
        else:
            # Si no, devuelve todos los nombres de productos
            cur.execute("SELECT DISTINCT nombre_producto FROM producto ORDER BY nombre_producto;")
            
        nombres = [row[0] for row in cur.fetchall()]
        return jsonify({"nombres": nombres})

    except Exception as e:
        # Manejo básico de errores
        print(f"Error en la API de nombres por categoría: {e}")
        return jsonify({"nombres": [], "error": str(e)}), 500
    finally:
        cur.close()
        conn.close()


# ---------------------------
# Rutas de Productos
# ---------------------------

# ---------------------------
# Agregar Productos
# ---------------------------

@app.route("/add", methods=["POST"])
def add_producto():
    # --- 1. Obtenemos los 5 dígitos del SKU y construimos el SKU completo ---
    sku_digits = request.form["sku_digits"]
    sku = f"AUR-{sku_digits}" # Construimos el SKU final. Ej: "AUR-00001"
    
    # El resto de los datos se obtienen igual
    nombre = request.form["nombre"]
    precio = request.form["precio"]
    color = request.form.get("color")
    descripcion = request.form.get("descripcion")
    categoria = request.form.get("categoria")
    imagen_url = request.form.get("imagen_url")

    if not color:
        flash("❌ Error: Debes seleccionar un color para el producto.", "danger")
        return redirect(url_for("crud_productos"))

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # --- 2. Validar que el SKU COMPLETO no exista ---
        cur.execute("SELECT id_producto FROM producto WHERE sku = %s", (sku,))
        if cur.fetchone():
            flash(f"❌ Error: El SKU '{sku}' ya está registrado.", "danger")
            return redirect(url_for("crud_productos"))

        # --- 3. Insertar el producto con el SKU COMPLETO ---
        cur.execute("""
            INSERT INTO producto (sku, nombre_producto, precio_producto, descripcion_producto, categoria_producto, imagen_url)
            VALUES (%s, %s, %s, %s, %s, %s) RETURNING id_producto;
        """, (sku, nombre, precio, descripcion, categoria, imagen_url))
        
        id_producto_nuevo = cur.fetchone()[0]

        # --- 4. Crear la variación de color Y SU SKU BASE ---
        
        # ¡NUEVA LÍNEA! Generamos el SKU para la variación base (producto + color)
        sku_variacion_base = f"{sku}-{color[:3].upper()}"

        # ¡LÍNEA MODIFICADA! Añadimos el nuevo sku_variacion_base al INSERT
        cur.execute("""
            INSERT INTO variacion_producto (id_producto, color, sku_variacion)
            VALUES (%s, %s, %s);
        """, (id_producto_nuevo, color, sku_variacion_base))
        
        # --- 5. Guardar cambios ---
        conn.commit()
        flash(" ✅ Producto agregado con éxito", "success")

    except Exception as e:
        conn.rollback()
        flash(f"❌ Ocurrió un error al agregar el producto: {e}", "danger")
    
    finally:
        cur.close()
        conn.close()

    return redirect(url_for("crud_productos"))

# ---------------------------
# Editar Productos
# ---------------------------

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

    # Validar SKU único (excluyendo el producto actual)
    cur.execute("SELECT id_producto FROM producto WHERE sku = %s AND id_producto != %s", (sku, id))
    existing = cur.fetchone()
    if existing:
        flash(f"❌ Error: El SKU '{sku}' ya está registrado en otro producto.", "danger")
        cur.close()
        conn.close()
        return redirect(url_for("crud_productos"))


    # UPDATE de Actualizar Producto
    cur.execute("""
        UPDATE producto
        SET sku = %s, nombre_producto = %s, precio_producto = %s,
            descripcion_producto = %s, categoria_producto = %s, imagen_url = %s
        WHERE id_producto = %s
    """, (sku, nombre, precio, descripcion, categoria, imagen_url, id))
    conn.commit()
    cur.close()
    conn.close()
    flash("✅ Producto actualizado", "success")
    return redirect(url_for("crud_productos"))

# ---------------------------
# Editar Stock de Productos
# ---------------------------

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
    flash("✅ Stock actualizado", "success")
    return redirect(url_for("crud_productos"))

# ---------------------------
# Eliminar Productos
# ---------------------------

@app.route("/delete/<int:id>", methods=["POST"])
def delete_producto(id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM producto WHERE id_producto = %s", (id,))
    conn.commit()
    cur.close()
    conn.close()
    flash(" ❌ Producto eliminado", "danger")
    return redirect(url_for("crud_productos"))

# ---------------------------
# Ver stock del Listado de Productos
# ---------------------------

# REEMPLAZA ESTA FUNCIÓN COMPLETA en app.py

@app.route("/ver_stock/<int:id_producto>")
@login_required
def ver_stock(id_producto):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    # 1. Obtener información del producto (sin cambios)
    cur.execute("SELECT * FROM producto WHERE id_producto = %s", (id_producto,))
    producto = cur.fetchone()
    if not producto:
        flash("Producto no encontrado.", "danger")
        return redirect(url_for("crud_productos"))

    # 2. Determinar las tallas disponibles (sin cambios)
    categoria = (producto["categoria_producto"] or "").strip()
    tallas_disponibles = []
    if categoria in CATEGORIAS_ROPA:
        tallas_disponibles = TALLAS_ROPA
    elif categoria in CATEGORIAS_CALZADO:
        tallas_disponibles = TALLAS_CALZADO
    
    usa_tallas = bool(tallas_disponibles)

    # 3. Obtener todas las sucursales (sin cambios)
    cur.execute("SELECT * FROM sucursal ORDER BY id_sucursal")
    sucursales = cur.fetchall()

    # 4. Obtener el stock por talla y el total por sucursal (sin cambios)
    stock_por_talla = {}
    stock_total_sucursal = {}
    for s in sucursales:
        id_sucursal = s["id_sucursal"]
        cur.execute("""
            SELECT v.talla, COALESCE(i.stock, 0) as stock
            FROM variacion_producto v
            LEFT JOIN inventario_sucursal i ON v.id_variacion = i.id_variacion AND i.id_sucursal = %s
            WHERE v.id_producto = %s
        """, (id_sucursal, id_producto))
        
        stock_tallas_sucursal = {row['talla']: row['stock'] for row in cur.fetchall()}
        stock_por_talla[id_sucursal] = stock_tallas_sucursal
        stock_total_sucursal[id_sucursal] = sum(stock_tallas_sucursal.values())

    cur.close()
    conn.close()

    # ¡NUEVO! 5. Calcular el stock total del producto sumando el de todas las sucursales.
    stock_total_producto = sum(stock_total_sucursal.values())

    return render_template(
        "productos/ver_stock.html",
        producto=producto,
        sucursales=sucursales,
        usa_tallas=usa_tallas,
        tallas_disponibles=tallas_disponibles,
        stock_por_talla=stock_por_talla,
        stock_total_sucursal=stock_total_sucursal,
        stock_total_producto=stock_total_producto  # ¡NUEVO! Enviamos el total general a la plantilla.
    )

# ---------------------------
# Gestionar talla de stock de productos
# ---------------------------

@app.route("/productos/<int:id_producto>/actualizar_stock_por_tallas", methods=["POST"])
@login_required
def actualizar_stock_por_tallas(id_producto):
    id_sucursal = request.form.get("id_sucursal")
    if not id_sucursal:
        flash("❌ Error: No se especificó una sucursal.", "danger")
        return redirect(url_for("ver_stock", id_producto=id_producto))

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    try:
        # 1. Obtener el color base y el SKU base del producto
        cur.execute("""
            SELECT p.sku, v.color 
            FROM producto p
            JOIN variacion_producto v ON p.id_producto = v.id_producto
            WHERE p.id_producto = %s AND v.color IS NOT NULL 
            LIMIT 1;
        """, (id_producto,))
        info_base = cur.fetchone()
        color_base = info_base['color'] if info_base else 'SIN_COLOR'
        sku_base = info_base['sku'] if info_base else f'SKU-{id_producto}'

        # 2. Recolectar las nuevas cantidades del formulario
        nuevas_cantidades = {}
        for key, value in request.form.items():
            if key.startswith("stock_talla_"):
                talla = key.replace("stock_talla_", "")
                cantidad = max(0, int(value or 0))
                nuevas_cantidades[talla] = cantidad

        # 3. Actualizar la base de datos
        for talla, cantidad in nuevas_cantidades.items():
            # Generar el SKU de variación
            sku_variacion = f"{sku_base}-{color_base[:3].upper()}-{talla.upper()}"

            # Buscar si la variación (producto + talla) ya existe
            cur.execute("SELECT id_variacion FROM variacion_producto WHERE id_producto = %s AND talla = %s", (id_producto, talla))
            variacion = cur.fetchone()
            
            if not variacion:
                # Si no existe, la CREA con el color y el SKU de variación
                cur.execute("""
                    INSERT INTO variacion_producto (id_producto, talla, color, sku_variacion) 
                    VALUES (%s, %s, %s, %s) RETURNING id_variacion
                """, (id_producto, talla, color_base, sku_variacion))
                id_variacion = cur.fetchone()[0]
            else:
                # Si ya existe, solo actualiza su SKU por si acaso no lo tenía
                id_variacion = variacion[0]
                cur.execute("UPDATE variacion_producto SET sku_variacion = %s WHERE id_variacion = %s", (sku_variacion, id_variacion))

            # Finalmente, inserta o actualiza el stock en el inventario
            cur.execute("""
                INSERT INTO inventario_sucursal (id_sucursal, id_variacion, stock) VALUES (%s, %s, %s)
                ON CONFLICT (id_sucursal, id_variacion) DO UPDATE SET stock = EXCLUDED.stock;
            """, (id_sucursal, id_variacion, cantidad))
        
        conn.commit()
        flash("✅ Stock por tallas actualizado correctamente.", "success")

    except Exception as e:
        conn.rollback()
        flash(f"❌ Error al actualizar el stock: {e}", "danger")
    finally:
        cur.close()
        conn.close()

    return redirect(url_for("ver_stock", id_producto=id_producto))


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
        flash(f"❌ No puedes asignar {total_nuevo} unidades. El máximo permitido es {stock_max}.")
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
    flash("✅ Stock por sucursal actualizado correctamente.")
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

    flash("✅ Stock actualizado en la sucursal", "success")
    return redirect(url_for("ver_stock", id_producto=id_producto))


# ---------------------------
# CRUD Sucursales
# ---------------------------

@app.route('/sucursales')
@login_required
def crud_sucursales():
    # 1. Obtener los parámetros de filtrado desde la URL
    filtro_nombre = request.args.get('filtro_nombre', '')
    filtro_region = request.args.get('filtro_region', '')
    filtro_comuna = request.args.get('filtro_comuna', '')
    q = request.args.get('q', '')

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    # 2. Construir la consulta SQL principal para la tabla (sin cambios)
    base_query = "SELECT * FROM sucursal"
    where_clauses = []
    params = []

    if q:
        where_clauses.append("id_sucursal::text ILIKE %s")
        params.append(f"%{q}%")
    if filtro_nombre:
        where_clauses.append("nombre_sucursal = %s") # Cambiado a '=' para coincidencia exacta del select
        params.append(filtro_nombre)
    if filtro_region:
        where_clauses.append("region_sucursal = %s") # Cambiado a '='
        params.append(filtro_region)
    if filtro_comuna:
        where_clauses.append("comuna_sucursal = %s") # Cambiado a '='
        params.append(filtro_comuna)

    final_query = base_query
    if where_clauses:
        final_query += " WHERE " + " AND ".join(where_clauses)
    final_query += " ORDER BY id_sucursal;"
    
    cur.execute(final_query, tuple(params))
    sucursales = cur.fetchall()

    # 3. Obtener listas para los menús desplegables de forma contextual
    # Para Regiones (siempre todas)
    cur.execute("SELECT DISTINCT region_sucursal FROM sucursal ORDER BY region_sucursal;")
    regiones = [row['region_sucursal'] for row in cur.fetchall()]
    
    # Para Comunas (depende de la región seleccionada)
    comunas_query = "SELECT DISTINCT comuna_sucursal FROM sucursal"
    comunas_params = []
    if filtro_region:
        comunas_query += " WHERE region_sucursal = %s"
        comunas_params.append(filtro_region)
    comunas_query += " ORDER BY comuna_sucursal;"
    cur.execute(comunas_query, comunas_params)
    comunas = [row['comuna_sucursal'] for row in cur.fetchall()]

    # Para Nombres de sucursal (depende de la comuna y región seleccionadas)
    nombres_query = "SELECT DISTINCT nombre_sucursal FROM sucursal"
    nombres_params = []
    nombres_where = []
    if filtro_region:
        nombres_where.append("region_sucursal = %s")
        nombres_params.append(filtro_region)
    if filtro_comuna:
        nombres_where.append("comuna_sucursal = %s")
        nombres_params.append(filtro_comuna)
    if nombres_where:
        nombres_query += " WHERE " + " AND ".join(nombres_where)
    nombres_query += " ORDER BY nombre_sucursal;"
    cur.execute(nombres_query, nombres_params)
    nombres_sucursales = [row['nombre_sucursal'] for row in cur.fetchall()]

    cur.close()
    conn.close()

    filtros_activos = {
        'nombre': filtro_nombre,
        'region': filtro_region,
        'comuna': filtro_comuna,
        'q': q
    }

    return render_template(
        "sucursales/crud_sucursales.html", 
        sucursales=sucursales,
        nombres_sucursales=nombres_sucursales,
        regiones=regiones,
        comunas=comunas,
        filtros_activos=filtros_activos
    )

# ---------------------------
# Filtrado de Sucursales: Comunas por Región escogida
# ---------------------------

@app.route("/api/sucursales/comunas_por_region")
@login_required
def api_comunas_por_region():
    region = request.args.get('region', '')
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        if region:
            cur.execute("SELECT DISTINCT comuna_sucursal FROM sucursal WHERE region_sucursal = %s ORDER BY comuna_sucursal;", (region,))
        else:
            cur.execute("SELECT DISTINCT comuna_sucursal FROM sucursal ORDER BY comuna_sucursal;")
        comunas = [row[0] for row in cur.fetchall()]
        return jsonify({"comunas": comunas})
    except Exception as e:
        return jsonify({"comunas": [], "error": str(e)}), 500
    finally:
        cur.close()
        conn.close()

# ---------------------------
# Filtrado de Sucursales: Nombres por Comuna escogida
# ---------------------------

@app.route("/api/sucursales/nombres_por_comuna")
@login_required
def api_nombres_por_comuna():
    comuna = request.args.get('comuna', '')
    region = request.args.get('region', '')
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        query = "SELECT DISTINCT nombre_sucursal FROM sucursal"
        where_clauses = []
        params = []
        if comuna:
            where_clauses.append("comuna_sucursal = %s")
            params.append(comuna)
        if region:
            where_clauses.append("region_sucursal = %s")
            params.append(region)

        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)
        
        query += " ORDER BY nombre_sucursal;"
        
        cur.execute(query, tuple(params))
        nombres = [row[0] for row in cur.fetchall()]
        return jsonify({"nombres": nombres})
    except Exception as e:
        return jsonify({"nombres": [], "error": str(e)}), 500
    finally:
        cur.close()
        conn.close()


# ---------------------------
# Rutas de Sucursales
# ---------------------------

# ---------------------------
# Agregar Sucursales
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
    flash("✅ Sucursal agregada con éxito", "success")
    return redirect(url_for("crud_sucursales"))

# ---------------------------
# Api para validar teléfono de la sucursal en la base de datos
# ---------------------------

@app.route('/api/check_telefono_sucursal', methods=['GET'])
@login_required
def check_telefono_sucursal():
    """
    Verifica si un número de teléfono ya está registrado en la base de datos,
    con la opción de excluir un ID de sucursal específico (para la edición).
    """
    telefono = request.args.get('telefono')
    exclude_id = request.args.get('exclude_id') # Nuevo parámetro para ignorar un ID

    if not telefono:
        return jsonify({'exists': False})

    conn = get_db_connection()
    cur = conn.cursor()
    try:
        query = "SELECT 1 FROM sucursal WHERE telefono_sucursal = %s"
        params = [telefono]

        # Si estamos editando, añadimos una condición para excluir la propia sucursal de la búsqueda
        if exclude_id:
            query += " AND id_sucursal != %s"
            params.append(exclude_id)
        
        query += " LIMIT 1;"
        
        cur.execute(query, tuple(params))
        telefono_exists = cur.fetchone() is not None
        return jsonify({'exists': telefono_exists})
    except Exception as e:
        print(f"Error al verificar el teléfono de sucursal: {e}")
        return jsonify({'exists': False}), 500
    finally:
        cur.close()
        conn.close()

# ---------------------------
# Api para validar dirección de la sucursal en la base de datos
# ---------------------------

@app.route('/api/check_direccion_sucursal', methods=['GET'])
@login_required
def check_direccion_sucursal():
    """
    Verifica si una dirección ya está registrada en otra sucursal,
    con la opción de excluir un ID de sucursal específico (para la edición).
    """
    direccion = request.args.get('direccion', '')
    exclude_id = request.args.get('exclude_id')

    if not direccion:
        return jsonify({'exists': False})

    conn = get_db_connection()
    cur = conn.cursor()
    try:
        # Usamos ILIKE para una comparación insensible a mayúsculas/minúsculas
        query = "SELECT 1 FROM sucursal WHERE direccion_sucursal ILIKE %s"
        params = [direccion.strip()]

        if exclude_id:
            query += " AND id_sucursal != %s"
            params.append(exclude_id)
        
        query += " LIMIT 1;"
        
        cur.execute(query, tuple(params))
        direccion_exists = cur.fetchone() is not None
        return jsonify({'exists': direccion_exists})
    except Exception as e:
        print(f"Error al verificar la dirección de sucursal: {e}")
        return jsonify({'exists': False}), 500
    finally:
        cur.close()
        conn.close()

# ---------------------------
# Editar Sucursales
# ---------------------------

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
    flash("✅ Sucursal actualizada con éxito", "success")
    return redirect(url_for("crud_sucursales"))

# ---------------------------
# Eliminar Sucursales
# ---------------------------

@app.route("/eliminar_sucursal/<int:id_sucursal>", methods=["POST"])
def eliminar_sucursal(id_sucursal):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM sucursal WHERE id_sucursal = %s", (id_sucursal,))
    conn.commit()
    cur.close()
    conn.close()
    flash("✅ Sucursal eliminada con éxito", "danger")
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
# CRUD USUARIOS
# ===========================

@app.route('/usuarios')
@login_required
def crud_usuarios():
    # 1. Obtener los parámetros de filtrado desde la URL
    filtro_rol = request.args.get('filtro_rol', '')
    filtro_nombre = request.args.get('filtro_nombre', '')

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    # 2. Construir la consulta SQL de forma dinámica
    base_query = """
        SELECT id_usuario, nombre_usuario, apellido_paterno, apellido_materno, rol_usuario, email_usuario, 
               calle, numero_calle, region, ciudad, comuna, telefono
        FROM usuario
    """
    where_clauses = []
    params = []

    if filtro_rol:
        where_clauses.append("rol_usuario = %s")
        params.append(filtro_rol)
    
    if filtro_nombre:
        # Usamos CONCAT para buscar en nombre y apellidos
        where_clauses.append("CONCAT(nombre_usuario, ' ', apellido_paterno, ' ', apellido_materno) ILIKE %s")
        params.append(f"%{filtro_nombre}%")

    # 3. Ensamblar y ejecutar la consulta final
    final_query = base_query
    if where_clauses:
        final_query += " WHERE " + " AND ".join(where_clauses)
    
    final_query += " ORDER BY id_usuario;"
    
    cur.execute(final_query, tuple(params))
    usuarios = cur.fetchall()

    # 4. Obtener listas únicas para poblar los menús desplegables de los filtros
    cur.execute("SELECT DISTINCT rol_usuario FROM usuario WHERE rol_usuario IS NOT NULL ORDER BY rol_usuario;")
    roles = [row['rol_usuario'] for row in cur.fetchall()]
    
    cur.execute("SELECT DISTINCT nombre_usuario FROM usuario ORDER BY nombre_usuario;")
    nombres_usuarios = [row['nombre_usuario'] for row in cur.fetchall()]

    cur.close()
    conn.close()

    # 5. Guardar los filtros activos para "recordarlos" en el formulario
    filtros_activos = {
        'rol': filtro_rol,
        'nombre': filtro_nombre
    }

    return render_template(
        "usuarios/crud_usuarios.html", 
        usuarios=usuarios,
        roles=roles,
        nombres_usuarios=nombres_usuarios,
        filtros_activos=filtros_activos
    )

# ===========================
# Agregar USUARIOS
# ===========================

@app.route("/usuarios/add", methods=["POST"])
@login_required
def add_usuario():
    data = request.form
    telefono = data.get("telefono")  # <-- Definición de la variable teléfono aquí
    email_usuario = data.get("email_usuario")  # <-- Definición de la variable email para "email_usuario" aquí
    password_hash = generate_password_hash(data["password"])
    conn = get_db_connection()
    cur = conn.cursor()

    # Validar correo electrónico duplicado
    cur.execute("SELECT id_usuario FROM usuario WHERE email_usuario = %s", (email_usuario,))
    existing_email = cur.fetchone()
    if existing_email:
        flash(f"❌ Error: El correo '{email_usuario}' ya está registrado en otro usuario.", "danger")
        cur.close()
        conn.close()
        return redirect(url_for("crud_usuarios"))


    # Validar que el teléfono no exista
    cur.execute("SELECT id_usuario FROM usuario WHERE telefono = %s", (telefono, )) 
    existing = cur.fetchone()
    if existing:
        flash(f"❌ Error: El teléfono '{telefono}' ya está registrado en otro usuario.", "danger")
        cur.close()
        conn.close()
        return redirect(url_for("crud_usuarios"))

    # Insertar Usuario
    try:
        cur.execute("""
            INSERT INTO usuario (nombre_usuario, apellido_paterno, apellido_materno, rol_usuario, email_usuario, password, calle, numero_calle, region, ciudad, comuna, telefono)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            data.get("nombre_usuario"),
            data.get("apellido_paterno"),
            data.get("apellido_materno"),
            data.get("rol_usuario"),
            data.get("email_usuario"),
            password_hash,
            data.get("calle"),
            data.get("numero_calle"),
            data.get("region"),
            data.get("ciudad"),
            data.get("comuna"),
            data.get("telefono")
        ))
        conn.commit()
        flash("✅ Usuario agregado correctamente", "success")
    except Exception as e:
        conn.rollback()
        flash(f"❌ Error: {str(e)}", "danger")
    finally:
        cur.close()
        conn.close()
    return redirect(url_for("crud_usuarios"))

# ===========================
# Editar USUARIOS
# ===========================

@app.route("/usuarios/edit/<int:id_usuario>", methods=["POST"])
@login_required
def edit_usuario(id_usuario):
    data = request.form
    telefono = data.get("telefono")  # <-- definir aquí
    email_usuario = data.get("email")  # <-- definir aquí
    conn = get_db_connection()
    cur = conn.cursor()

    # 🔹 Validar correo electrónico duplicado (en otro usuario)
    cur.execute("SELECT id_usuario FROM usuario WHERE email_usuario = %s AND id_usuario != %s", (email_usuario, id_usuario))
    existing_email = cur.fetchone()
    if existing_email:
        flash(f"❌ Error: El correo '{email_usuario}' ya está registrado en otro usuario.", "danger")
        cur.close()
        conn.close()
        return redirect(url_for("crud_usuarios"))

    # Validar que el teléfono no exista en otro usuario
    cur.execute("SELECT id_usuario FROM usuario WHERE telefono = %s AND id_usuario != %s", (telefono, id_usuario))
    existing = cur.fetchone()
    if existing:
        flash(f"❌ Error: El teléfono '{telefono}' ya está registrado en otro usuario.", "danger")
        cur.close()
        conn.close()
        return redirect(url_for("crud_usuarios"))

    try:
        # Solo actualizar password si no está vacío
        if data.get("password"):
            password_hash = generate_password_hash(data["password"])
            cur.execute("""
                UPDATE usuario SET nombre_usuario=%s, apellido_paterno=%s, apellido_materno=%s,
                    rol_usuario=%s, email_usuario=%s, password=%s, calle=%s, numero_calle=%s,
                    region=%s, ciudad=%s, comuna=%s, telefono=%s
                WHERE id_usuario=%s
            """, (
                data.get("nombre_usuario"),
                data.get("apellido_paterno"),
                data.get("apellido_materno"),
                data.get("rol_usuario"),
                data.get("email_usuario"),
                password_hash,
                data.get("calle"),
                data.get("numero_calle"),
                data.get("region"),
                data.get("ciudad"),
                data.get("comuna"),
                data.get("telefono"),
                id_usuario
            ))
        else:
            cur.execute("""
                UPDATE usuario SET nombre_usuario=%s, apellido_paterno=%s, apellido_materno=%s,
                    rol_usuario=%s, email_usuario=%s, calle=%s, numero_calle=%s,
                    region=%s, ciudad=%s, comuna=%s, telefono=%s
                WHERE id_usuario=%s
            """, (
                data.get("nombre_usuario"),
                data.get("apellido_paterno"),
                data.get("apellido_materno"),
                data.get("rol_usuario"),
                data.get("email_usuario"),
                data.get("calle"),
                data.get("numero_calle"),
                data.get("region"),
                data.get("ciudad"),
                data.get("comuna"),
                data.get("telefono"),
                id_usuario
            ))
        conn.commit()
        flash("✅ Usuario actualizado correctamente", "success")
    except Exception as e:
        conn.rollback()
        flash(f"❌ Error: {str(e)}", "danger")
    finally:
        cur.close()
        conn.close()
    return redirect(url_for("crud_usuarios"))

# ===========================
# Eliminar USUARIOS
# ===========================

@app.route("/usuarios/delete/<int:id_usuario>", methods=["POST"])
@login_required
def delete_usuario(id_usuario):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM usuario WHERE id_usuario=%s", (id_usuario,))
        conn.commit()
        flash("✅ Usuario eliminado correctamente", "success")
    except Exception as e:
        conn.rollback()
        flash(f"❌ Error: {str(e)}", "danger")
    finally:
        cur.close()
        conn.close()
    return redirect(url_for("crud_usuarios"))


# ===========================
# CRUD USUARIOS: Listado de Usuarios
# ===========================

@app.route("/usuarios/view/<int:id_usuario>")
@login_required
def view_usuario(id_usuario):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute("""
        SELECT * FROM usuario WHERE id_usuario=%s
    """, (id_usuario,))
    usuario = cur.fetchone()
    cur.close()
    conn.close()
    return render_template("usuarios/view_usuario.html", usuario=usuario)


# ===========================
# CRUD OFERTAS 
# ===========================

# REEMPLAZA ESTA FUNCIÓN COMPLETA en app.py

@app.route('/ofertas')
@login_required # Es buena práctica proteger las vistas
def crud_ofertas():
    # 1. Obtener parámetros de filtrado desde la URL
    filtro_id = request.args.get('q', '')
    filtro_estado = request.args.get('filtro_estado', '')
    filtro_titulo = request.args.get('filtro_titulo', '')
    filtro_producto = request.args.get('filtro_producto', '')
    filtro_descuento = request.args.get('filtro_descuento', '')

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    # 2. Construir la consulta SQL dinámicamente
    base_query = """
        SELECT o.id_oferta, o.titulo, o.descripcion, o.descuento_pct, o.fecha_inicio, o.fecha_fin, o.vigente_bool,
               p.id_producto, p.nombre_producto, p.imagen_url, p.precio_producto
        FROM oferta o
        JOIN oferta_producto op ON o.id_oferta = op.id_oferta
        JOIN producto p ON op.id_producto = p.id_producto
    """
    where_clauses = []
    params = []

    if filtro_id:
        where_clauses.append("o.id_oferta::text ILIKE %s")
        params.append(f"%{filtro_id}%")
    
    if filtro_titulo:
        where_clauses.append("o.titulo = %s")
        params.append(filtro_titulo)
        
    if filtro_producto:
        where_clauses.append("p.id_producto = %s")
        params.append(filtro_producto)

    # Lógica para filtro de estado (derivado de las fechas)
    if filtro_estado == 'vigente':
        where_clauses.append("CURRENT_DATE BETWEEN o.fecha_inicio AND o.fecha_fin")
    elif filtro_estado == 'finalizada':
        where_clauses.append("o.fecha_fin < CURRENT_DATE")
    elif filtro_estado == 'en_espera':
        where_clauses.append("o.fecha_inicio > CURRENT_DATE")

    # Lógica para filtro de descuento por rangos
    if filtro_descuento == 'high':
        where_clauses.append("o.descuento_pct BETWEEN 70 AND 95")
    elif filtro_descuento == 'medium':
        where_clauses.append("o.descuento_pct BETWEEN 30 AND 69.99")
    elif filtro_descuento == 'low':
        where_clauses.append("o.descuento_pct BETWEEN 5 AND 29.99")

    # 3. Ensamblar y ejecutar la consulta
    final_query = base_query
    if where_clauses:
        final_query += " WHERE " + " AND ".join(where_clauses)
    
    final_query += " ORDER BY o.id_oferta DESC;"
    
    cur.execute(final_query, tuple(params))
    ofertas = cur.fetchall()

    # 4. Obtener datos para poblar los menús desplegables de los filtros
    # Esta es la corrección
    cur.execute("""
                SELECT p.id_producto, p.nombre_producto, COALESCE(SUM(i.stock), 0) AS stock
                FROM producto p
                LEFT JOIN variacion_producto v ON v.id_producto = p.id_producto
                LEFT JOIN inventario_sucursal i ON i.id_variacion = v.id_variacion
                GROUP BY p.id_producto, p.nombre_producto
                ORDER BY p.nombre_producto;
                """)
    productos = cur.fetchall() # Reutilizamos esta lista para el formulario de agregar y el filtro
    
    cur.execute("SELECT DISTINCT titulo FROM oferta ORDER BY titulo;")
    titulos_ofertas = [row['titulo'] for row in cur.fetchall()]

    cur.close()
    conn.close()

    # 5. Guardar los filtros activos para "recordarlos" en el formulario
    filtros_activos = {
        'q': filtro_id,
        'estado': filtro_estado,
        'titulo': filtro_titulo,
        'producto': filtro_producto,
        'descuento': filtro_descuento
    }

    return render_template(
        "ofertas/crud_ofertas.html",
        ofertas=ofertas,
        productos=productos,
        titulos_ofertas=titulos_ofertas,
        filtros_activos=filtros_activos,
        now=datetime.datetime.now, # Tu código original ya lo pasaba
    )

# ===========================
# Filtrado de ofertas: Por Estado
# ===========================

@app.route("/api/ofertas/titulos_por_estado")
@login_required
def api_titulos_por_estado():
    """
    Devuelve una lista JSON de títulos de ofertas filtrados por su estado (vigente, finalizada, en_espera).
    """
    estado = request.args.get('estado', '')
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        query = "SELECT DISTINCT titulo FROM oferta"
        params = []
        
        # Traducimos el 'estado' a una condición SQL sobre las fechas
        if estado == 'vigente':
            query += " WHERE CURRENT_DATE BETWEEN fecha_inicio AND fecha_fin"
        elif estado == 'finalizada':
            query += " WHERE fecha_fin < CURRENT_DATE"
        elif estado == 'en_espera':
            query += " WHERE fecha_inicio > CURRENT_DATE"
        
        query += " ORDER BY titulo;"
        
        cur.execute(query, tuple(params))
        titulos = [row[0] for row in cur.fetchall()]
        return jsonify({"titulos": titulos})

    except Exception as e:
        print(f"Error en la API de títulos por estado: {e}")
        return jsonify({"titulos": [], "error": str(e)}), 500
    finally:
        cur.close()
        conn.close()


# ===========================
# Agregar OFERTAS 
# ===========================

from datetime import date

@app.route("/ofertas/add", methods=["POST"])
@login_required
def add_oferta():
    data = request.form
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        # Obtener fechas desde el formulario
        fecha_inicio = data.get("fecha_inicio")
        fecha_fin = data.get("fecha_fin")

        # Calcular si la oferta está vigente actualmente
        hoy = date.today()
        vigente = fecha_inicio <= str(hoy) <= fecha_fin

        # Insertar la nueva oferta
        cur.execute("""
            INSERT INTO oferta (titulo, descripcion, descuento_pct, fecha_inicio, fecha_fin, vigente_bool)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id_oferta;
        """, (
            data.get("titulo"),
            data.get("descripcion"),
            data.get("descuento_pct"),
            fecha_inicio,
            fecha_fin,
            vigente
        ))
        id_oferta = cur.fetchone()[0]

        # Asociar producto a la oferta
        id_producto = data.get("productos")
        if id_producto and id_producto.strip() != "":
            id_producto = int(id_producto)
            cur.execute("""
                INSERT INTO oferta_producto (id_oferta, id_producto)
                VALUES (%s, %s);
            """, (id_oferta, id_producto))
        else:
            raise ValueError("Debes seleccionar un producto para la oferta")

        conn.commit()
        flash("✅ Oferta agregada correctamente", "success")

    except Exception as e:
        conn.rollback()
        flash(f"❌ Error al agregar la oferta: {str(e)}", "danger")

    finally:
        cur.close()
        conn.close()

    return redirect(url_for("crud_ofertas"))



# ===========================
# Editar OFERTAS 
# ===========================

@app.route("/ofertas/edit/<int:id_oferta>", methods=["GET", "POST"])
@login_required
def edit_oferta(id_oferta):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    if request.method == "POST":
        data = request.form
        try:
            # --- INICIO DE LA LÓGICA CORREGIDA ---
            # 1. Obtenemos las fechas del formulario de edición.
            fecha_inicio_str = data.get("fecha_inicio")
            fecha_fin_str = data.get("fecha_fin")
            
            # 2. Obtenemos la fecha de hoy para comparar.
            hoy_str = date.today().isoformat()
            
            # 3. Recalculamos si la oferta está vigente con las nuevas fechas.
            vigente = (fecha_inicio_str <= hoy_str <= fecha_fin_str)
            # --- FIN DE LA LÓGICA CORREGIDA ---

            cur.execute("""
                UPDATE oferta
                SET titulo=%s, descripcion=%s, descuento_pct=%s, 
                    fecha_inicio=%s, fecha_fin=%s, vigente_bool=%s
                WHERE id_oferta=%s;
            """, (
                data.get("titulo"),
                data.get("descripcion"),
                data.get("descuento_pct"),
                fecha_inicio_str,      # Usamos la fecha del formulario
                fecha_fin_str,         # Usamos la fecha del formulario
                vigente,               # Usamos el valor booleano que acabamos de calcular
                id_oferta
            ))

            # Actualizar productos asociados (esta parte ya estaba bien)
            cur.execute("DELETE FROM oferta_producto WHERE id_oferta=%s;", (id_oferta,))
            productos_seleccionados = data.getlist("productos") # Corregido a getlist para múltiples productos si se implementa en el futuro
            for id_producto in productos_seleccionados:
                cur.execute("""
                    INSERT INTO oferta_producto (id_oferta, id_producto)
                    VALUES (%s, %s);
                """, (id_oferta, id_producto))

            conn.commit()
            flash("✅ Oferta actualizada correctamente", "success")
        except Exception as e:
            conn.rollback()
            flash(f"❌ Error al actualizar la oferta: {str(e)}", "danger")
        finally:
            cur.close()
            conn.close()
        return redirect(url_for("crud_ofertas"))
    else: # La parte GET para mostrar el modal se mantiene igual
        cur.execute("SELECT * FROM oferta WHERE id_oferta=%s;", (id_oferta,))
        oferta = cur.fetchone()

        cur.execute("SELECT id_producto FROM oferta_producto WHERE id_oferta=%s;", (id_oferta,))
        # ... el resto de tu código GET ...
        
        # Necesitamos la lista de todos los productos para poblar el select en el modal
        cur.execute("""
            SELECT p.id_producto, p.nombre_producto, COALESCE(SUM(i.stock), 0) AS stock
            FROM producto p
            LEFT JOIN variacion_producto v ON v.id_producto = p.id_producto
            LEFT JOIN inventario_sucursal i ON i.id_variacion = v.id_variacion
            GROUP BY p.id_producto, p.nombre_producto
            ORDER BY p.nombre_producto;
        """)
        productos = cur.fetchall()

        cur.close()
        conn.close()
        
        # Renderizar la plantilla principal, el modal se activará desde allí
        return redirect(url_for('crud_ofertas')) # Es mejor redirigir para que la URL se mantenga limpia


# ===========================
# Eliminar OFERTAS 
# ===========================

@app.route("/ofertas/delete/<int:id_oferta>", methods=["POST"])
@login_required
def delete_oferta(id_oferta):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM oferta_producto WHERE id_oferta=%s;", (id_oferta,))
        cur.execute("DELETE FROM oferta WHERE id_oferta=%s;", (id_oferta,))
        conn.commit()
        flash("✅ Oferta eliminada correctamente", "success")
    except Exception as e:
        conn.rollback()
        flash(f"❌ Error al eliminar la oferta: {str(e)}", "danger")
    finally:
        cur.close()
        conn.close()
    return redirect(url_for("crud_ofertas"))


# ===========================
# CRUD OFERTAS: Listado de Ofertas
# ===========================

@app.route("/ofertas/view/<int:id_oferta>")
@login_required
def view_oferta(id_oferta):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute("""
        SELECT 
            o.id_oferta, 
            o.titulo, 
            o.descripcion, 
            o.descuento_pct, 
            o.fecha_inicio, 
            o.fecha_fin, 
            o.vigente_bool,
            STRING_AGG(op.id_producto::TEXT, ', ') AS productos_asociados
        FROM oferta o
        LEFT JOIN oferta_producto op ON o.id_oferta = op.id_oferta
        WHERE o.id_oferta = %s
        GROUP BY o.id_oferta;
    """, (id_oferta,))
    oferta = cur.fetchone()
    cur.close()
    conn.close()
    return render_template("ofertas/crud_ofertas.html", ofertas=ofertas, productos=producto, now=datetime.now)




# ===========================
# HELPERS
# ===========================
def get_user_by_email(email):
    """Obtiene el usuario por email (o None)."""
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute("""
        SELECT id_usuario, nombre_usuario, apellido_paterno, apellido_materno,
               email_usuario, rol_usuario, password, calle, numero_calle, region, ciudad, comuna, telefono, creado_en
        FROM usuario
        WHERE LOWER(email_usuario) = LOWER(%s)
        LIMIT 1;
    """, (email,))
    user = cur.fetchone()
    cur.close()
    conn.close()
    return user
def create_user(data):
    """Crea un usuario con password hasheada (versión para tabla con SERIAL PRIMARY KEY)."""
    email_norm = (data.get("email_usuario") or "").strip().lower()
    password_plano = data.get("password")
    password_hash = generate_password_hash(password_plano)

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    try:
        # Verificar si ya existe un usuario con ese correo
        cur.execute("SELECT 1 FROM usuario WHERE LOWER(email_usuario)=LOWER(%s) LIMIT 1;", (email_norm,))
        if cur.fetchone():
            return False, "El correo ya está registrado."

        query = """
        INSERT INTO usuario (
            nombre_usuario, apellido_paterno, apellido_materno,
            email_usuario, rol_usuario, password,
            calle, numero_calle, region, ciudad, comuna, telefono, creado_en
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id_usuario;
        """

        values = (
            data.get("nombre_usuario"),
            data.get("apellido_paterno"),
            data.get("apellido_materno"),
            email_norm,
            "cliente",  # rol por defecto
            password_hash,
            data.get("calle"),
            data.get("numero_calle"),
            data.get("region"),
            data.get("ciudad"),
            data.get("comuna"),
            data.get("telefono"),
            datetime.utcnow()
        )

        cur.execute(query, values)
        new_id = cur.fetchone()[0]
        conn.commit()
        return True, new_id

    except errors.UniqueViolation:
        conn.rollback()
        return False, "El correo ya está registrado."
    except Exception as e:
        import traceback
        print("❌ Error al obtener ofertas:", e)
        traceback.print_exc()   # 👈 mostrará línea exacta del error
        return jsonify({"ok": False, "error": str(e)}), 500




def do_login(email, password):
    """Valida credenciales y setea sesión."""
    if not email or not password:
        return False, "Debes ingresar correo y contraseña."

    user = get_user_by_email(email)
    if not user or not check_password_hash(user["password"], password):
        return False, "Credenciales inválidas."

    session["user_id"] = user["id_usuario"]
    session["nombre_usuario"] = user["nombre_usuario"]
    session["apellido_paterno"] = user["apellido_paterno"]
    session["apellido_materno"] = user["apellido_materno"]
    session["email_usuario"] = user["email_usuario"]
    session["rol_usuario"] = user["rol_usuario"].strip().lower()
    return True, None


def do_register(data):
    """Crea usuario y auto-login."""
    if not data.get("nombre_usuario") or not data.get("email_usuario") or not data.get("password"):
        return False, "Nombre, correo y contraseña son obligatorios."

    ok, result = create_user(data)
    if not ok:
        return False, result

    ok_l, msg = do_login(data.get("email_usuario"), data.get("password"))
    if not ok_l:
        return False, msg
    return True, None

# ===========================
# RUTAS AUTENTICACIÓN
# ===========================


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return send_from_directory(SRC_DIR, "login.html")

    email = (request.form.get("email_usuario") or "").strip()
    password = (request.form.get("password") or "").strip()

    if not email or not password:
        return redirect(url_for("login") + "?error=missing&tab=login&src=login")

    user = get_user_by_email(email)
    if not user:
        return redirect(url_for("login") + "?error=user_not_found&tab=login&src=login")

    if not check_password_hash(user["password"], password):
        return redirect(url_for("login") + "?error=bad_password&tab=login&src=login")

    session["user_id"] = user["id_usuario"]
    session["nombre_usuario"] = user["nombre_usuario"]
    session["apellido_paterno"] = user["apellido_paterno"]
    session["apellido_materno"] = user["apellido_materno"]
    session["email_usuario"] = user["email_usuario"]
    session["rol_usuario"] = user["rol_usuario"]

    return redirect(FRONTEND_MAIN_URL)

# ===========================
# RUTAS Registro
# ===========================

def validar_password(password):
    """Valida las reglas de la contraseña."""
    if not password:
        return False, "Debes ingresar una contraseña."
    if len(password) < 6 or len(password) > 24:
        return False, "La contraseña debe tener entre 6 y 24 caracteres."
    if not re.search(r"[A-Z]", password):
        return False, "La contraseña debe incluir al menos una letra mayúscula."
    if not re.search(r"\d", password):
        return False, "La contraseña debe incluir al menos un número."
    if not re.search(r"[^A-Za-z0-9]", password):
        return False, "La contraseña debe incluir al menos un carácter especial."
    return True, None

from werkzeug.security import generate_password_hash

from werkzeug.security import generate_password_hash

@app.route("/register", methods=["POST"])
def register():
    data = {
        "nombre_usuario": request.form.get("nombre_usuario"),
        "apellido_paterno": request.form.get("apellido_paterno"),
        "apellido_materno": request.form.get("apellido_materno"),
        "email_usuario": request.form.get("email_usuario"),
        "email_confirm": request.form.get("email_confirm"),
        "password": request.form.get("password"),
        "password_confirm": request.form.get("password_confirm"),
        "calle": request.form.get("calle"),
        "numero_calle": request.form.get("numero_calle"),
        "region": request.form.get("region"),
        "ciudad": request.form.get("ciudad"),
        "comuna": request.form.get("comuna"),
        "telefono": request.form.get("telefono"),
    }

    # ----------------------------
    # 1️⃣ Validaciones
    # ----------------------------
    if data["email_usuario"].lower() != (data["email_confirm"] or "").lower():
        return redirect(url_for("login") + "?error=email_mismatch&tab=register&src=register")
    if data["password"] != data["password_confirm"]:
        return redirect(url_for("login") + "?error=password_mismatch&tab=register&src=register")

    ok, msg = validar_password(data["password"])
    if not ok:
        return redirect(url_for("login") + f"?error=weak_password&tab=register&src=register&msg={msg}")

    # ----------------------------
    # 2️⃣ Insertar en la base de datos con rol 'cliente'
    # ----------------------------
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Validar si el teléfono ya existe
        cur.execute("SELECT 1 FROM usuario WHERE telefono = %s LIMIT 1;", (data["telefono"],))
        if cur.fetchone() is not None:
            return redirect(url_for("login") + "?error=telefono_exists&tab=register&src=register")

        # Validar si el correo ya existe
        cur.execute("SELECT 1 FROM usuario WHERE email_usuario = %s LIMIT 1;", (data["email_usuario"],))
        if cur.fetchone() is not None:
            return redirect(url_for("login") + "?error=email_exists&tab=register&src=register")

        # Hashear contraseña
        hashed_password = generate_password_hash(data["password"])

        # Insertar usuario con rol predeterminado 'cliente'
        cur.execute("""
            INSERT INTO usuario (
                nombre_usuario, apellido_paterno, apellido_materno, email_usuario,
                password, rol_usuario, calle, numero_calle, region, ciudad, comuna, telefono
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
        """, (
            data["nombre_usuario"], data["apellido_paterno"], data["apellido_materno"],
            data["email_usuario"], hashed_password, 'cliente', data["calle"], data["numero_calle"],
            data["region"], data["ciudad"], data["comuna"], data["telefono"]
        ))

        conn.commit()  # Muy importante para guardar el registro
        cur.close()
        conn.close()

    except Exception as e:
        print("Error al registrar usuario:", e)
        return redirect(url_for("login") + "?error=unknown&tab=register&src=register")

    # ----------------------------
    # 3️⃣ Redirigir al frontend
    # ----------------------------
    return redirect(FRONTEND_MAIN_URL)


# ===========================
# Validar Email en registro
# ===========================

@app.route('/check_email', methods=['GET'])
def check_email():
    """
    Ruta para verificar si un correo electrónico ya existe en la base de datos.
    Llamada por JavaScript asíncronamente.
    """
    email = request.args.get('email')

    if not email:
        return jsonify({'exists': False}) # O podrías devolver un error 400

    conn = None # Inicializar conexión
    try:
        # 1. CONEXIÓN A LA BASE DE DATOS
        conn = get_db_connection()
        cur = conn.cursor()

        # 2. CONSULTA SQL
        query = "SELECT 1 FROM usuario WHERE email_usuario = %s LIMIT 1;"
        cur.execute(query, (email,))
        
        # 3. VERIFICACIÓN DE RESULTADOS
        # Si fetchone() no es None, significa que se encontró un registro.
        email_exists = cur.fetchone() is not None

        cur.close()
        # No se hace commit porque solo es una consulta (SELECT)

        # 4. RESPUESTA JSON
        return jsonify({'exists': email_exists})

    except Exception as e:
        print(f"Error al verificar el correo en DB: {e}")
        # En caso de error de DB, lo tratamos como que NO existe para no bloquear al usuario,
        # pero la verificación final en /register lo atrapará.
        return jsonify({'exists': False}), 500 # Devolver un error 500 para indicar un problema en el servidor
    finally:
        if conn:
            conn.close()

# Insertar usuario en DB
    hashed_password = generate_password_hash(password)
    cur.execute("""
        INSERT INTO usuarios (nombre_usuario, apellido_paterno, apellido_materno, email_usuario, telefono, password)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (nombre, apellido_paterno, apellido_materno, email, telefono, hashed_password))

    conn.commit()
    cur.close()
    conn.close()

    return redirect(url_for("crud_usuarios"))

# ===========================
# Validar Email en registro
# ===========================

@app.route('/check_telefono', methods=['GET'])
def check_telefono():
    telefono = request.args.get('telefono')
    if not telefono:
        return jsonify({'exists': False})

    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM usuario WHERE telefono = %s LIMIT 1;", (telefono,))
        telefono_exists = cur.fetchone() is not None
        cur.close()
        return jsonify({'exists': telefono_exists})
    except Exception as e:
        print(f"Error al verificar el teléfono en DB: {e}")
        return jsonify({'exists': False}), 500
    finally:
        if conn:
            conn.close()


@app.route("/logout")
def logout():
    session.clear()
    flash("✅ Sesión cerrada.", "info")
    return redirect(url_for("login"))


def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            flash("⚠️ Debes iniciar sesión.", "warning")
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapper


@app.route("/perfil")
@login_required
def perfil():
    return f"""
    <h1>Perfil</h1>
    <ul>
        <li>ID: {session.get('user_id')}</li>
        <li>Nombre: {session.get('nombre_usuario')}</li>
        <li>Apellido Paterno: {session.get('apellido_paterno')}</li>
        <li>Apellido Materno: {session.get('apellido_materno')}</li>
        <li>Email: {session.get('email_usuario')}</li>
        <li>Rol: {session.get('rol_usuario')}</li>
    </ul>
    """


#Productos para admin producto

# ===========================
# API Productos (JSON)
# ===========================

@app.route("/api/productos", methods=["GET"])
def api_list_productos():
    """Lista productos con stock agregado (como en tu index) + búsqueda + filtro de categoría."""
    q = (request.args.get("q") or "").strip()
    categoria = (request.args.get("categoria") or "").strip()

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    base_sql = """
        SELECT p.id_producto, p.sku, p.nombre_producto, p.descripcion_producto,
            p.categoria_producto, p.precio_producto, p.imagen_url,
            COALESCE(SUM(i.stock),0) as stock
        FROM producto p
        LEFT JOIN variacion_producto v ON v.id_producto = p.id_producto
        LEFT JOIN inventario_sucursal i ON i.id_variacion = v.id_variacion
    """
    where = []
    params = []

    if q:
        where.append("(p.sku ILIKE %s OR p.nombre_producto ILIKE %s)")
        params += [f"%{q}%", f"%{q}%"]
    if categoria and categoria.lower() != "todas":
        where.append("p.categoria_producto ILIKE %s")
        params.append(categoria)

    if where:
        base_sql += " WHERE " + " AND ".join(where)

    base_sql += " GROUP BY p.id_producto ORDER BY p.id_producto;"

    cur.execute(base_sql, params)
    rows = cur.fetchall()
    cur.close()
    conn.close()

    data = [dict(r) for r in rows]
    return jsonify(data), 200


@app.route("/api/productos", methods=["POST"])
def api_create_producto():
    """Crea un producto (usa JSON o form-data)."""
    payload = request.get_json(silent=True) or request.form
    sku = (payload.get("sku") or "").strip()
    nombre = (payload.get("nombre_producto") or "").strip()
    precio = payload.get("precio_producto")
    descripcion = payload.get("descripcion_producto") or None
    categoria = payload.get("categoria_producto") or None
    imagen_url = payload.get("imagen_url") or None

    # Validaciones mínimas
    if not sku or not nombre or not precio:
        return jsonify({"error": "sku, nombre_producto y precio_producto son obligatorios."}), 400

    try:
        precio = float(precio)
    except:
        return jsonify({"error": "precio_producto debe ser numérico."}), 400

    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO producto (sku, nombre_producto, precio_producto, descripcion_producto, categoria_producto, imagen_url)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id_producto;
        """, (sku, nombre, precio, descripcion, categoria, imagen_url))
        new_id = cur.fetchone()[0]
        conn.commit()
        return jsonify({"ok": True, "id_producto": new_id}), 201
    except errors.UniqueViolation:
        conn.rollback()
        return jsonify({"error": "El SKU ya existe."}), 409
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        cur.close()
        conn.close()


@app.route("/api/productos/<int:id_producto>", methods=["PUT", "PATCH"])
def api_update_producto(id_producto):
    """Actualiza un producto."""
    payload = request.get_json(silent=True) or request.form
    sku = payload.get("sku")
    nombre = payload.get("nombre_producto")
    precio = payload.get("precio_producto")
    descripcion = payload.get("descripcion_producto")
    categoria = payload.get("categoria_producto")
    imagen_url = payload.get("imagen_url")

    # construir update dinámico
    sets, params = [], []
    if sku is not None:           sets += ["sku=%s"];                   params.append(sku)
    if nombre is not None:        sets += ["nombre_producto=%s"];       params.append(nombre)
    if precio is not None:        sets += ["precio_producto=%s"];       params.append(precio)
    if descripcion is not None:   sets += ["descripcion_producto=%s"];  params.append(descripcion)
    if categoria is not None:     sets += ["categoria_producto=%s"];    params.append(categoria)
    if imagen_url is not None:    sets += ["imagen_url=%s"];            params.append(imagen_url)

    if not sets:
        return jsonify({"error": "Nada que actualizar."}), 400

    sql = f"UPDATE producto SET {', '.join(sets)} WHERE id_producto=%s"
    params.append(id_producto)

    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(sql, params)
        if cur.rowcount == 0:
            conn.rollback()
            return jsonify({"error": "Producto no encontrado."}), 404
        conn.commit()
        return jsonify({"ok": True}), 200
    except errors.UniqueViolation:
        conn.rollback()
        return jsonify({"error": "El SKU ya existe."}), 409
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        cur.close()
        conn.close()


@app.route("/api/productos/<int:id_producto>", methods=["DELETE"])
def api_delete_producto(id_producto):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM producto WHERE id_producto=%s", (id_producto,))
        if cur.rowcount == 0:
            conn.rollback()
            return jsonify({"error": "Producto no encontrado."}), 404
        conn.commit()
        return jsonify({"ok": True}), 200
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        cur.close()
        conn.close()


@app.route("/api/productos/bulk_delete", methods=["POST"])
def api_bulk_delete_productos():
    payload = request.get_json(silent=True) or {}
    ids = payload.get("ids") or []
    if not isinstance(ids, list) or not ids:
        return jsonify({"error": "Debes enviar lista 'ids'."}), 400

    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM producto WHERE id_producto = ANY(%s::int[])", (ids,))
        conn.commit()
        return jsonify({"ok": True, "deleted": cur.rowcount}), 200
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        cur.close()
        conn.close()


# ===========================
# Mostrar página de Gestión de Imágenes
# ===========================

@app.route('/producto/<int:id_producto>/imagenes', methods=['GET'])
@login_required
def gestionar_imagenes(id_producto):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    # Obtener el producto principal
    cur.execute("SELECT * FROM producto WHERE id_producto = %s", (id_producto,))
    producto = cur.fetchone()

    # Obtener las imágenes adicionales de la nueva tabla
    cur.execute("SELECT * FROM producto_imagenes WHERE id_producto = %s ORDER BY orden", (id_producto,))
    imagenes_adicionales = cur.fetchall()

    cur.close()
    conn.close()

    if not producto:
        flash("❌ Producto no encontrado.", "danger")
        return redirect(url_for('crud_productos'))

    return render_template('productos/gestionar_imagenes.html', producto=producto, imagenes_adicionales=imagenes_adicionales)


# ===========================
# Gestión de Imágenes: Guardar cambios
# ===========================

@app.route('/producto/<int:id_producto>/guardar_imagenes', methods=['POST'])
@login_required
def guardar_imagenes(id_producto):
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # 1. Actualizar la imagen principal en la tabla 'producto'
        imagen_principal_url = request.form.get('imagen_principal')
        cur.execute("UPDATE producto SET imagen_url = %s WHERE id_producto = %s", (imagen_principal_url, id_producto))

        # 2. Borrar las imágenes adicionales antiguas para reemplazarlas
        cur.execute("DELETE FROM producto_imagenes WHERE id_producto = %s", (id_producto,))

        # 3. Insertar las nuevas imágenes adicionales
        imagenes_adicionales = request.form.getlist('imagenes_adicionales[]')
        orden = 1
        for url in imagenes_adicionales:
            if url: # Solo insertar si el campo no está vacío
                cur.execute(
                    "INSERT INTO producto_imagenes (id_producto, url_imagen, orden) VALUES (%s, %s, %s)",
                    (id_producto, url, orden)
                )
                orden += 1
        
        conn.commit()
        flash("✅ Imágenes guardadas correctamente.", "success")

    except Exception as e:
        conn.rollback()
        flash(f"❌ Error al guardar las imágenes: {e}", "danger")
    finally:
        cur.close()
        conn.close()

    return redirect(url_for('gestionar_imagenes', id_producto=id_producto))


# ===========================
# Detalle de los productos en productos.html
# ===========================

## AGREGA ESTA NUEVA RUTA en app.py

@app.route('/api/producto/<int:id_producto>')
def api_detalle_producto(id_producto):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    try:
        cur.execute("SELECT * FROM producto WHERE id_producto = %s", (id_producto,))
        producto = cur.fetchone()

        if not producto:
            return jsonify({"error": "Producto no encontrado"}), 404

        todas_las_imagenes = [producto['imagen_url']] if producto['imagen_url'] else []
        cur.execute("SELECT url_imagen FROM producto_imagenes WHERE id_producto = %s ORDER BY orden", (id_producto,))
        imagenes_adicionales = [row['url_imagen'] for row in cur.fetchall()]
        todas_las_imagenes.extend(imagenes_adicionales)

        cur.execute("""
            SELECT talla, sku_variacion, color FROM variacion_producto 
            WHERE id_producto = %s AND talla IS NOT NULL 
            ORDER BY 
                CASE 
                    WHEN talla = 'XS' THEN 1 WHEN talla = 'S' THEN 2
                    WHEN talla = 'M' THEN 3 WHEN talla = 'L' THEN 4
                    WHEN talla = 'XL' THEN 5 ELSE 6
                END;
        """, (id_producto,))
        variaciones = cur.fetchall()

        # Prepara los datos para enviar como JSON
        datos_producto = {
            "producto": dict(producto),
            "imagenes": todas_las_imagenes,
            "variaciones": [dict(v) for v in variaciones]
        }
        return jsonify(datos_producto)

    except Exception as e:
        print(f"Error en API de detalle de producto: {e}")
        return jsonify({"error": "Error interno del servidor"}), 500
    finally:
        cur.close()
        conn.close()

#productos para la pag principal

# ===========================
# API Productos (JSON - PUBLIC)
# ===========================

@app.route("/api/productos_public", methods=["GET"])
def api_list_productos_public():
    """Lista productos con stock agregado (como en tu index) + búsqueda + filtro de categoría (versión pública)."""
    q = (request.args.get("q") or "").strip()
    categoria = (request.args.get("categoria") or "").strip()

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    base_sql = """
        SELECT p.id_producto, p.sku, p.nombre_producto, p.descripcion_producto,
            p.categoria_producto, p.precio_producto, p.imagen_url,
            COALESCE(SUM(i.stock),0) as stock
        FROM producto p
        LEFT JOIN variacion_producto v ON v.id_producto = p.id_producto
        LEFT JOIN inventario_sucursal i ON i.id_variacion = v.id_variacion
    """
    where = []
    params = []

    if q:
        where.append("(p.sku ILIKE %s OR p.nombre_producto ILIKE %s)")
        params += [f"%{q}%", f"%{q}%"]
    if categoria and categoria.lower() != "todas":
        where.append("p.categoria_producto ILIKE %s")
        params.append(categoria)

    if where:
        base_sql += " WHERE " + " AND ".join(where)

    base_sql += " GROUP BY p.id_producto ORDER BY p.id_producto;"

    cur.execute(base_sql, params)
    rows = cur.fetchall()
    cur.close()
    conn.close()

    data = [dict(r) for r in rows]
    return jsonify(data), 200


@app.route("/api/productos_public", methods=["POST"])
def api_create_producto_public():
    """Crea un producto (usa JSON o form-data)."""
    payload = request.get_json(silent=True) or request.form
    sku = (payload.get("sku") or "").strip()
    nombre = (payload.get("nombre_producto") or "").strip()
    precio = payload.get("precio_producto")
    descripcion = payload.get("descripcion_producto") or None
    categoria = payload.get("categoria_producto") or None
    imagen_url = payload.get("imagen_url") or None

    # Validaciones mínimas
    if not sku or not nombre or not precio:
        return jsonify({"error": "sku, nombre_producto y precio_producto son obligatorios."}), 400

    try:
        precio = float(precio)
    except:
        return jsonify({"error": "precio_producto debe ser numérico."}), 400

    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO producto (sku, nombre_producto, precio_producto, descripcion_producto, categoria_producto, imagen_url)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id_producto;
        """, (sku, nombre, precio, descripcion, categoria, imagen_url))
        new_id = cur.fetchone()[0]
        conn.commit()
        return jsonify({"ok": True, "id_producto": new_id}), 201
    except errors.UniqueViolation:
        conn.rollback()
        return jsonify({"error": "El SKU ya existe."}), 409
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        cur.close()
        conn.close()


@app.route("/api/productos_public/<int:id_producto>", methods=["PUT", "PATCH"])
def api_update_producto_public(id_producto):
    """Actualiza un producto (versión pública)."""
    payload = request.get_json(silent=True) or request.form
    sku = payload.get("sku")
    nombre = payload.get("nombre_producto")
    precio = payload.get("precio_producto")
    descripcion = payload.get("descripcion_producto")
    categoria = payload.get("categoria_producto")
    imagen_url = payload.get("imagen_url")

    # construir update dinámico
    sets, params = [], []
    if sku is not None:           sets += ["sku=%s"];                   params.append(sku)
    if nombre is not None:        sets += ["nombre_producto=%s"];       params.append(nombre)
    if precio is not None:        sets += ["precio_producto=%s"];       params.append(precio)
    if descripcion is not None:   sets += ["descripcion_producto=%s"];  params.append(descripcion)
    if categoria is not None:     sets += ["categoria_producto=%s"];    params.append(categoria)
    if imagen_url is not None:    sets += ["imagen_url=%s"];            params.append(imagen_url)

    if not sets:
        return jsonify({"error": "Nada que actualizar."}), 400

    sql = f"UPDATE producto SET {', '.join(sets)} WHERE id_producto=%s"
    params.append(id_producto)

    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(sql, params)
        if cur.rowcount == 0:
            conn.rollback()
            return jsonify({"error": "Producto no encontrado."}), 404
        conn.commit()
        return jsonify({"ok": True}), 200
    except errors.UniqueViolation:
        conn.rollback()
        return jsonify({"error": "El SKU ya existe."}), 409
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        cur.close()
        conn.close()


@app.route("/api/productos_public/<int:id_producto>", methods=["DELETE"])
def api_delete_producto_public(id_producto):
    """Elimina un producto (versión pública)."""
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM producto WHERE id_producto=%s", (id_producto,))
        if cur.rowcount == 0:
            conn.rollback()
            return jsonify({"error": "Producto no encontrado."}), 404
        conn.commit()
        return jsonify({"ok": True}), 200
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        cur.close()
        conn.close()


@app.route("/api/productos_public/bulk_delete", methods=["POST"])
def api_bulk_delete_productos_public():
    """Elimina múltiples productos por ID (versión pública)."""
    payload = request.get_json(silent=True) or {}
    ids = payload.get("ids") or []
    if not isinstance(ids, list) or not ids:
        return jsonify({"error": "Debes enviar lista 'ids'."}), 400

    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM producto WHERE id_producto = ANY(%s::int[])", (ids,))
        conn.commit()
        return jsonify({"ok": True, "deleted": cur.rowcount}), 200
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        cur.close()
        conn.close()


@app.route("/api/ofertas_public", methods=["GET"])
def api_list_ofertas_public():
    """
    Devuelve todas las ofertas vigentes con su información y sus productos.
    """
    try:
        conn = get_db_connection()

        # Cursor 1: obtener todas las ofertas vigentes
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur_ofertas:
            cur_ofertas.execute("""
                SELECT id_oferta, titulo, descripcion, descuento_pct, 
                       fecha_inicio, fecha_fin
                FROM oferta
                WHERE vigente_bool = TRUE
                  AND CURRENT_DATE BETWEEN fecha_inicio AND fecha_fin
                ORDER BY fecha_inicio DESC;
            """)
            ofertas = cur_ofertas.fetchall()

        # Cursor 2: para obtener los productos por oferta
        data = []
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur_prod:
            for o in ofertas:
                cur_prod.execute("""
                    SELECT p.id_producto, p.nombre_producto, p.precio_producto, p.imagen_url, p.sku
                    FROM producto p
                    INNER JOIN oferta_producto op ON op.id_producto = p.id_producto
                    WHERE op.id_oferta = %s;
                """, (o["id_oferta"],))
                productos = cur_prod.fetchall()

                data.append({
                    "id_oferta": o["id_oferta"],
                    "titulo": o["titulo"],
                    "descripcion": o["descripcion"],
                    "descuento_pct": float(o["descuento_pct"]),
                    "fecha_inicio": o["fecha_inicio"].isoformat(),
                    "fecha_fin": o["fecha_fin"].isoformat(),
                    "productos": [dict(p) for p in productos]
                })

        conn.close()
        return jsonify(data), 200

    except Exception as e:
        print(f"❌ Error en /api/ofertas_public: {e}")
        return jsonify({"error": str(e)}), 500

# ===========================
# RUN
# ===========================
if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)