import json
import re
import traceback
import os
from datetime import datetime, date
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, session, send_from_directory, jsonify
import psycopg2
import psycopg2.extras
from psycopg2 import errors
from psycopg2 import pool 
from werkzeug.security import generate_password_hash, check_password_hash
from flask_cors import CORS
import requests



# --- NUEVAS IMPORTACIONES PARA CORREO Y TOKENS ---
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadTimeSignature


app = Flask(__name__)
app.secret_key = "supersecretkey" # ¡Mantén esto seguro y secreto!

# ---  CONFIGURACIÓN DE FLASK-MAIL  ---
# (Usa la Contraseña de Aplicación de 16 dígitos, no tu contraseña real)
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USE_SSL'] = True
app.config['MAIL_USERNAME'] = 'painless199388@gmail.com' # <--- REEMPLAZA ESTO
app.config['MAIL_PASSWORD'] = 'djrl xfiz wbmb fger' # <--- REEMPLAZA ESTO (la de 16 dígitos)
app.config['MAIL_DEFAULT_SENDER'] = ('Aurora', 'painless199388@gmail.com') # Nombre amigable
mail = Mail(app)
# ---  FIN CONFIGURACIÓN MAIL ---

# --- NUEVO: CONFIGURACIÓN DE SERIALIZER (TOKEN)  ---
s = URLSafeTimedSerializer(app.secret_key)
# ---  FIN SERIALIZER  ---


# Constantes para categorías y tallas (SIN CAMBIOS)
CATEGORIAS_ROPA = ["Abrigos", "Chaquetas", "Parkas", "Polerones", "Poleras", "Ropa interior", "Top", "Traje de baño"]
CATEGORIAS_CALZADO = ["Calzado", "Pantalones"]
TALLAS_ROPA = ["XS", "S", "M", "L", "XL"]
TALLAS_CALZADO = [str(i) for i in range(35, 47)]

# ===========================
# SESSION INFO (SIN CAMBIOS)
# ===========================
@app.route("/api/session_info")
def api_session_info():
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


# Configuración PostgreSQL (SIN CAMBIOS)
app.config['PG_HOST'] = "localhost"
app.config['PG_DATABASE'] = "aurora"
app.config['PG_USER'] = "postgres"
app.config['PG_PASSWORD'] = "duoc"


# --- POOL DE CONEXIONES (Tu código, SIN CAMBIOS) ---
try:
    db_pool = psycopg2.pool.SimpleConnectionPool(
        1, 20, # minconn=1, maxconn=20
        host=app.config['PG_HOST'],
        database=app.config['PG_DATABASE'],
        user=app.config['PG_USER'],
        password=app.config['PG_PASSWORD']
    )
    print("[Flask] Pool de conexiones a PostgreSQL creado exitosamente.")
except psycopg2.OperationalError as e:
    print(f"❌ ERROR: No se pudo crear el pool de conexiones a PostgreSQL: {e}")
    db_pool = None
# --- FIN POOL ---


# --- FUNCIONES DE CONEXIÓN CON POOL (Tu código, SIN CAMBIOS) ---
def get_db_connection():
    if db_pool:
        return db_pool.getconn()
    else:
        print("Error: db_pool no está inicializado. Creando conexión de emergencia.")
        return psycopg2.connect(
            host=app.config['PG_HOST'],
            database=app.config['PG_DATABASE'],
            user=app.config['PG_USER'],
            password=app.config['PG_PASSWORD']
        )

def return_db_connection(conn):
    if db_pool:
        db_pool.putconn(conn)
    else:
        conn.close()
# --- FIN FUNCIONES DE CONEXIÓN ---

# --- ▼▼▼ DECORADORES (CORREGIDOS) ▼▼▼ ---
def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            # Si la petición es a una API (como crear-pedido), devuelve un error JSON
            if request.path.startswith('/api/'):
                 return jsonify({"error": "No autorizado. Debes iniciar sesión."}), 401
            
            # Si NO es una API, redirige a la página de login
            flash("⚠️ Debes iniciar sesión.", "warning")
            return redirect(url_for("login"))
            
        # Si el usuario sí tiene sesión, simplemente ejecuta la función
        return fn(*args, **kwargs)
    return wrapper

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "rol_usuario" not in session or session["rol_usuario"] not in ["admin", "soporte"]:
            # Si es API, devuelve error JSON
            if request.path.startswith('/api/'):
                 return jsonify({"error": "Acceso denegado. Requiere rol de administrador."}), 403
            
            # Si no, redirige
            return redirect(url_for("menu_principal"))
        return f(*args, **kwargs)
    return decorated_function
# --- ▲▲▲ FIN DECORADORES ▲▲▲ ---

# ===========================
# RUTAS (SIN CAMBIOS)
# ===========================
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
SRC_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "src"))
PUBLIC_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "Public"))
FRONTEND_MAIN_URL = "http://localhost:3000/src/main.html"
CORS(app,
    supports_credentials=True,
    resources={r"/api/*": {"origins": ["http://localhost:3000"]}})

@app.route("/Public/<path:filename>")
def public_files(filename):
    return send_from_directory(PUBLIC_DIR, filename)

FRONTEND_ORIGIN = "http://localhost:3000"

@app.route("/src/main.html")
def redirect_main_frontend():
    from flask import redirect
    return redirect(f"{FRONTEND_ORIGIN}/src/main.html", code=302)



# ---------------------------
# Página Principal (Menú) (SIN CAMBIOS)
# ---------------------------
@app.route('/')
def menu_principal():
    return render_template("index_options.html")

@app.route("/index_options")
def index_options():
    return render_template("index_options.html")



# ---------------------------
# API Sucursales (CON POOL)
# ---------------------------
@app.route("/api/sucursales_con_coords")
def api_sucursales_con_coords():
    conn = None; cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute("""
            SELECT id_sucursal, nombre_sucursal, latitud_sucursal, longitud_sucursal
            FROM sucursal
            WHERE latitud_sucursal IS NOT NULL AND longitud_sucursal IS NOT NULL
            ORDER BY id_sucursal;
        """)
        sucursales = cur.fetchall()
        lista_sucursales = []
        for s in sucursales:
            try:
                lista_sucursales.append({
                    "id_sucursal": s["id_sucursal"],
                    "nombre_sucursal": s["nombre_sucursal"],
                    "latitud": float(s["latitud_sucursal"]),
                    "longitud": float(s["longitud_sucursal"])
                })
            except (TypeError, ValueError):
                print(f"Advertencia: Sucursal ID {s['id_sucursal']} tiene coordenadas inválidas.")
                continue
        return jsonify(lista_sucursales)
    except Exception as e:
        print(f"Error en /api/sucursales_con_coords: {e}")
        traceback.print_exc()
        return jsonify({"error": "Error al obtener sucursales"}), 500
    finally:
        if cur: cur.close()
        if conn: return_db_connection(conn) # <-- USA POOL



# ---------------------------
# CRUD Productos (CON POOL)
# ---------------------------
@app.route('/productos')
@login_required
def crud_productos():
    filtro_categoria = request.args.get('filtro_categoria', '')
    filtro_nombre = request.args.get('filtro_nombre', '')
    filtro_sucursal = request.args.get('filtro_sucursal', '')
    q = request.args.get('q', '')
    conn = None; cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        params = []
        join_clause = "LEFT JOIN variacion_producto v ON v.id_producto = p.id_producto LEFT JOIN inventario_sucursal i ON i.id_variacion = v.id_variacion"
        if filtro_sucursal:
            join_clause = "LEFT JOIN variacion_producto v ON v.id_producto = p.id_producto LEFT JOIN inventario_sucursal i ON i.id_variacion = v.id_variacion AND i.id_sucursal = %s"
            params.append(filtro_sucursal)
        base_query = f"""
            SELECT p.id_producto, p.sku, p.nombre_producto, p.precio_producto, 
            p.descripcion_producto, p.categoria_producto, p.imagen_url, 
            COALESCE(SUM(i.stock), 0) as stock
            FROM producto p {join_clause}
        """
        where_clauses = []
        if filtro_categoria: where_clauses.append("p.categoria_producto = %s"); params.append(filtro_categoria)
        if filtro_nombre: where_clauses.append("p.nombre_producto = %s"); params.append(filtro_nombre)
        if filtro_sucursal: where_clauses.append("p.id_producto IN (SELECT v.id_producto FROM inventario_sucursal i JOIN variacion_producto v ON i.id_variacion = v.id_variacion WHERE i.id_sucursal = %s AND i.stock > 0)"); params.append(filtro_sucursal)
        if q: where_clauses.append("(p.id_producto::text ILIKE %s OR p.sku ILIKE %s)"); params.extend([f"%{q}%", f"%{q}%"])
        final_query = base_query
        if where_clauses: final_query += " WHERE " + " AND ".join(where_clauses)
        final_query += " GROUP BY p.id_producto ORDER BY p.id_producto;"
        cur.execute(final_query, tuple(params))
        productos = cur.fetchall()
        cur.execute("SELECT DISTINCT categoria_producto FROM producto WHERE categoria_producto IS NOT NULL ORDER BY categoria_producto;")
        categorias = [row['categoria_producto'] for row in cur.fetchall()]
        nombres_productos_query = "SELECT DISTINCT nombre_producto FROM producto"
        nombres_params = []
        if filtro_categoria: nombres_productos_query += " WHERE categoria_producto = %s"; nombres_params.append(filtro_categoria)
        nombres_productos_query += " ORDER BY nombre_producto;"
        cur.execute(nombres_productos_query, nombres_params)
        nombres_productos = [row['nombre_producto'] for row in cur.fetchall()]
        cur.execute("SELECT * FROM sucursal ORDER BY id_sucursal;")
        sucursales = cur.fetchall()
        filtros_activos = { 'categoria': filtro_categoria, 'nombre': filtro_nombre, 'sucursal': filtro_sucursal, 'q': q }
        return render_template("productos/crud_productos.html", productos=productos, sucursales=sucursales, categorias=categorias, nombres_productos=nombres_productos, filtros_activos=filtros_activos)
    except Exception as e:
        print(f"Error en crud_productos: {e}"); traceback.print_exc()
        flash("Error al cargar productos", "danger")
        return redirect(url_for("index_options"))
    finally:
        if cur: cur.close()
        if conn: return_db_connection(conn) # <-- USA POOL

@app.route("/api/productos/nombres_por_categoria")
@login_required
def api_nombres_por_categoria():
    categoria = request.args.get('categoria', '')
    conn = None; cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        if categoria:
            cur.execute("SELECT DISTINCT nombre_producto FROM producto WHERE categoria_producto = %s ORDER BY nombre_producto;", (categoria,))
        else:
            cur.execute("SELECT DISTINCT nombre_producto FROM producto ORDER BY nombre_producto;")
        nombres = [row[0] for row in cur.fetchall()]
        return jsonify({"nombres": nombres})
    except Exception as e:
        print(f"Error en la API de nombres por categoría: {e}")
        return jsonify({"nombres": [], "error": str(e)}), 500
    finally:
        if cur: cur.close()
        if conn: return_db_connection(conn) # <-- USA POOL

