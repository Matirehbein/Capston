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
            flash("Debes iniciar sesión.", "warning")
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
# Rutas de Productos
# ---------------------------

# ---------------------------
# Agregar Productos
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

# Validar que el SKU no exista
    cur.execute("SELECT id_producto FROM producto WHERE sku = %s", (sku,))
    existing = cur.fetchone()
    if existing:
        flash(f"Error: El SKU '{sku}' ya está registrado en otro producto.", "danger")
        cur.close()
        conn.close()
        return redirect(url_for("crud_productos"))


    #Insertar Productos
    cur.execute("""
        INSERT INTO producto (sku, nombre_producto, precio_producto, descripcion_producto, categoria_producto, imagen_url)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (sku, nombre, precio, descripcion, categoria, imagen_url))
    conn.commit()
    cur.close()
    conn.close()
    flash("Producto agregado con éxito", "success")
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
        flash(f"Error: El SKU '{sku}' ya está registrado en otro producto.", "danger")
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
    flash("Producto actualizado", "success")
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
    flash("Stock actualizado", "success")
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
    flash("Producto eliminado", "danger")
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

    flash("Stock actualizado en la sucursal", "success")
    return redirect(url_for("ver_stock", id_producto=id_producto))


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
    flash("Sucursal agregada con éxito", "success")
    return redirect(url_for("crud_sucursales"))

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
    flash("Sucursal actualizada con éxito", "success")
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
    flash("Sucursal eliminada con éxito", "danger")
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
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute("""
        SELECT id_usuario, nombre_usuario, apellido_paterno, apellido_materno, rol_usuario, email_usuario, calle, numero_calle, region, ciudad, comuna, telefono
        FROM usuario
        ORDER BY id_usuario;
    """)
    usuarios = cur.fetchall()
    cur.close()
    conn.close()
    return render_template("usuarios/crud_usuarios.html", usuarios=usuarios)

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
        flash(f"Error: El correo '{email_usuario}' ya está registrado en otro usuario.", "danger")
        cur.close()
        conn.close()
        return redirect(url_for("crud_usuarios"))


    # Validar que el teléfono no exista
    cur.execute("SELECT id_usuario FROM usuario WHERE telefono = %s", (telefono, )) 
    existing = cur.fetchone()
    if existing:
        flash(f"Error: El teléfono '{telefono}' ya está registrado en otro usuario.", "danger")
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
        flash("Usuario agregado correctamente", "success")
    except Exception as e:
        conn.rollback()
        flash(f"Error: {str(e)}", "danger")
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
        flash(f"Error: El correo '{email_usuario}' ya está registrado en otro usuario.", "warning")
        cur.close()
        conn.close()
        return redirect(url_for("crud_usuarios"))

    # Validar que el teléfono no exista en otro usuario
    cur.execute("SELECT id_usuario FROM usuario WHERE telefono = %s AND id_usuario != %s", (telefono, id_usuario))
    existing = cur.fetchone()
    if existing:
        flash(f"Error: El teléfono '{telefono}' ya está registrado en otro usuario.", "warning")
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
        flash("Usuario actualizado correctamente", "success")
    except Exception as e:
        conn.rollback()
        flash(f"Error: {str(e)}", "danger")
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
        flash("Usuario eliminado correctamente", "success")
    except Exception as e:
        conn.rollback()
        flash(f"Error: {str(e)}", "danger")
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

@app.route('/ofertas')
def crud_ofertas():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    # Productos (para el formulario)
    cur.execute("""
        SELECT p.id_producto, p.nombre_producto, p.imagen_url, COALESCE(SUM(i.stock), 0) AS stock
        FROM producto p
        LEFT JOIN variacion_producto v ON v.id_producto = p.id_producto
        LEFT JOIN inventario_sucursal i ON i.id_variacion = v.id_variacion
        GROUP BY p.id_producto, p.nombre_producto, p.imagen_url
        ORDER BY p.nombre_producto;
    """)
    productos = cur.fetchall()

    # Ofertas (para el listado)
    cur.execute("""
        SELECT o.id_oferta,
                o.titulo,
                o.descripcion, 
                o.descuento_pct,
               o.fecha_inicio, 
                o.fecha_fin, 
                o.vigente_bool,
               p.id_producto, 
                p.nombre_producto,
                p.imagen_url, 
                p.precio_producto
        FROM oferta o
        JOIN oferta_producto op ON o.id_oferta = op.id_oferta
        JOIN producto p ON op.id_producto = p.id_producto
        ORDER BY o.id_oferta DESC;
    """)
    ofertas = cur.fetchall()

    cur.close()
    conn.close()

    from datetime import datetime
    return render_template(
        "ofertas/crud_ofertas.html",
        ofertas=ofertas,
        productos=productos,
        now=datetime.now,
    )


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
        flash(f"⚠️ Error al agregar la oferta: {str(e)}", "danger")

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
            cur.execute("""
                UPDATE oferta
                SET titulo=%s, descripcion=%s, descuento_pct=%s, 
                    fecha_inicio=%s, fecha_fin=%s, vigente_bool=%s
                WHERE id_oferta=%s;
            """, (
                data.get("titulo"),
                data.get("descripcion"),
                data.get("descuento_pct"),
                data.get("fecha_inicio"),
                data.get("fecha_fin"),
                data.get("vigente_bool") == "on",
                id_oferta
            ))

            # Actualizar productos asociados
            cur.execute("DELETE FROM oferta_producto WHERE id_oferta=%s;", (id_oferta,))
            productos = data.getlist("productos")
            for id_producto in productos:
                cur.execute("""
                    INSERT INTO oferta_producto (id_oferta, id_producto)
                    VALUES (%s, %s);
                """, (id_oferta, id_producto))

            conn.commit()
            flash("✅ Oferta actualizada correctamente", "success")
        except Exception as e:
            conn.rollback()
            flash(f"⚠️ Error al actualizar la oferta: {str(e)}", "danger")
        finally:
            cur.close()
            conn.close()
        return redirect(url_for("crud_ofertas"))
    else:
        cur.execute("SELECT * FROM oferta WHERE id_oferta=%s;", (id_oferta,))
        oferta = cur.fetchone()

        cur.execute("SELECT id_producto FROM oferta_producto WHERE id_oferta=%s;", (id_oferta,))
        productos_asociados = [row[0] for row in cur.fetchall()]

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
        return render_template("ofertas/edit_oferta.html",
                               oferta=oferta,
                               productos=productos)


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
        flash(f"⚠️ Error al eliminar la oferta: {str(e)}", "danger")
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

    # Validaciones
    if data["email_usuario"].lower() != (data["email_confirm"] or "").lower():
        return redirect(url_for("login") + "?error=email_mismatch&tab=register&src=register")
    if data["password"] != data["password_confirm"]:
        return redirect(url_for("login") + "?error=password_mismatch&tab=register&src=register")

    # Validar fuerza de password
    ok, msg = validar_password(data["password"])
    if not ok:
        return redirect(url_for("login") + f"?error=weak_password&tab=register&src=register&msg={msg}")

    # Crear usuario y loguearlo automáticamente
    ok, result = do_register(data)
    if not ok:
        error_code = "email" if (result and "correo" in result.lower()) else "unknown"
        return redirect(url_for("login") + f"?error={error_code}&tab=register&src=register")

    # Sesión ya creada en do_register, redirige al frontend
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
        # Asume que tienes una función para obtener la conexión a PostgreSQL
        # Reemplaza 'get_db_connection()' con tu método real de conexión.
        conn = get_db_connection()
        cur = conn.cursor()

        # 2. CONSULTA SQL
        # Reemplaza 'nombre_de_tu_tabla' y 'nombre_de_la_columna_email'
        query = "SELECT 1 FROM nombre_de_tu_tabla WHERE nombre_de_la_columna_email = %s LIMIT 1;"
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


@app.route("/logout")
def logout():
    session.clear()
    flash("Sesión cerrada.", "info")
    return redirect(url_for("login"))


def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            flash("Debes iniciar sesión.", "warning")
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
    Devuelve las ofertas vigentes con su información básica y productos asociados.
    """
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    # Filtrar ofertas vigentes por fecha y campo booleano
    cur.execute("""
        SELECT o.id_oferta, o.titulo, o.descripcion, o.descuento_pct, 
               o.fecha_inicio, o.fecha_fin
        FROM oferta o
        WHERE o.vigente_bool = TRUE
        AND CURRENT_DATE BETWEEN o.fecha_inicio AND o.fecha_fin
        ORDER BY o.fecha_inicio DESC;
    """)
    ofertas = cur.fetchall()

    data = []
    for o in ofertas:
        # Buscar productos asociados
        cur.execute("""
            SELECT p.id_producto, p.nombre_producto, p.precio_producto, p.imagen_url, p.sku
            FROM producto p
            INNER JOIN oferta_producto op ON op.id_producto = p.id_producto
            WHERE op.id_oferta = %s
        """, (o["id_oferta"],))
        productos = cur.fetchall()

        data.append({
            "id_oferta": o["id_oferta"],
            "titulo": o["titulo"],
            "descripcion": o["descripcion"],
            "descuento_pct": float(o["descuento_pct"]),
            "fecha_inicio": o["fecha_inicio"].isoformat(),
            "fecha_fin": o["fecha_fin"].isoformat(),
            "productos": [dict(p) for p in productos]
        })

    cur.close()
    conn.close()
    return jsonify(data), 200

# ===========================
# RUN
# ===========================
if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)