@app.route("/api/productos_por_color")
def api_productos_por_color():
    color_buscado = request.args.get('color', '').strip()
    exclude_id_str = request.args.get('exclude_id', None)
    conn = None; cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        query = "SELECT DISTINCT p.id_producto, p.nombre_producto, p.precio_producto, p.imagen_url FROM producto p JOIN variacion_producto v ON p.id_producto = v.id_producto WHERE v.color ILIKE %s"
        params = [f'%{color_buscado}%']
        if exclude_id_str:
            try:
                exclude_id_int = int(exclude_id_str)
                query += " AND p.id_producto != %s"; params.append(exclude_id_int)
            except ValueError: print(f"[API Color Warn] exclude_id ('{exclude_id_str}') no válido.")
        query += " LIMIT 4;"
        print("\n--- [API Color Debug] ---")
        try: print("Query a ejecutar (mogrify):\n", cur.mogrify(query, tuple(params)).decode('utf-8'))
        except Exception as me: print("No se pudo usar mogrify. Query:", query); print("Params:", tuple(params)); print("Mogrify error:", me)
        cur.execute(query, tuple(params))
        productos = cur.fetchall()
        print(f"Productos encontrados: {len(productos)}"); print("-------------------------\n")
        return jsonify([dict(p) for p in productos])
    except Exception as e:
        print(f"\n--- ¡ERROR GRAVE EN /api/productos_por_color! ---"); traceback.print_exc()
        return jsonify({"error": "Error buscando productos por color"}), 500
    finally:
        if cur: cur.close()
        if conn: return_db_connection(conn) # <-- USA POOL

@app.route("/add", methods=["POST"])
@login_required # Añadido decorador
def add_producto():
    conn = None; cur = None
    try:
        sku_digits = request.form["sku_digits"]; sku = f"AUR-{sku_digits}"
        nombre = request.form["nombre"]; precio = request.form["precio"]
        color = request.form.get("color"); descripcion = request.form.get("descripcion")
        categoria = request.form.get("categoria"); imagen_url = request.form.get("imagen_url")
        if not color: flash("❌ Error: Debes seleccionar un color.", "danger"); return redirect(url_for("crud_productos"))
        
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT id_producto FROM producto WHERE sku = %s", (sku,))
        if cur.fetchone():
            flash(f"❌ Error: El SKU '{sku}' ya está registrado.", "danger")
            return redirect(url_for("crud_productos"))
        cur.execute("""
            INSERT INTO producto (sku, nombre_producto, precio_producto, descripcion_producto, categoria_producto, imagen_url)
            VALUES (%s, %s, %s, %s, %s, %s) RETURNING id_producto;
        """, (sku, nombre, precio, descripcion, categoria, imagen_url))
        id_producto_nuevo = cur.fetchone()[0]
        sku_variacion_base = f"{sku}-{color[:3].upper()}"
        cur.execute("INSERT INTO variacion_producto (id_producto, color, sku_variacion) VALUES (%s, %s, %s);", (id_producto_nuevo, color, sku_variacion_base))
        conn.commit()
        flash(" ✅ Producto agregado con éxito", "success")
    except Exception as e:
        if conn: conn.rollback()
        flash(f"❌ Ocurrió un error al agregar el producto: {e}", "danger")
    finally:
        if cur: cur.close()
        if conn: return_db_connection(conn) # <-- USA POOL
    return redirect(url_for("crud_productos"))

@app.route("/edit/<int:id>", methods=["POST"])
@login_required # Añadido decorador
def edit_producto(id):
    conn = None; cur = None
    try:
        sku = request.form["sku"]; nombre = request.form["nombre"]; precio = request.form["precio"]
        descripcion = request.form.get("descripcion"); categoria = request.form.get("categoria"); imagen_url = request.form.get("imagen_url")
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT id_producto FROM producto WHERE sku = %s AND id_producto != %s", (sku, id))
        if cur.fetchone():
            flash(f"❌ Error: El SKU '{sku}' ya está registrado.", "danger")
            return redirect(url_for("crud_productos"))
        cur.execute("""
            UPDATE producto SET sku = %s, nombre_producto = %s, precio_producto = %s,
            descripcion_producto = %s, categoria_producto = %s, imagen_url = %s
            WHERE id_producto = %s
        """, (sku, nombre, precio, descripcion, categoria, imagen_url, id))
        conn.commit()
        flash("✅ Producto actualizado", "success")
    except Exception as e:
        if conn: conn.rollback()
        flash(f"Error al editar producto: {e}", "danger")
    finally:
        if cur: cur.close()
        if conn: return_db_connection(conn) # <-- USA POOL
    return redirect(url_for("crud_productos"))

@app.route("/edit_stock/<int:id>", methods=["POST"])
@login_required # Añadido decorador
def edit_stock(id):
    id_sucursal = request.form["id_sucursal"]
    stock = request.form["stock"]
    conn = None; cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT id_variacion FROM variacion_producto WHERE id_producto = %s", (id,))
        variacion = cur.fetchone()
        if not variacion:
            cur.execute("INSERT INTO variacion_producto (id_producto, sku_variacion) VALUES (%s, %s) RETURNING id_variacion", (id, f"VAR-{id}"))
            variacion_id = cur.fetchone()[0]
        else:
            variacion_id = variacion[0]
        cur.execute("""
            INSERT INTO inventario_sucursal (id_sucursal, id_variacion, stock) VALUES (%s, %s, %s)
            ON CONFLICT (id_sucursal, id_variacion) DO UPDATE SET stock = EXCLUDED.stock
        """, (id_sucursal, variacion_id, stock))
        conn.commit()
        flash("✅ Stock actualizado", "success")
    except Exception as e:
        if conn: conn.rollback()
        flash(f"Error al editar stock: {e}", "danger")
    finally:
        if cur: cur.close()
        if conn: return_db_connection(conn) # <-- USA POOL
    return redirect(url_for("crud_productos"))

@app.route("/delete/<int:id>", methods=["POST"])
@login_required # Añadido decorador
def delete_producto(id):
    conn = None; cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM producto WHERE id_producto = %s", (id,))
        conn.commit()
        flash(" ❌ Producto eliminado", "danger")
    except Exception as e:
        if conn: conn.rollback()
        flash(f"Error al eliminar producto: {e}", "danger")
    finally:
        if cur: cur.close()
        if conn: return_db_connection(conn) # <-- USA POOL
    return redirect(url_for("crud_productos"))

@app.route("/ver_stock/<int:id_producto>")
@login_required
def ver_stock(id_producto):
    conn = None; cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute("SELECT * FROM producto WHERE id_producto = %s", (id_producto,))
        producto = cur.fetchone()
        if not producto:
            flash("Producto no encontrado.", "danger")
            return redirect(url_for("crud_productos"))
        categoria = (producto["categoria_producto"] or "").strip()
        tallas_disponibles = []
        if categoria in CATEGORIAS_ROPA: tallas_disponibles = TALLAS_ROPA
        elif categoria in CATEGORIAS_CALZADO: tallas_disponibles = TALLAS_CALZADO
        usa_tallas = bool(tallas_disponibles)
        cur.execute("SELECT * FROM sucursal ORDER BY id_sucursal")
        sucursales = cur.fetchall()
        stock_por_talla = {}
        stock_total_sucursal = {}
        stock_base_sucursal = {} # <-- NUEVO
        for s in sucursales:
            id_sucursal = s["id_sucursal"]
            cur.execute("""
                SELECT v.talla, COALESCE(i.stock, 0) as stock
                FROM variacion_producto v
                LEFT JOIN inventario_sucursal i ON v.id_variacion = i.id_variacion AND i.id_sucursal = %s
                WHERE v.id_producto = %s AND v.talla IS NOT NULL
            """, (id_sucursal, id_producto))
            stock_tallas_sucursal = {row['talla']: row['stock'] for row in cur.fetchall()}
            stock_por_talla[id_sucursal] = stock_tallas_sucursal
            
            cur.execute("""
                SELECT COALESCE(i.stock, 0) as stock
                FROM variacion_producto v
                LEFT JOIN inventario_sucursal i ON v.id_variacion = i.id_variacion AND i.id_sucursal = %s
                WHERE v.id_producto = %s AND v.talla IS NULL LIMIT 1;
            """, (id_sucursal, id_producto))
            stock_base_row = cur.fetchone()
            stock_base_sucursal[s['id_sucursal']] = stock_base_row['stock'] if stock_base_row else 0 # <-- CORREGIDO
            stock_total_sucursal[s['id_sucursal']] = sum(stock_tallas_sucursal.values()) + stock_base_sucursal[s['id_sucursal']] # <-- CORREGIDO
            
        stock_total_producto = sum(stock_total_sucursal.values())
        return render_template(
            "productos/ver_stock.html",
            producto=producto, sucursales=sucursales, usa_tallas=usa_tallas,
            tallas_disponibles=tallas_disponibles, stock_por_talla=stock_por_talla,
            stock_total_sucursal=stock_total_sucursal, stock_total_producto=stock_total_producto,
            stock_base_sucursal=stock_base_sucursal # <-- NUEVO
        )
    except Exception as e:
        print(f"Error en ver_stock: {e}"); traceback.print_exc()
        flash("Error al cargar stock", "danger")
        return redirect(url_for("crud_productos"))
    finally:
        if cur: cur.close()
        if conn: return_db_connection(conn) # <-- USA POOL

# --- ▼▼▼ NUEVA RUTA (tal como te la pasé) ▼▼▼ ---
@app.route("/productos/<int:id_producto>/actualizar_stock_estandar", methods=["POST"])
@login_required
def actualizar_stock_estandar(id_producto):
    id_sucursal = request.form.get("id_sucursal")
    stock_estandar = request.form.get("stock_estandar", 0)
    if not id_sucursal:
        flash("❌ Error: No se especificó una sucursal.", "danger")
        return redirect(url_for("ver_stock", id_producto=id_producto))
    conn = None; cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute("SELECT id_variacion FROM variacion_producto WHERE id_producto = %s AND talla IS NULL LIMIT 1;", (id_producto,))
        variacion = cur.fetchone()
        if not variacion:
            flash("❌ Error: No se encontró la variación base del producto.", "danger")
            raise Exception("No se encontró variación base (talla NULL)")
        id_variacion_base = variacion['id_variacion']
        cur.execute("""
            INSERT INTO inventario_sucursal (id_sucursal, id_variacion, stock)
            VALUES (%s, %s, %s)
            ON CONFLICT (id_sucursal, id_variacion)
            DO UPDATE SET stock = EXCLUDED.stock;
        """, (id_sucursal, id_variacion_base, stock_estandar))
        conn.commit()
        flash("✅ Stock estándar actualizado correctamente.", "success")
    except Exception as e:
        if conn: conn.rollback()
        print(f"❌ Error al actualizar stock estándar: {e}"); traceback.print_exc()
        flash(f"❌ Error al actualizar el stock: {e}", "danger")
    finally:
        if cur: cur.close()
        if conn: return_db_connection(conn) # <-- USA POOL
    return redirect(url_for("ver_stock", id_producto=id_producto))
# --- ▲▲▲ FIN NUEVA RUTA ▲▲▲ ---

@app.route("/productos/<int:id_producto>/actualizar_stock_por_tallas", methods=["POST"])
@login_required
def actualizar_stock_por_tallas(id_producto):
    id_sucursal = request.form.get("id_sucursal")
    if not id_sucursal:
        flash("❌ Error: No se especificó una sucursal.", "danger")
        return redirect(url_for("ver_stock", id_producto=id_producto))
    conn = None; cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute("""
            SELECT p.sku, v.color FROM producto p
            JOIN variacion_producto v ON p.id_producto = v.id_producto
            WHERE p.id_producto = %s AND v.color IS NOT NULL LIMIT 1;
        """, (id_producto,))
        info_base = cur.fetchone()
        color_base = info_base['color'] if info_base else 'SIN_COLOR'
        sku_base = info_base['sku'] if info_base else f'SKU-{id_producto}'
        nuevas_cantidades = {}
        for key, value in request.form.items():
            if key.startswith("stock_talla_"):
                talla = key.replace("stock_talla_", "")
                cantidad = max(0, int(value or 0))
                nuevas_cantidades[talla] = cantidad
        for talla, cantidad in nuevas_cantidades.items():
            sku_variacion = f"{sku_base}-{color_base[:3].upper()}-{talla.upper()}"
            cur.execute("SELECT id_variacion FROM variacion_producto WHERE id_producto = %s AND talla = %s", (id_producto, talla))
            variacion = cur.fetchone()
            if not variacion:
                cur.execute("""
                    INSERT INTO variacion_producto (id_producto, talla, color, sku_variacion) 
                    VALUES (%s, %s, %s, %s) RETURNING id_variacion
                """, (id_producto, talla, color_base, sku_variacion))
                id_variacion = cur.fetchone()[0]
            else:
                id_variacion = variacion[0]
                cur.execute("UPDATE variacion_producto SET sku_variacion = %s WHERE id_variacion = %s", (sku_variacion, id_variacion))
            cur.execute("""
                INSERT INTO inventario_sucursal (id_sucursal, id_variacion, stock) VALUES (%s, %s, %s)
                ON CONFLICT (id_sucursal, id_variacion) DO UPDATE SET stock = EXCLUDED.stock;
            """, (id_sucursal, id_variacion, cantidad))
        conn.commit()
        flash("✅ Stock por tallas actualizado correctamente.", "success")
    except Exception as e:
        if conn: conn.rollback()
        flash(f"❌ Error al actualizar el stock: {e}", "danger")
    finally:
        if cur: cur.close()
        if conn: return_db_connection(conn) # <-- USA POOL
    return redirect(url_for("ver_stock", id_producto=id_producto))

@app.route("/guardar_stock_sucursales/<int:id_producto>", methods=["POST"])
@login_required
def guardar_stock_sucursales(id_producto):
    conn = None; cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute("SELECT id_variacion FROM variacion_producto WHERE id_producto = %s LIMIT 1", (id_producto,))
        variacion_row = cur.fetchone()
        if not variacion_row:
             flash("❌ Error: Producto no tiene variaciones base.", "danger")
             return redirect(url_for("ver_stock", id_producto=id_producto))
        variacion_id = variacion_row[0]
        
        cur.execute("SELECT COALESCE(SUM(i.stock),0) FROM producto p LEFT JOIN variacion_producto v ON v.id_producto = p.id_producto LEFT JOIN inventario_sucursal i ON i.id_variacion = v.id_variacion WHERE p.id_producto = %s", (id_producto,)) # ID estaba mal
        stock_max = cur.fetchone()[0]
        
        total_nuevo = 0
        for key, val in request.form.items():
            if key.startswith("stock_"): total_nuevo += int(val)
        
        # if total_nuevo > stock_max: # Validación comentada
        #     flash(f"❌ No puedes asignar {total_nuevo} unidades. El máximo permitido es {stock_max}.")
        #     return redirect(url_for("ver_stock", id_producto=id_producto))
        
        for key, val in request.form.items():
            if key.startswith("stock_"):
                id_sucursal = int(key.split("_")[1])
                stock_val = int(val)
                cur.execute("""
                    INSERT INTO inventario_sucursal (id_sucursal, id_variacion, stock) VALUES (%s, %s, %s)
                    ON CONFLICT (id_sucursal, id_variacion) DO UPDATE SET stock = EXCLUDED.stock
                """, (id_sucursal, variacion_id, stock_val))
        conn.commit()
        flash("✅ Stock por sucursal actualizado correctamente.")
    except Exception as e:
        if conn: conn.rollback()
        flash(f"Error al guardar stock: {e}", "danger")
    finally:
        if cur: cur.close()
        if conn: return_db_connection(conn) # <-- USA POOL
    return redirect(url_for("ver_stock", id_producto=id_producto))

@app.route("/update_stock/<int:id_producto>/<int:id_sucursal>", methods=["POST"])
@login_required
def update_stock_sucursal(id_producto, id_sucursal):
    nuevo_stock = int(request.form["stock"])
    conn = None; cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT id_variacion FROM variacion_producto WHERE id_producto = %s LIMIT 1", (id_producto,))
        variacion = cur.fetchone()
        if not variacion:
            cur.execute("INSERT INTO variacion_producto (id_producto, sku_variacion) VALUES (%s, %s) RETURNING id_variacion", (id_producto, f"VAR-{id_producto}"))
            id_variacion = cur.fetchone()[0]
        else:
            id_variacion = variacion[0]
        cur.execute("""
            INSERT INTO inventario_sucursal (id_sucursal, id_variacion, stock) VALUES (%s, %s, %s)
            ON CONFLICT (id_sucursal, id_variacion) DO UPDATE SET stock = EXCLUDED.stock
        """, (id_sucursal, id_variacion, nuevo_stock))
        conn.commit()
        flash("✅ Stock actualizado en la sucursal", "success")
    except Exception as e:
        if conn: conn.rollback()
        flash(f"Error al actualizar stock: {e}", "danger")
    finally:
        if cur: cur.close()
        if conn: return_db_connection(conn) # <-- USA POOL
    return redirect(url_for("ver_stock", id_producto=id_producto))

# ---------------------------
# CRUD Sucursales
# ---------------------------
@app.route('/sucursales')
@login_required
def crud_sucursales():
    filtro_nombre = request.args.get('filtro_nombre', '')
    filtro_region = request.args.get('filtro_region', '')
    filtro_comuna = request.args.get('filtro_comuna', '')
    q = request.args.get('q', '')
    conn = None; cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        base_query = "SELECT * FROM sucursal"
        where_clauses, params = [], []
        if q: where_clauses.append("id_sucursal::text ILIKE %s"); params.append(f"%{q}%")
        if filtro_nombre: where_clauses.append("nombre_sucursal = %s"); params.append(filtro_nombre)
        if filtro_region: where_clauses.append("region_sucursal = %s"); params.append(filtro_region)
        if filtro_comuna: where_clauses.append("comuna_sucursal = %s"); params.append(filtro_comuna)
        final_query = base_query
        if where_clauses: final_query += " WHERE " + " AND ".join(where_clauses)
        final_query += " ORDER BY id_sucursal;"
        cur.execute(final_query, tuple(params))
        sucursales = cur.fetchall()
        cur.execute("SELECT DISTINCT region_sucursal FROM sucursal ORDER BY region_sucursal;")
        regiones = [row['region_sucursal'] for row in cur.fetchall()]
        comunas_query, comunas_params = "SELECT DISTINCT comuna_sucursal FROM sucursal", []
        if filtro_region: comunas_query += " WHERE region_sucursal = %s"; comunas_params.append(filtro_region)
        comunas_query += " ORDER BY comuna_sucursal;"
        cur.execute(comunas_query, comunas_params)
        comunas = [row['comuna_sucursal'] for row in cur.fetchall()]
        nombres_query, nombres_params, nombres_where = "SELECT DISTINCT nombre_sucursal FROM sucursal", [], []
        if filtro_region: nombres_where.append("region_sucursal = %s"); nombres_params.append(filtro_region)
        if filtro_comuna: nombres_where.append("comuna_sucursal = %s"); nombres_params.append(filtro_comuna)
        if nombres_where: nombres_query += " WHERE " + " AND ".join(nombres_where)
        nombres_query += " ORDER BY nombre_sucursal;"
        cur.execute(nombres_query, nombres_params)
        nombres_sucursales = [row['nombre_sucursal'] for row in cur.fetchall()]
        filtros_activos = { 'nombre': filtro_nombre, 'region': filtro_region, 'comuna': filtro_comuna, 'q': q }
        return render_template("sucursales/crud_sucursales.html", sucursales=sucursales, nombres_sucursales=nombres_sucursales, regiones=regiones, comunas=comunas, filtros_activos=filtros_activos)
    except Exception as e:
        print(f"Error en crud_sucursales: {e}"); traceback.print_exc()
        flash("Error al cargar sucursales", "danger")
        return redirect(url_for("index_options"))
    finally:
        if cur: cur.close()
        if conn: return_db_connection(conn) # <-- USA POOL

@app.route("/api/sucursales/comunas_por_region")
@login_required
def api_comunas_por_region():
    region = request.args.get('region', '')
    conn = None; cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        if region:
            cur.execute("SELECT DISTINCT comuna_sucursal FROM sucursal WHERE region_sucursal = %s ORDER BY comuna_sucursal;", (region,))
        else:
            cur.execute("SELECT DISTINCT comuna_sucursal FROM sucursal ORDER BY comuna_sucursal;")
        comunas = [row[0] for row in cur.fetchall()]
        return jsonify({"comunas": comunas})
    except Exception as e:
        return jsonify({"comunas": [], "error": str(e)}), 500
    finally:
        if cur: cur.close()
        if conn: return_db_connection(conn) # <-- USA POOL

@app.route("/api/sucursales/nombres_por_comuna")
@login_required
def api_nombres_por_comuna():
    comuna = request.args.get('comuna', '')
    region = request.args.get('region', '')
    conn = None; cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        query, where_clauses, params = "SELECT DISTINCT nombre_sucursal FROM sucursal", [], []
        if comuna: where_clauses.append("comuna_sucursal = %s"); params.append(comuna)
        if region: where_clauses.append("region_sucursal = %s"); params.append(region)
        if where_clauses: query += " WHERE " + " AND ".join(where_clauses)
        query += " ORDER BY nombre_sucursal;"
        cur.execute(query, tuple(params))
        nombres = [row[0] for row in cur.fetchall()]
        return jsonify({"nombres": nombres})
    except Exception as e:
        return jsonify({"nombres": [], "error": str(e)}), 500
    finally:
        if cur: cur.close()
        if conn: return_db_connection(conn) # <-- USA POOL

@app.route("/add_sucursal", methods=["POST"])
@login_required # Añadido decorador
def add_sucursal():
    conn = None; cur = None
    try:
        nombre = request.form["nombre"]; region = request.form["region"]; comuna = request.form["comuna"]
        direccion = request.form["direccion"]; latitud = request.form.get("latitud") or None
        longitud = request.form.get("longitud") or None; horario = request.form.get("horario") or '{}'
        telefono = request.form.get("telefono") or None
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO sucursal 
            (nombre_sucursal, region_sucursal, comuna_sucursal, direccion_sucursal, latitud_sucursal, longitud_sucursal, horario_json, telefono_sucursal)
            VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb, %s)
        """, (nombre, region, comuna, direccion, latitud, longitud, horario, telefono))
        conn.commit()
        flash("✅ Sucursal agregada con éxito", "success")
    except Exception as e:
        if conn: conn.rollback()
        flash(f"Error al añadir sucursal: {e}", "danger")
    finally:
        if cur: cur.close()
        if conn: return_db_connection(conn) # <-- USA POOL
    return redirect(url_for("crud_sucursales"))

@app.route('/api/check_telefono_sucursal', methods=['GET'])
@login_required
def check_telefono_sucursal():
    telefono = request.args.get('telefono')
    exclude_id = request.args.get('exclude_id')
    if not telefono: return jsonify({'exists': False})
    conn = None; cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        query, params = "SELECT 1 FROM sucursal WHERE telefono_sucursal = %s", [telefono]
        if exclude_id: query += " AND id_sucursal != %s"; params.append(exclude_id)
        query += " LIMIT 1;"
        cur.execute(query, tuple(params))
        telefono_exists = cur.fetchone() is not None
        return jsonify({'exists': telefono_exists})
    except Exception as e:
        print(f"Error al verificar el teléfono de sucursal: {e}")
        return jsonify({'exists': False}), 500
    finally:
        if cur: cur.close()
        if conn: return_db_connection(conn) # <-- USA POOL

@app.route('/api/check_direccion_sucursal', methods=['GET'])
@login_required
def check_direccion_sucursal():
    direccion = request.args.get('direccion', '')
    exclude_id = request.args.get('exclude_id')
    if not direccion: return jsonify({'exists': False})
    conn = None; cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        query, params = "SELECT 1 FROM sucursal WHERE direccion_sucursal ILIKE %s", [direccion.strip()]
        if exclude_id: query += " AND id_sucursal != %s"; params.append(exclude_id)
        query += " LIMIT 1;"
        cur.execute(query, tuple(params))
        direccion_exists = cur.fetchone() is not None
        return jsonify({'exists': direccion_exists})
    except Exception as e:
        print(f"Error al verificar la dirección de sucursal: {e}")
        return jsonify({'exists': False}), 500
    finally:
        if cur: cur.close()
        if conn: return_db_connection(conn) # <-- USA POOL

@app.route("/editar_sucursal/<int:id_sucursal>", methods=["POST"])
@login_required # Añadido decorador
def editar_sucursal(id_sucursal):
    conn = None; cur = None
    try:
        nombre = request.form["nombre_sucursal"]; region = request.form["region_sucursal"]; comuna = request.form["comuna_sucursal"]
        direccion = request.form["direccion_sucursal"]; latitud = request.form.get("latitud_sucursal") or None
        longitud = request.form.get("longitud_sucursal") or None; horario = request.form.get("horario_json") or "{}"
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
        flash("✅ Sucursal actualizada con éxito", "success")
    except Exception as e:
        if conn: conn.rollback()
        flash(f"Error al editar sucursal: {e}", "danger")
    finally:
        if cur: cur.close()
        if conn: return_db_connection(conn) # <-- USA POOL
    return redirect(url_for("crud_sucursales"))

@app.route("/eliminar_sucursal/<int:id_sucursal>", methods=["POST"])
@login_required # Añadido decorador
def eliminar_sucursal(id_sucursal):
    conn = None; cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM sucursal WHERE id_sucursal = %s", (id_sucursal,))
        conn.commit()
        flash("✅ Sucursal eliminada con éxito", "danger")
    except Exception as e:
        if conn: conn.rollback()
        flash(f"Error al eliminar sucursal: {e}", "danger")
    finally:
        if cur: cur.close()
        if conn: return_db_connection(conn) # <-- USA POOL
    return redirect(url_for("crud_sucursales"))

@app.route("/stock_sucursales")
@login_required # Añadido decorador
def stock_sucursales():
    conn = None; cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute("SELECT id_sucursal, nombre_sucursal FROM sucursal ORDER BY id_sucursal;")
        sucursales = cur.fetchall()
        return render_template("sucursales/stock_sucursales.html", sucursales=sucursales)
    except Exception as e:
        print(f"Error en stock_sucursales: {e}"); traceback.print_exc()
        flash("Error al cargar página de stock", "danger")
        return redirect(url_for("crud_sucursales"))
    finally:
        if cur: cur.close()
        if conn: return_db_connection(conn) # <-- USA POOL

@app.route("/stock_sucursal/<int:id_sucursal>")
@login_required # Añadido decorador
def detalle_sucursal(id_sucursal):
    conn = None; cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute("SELECT * FROM sucursal WHERE id_sucursal = %s", (id_sucursal,))
        sucursal = cur.fetchone()
        if not sucursal:
            flash(f"Sucursal con ID {id_sucursal} no encontrada.", "danger")
            return redirect(url_for('crud_sucursales'))
        cur.execute("""
            SELECT DISTINCT p.categoria_producto FROM producto p
            JOIN variacion_producto v ON p.id_producto = v.id_producto
            JOIN inventario_sucursal i ON v.id_variacion = i.id_variacion
            WHERE i.id_sucursal = %s AND i.stock > 0 AND p.categoria_producto IS NOT NULL
            ORDER BY p.categoria_producto;
        """, (id_sucursal,))
        categorias_con_stock = [row['categoria_producto'] for row in cur.fetchall()]
        cur.execute("""
            SELECT 1 FROM producto p
            JOIN variacion_producto v ON p.id_producto = v.id_producto
            JOIN inventario_sucursal i ON v.id_variacion = i.id_variacion
            WHERE i.id_sucursal = %s AND i.stock > 0 AND p.categoria_producto IS NULL LIMIT 1;
        """, (id_sucursal,))
        if cur.fetchone():
            categorias_con_stock.append("Sin Categoría")
        cur.execute("""
            SELECT p.id_producto, p.nombre_producto, p.imagen_url, p.precio_producto,
                   p.categoria_producto, COALESCE(SUM(i.stock), 0) as stock_en_sucursal
            FROM producto p
            JOIN variacion_producto v ON p.id_producto = v.id_producto
            JOIN inventario_sucursal i ON v.id_variacion = i.id_variacion
            WHERE i.id_sucursal = %s AND i.stock > 0
            GROUP BY p.id_producto, p.categoria_producto
            ORDER BY p.categoria_producto NULLS LAST, p.nombre_producto;
        """, (id_sucursal,))
        productos_en_stock = cur.fetchall()
        productos_por_categoria = {cat: [] for cat in categorias_con_stock}
        for p in productos_en_stock:
            categoria_actual = p['categoria_producto'] if p['categoria_producto'] else "Sin Categoría"
            if categoria_actual in productos_por_categoria:
                productos_por_categoria[categoria_actual].append(dict(p))
        return render_template("sucursales/detalle_sucursal.html", sucursal=sucursal, categorias=categorias_con_stock, productos_agrupados=productos_por_categoria)
    except Exception as e:
        print(f"❌ Error en /stock_sucursal/{id_sucursal}: {e}"); traceback.print_exc()
        flash("Ocurrió un error al cargar el stock de la sucursal.", "danger")
        return redirect(url_for('crud_sucursales'))
    finally:
        if cur: cur.close()
        if conn: return_db_connection(conn) # <-- CAMBIO

# ===========================
# CRUD USUARIOS
# ===========================
@app.route('/usuarios')
@login_required
def crud_usuarios():
    filtro_rol = request.args.get('filtro_rol', '')
    filtro_nombre = request.args.get('filtro_nombre', '')
    conn = None; cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        base_query = "SELECT id_usuario, nombre_usuario, apellido_paterno, apellido_materno, rol_usuario, email_usuario, calle, numero_calle, region, ciudad, comuna, telefono FROM usuario"
        where_clauses, params = [], []
        if filtro_rol: where_clauses.append("rol_usuario = %s"); params.append(filtro_rol)
        if filtro_nombre: where_clauses.append("CONCAT(nombre_usuario, ' ', apellido_paterno, ' ', apellido_materno) ILIKE %s"); params.append(f"%{filtro_nombre}%")
        final_query = base_query
        if where_clauses: final_query += " WHERE " + " AND ".join(where_clauses)
        final_query += " ORDER BY id_usuario;"
        cur.execute(final_query, tuple(params))
        usuarios = cur.fetchall()
        cur.execute("SELECT DISTINCT rol_usuario FROM usuario WHERE rol_usuario IS NOT NULL ORDER BY rol_usuario;")
        roles = [row['rol_usuario'] for row in cur.fetchall()]
        cur.execute("SELECT DISTINCT nombre_usuario FROM usuario ORDER BY nombre_usuario;")
        nombres_usuarios = [row['nombre_usuario'] for row in cur.fetchall()]
        filtros_activos = { 'rol': filtro_rol, 'nombre': filtro_nombre }
        return render_template("usuarios/crud_usuarios.html", usuarios=usuarios, roles=roles, nombres_usuarios=nombres_usuarios, filtros_activos=filtros_activos)
    except Exception as e:
        print(f"Error en crud_usuarios: {e}"); traceback.print_exc()
        flash("Error al cargar usuarios", "danger")
        return redirect(url_for("index_options"))
    finally:
        if cur: cur.close()
        if conn: return_db_connection(conn) # <-- USA POOL

@app.route("/usuarios/add", methods=["POST"])
@login_required
def add_usuario():
    data = request.form
    telefono = data.get("telefono")
    email_usuario = data.get("email_usuario")
    password_hash = generate_password_hash(data["password"])
    conn = None; cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT id_usuario FROM usuario WHERE email_usuario = %s", (email_usuario,))
        if cur.fetchone():
            flash(f"❌ Error: El correo '{email_usuario}' ya está registrado.", "danger")
            return redirect(url_for("crud_usuarios"))
        cur.execute("SELECT id_usuario FROM usuario WHERE telefono = %s", (telefono, )) 
        if cur.fetchone():
            flash(f"❌ Error: El teléfono '{telefono}' ya está registrado.", "danger")
            return redirect(url_for("crud_usuarios"))
        cur.execute("""
            INSERT INTO usuario (nombre_usuario, apellido_paterno, apellido_materno, rol_usuario, email_usuario, password, calle, numero_calle, region, ciudad, comuna, telefono)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            data.get("nombre_usuario"), data.get("apellido_paterno"), data.get("apellido_materno"),
            data.get("rol_usuario"), data.get("email_usuario"), password_hash,
            data.get("calle"), data.get("numero_calle"), data.get("region"),
            data.get("ciudad"), data.get("comuna"), data.get("telefono")
        ))
        conn.commit()
        flash("✅ Usuario agregado correctamente", "success")
    except Exception as e:
        if conn: conn.rollback()
        flash(f"❌ Error: {str(e)}", "danger")
    finally:
        if cur: cur.close()
        if conn: return_db_connection(conn) # <-- USA POOL
    return redirect(url_for("crud_usuarios"))

@app.route("/usuarios/edit/<int:id_usuario>", methods=["POST"])
@login_required
def edit_usuario(id_usuario):
    data = request.form
    telefono = data.get("telefono")
    email_usuario = data.get("email_usuario") # Corregido
    conn = None; cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT id_usuario FROM usuario WHERE email_usuario = %s AND id_usuario != %s", (email_usuario, id_usuario))
        if cur.fetchone():
            flash(f"❌ Error: El correo '{email_usuario}' ya está registrado.", "danger")
            return redirect(url_for("crud_usuarios"))
        cur.execute("SELECT id_usuario FROM usuario WHERE telefono = %s AND id_usuario != %s", (telefono, id_usuario))
        if cur.fetchone():
            flash(f"❌ Error: El teléfono '{telefono}' ya está registrado.", "danger")
            return redirect(url_for("crud_usuarios"))
        if data.get("password"):
            password_hash = generate_password_hash(data["password"])
            cur.execute("""
                UPDATE usuario SET nombre_usuario=%s, apellido_paterno=%s, apellido_materno=%s,
                rol_usuario=%s, email_usuario=%s, password=%s, calle=%s, numero_calle=%s,
                region=%s, ciudad=%s, comuna=%s, telefono=%s
                WHERE id_usuario=%s
            """, (
                data.get("nombre_usuario"), data.get("apellido_paterno"), data.get("apellido_materno"),
                data.get("rol_usuario"), email_usuario, password_hash,
                data.get("calle"), data.get("numero_calle"), data.get("region"),
                data.get("ciudad"), data.get("comuna"), telefono, id_usuario
            ))
        else:
            cur.execute("""
                UPDATE usuario SET nombre_usuario=%s, apellido_paterno=%s, apellido_materno=%s,
                rol_usuario=%s, email_usuario=%s, calle=%s, numero_calle=%s,
                region=%s, ciudad=%s, comuna=%s, telefono=%s
                WHERE id_usuario=%s
            """, (
                data.get("nombre_usuario"), data.get("apellido_paterno"), data.get("apellido_materno"),
                data.get("rol_usuario"), email_usuario,
                data.get("calle"), data.get("numero_calle"), data.get("region"),
                data.get("ciudad"), data.get("comuna"), telefono, id_usuario
            ))
        conn.commit()
        flash("✅ Usuario actualizado correctamente", "success")
    except Exception as e:
        if conn: conn.rollback()
        flash(f"❌ Error: {str(e)}", "danger")
    finally:
        if cur: cur.close()
        if conn: return_db_connection(conn) # <-- USA POOL
    return redirect(url_for("crud_usuarios"))

@app.route("/usuarios/delete/<int:id_usuario>", methods=["POST"])
@login_required
def delete_usuario(id_usuario):
    conn = None; cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM usuario WHERE id_usuario=%s", (id_usuario,))
        conn.commit()
        flash("✅ Usuario eliminado correctamente", "success")
    except Exception as e:
        if conn: conn.rollback()
        flash(f"❌ Error: {str(e)}", "danger")
    finally:
        if cur: cur.close()
        if conn: return_db_connection(conn) # <-- USA POOL
    return redirect(url_for("crud_usuarios"))

@app.route("/usuarios/view/<int:id_usuario>")
@login_required
def view_usuario(id_usuario):
    conn = None; cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute("SELECT * FROM usuario WHERE id_usuario=%s", (id_usuario,))
        usuario = cur.fetchone()
        return render_template("usuarios/view_usuario.html", usuario=usuario)
    except Exception as e:
        print(f"Error en view_usuario: {e}"); traceback.print_exc()
        flash("Error al ver usuario", "danger")
        return redirect(url_for("crud_usuarios"))
    finally:
        if cur: cur.close()
        if conn: return_db_connection(conn) # <-- USA POOL

# ===========================
# CRUD OFERTAS 
# ===========================
@app.route('/ofertas')
@login_required
def crud_ofertas():
    filtro_id = request.args.get('q', '')
    filtro_estado = request.args.get('filtro_estado', '')
    filtro_titulo = request.args.get('filtro_titulo', '')
    filtro_producto = request.args.get('filtro_producto', '')
    filtro_descuento = request.args.get('filtro_descuento', '')
    conn = None; cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        base_query = """
            SELECT o.id_oferta, o.titulo, o.descripcion, o.descuento_pct, o.fecha_inicio, o.fecha_fin, o.vigente_bool,
                   p.id_producto, p.nombre_producto, p.imagen_url, p.precio_producto
            FROM oferta o JOIN oferta_producto op ON o.id_oferta = op.id_oferta
            JOIN producto p ON op.id_producto = p.id_producto
        """
        where_clauses, params = [], []
        if filtro_id: where_clauses.append("o.id_oferta::text ILIKE %s"); params.append(f"%{filtro_id}%")
        if filtro_titulo: where_clauses.append("o.titulo = %s"); params.append(filtro_titulo)
        if filtro_producto: where_clauses.append("p.id_producto = %s"); params.append(filtro_producto)
        if filtro_estado == 'vigente': where_clauses.append("CURRENT_DATE BETWEEN o.fecha_inicio AND o.fecha_fin")
        elif filtro_estado == 'finalizada': where_clauses.append("o.fecha_fin < CURRENT_DATE")
        elif filtro_estado == 'en_espera': where_clauses.append("o.fecha_inicio > CURRENT_DATE")
        if filtro_descuento == 'high': where_clauses.append("o.descuento_pct BETWEEN 70 AND 95")
        elif filtro_descuento == 'medium': where_clauses.append("o.descuento_pct BETWEEN 30 AND 69.99")
        elif filtro_descuento == 'low': where_clauses.append("o.descuento_pct BETWEEN 5 AND 29.99")
        final_query = base_query
        if where_clauses: final_query += " WHERE " + " AND ".join(where_clauses)
        final_query += " ORDER BY o.id_oferta DESC;"
        cur.execute(final_query, tuple(params))
        ofertas = cur.fetchall()
        cur.execute("""
            SELECT p.id_producto, p.nombre_producto, COALESCE(SUM(i.stock), 0) AS stock
            FROM producto p
            LEFT JOIN variacion_producto v ON v.id_producto = p.id_producto
            LEFT JOIN inventario_sucursal i ON i.id_variacion = v.id_variacion
            GROUP BY p.id_producto, p.nombre_producto ORDER BY p.nombre_producto;
        """)
        productos = cur.fetchall()
        cur.execute("SELECT DISTINCT titulo FROM oferta ORDER BY titulo;")
        titulos_ofertas = [row['titulo'] for row in cur.fetchall()]
        filtros_activos = { 'q': filtro_id, 'estado': filtro_estado, 'titulo': filtro_titulo, 'producto': filtro_producto, 'descuento': filtro_descuento }
        return render_template("ofertas/crud_ofertas.html", ofertas=ofertas, productos=productos, titulos_ofertas=titulos_ofertas, filtros_activos=filtros_activos, now=datetime.now()) # <-- CORREGIDO
    except Exception as e:
        print(f"Error en crud_ofertas: {e}"); traceback.print_exc()
        flash("Error al cargar ofertas", "danger")
        return redirect(url_for("index_options"))
    finally:
        if cur: cur.close()
        if conn: return_db_connection(conn) # <-- USA POOL

@app.route("/api/ofertas/titulos_por_estado")
@login_required
def api_titulos_por_estado():
    estado = request.args.get('estado', '')
    conn = None; cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        query = "SELECT DISTINCT titulo FROM oferta"
        if estado == 'vigente': query += " WHERE CURRENT_DATE BETWEEN fecha_inicio AND fecha_fin"
        elif estado == 'finalizada': query += " WHERE fecha_fin < CURRENT_DATE"
        elif estado == 'en_espera': query += " WHERE fecha_inicio > CURRENT_DATE"
        query += " ORDER BY titulo;"
        cur.execute(query)
        titulos = [row[0] for row in cur.fetchall()]
        return jsonify({"titulos": titulos})
    except Exception as e:
        return jsonify({"titulos": [], "error": str(e)}), 500
    finally:
        if cur: cur.close()
        if conn: return_db_connection(conn) # <-- USA POOL

@app.route("/ofertas/add", methods=["POST"])
@login_required
def add_oferta():
    data = request.form
    conn = None; cur = None
    try:
        fecha_inicio = data.get("fecha_inicio"); fecha_fin = data.get("fecha_fin")
        hoy = date.today(); vigente = fecha_inicio <= str(hoy) <= fecha_fin
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO oferta (titulo, descripcion, descuento_pct, fecha_inicio, fecha_fin, vigente_bool)
            VALUES (%s, %s, %s, %s, %s, %s) RETURNING id_oferta;
        """, (data.get("titulo"), data.get("descripcion"), data.get("descuento_pct"), fecha_inicio, fecha_fin, vigente))
        id_oferta = cur.fetchone()[0]
        id_producto = data.get("productos")
        if id_producto and id_producto.strip() != "":
            id_producto = int(id_producto)
            cur.execute("INSERT INTO oferta_producto (id_oferta, id_producto) VALUES (%s, %s);", (id_oferta, id_producto))
        else:
            raise ValueError("Debes seleccionar un producto para la oferta")
        conn.commit()
        flash("✅ Oferta agregada correctamente", "success")
    except Exception as e:
        if conn: conn.rollback()
        flash(f"❌ Error al agregar la oferta: {str(e)}", "danger")
    finally:
        if cur: cur.close()
        if conn: return_db_connection(conn) # <-- USA POOL
    return redirect(url_for("crud_ofertas"))

@app.route("/ofertas/edit/<int:id_oferta>", methods=["GET", "POST"])
@login_required
def edit_oferta(id_oferta):
    conn = None; cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        if request.method == "POST":
            data = request.form
            fecha_inicio_str = data.get("fecha_inicio"); fecha_fin_str = data.get("fecha_fin")
            hoy_str = date.today().isoformat(); vigente = (fecha_inicio_str <= hoy_str <= fecha_fin_str)
            cur.execute("""
                UPDATE oferta SET titulo=%s, descripcion=%s, descuento_pct=%s, 
                fecha_inicio=%s, fecha_fin=%s, vigente_bool=%s
                WHERE id_oferta=%s;
            """, (data.get("titulo"), data.get("descripcion"), data.get("descuento_pct"), fecha_inicio_str, fecha_fin_str, vigente, id_oferta))
            cur.execute("DELETE FROM oferta_producto WHERE id_oferta=%s;", (id_oferta,))
            productos_seleccionados = data.getlist("productos")
            for id_producto in productos_seleccionados:
                cur.execute("INSERT INTO oferta_producto (id_oferta, id_producto) VALUES (%s, %s);", (id_oferta, id_producto))
            conn.commit()
            flash("✅ Oferta actualizada correctamente", "success")
            return redirect(url_for("crud_ofertas"))
        
        # GET
        cur.execute("SELECT * FROM oferta WHERE id_oferta=%s;", (id_oferta,))
        oferta = cur.fetchone()
        cur.execute("SELECT id_producto FROM oferta_producto WHERE id_oferta=%s;", (id_oferta,))
        cur.execute("""
            SELECT p.id_producto, p.nombre_producto, COALESCE(SUM(i.stock), 0) AS stock
            FROM producto p
            LEFT JOIN variacion_producto v ON v.id_producto = p.id_producto
            LEFT JOIN inventario_sucursal i ON i.id_variacion = v.id_variacion
            GROUP BY p.id_producto, p.nombre_producto ORDER BY p.nombre_producto;
        """)
        productos = cur.fetchall()
        return redirect(url_for('crud_ofertas')) # Tu lógica original
        
    except Exception as e:
        if conn: conn.rollback()
        flash(f"❌ Error al editar la oferta: {str(e)}", "danger")
        return redirect(url_for("crud_ofertas"))
    finally:
        if cur: cur.close()
        if conn: return_db_connection(conn) # <-- USA POOL

@app.route("/ofertas/delete/<int:id_oferta>", methods=["POST"])
@login_required
def delete_oferta(id_oferta):
    conn = None; cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM oferta_producto WHERE id_oferta=%s;", (id_oferta,))
        cur.execute("DELETE FROM oferta WHERE id_oferta=%s;", (id_oferta,))
        conn.commit()
        flash("✅ Oferta eliminada correctamente", "success")
    except Exception as e:
        if conn: conn.rollback()
        flash(f"❌ Error al eliminar la oferta: {str(e)}", "danger")
    finally:
        if cur: cur.close()
        if conn: return_db_connection(conn) # <-- USA POOL
    return redirect(url_for("crud_ofertas"))

@app.route("/ofertas/view/<int:id_oferta>")
@login_required
def view_oferta(id_oferta):
    conn = None; cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute("""
            SELECT o.id_oferta, o.titulo, o.descripcion, o.descuento_pct, 
                   o.fecha_inicio, o.fecha_fin, o.vigente_bool,
                   STRING_AGG(op.id_producto::TEXT, ', ') AS productos_asociados
            FROM oferta o
            LEFT JOIN oferta_producto op ON o.id_oferta = op.id_oferta
            WHERE o.id_oferta = %s GROUP BY o.id_oferta;
        """, (id_oferta,))
        oferta = cur.fetchone()
        return render_template("ofertas/crud_ofertas.html", ofertas=oferta, now=datetime.now()) # <-- CORREGIDO
    except Exception as e:
        print(f"Error en view_oferta: {e}"); traceback.print_exc()
        flash("Error al ver oferta", "danger")
        return redirect(url_for("crud_ofertas"))
    finally:
        if cur: cur.close()
        if conn: return_db_connection(conn) # <-- USA POOL

# ===========================
# HELPERS (CON POOL)
# ===========================
def get_user_by_email(email):
    conn = None; cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute("""
            SELECT id_usuario, nombre_usuario, apellido_paterno, apellido_materno,
                   email_usuario, rol_usuario, password, calle, numero_calle, region, ciudad, comuna, telefono, creado_en
            FROM usuario WHERE LOWER(email_usuario) = LOWER(%s) LIMIT 1;
        """, (email,))
        user = cur.fetchone()
        return user
    except Exception as e:
        print(f"Error en get_user_by_email: {e}"); return None
    finally:
        if cur: cur.close()
        if conn: return_db_connection(conn) # <-- USA POOL

def create_user(data):
    email_norm = (data.get("email_usuario") or "").strip().lower()
    password_plano = data.get("password")
    password_hash = generate_password_hash(password_plano)
    conn = None; cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute("SELECT 1 FROM usuario WHERE LOWER(email_usuario)=LOWER(%s) LIMIT 1;", (email_norm,))
        if cur.fetchone():
            return False, "El correo ya está registrado."
        query = """
        INSERT INTO usuario (
            nombre_usuario, apellido_paterno, apellido_materno,
            email_usuario, rol_usuario, password,
            calle, numero_calle, region, ciudad, comuna, telefono, creado_en
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id_usuario;
        """
        values = (
            data.get("nombre_usuario"), data.get("apellido_paterno"), data.get("apellido_materno"),
            email_norm, "cliente", password_hash,
            data.get("calle"), data.get("numero_calle"), data.get("region"),
            data.get("ciudad"), data.get("comuna"), data.get("telefono"),
            datetime.now() # Corregido
        )
        cur.execute(query, values)
        new_id = cur.fetchone()[0]
        conn.commit()
        return True, new_id
    except errors.UniqueViolation:
        if conn: conn.rollback(); return False, "El correo ya está registrado."
    except Exception as e:
        if conn: conn.rollback()
        print(f"❌ Error al crear usuario: {e}"); traceback.print_exc()
        return False, f"Error de servidor: {e}"
    finally:
        if cur: cur.close()
        if conn: return_db_connection(conn) # <-- USA POOL

def do_login(email, password):
    if not email or not password:
        return False, "Debes ingresar correo y contraseña."
    user = get_user_by_email(email) # Esta función ya usa el pool
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
    if not data.get("nombre_usuario") or not data.get("email_usuario") or not data.get("password"):
        return False, "Nombre, correo y contraseña son obligatorios."
    ok, result = create_user(data)
    if not ok: return False, result
    ok_l, msg = do_login(data.get("email_usuario"), data.get("password"))
    if not ok_l: return False, msg
    return True, None

# ===========================
# RUTAS AUTENTICACIÓN (CON POOL)
# ===========================
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return send_from_directory(SRC_DIR, "login.html")
    
    email = (request.form.get("email_usuario") or "").strip()
    password = (request.form.get("password") or "").strip()
    if not email or not password:
        return redirect(url_for("login") + "?error=missing&tab=login&src=login")
    
    # do_login ya usa el pool (a través de get_user_by_email)
    ok, msg = do_login(email, password) 
    
    if not ok:
        if msg == "Credenciales inválidas.":
             return redirect(url_for("login") + "?error=bad_password&tab=login&src=login")
        else:
             return redirect(url_for("login") + "?error=user_not_found&tab=login&src=login")

    return redirect(FRONTEND_MAIN_URL)

# ===========================
# RUTAS Registro (CON POOL)
# ===========================
def validar_password(password):
    if not password: return False, "Debes ingresar una contraseña."
    if len(password) < 6 or len(password) > 24: return False, "La contraseña debe tener entre 6 y 24 caracteres."
    if not re.search(r"[A-Z]", password): return False, "La contraseña debe incluir al menos una letra mayúscula."
    if not re.search(r"\d", password): return False, "La contraseña debe incluir al menos un número."
    if not re.search(r"[^A-Za-z0-9]", password): return False, "La contraseña debe incluir al menos un carácter especial."
    return True, None

@app.route("/register", methods=["POST"])
def register():
    data = request.form.to_dict()
    conn = None; cur = None
    try:
        # 1. Validaciones
        if data.get("email_usuario", "").lower() != (data.get("email_confirm") or "").lower():
            return redirect(url_for("login") + "?error=email_mismatch&tab=register&src=register")
        if data.get("password") != data.get("password_confirm"):
            return redirect(url_for("login") + "?error=password_mismatch&tab=register&src=register")
        ok, msg = validar_password(data.get("password"))
        if not ok:
            return redirect(url_for("login") + f"?error=weak_password&tab=register&src=register&msg={msg}")

        # 2. Insertar en DB (usando pool)
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("SELECT 1 FROM usuario WHERE telefono = %s LIMIT 1;", (data.get("telefono"),))
        if cur.fetchone() is not None:
            return redirect(url_for("login") + "?error=telefono_exists&tab=register&src=register")
        cur.execute("SELECT 1 FROM usuario WHERE email_usuario = %s LIMIT 1;", (data.get("email_usuario"),))
        if cur.fetchone() is not None:
            return redirect(url_for("login") + "?error=email_exists&tab=register&src=register")

        hashed_password = generate_password_hash(data["password"])
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
        conn.commit()
        
        # 3. Auto-login y Redirección
        do_login(data.get("email_usuario"), data.get("password"))
        return redirect(FRONTEND_MAIN_URL)

    except Exception as e:
        if conn: conn.rollback()
        print(f"Error al registrar usuario: {e}"); traceback.print_exc()
        return redirect(url_for("login") + f"?error=unknown&tab=register&src=register&msg={e}")
    finally:
        if cur: cur.close()
        if conn: return_db_connection(conn) # <-- USA POOL

# ===========================
# Validar Email/Teléfono en registro (Async) (CON POOL)
# ===========================
@app.route('/check_email', methods=['GET'])
def check_email():
    email = request.args.get('email')
    if not email: return jsonify({'exists': False})
    conn = None; cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        query = "SELECT 1 FROM usuario WHERE email_usuario = %s LIMIT 1;"
        cur.execute(query, (email,))
        email_exists = cur.fetchone() is not None
        return jsonify({'exists': email_exists})
    except Exception as e:
        print(f"Error al verificar el correo en DB: {e}")
        return jsonify({'exists': False}), 500
    finally:
        if cur: cur.close()
        if conn: return_db_connection(conn) # <-- USA POOL

@app.route('/check_telefono', methods=['GET'])
def check_telefono():
    telefono = request.args.get('telefono')
    if not telefono: return jsonify({'exists': False})
    conn = None; cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM usuario WHERE telefono = %s LIMIT 1;", (telefono,))
        telefono_exists = cur.fetchone() is not None
        return jsonify({'exists': telefono_exists})
    except Exception as e:
        print(f"Error al verificar el teléfono en DB: {e}")
        return jsonify({'exists': False}), 500
    finally:
        if cur: cur.close()
        if conn: return_db_connection(conn) # <-- USA POOL

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login")) # Redirige a la página de login HTML

@app.route("/perfil")
@login_required
def perfil():
    conn = None; cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        return f"""
        <h1>Perfil</h1>
        <ul>
            <li>ID: {session.get('user_id')}</li>
            <li>Nombre: {session.get('nombre_usuario')}</li>
            <li>Rol: {session.get('rol_usuario')}</li>
            <li>Email: {session.get('email_usuario')}</li>
        </ul>
        """
    except Exception as e:
        print(f"Error en perfil: {e}")
        return "Error al cargar perfil"
    finally:
        if cur: cur.close()
        if conn: return_db_connection(conn) # <-- USA POOL

# ===========================
# API Productos (JSON) - (Admin) (CON POOL)
# ===========================
@app.route("/api/productos", methods=["GET"])
@login_required
def api_list_productos():
    q = (request.args.get("q") or "").strip()
    categoria = (request.args.get("categoria") or "").strip()
    conn = None; cur = None
    try:
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
        where, params = [], []
        if q: where.append("(p.sku ILIKE %s OR p.nombre_producto ILIKE %s)"); params += [f"%{q}%", f"%{q}%"]
        if categoria and categoria.lower() != "todas": where.append("p.categoria_producto ILIKE %s"); params.append(categoria)
        if where: base_sql += " WHERE " + " AND ".join(where)
        base_sql += " GROUP BY p.id_producto ORDER BY p.id_producto;"
        cur.execute(base_sql, params)
        rows = cur.fetchall()
        data = [dict(r) for r in rows]
        return jsonify(data), 200
    except Exception as e:
        print(f"Error en api_list_productos: {e}"); traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    finally:
        if cur: cur.close()
        if conn: return_db_connection(conn) # <-- USA POOL

@app.route("/api/productos", methods=["POST"])
@login_required
def api_create_producto():
    payload = request.get_json(silent=True) or request.form
    sku = (payload.get("sku") or "").strip()
    nombre = (payload.get("nombre_producto") or "").strip()
    precio = payload.get("precio_producto")
    if not sku or not nombre or not precio:
        return jsonify({"error": "sku, nombre_producto y precio_producto son obligatorios."}), 400
    conn = None; cur = None
    try:
        precio = float(precio)
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO producto (sku, nombre_producto, precio_producto, descripcion_producto, categoria_producto, imagen_url)
            VALUES (%s, %s, %s, %s, %s, %s) RETURNING id_producto;
        """, (sku, nombre, precio, payload.get("descripcion_producto"), payload.get("categoria_producto"), payload.get("imagen_url")))
        new_id = cur.fetchone()[0]
        conn.commit()
        return jsonify({"ok": True, "id_producto": new_id}), 201
    except errors.UniqueViolation:
        if conn: conn.rollback(); return jsonify({"error": "El SKU ya existe."}), 409
    except Exception as e:
        if conn: conn.rollback(); return jsonify({"error": str(e)}), 500
    finally:
        if cur: cur.close()
        if conn: return_db_connection(conn) # <-- USA POOL

@app.route("/api/productos/<int:id_producto>", methods=["PUT", "PATCH"])
@login_required
def api_update_producto(id_producto):
    payload = request.get_json(silent=True) or request.form
    sets, params = [], []
    if payload.get("sku") is not None: sets.append("sku=%s"); params.append(payload.get("sku"))
    if payload.get("nombre_producto") is not None: sets.append("nombre_producto=%s"); params.append(payload.get("nombre_producto"))
    if payload.get("precio_producto") is not None: sets.append("precio_producto=%s"); params.append(payload.get("precio_producto"))
    if payload.get("descripcion_producto") is not None: sets.append("descripcion_producto=%s"); params.append(payload.get("descripcion_producto"))
    if payload.get("categoria_producto") is not None: sets.append("categoria_producto=%s"); params.append(payload.get("categoria_producto"))
    if payload.get("imagen_url") is not None: sets.append("imagen_url=%s"); params.append(payload.get("imagen_url"))
    if not sets: return jsonify({"error": "Nada que actualizar."}), 400
    
    sql = f"UPDATE producto SET {', '.join(sets)} WHERE id_producto=%s"
    params.append(id_producto)
    conn = None; cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(sql, params)
        if cur.rowcount == 0: conn.rollback(); return jsonify({"error": "Producto no encontrado."}), 404
        conn.commit()
        return jsonify({"ok": True}), 200
    except errors.UniqueViolation:
        if conn: conn.rollback(); return jsonify({"error": "El SKU ya existe."}), 409
    except Exception as e:
        if conn: conn.rollback(); return jsonify({"error": str(e)}), 500
    finally:
        if cur: cur.close()
        if conn: return_db_connection(conn) # <-- USA POOL

@app.route("/api/productos/<int:id_producto>", methods=["DELETE"])
@login_required
def api_delete_producto(id_producto):
    conn = None; cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM producto WHERE id_producto=%s", (id_producto,))
        if cur.rowcount == 0: conn.rollback(); return jsonify({"error": "Producto no encontrado."}), 404
        conn.commit()
        return jsonify({"ok": True}), 200
    except Exception as e:
        if conn: conn.rollback(); return jsonify({"error": str(e)}), 500
    finally:
        if cur: cur.close()
        if conn: return_db_connection(conn) # <-- USA POOL

@app.route("/api/productos/bulk_delete", methods=["POST"])
@login_required
def api_bulk_delete_productos():
    payload = request.get_json(silent=True) or {}; ids = payload.get("ids") or []
    if not isinstance(ids, list) or not ids: return jsonify({"error": "Debes enviar lista 'ids'."}), 400
    conn = None; cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM producto WHERE id_producto = ANY(%s::int[])", (ids,))
        conn.commit()
        return jsonify({"ok": True, "deleted": cur.rowcount}), 200
    except Exception as e:
        if conn: conn.rollback(); return jsonify({"error": str(e)}), 500
    finally:
        if cur: cur.close()
        if conn: return_db_connection(conn) # <-- USA POOL

# ===========================
# Gestión de Imágenes (Admin) (CON POOL)
# ===========================
@app.route('/producto/<int:id_producto>/imagenes', methods=['GET'])
@login_required
def gestionar_imagenes(id_producto):
    conn = None; cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute("SELECT * FROM producto WHERE id_producto = %s", (id_producto,))
        producto = cur.fetchone()
        cur.execute("SELECT * FROM producto_imagenes WHERE id_producto = %s ORDER BY orden", (id_producto,))
        imagenes_adicionales = cur.fetchall()
        if not producto: flash("❌ Producto no encontrado.", "danger"); return redirect(url_for('crud_productos'))
        return render_template('productos/gestionar_imagenes.html', producto=producto, imagenes_adicionales=imagenes_adicionales)
    except Exception as e:
        print(f"Error en gestionar_imagenes: {e}"); traceback.print_exc()
        flash("Error al cargar página de imágenes", "danger")
        return redirect(url_for('crud_productos'))
    finally:
        if cur: cur.close()
        if conn: return_db_connection(conn) # <-- USA POOL

@app.route('/producto/<int:id_producto>/guardar_imagenes', methods=['POST'])
@login_required
def guardar_imagenes(id_producto):
    conn = None; cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        imagen_principal_url = request.form.get('imagen_principal')
        cur.execute("UPDATE producto SET imagen_url = %s WHERE id_producto = %s", (imagen_principal_url, id_producto))
        cur.execute("DELETE FROM producto_imagenes WHERE id_producto = %s", (id_producto,))
        imagenes_adicionales = request.form.getlist('imagenes_adicionales[]')
        orden = 1
        for url in imagenes_adicionales:
            if url:
                cur.execute("INSERT INTO producto_imagenes (id_producto, url_imagen, orden) VALUES (%s, %s, %s)", (id_producto, url, orden))
                orden += 1
        conn.commit()
        flash("✅ Imágenes guardadas correctamente.", "success")
    except Exception as e:
        if conn: conn.rollback()
        flash(f"❌ Error al guardar las imágenes: {e}", "danger")
    finally:
        if cur: cur.close()
        if conn: return_db_connection(conn) # <-- USA POOL
    return redirect(url_for('gestionar_imagenes', id_producto=id_producto))

# ===========================
# API Detalle Producto (Público) (CON POOL)
# ===========================
@app.route('/api/producto/<int:id_producto>')
def api_detalle_producto(id_producto):
    sucursal_id_str = request.args.get('sucursal_id', None)
    sucursal_id = None
    if sucursal_id_str:
        try: sucursal_id = int(sucursal_id_str); print(f"[API Detalle Debug] Buscando stock para sucursal ID: {sucursal_id}")
        except ValueError: print(f"[API Detalle Warn] sucursal_id ('{sucursal_id_str}') inválido."); sucursal_id = None
    else: print("[API Detalle Debug] No se proporcionó sucursal_id. Calculando stock total.")
    
    conn = None; cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute("""
            SELECT p.*, o.descuento_pct, o.fecha_fin AS oferta_fecha_fin
            FROM producto p
            LEFT JOIN oferta_producto op ON p.id_producto = op.id_producto
            LEFT JOIN oferta o ON op.id_oferta = o.id_oferta
                 AND CURRENT_DATE BETWEEN o.fecha_inicio AND o.fecha_fin AND o.vigente_bool = TRUE
            WHERE p.id_producto = %s LIMIT 1;
        """, (id_producto,))
        producto_data = cur.fetchone()
        if not producto_data: return jsonify({"error": "Producto no encontrado"}), 404
        producto = dict(producto_data)
        todas_las_imagenes = [producto.get('imagen_url')] if producto.get('imagen_url') else []
        cur.execute("SELECT url_imagen FROM producto_imagenes WHERE id_producto = %s ORDER BY orden", (id_producto,))
        imagenes_adicionales = [row['url_imagen'] for row in cur.fetchall()]
        todas_las_imagenes.extend(imagenes_adicionales)
        variaciones_params = [id_producto]
        variaciones_query = "SELECT v.talla, v.sku_variacion, v.color, "
        if sucursal_id is not None:
            variaciones_query += "COALESCE(i.stock, 0) as stock FROM variacion_producto v LEFT JOIN inventario_sucursal i ON v.id_variacion = i.id_variacion AND i.id_sucursal = %s WHERE v.id_producto = %s"
            variaciones_params.insert(0, sucursal_id)
        else:
            variaciones_query += "COALESCE(SUM(i.stock), 0) as stock FROM variacion_producto v LEFT JOIN inventario_sucursal i ON v.id_variacion = i.id_variacion WHERE v.id_producto = %s GROUP BY v.id_variacion, v.talla, v.sku_variacion, v.color"
        variaciones_query += " ORDER BY v.talla IS NULL DESC, CASE WHEN v.talla = 'XS' THEN 1 WHEN v.talla = 'S' THEN 2 WHEN v.talla = 'M' THEN 3 WHEN v.talla = 'L' THEN 4 WHEN v.talla = 'XL' THEN 5 ELSE 6 END;"
        cur.execute(variaciones_query, tuple(variaciones_params))
        variaciones = cur.fetchall()
        stock_total_calculado = sum(v['stock'] for v in variaciones if v['stock'] is not None)
        precio_original = float(producto.get('precio_producto', 0))
        descuento = producto.get('descuento_pct')
        if descuento is not None:
            try:
                descuento_float = float(descuento)
                if 0 < descuento_float <= 100: producto['descuento_pct'] = descuento_float; producto['precio_oferta'] = round(precio_original * (1 - descuento_float / 100.0))
                else: producto['descuento_pct'] = None; producto['precio_oferta'] = None
            except (ValueError, TypeError): producto['descuento_pct'] = None; producto['precio_oferta'] = None
        else: producto['descuento_pct'] = None; producto['precio_oferta'] = None
        datos_producto = {
            "producto": producto, "imagenes": todas_las_imagenes,
            "variaciones": [dict(v) for v in variaciones],
            "stock_disponible": int(stock_total_calculado)
        }
        return jsonify(datos_producto)
    except Exception as e:
        print(f"\n--- ¡ERROR GRAVE EN /api/producto/{id_producto}! ---"); traceback.print_exc()
        return jsonify({"error": "Error interno del servidor"}), 500
    finally:
        if cur: cur.close()
        if conn: return_db_connection(conn) # <-- USA POOL

# ===========================
# API Productos (Público) (CON POOL)
# ===========================
@app.route("/api/productos_public", methods=["GET"])
def api_list_productos_public():
    q = (request.args.get("q") or "").strip()
    categoria = (request.args.get("categoria") or "").strip()
    print(f"\n--- [API Productos Public Recibido] ---"); print(f"Parámetro 'q': '{q}'"); print(f"Parámetro 'categoria': '{categoria}'")
    conn = None; cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        base_sql = """
            SELECT
                p.id_producto, p.sku, p.nombre_producto, p.descripcion_producto,
                p.categoria_producto, p.precio_producto, p.imagen_url,
                (SELECT COALESCE(SUM(i_sub.stock), 0) FROM variacion_producto v_sub
                 JOIN inventario_sucursal i_sub ON i_sub.id_variacion = v_sub.id_variacion
                 WHERE v_sub.id_producto = p.id_producto) as stock,
                o.descuento_pct, o.fecha_fin
            FROM producto p
            LEFT JOIN oferta_producto op ON p.id_producto = op.id_producto
            LEFT JOIN oferta o ON op.id_oferta = o.id_oferta
                 AND CURRENT_DATE BETWEEN o.fecha_inicio AND o.fecha_fin AND o.vigente_bool = TRUE
        """
        where_clauses, params = [], []
        if q: where_clauses.append("(p.sku ILIKE %s OR p.nombre_producto ILIKE %s)"); params.extend([f"%{q}%", f"%{q}%"])
        if categoria: where_clauses.append("TRIM(LOWER(p.categoria_producto)) = LOWER(%s)"); params.append(categoria); print(f"Aplicando filtro EXACTO (lower/trim) por categoría: {categoria}")
        if where_clauses: base_sql += " WHERE " + " AND ".join(where_clauses)
        base_sql += " ORDER BY p.id_producto;"
        print("Query SQL final a ejecutar:\n", cur.mogrify(base_sql, tuple(params)).decode('utf-8', 'ignore'))
        cur.execute(base_sql, tuple(params))
        rows = cur.fetchall()
        print(f"Productos encontrados: {len(rows)}"); print("------------------------------------\n")
        data, processed_ids = [], set()
        for r in rows:
            product_id = r['id_producto']
            if product_id in processed_ids: continue
            producto_dict = dict(r); precio_original = float(producto_dict.get('precio_producto', 0)); descuento = producto_dict.get('descuento_pct')
            if descuento is not None:
                try:
                    descuento_float = float(descuento)
                    precio_con_descuento = precio_original * (1 - descuento_float / 100.0)
                    producto_dict['precio_oferta'] = round(precio_con_descuento)
                    producto_dict['descuento_pct'] = descuento_float
                except (ValueError, TypeError): producto_dict['precio_oferta'] = None; producto_dict['descuento_pct'] = None
            else: producto_dict['precio_oferta'] = None; producto_dict['descuento_pct'] = None
            data.append(producto_dict); processed_ids.add(product_id)
        return jsonify(data), 200
    except Exception as e:
        print(f"❌ Error en /api/productos_public: {e}"); traceback.print_exc()
        return jsonify({"error": "Error al cargar productos"}), 500
    finally:
        if cur: cur.close()
        if conn: return_db_connection(conn) # <-- USA POOL

@app.route("/api/ofertas_public", methods=["GET"])
def api_list_ofertas_public():
    conn = None
    try:
        conn = get_db_connection()
        data = []
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur_ofertas:
            cur_ofertas.execute("""
                SELECT id_oferta, titulo, descripcion, descuento_pct, fecha_inicio, fecha_fin
                FROM oferta WHERE vigente_bool = TRUE AND CURRENT_DATE BETWEEN fecha_inicio AND fecha_fin
                ORDER BY fecha_inicio DESC;
            """)
            ofertas = cur_ofertas.fetchall()
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur_prod:
            for o in ofertas:
                cur_prod.execute("""
                    SELECT p.id_producto, p.nombre_producto, p.precio_producto,
                           p.imagen_url, p.sku, p.categoria_producto
                    FROM producto p INNER JOIN oferta_producto op ON op.id_producto = p.id_producto
                    WHERE op.id_oferta = %s;
                """, (o["id_oferta"],))
                productos_de_oferta = cur_prod.fetchall()
                data.append({
                    "id_oferta": o["id_oferta"], "titulo": o["titulo"], "descripcion": o["descripcion"],
                    "descuento_pct": float(o["descuento_pct"]),
                    "fecha_inicio": o["fecha_inicio"].isoformat(), "fecha_fin": o["fecha_fin"].isoformat(),
                    "productos": [dict(p) for p in productos_de_oferta]
                })
        return jsonify(data), 200
    except Exception as e:
        print(f"❌ Error en /api/ofertas_public: {e}"); traceback.print_exc()
        return jsonify({"error": "Error al cargar ofertas"}), 500
    finally:
        if conn: return_db_connection(conn) # <-- USA POOL


# ===========================
# RUTAS DE PEDIDOS Y PAGOS
# ===========================  

@app.route('/api/crear-pedido', methods=['POST'])
@login_required 
def crear_pedido():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No se recibieron datos JSON"}), 400
        
    cart_items = data.get('items')
    total = data.get('total')
    user_id = session.get('user_id') 
    # --- ▼▼▼ ¡NUEVO! Obtener sucursal del frontend ▼▼▼ ---
    sucursal_id = data.get('sucursal_id') 
    # --- ▲▲▲ FIN NUEVO ▲▲▲ ---

    if not cart_items or not total or not user_id:
        return jsonify({"error": "Faltan datos (items, total o usuario)"}), 400
    
    # Es válido comprar sin una sucursal (ej. si el stock es nacional)
    if not sucursal_id:
        print("Advertencia: Pedido creado sin ID de sucursal.")
        # O puedes devolver un error si es obligatorio:
        # return jsonify({"error": "Falta id_sucursal"}), 400

    conn = None
    cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor) 

        # --- ▼▼▼ ¡MODIFICADO! Añadir id_sucursal al SQL ▼▼▼ ---
        sql_pedido = """
            INSERT INTO pedido (id_usuario, total, estado_pedido, id_sucursal)
            VALUES (%s, %s, %s, %s)
            RETURNING id_pedido;
        """
        cur.execute(sql_pedido, (user_id, total, 'pendiente', sucursal_id))
        # --- ▲▲▲ FIN MODIFICACIÓN ▲▲▲ ---
        
        id_pedido_nuevo = cur.fetchone()['id_pedido'] 
        
        print(f"Pedido {id_pedido_nuevo} creado para usuario {user_id} desde sucursal {sucursal_id}")

        sql_detalle = """
            INSERT INTO detalle_pedido (id_pedido, sku_producto, cantidad, precio_unitario)
            VALUES (%s, %s, %s, %s);
        """
        for item in cart_items:
            cur.execute(sql_detalle, (
                id_pedido_nuevo,
                item.get('sku'),
                item.get('qty'),
                item.get('price')
            ))
        
        conn.commit()
        
        return jsonify({"id_pedido": id_pedido_nuevo}), 201

    except psycopg2.Error as db_err:
        if conn: conn.rollback()
        print(f"Error de base de datos en /api/crear-pedido: {db_err}"); traceback.print_exc()
        return jsonify({"error": f"Error de base de datos: {db_err.pgerror}"}), 500
    except Exception as e:
        if conn: conn.rollback()
        print(f"Error en /api/crear-pedido: {e}"); traceback.print_exc()
        return jsonify({"error": f"Error de servidor al crear pedido: {e}"}), 500
    finally:
        if cur: cur.close()
        if conn: return_db_connection(conn)


@app.route('/api/registrar-pago', methods=['POST'])
def registrar_pago():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No se recibieron datos JSON"}), 400
        
    print(f"Recibiendo datos de pago: {data}")

    try:
        id_pedido = int(data.get('buy_order'))
        monto = data.get('amount')
        auth_code = data.get('authorization_code')
        timestamp = datetime.now().strftime('%H%M%S')
        transaccion_id = f"{auth_code}-{timestamp}" 
        estado_pago = data.get('status')
        metodo_pago = data.get('payment_type_code')
        
        if estado_pago == 'AUTHORIZED':
            estado_db = 'aprobado'
        elif estado_pago == 'FAILED':
            estado_db = 'rechazado'
        else:
            estado_db = 'pendiente'
            
        if metodo_pago == 'VN':
            metodo_db = 'Débito (Webpay)'
        elif metodo_pago == 'VC':
            metodo_db = 'Crédito (Webpay)'
        else:
            metodo_db = str(metodo_pago)

    except Exception as e:
        print(f"Error parseando datos de pago: {e}")
        return jsonify({"error": f"Datos de pago incompletos o malformados: {e}"}), 400

    conn = None
    cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        # 1. Insertar en la tabla PAGO
        sql_pago = """
            INSERT INTO pago (id_pedido, monto, metodo_pago, estado_pago, transaccion_id, observaciones)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id_pago;
        """
        cur.execute(sql_pago, (
            id_pedido, monto, metodo_db, estado_db, transaccion_id,
            json.dumps(data)
        ))
        id_pago_nuevo = cur.fetchone()['id_pago']
        print(f"Pago {id_pago_nuevo} registrado para pedido {id_pedido} con transaccion_id {transaccion_id}")

        # 2. Actualizar el estado del Pedido principal
        estado_pedido_db = 'pendiente'
        if estado_db == 'aprobado':
            estado_pedido_db = 'pagado'
        elif estado_db == 'rechazado':
            estado_pedido_db = 'rechazado'
        
        sql_update_pedido = "UPDATE pedido SET estado_pedido = %s WHERE id_pedido = %s;"
        cur.execute(sql_update_pedido, (estado_pedido_db, id_pedido))
        print(f"Pedido {id_pedido} actualizado a '{estado_pedido_db}'")

        # --- ▼▼▼ 3. ¡NUEVO! Descontar Stock SI EL PAGO FUE APROBADO ▼▼▼ ---
        if estado_db == 'aprobado':
            print(f"Iniciando descuento de stock para Pedido {id_pedido}...")
            
            # A. Obtener la sucursal de la que se vendió
            cur.execute("SELECT id_sucursal FROM pedido WHERE id_pedido = %s", (id_pedido,))
            pedido_data = cur.fetchone()
            id_sucursal_venta = pedido_data['id_sucursal'] if pedido_data else None

            if id_sucursal_venta:
                print(f"Venta desde Sucursal ID: {id_sucursal_venta}")
                
                # B. Obtener los items (SKUs y cantidades) del pedido
                cur.execute("""
                    SELECT sku_producto, cantidad 
                    FROM detalle_pedido 
                    WHERE id_pedido = %s
                """, (id_pedido,))
                items_vendidos = cur.fetchall()
                
                for item in items_vendidos:
                    item_sku = item['sku_producto']
                    item_cantidad = item['cantidad']
                    
                    print(f"Descontando {item_cantidad} de SKU {item_sku} de sucursal {id_sucursal_venta}...")
                    
                    # C. Encontrar el id_variacion usando el SKU
                    cur.execute("""
                        SELECT id_variacion FROM variacion_producto 
                        WHERE sku_variacion = %s
                    """, (item_sku,))
                    variacion_data = cur.fetchone()
                    
                    if variacion_data:
                        id_variacion_vendida = variacion_data['id_variacion']
                        
                        # D. Actualizar el inventario
                        sql_update_stock = """
                            UPDATE inventario_sucursal
                            SET stock = stock - %s
                            WHERE id_variacion = %s AND id_sucursal = %s;
                        """
                        cur.execute(sql_update_stock, (item_cantidad, id_variacion_vendida, id_sucursal_venta))
                        print(f"Stock para id_variacion {id_variacion_vendida} actualizado.")
                    else:
                        print(f"ADVERTENCIA: No se encontró id_variacion para SKU {item_sku}. No se descontó stock.")
            else:
                print(f"ADVERTENCIA: Pedido {id_pedido} no tiene sucursal asignada. No se descontó stock.")
        # --- ▲▲▲ FIN DESCONTAR STOCK ▲▲▲ ---

        conn.commit()
        
        return jsonify({"success": True, "id_pago": id_pago_nuevo}), 201

    except psycopg2.Error as db_err:
        if conn: conn.rollback()
        print(f"Error de base de datos en /api/registrar-pago: {db_err}"); traceback.print_exc()
        return jsonify({"error": f"Error de base de datos: {db_err.pgerror}"}), 500
    except Exception as e:
        if conn: conn.rollback()
        print(f"Error en /api/registrar-pago: {e}"); traceback.print_exc()
        return jsonify({"error": f"Error de servidor al registrar pago: {e}"}), 500
    finally:
        if cur: cur.close()
        if conn: return_db_connection(conn)

# --- ▲▲▲ FIN RUTAS DE PAGO ▲▲▲ ---


# ===========================
# RUN (SIN CAMBIOS)
# ===========================
if __name__ == "__main__":
    app.run(host="localhost", port=5000, debug=True)