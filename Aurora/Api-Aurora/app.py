import json
import re
import traceback
import os
import io
import csv
import random
from dotenv import load_dotenv
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, session, send_from_directory, jsonify, make_response
import psycopg2
import psycopg2.extras
from psycopg2 import errors
from psycopg2 import pool  # <-- 1. IMPORTACIÓN AÑADIDA
from werkzeug.security import generate_password_hash, check_password_hash
from flask_cors import CORS
from datetime import datetime, date
import requests
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadTimeSignature
import smtplib
from email.utils import make_msgid
import traceback

app = Flask(__name__)
app.secret_key = "supersecretkey" # ¡Mantén esto seguro y secreto!

# ---  CONFIGURACIÓN DE FLASK-MAIL  ---
# (Usa la Contraseña de Aplicación de 16 dígitos, no tu contraseña real)
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USE_SSL'] = True
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USERNAME'] = 'painless199388@gmail.com'
app.config['MAIL_PASSWORD'] = 'djrlxfizwbmbfger' 

mail = Mail(app)

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
    """
    Devuelve la información de sesión del usuario logueado.
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


load_dotenv()

app.config['PG_HOST'] = os.getenv("PG_HOST")
app.config['PG_DATABASE'] = os.getenv("PG_DATABASE")
app.config['PG_USER'] = os.getenv("PG_USER")
app.config['PG_PASSWORD'] = os.getenv("PG_PASSWORD")
app.config['PG_PORT'] = int(os.getenv("PG_PORT", 6543))

# --- 2. Crear pool de conexiones ---
try:
    db_pool = psycopg2.pool.SimpleConnectionPool(
        1, 20,
        host=app.config['PG_HOST'],
        database=app.config['PG_DATABASE'],
        user=app.config['PG_USER'],
        password=app.config['PG_PASSWORD'],
        port=app.config['PG_PORT'],
        sslmode="require"
    )
    print("[Flask] ✅ Conectado a Supabase (PostgreSQL en la nube)")
except psycopg2.OperationalError as e:
    print(f"❌ ERROR: No se pudo conectar a Supabase: {e}")
    db_pool = None

# --- 3. Función para obtener conexión ---
def get_db_connection():
    if db_pool:
        return db_pool.getconn()
    else:
        print("Error: Pool no disponible, abriendo conexión directa")
        return psycopg2.connect(
            host=app.config['PG_HOST'],
            database=app.config['PG_DATABASE'],
            user=app.config['PG_USER'],
            password=app.config['PG_PASSWORD'],
            port=app.config['PG_PORT']
        )

# ---  AÑADIR FUNCIÓN return_db_connection()  ---
def return_db_connection(conn):
    """
    Devuelve una conexión al pool.
    """
    if db_pool:
        db_pool.putconn(conn)
    else:
        conn.close() # Cierra la conexión de emergencia
# ---  FIN FUNCIÓN AÑADIDA  ---

# Decoradores (SIN CAMBIOS)
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
        # --- ▼▼▼ 5. BLOQUE FINALLY MODIFICADO ▼▼▼ ---
        if cur: cur.close()
        if conn: return_db_connection(conn)
        # --- ▲▲▲ FIN BLOQUE MODIFICADO ▲▲▲ ---

# ---------------------------
# CRUD Productos (CON POOL)
# ---------------------------
@app.route('/productos')
@login_required
def crud_productos():
    filtro_categoria = request.args.get('filtro_categoria', '')
    filtro_nombre = request.args.get('filtro_nombre', '')
    filtro_sucursal = request.args.get('filtro_sucursal', '')
    filtro_coleccion = request.args.get('filtro_coleccion', '') # <-- NUEVO
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
        
        # --- CONSULTA BASE MODIFICADA ---
        base_query = f"""
            SELECT p.id_producto, p.sku, p.nombre_producto, p.precio_producto, 
            p.descripcion_producto, p.categoria_producto, p.imagen_url, 
            p.coleccion_producto, -- <-- NUEVO
            COALESCE(SUM(i.stock), 0) as stock
            FROM producto p {join_clause}
        """
        
        where_clauses = []
        if filtro_categoria: where_clauses.append("p.categoria_producto = %s"); params.append(filtro_categoria)
        if filtro_nombre: where_clauses.append("p.nombre_producto = %s"); params.append(filtro_nombre)
        if filtro_coleccion: where_clauses.append("p.coleccion_producto = %s"); params.append(filtro_coleccion) # <-- NUEVO
        if filtro_sucursal: where_clauses.append("p.id_producto IN (SELECT v.id_producto FROM inventario_sucursal i JOIN variacion_producto v ON i.id_variacion = v.id_variacion WHERE i.id_sucursal = %s AND i.stock > 0)"); params.append(filtro_sucursal)
        if q: where_clauses.append("(p.id_producto::text ILIKE %s OR p.sku ILIKE %s)"); params.extend([f"%{q}%", f"%{q}%"])
        
        final_query = base_query
        if where_clauses: final_query += " WHERE " + " AND ".join(where_clauses)
        
        # --- GROUP BY MODIFICADO ---
        final_query += " GROUP BY p.id_producto, p.coleccion_producto ORDER BY p.id_producto;" # <-- NUEVO
        
        cur.execute(final_query, tuple(params))
        productos = cur.fetchall()
        
        cur.execute("SELECT DISTINCT categoria_producto FROM producto WHERE categoria_producto IS NOT NULL ORDER BY categoria_producto;")
        categorias = [row['categoria_producto'] for row in cur.fetchall()]
        
        # --- OBTENER COLECCIONES PARA FILTRO ---
        cur.execute("SELECT DISTINCT coleccion_producto FROM producto WHERE coleccion_producto IS NOT NULL ORDER BY coleccion_producto;") # <-- NUEVO
        colecciones = [row['coleccion_producto'] for row in cur.fetchall()] # <-- NUEVO
        
        nombres_productos_query = "SELECT DISTINCT nombre_producto FROM producto"
        nombres_params = []
        if filtro_categoria: nombres_productos_query += " WHERE categoria_producto = %s"; nombres_params.append(filtro_categoria)
        nombres_productos_query += " ORDER BY nombre_producto;"
        cur.execute(nombres_productos_query, nombres_params)
        nombres_productos = [row['nombre_producto'] for row in cur.fetchall()]
        
        cur.execute("SELECT * FROM sucursal ORDER BY id_sucursal;")
        sucursales = cur.fetchall()
        
        # --- FILTROS ACTIVOS MODIFICADOS ---
        filtros_activos = { 
            'categoria': filtro_categoria, 
            'nombre': filtro_nombre, 
            'sucursal': filtro_sucursal, 
            'q': q,
            'coleccion': filtro_coleccion # <-- NUEVO
        }
        
        # --- RENDER TEMPLATE MODIFICADO ---
        return render_template("productos/crud_productos.html", 
                               productos=productos, 
                               sucursales=sucursales, 
                               categorias=categorias, 
                               colecciones=colecciones, # <-- NUEVO
                               nombres_productos=nombres_productos, 
                               filtros_activos=filtros_activos)
    except Exception as e:
        print(f"Error en crud_productos: {e}"); traceback.print_exc()
        flash("Error al cargar productos", "danger")
        return redirect(url_for("index_options"))
    finally:
        if cur: cur.close()
        if conn: return_db_connection(conn)

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
        if conn: return_db_connection(conn) # <-- CAMBIO

@app.route("/add", methods=["POST"])
@login_required
def add_producto():
    conn = None; cur = None
    try:
        sku_digits = request.form["sku_digits"]; sku = f"AUR-{sku_digits}"
        nombre = request.form["nombre"]; precio = request.form["precio"]
        color = request.form.get("color"); descripcion = request.form.get("descripcion")
        categoria = request.form.get("categoria"); imagen_url = request.form.get("imagen_url")
        coleccion = request.form.get("coleccion") # <-- NUEVO

        if not color: flash("❌ Error: Debes seleccionar un color.", "danger"); return redirect(url_for("crud_productos"))
        
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT id_producto FROM producto WHERE sku = %s", (sku,))
        if cur.fetchone():
            flash(f"❌ Error: El SKU '{sku}' ya está registrado.", "danger")
            return redirect(url_for("crud_productos"))
        
        # --- INSERT MODIFICADO ---
        cur.execute("""
            INSERT INTO producto (sku, nombre_producto, precio_producto, descripcion_producto, categoria_producto, imagen_url, coleccion_producto)
            VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id_producto;
        """, (sku, nombre, precio, descripcion, categoria, imagen_url, coleccion)) # <-- AÑADIDO
        
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
        if conn: return_db_connection(conn)
    return redirect(url_for("crud_productos"))

@app.route("/edit/<int:id>", methods=["POST"])
@login_required
def edit_producto(id):
    conn = None; cur = None
    try:
        sku = request.form["sku"]; nombre = request.form["nombre"]; precio = request.form["precio"]
        descripcion = request.form.get("descripcion"); categoria = request.form.get("categoria"); imagen_url = request.form.get("imagen_url")
        coleccion = request.form.get("coleccion") # <-- NUEVO
        
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT id_producto FROM producto WHERE sku = %s AND id_producto != %s", (sku, id))
        if cur.fetchone():
            flash(f"❌ Error: El SKU '{sku}' ya está registrado.", "danger")
            return redirect(url_for("crud_productos"))
        
        # --- UPDATE MODIFICADO ---
        cur.execute("""
            UPDATE producto SET sku = %s, nombre_producto = %s, precio_producto = %s,
            descripcion_producto = %s, categoria_producto = %s, imagen_url = %s,
            coleccion_producto = %s
            WHERE id_producto = %s
        """, (sku, nombre, precio, descripcion, categoria, imagen_url, coleccion, id)) # <-- AÑADIDO
        
        conn.commit()
        flash("✅ Producto actualizado", "success")
    except Exception as e:
        if conn: conn.rollback()
        flash(f"Error al editar producto: {e}", "danger")
    finally:
        if cur: cur.close()
        if conn: return_db_connection(conn)
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
@login_required 
def delete_producto(id):
    conn = None; cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # --- NUEVA LÓGICA DE BORRADO EN CASCADA MANUAL ---
        
        # 1. Obtener todas las variaciones de este producto
        cur.execute("SELECT id_variacion FROM variacion_producto WHERE id_producto = %s", (id,))
        variaciones = cur.fetchall()
        
        if variaciones:
            # 'variaciones' es una lista de tuplas, ej: [(28,), (29,)]
            # Necesitamos una lista simple de IDs: [28, 29]
            variacion_ids = [v[0] for v in variaciones]
            
            # 2. Desvincular 'detalle_pedido' (anular la FK)
            # ¡Esto asume que id_variacion EN detalle_pedido PUEDE SER NULL!
            # Si esto falla, debes alterar tu tabla: ALTER TABLE detalle_pedido ALTER COLUMN id_variacion DROP NOT NULL;
            cur.execute("UPDATE detalle_pedido SET id_variacion = NULL WHERE id_variacion = ANY(%s)", (variacion_ids,))
            
            # 3. Eliminar de 'inventario_sucursal'
            cur.execute("DELETE FROM inventario_sucursal WHERE id_variacion = ANY(%s)", (variacion_ids,))
        
        # 4. Eliminar de 'producto_imagenes' (si tienes esta tabla)
        cur.execute("DELETE FROM producto_imagenes WHERE id_producto = %s", (id,))
        
        # 5. Eliminar de 'oferta_producto'
        cur.execute("DELETE FROM oferta_producto WHERE id_producto = %s", (id,))

        # 6. Eliminar de 'variacion_producto'
        cur.execute("DELETE FROM variacion_producto WHERE id_producto = %s", (id,))
        
        # 7. Finalmente, eliminar el producto principal
        cur.execute("DELETE FROM producto WHERE id_producto = %s", (id,))
        
        # --- FIN NUEVA LÓGICA ---
        
        conn.commit()
        # Cambiamos el mensaje a éxito
        flash(" ❌ Producto eliminado y todas sus dependencias han sido limpiadas.", "success") 
    
    except psycopg2.Error as e:
        if conn: conn.rollback()
        # Proporcionar un error más detallado
        print(f"Error de base de datos al eliminar: {e}")
        traceback.print_exc()
        flash(f"Error al eliminar producto: {e.pgerror}", "danger")
    except Exception as e:
        if conn: conn.rollback()
        print(f"Error genérico al eliminar: {e}")
        traceback.print_exc()
        flash(f"Error al eliminar producto: {e}", "danger")
    finally:
        if cur: cur.close()
        if conn: return_db_connection(conn)
    
    return redirect(url_for("crud_productos"))


@app.route("/ver_stock/<int:id_producto>")
@login_required
def ver_stock(id_producto):
    conn = None; cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        # 1. Obtener información del producto
        cur.execute("SELECT * FROM producto WHERE id_producto = %s", (id_producto,))
        producto = cur.fetchone()
        if not producto:
            flash("Producto no encontrado.", "danger")
            return redirect(url_for("crud_productos"))

        # 2. Determinar las tallas disponibles
        categoria = (producto["categoria_producto"] or "").strip()
        tallas_disponibles = []
        if categoria in CATEGORIAS_ROPA: tallas_disponibles = TALLAS_ROPA
        elif categoria in CATEGORIAS_CALZADO: tallas_disponibles = TALLAS_CALZADO
        usa_tallas = bool(tallas_disponibles)

        # 3. Obtener todas las sucursales
        cur.execute("SELECT * FROM sucursal ORDER BY id_sucursal")
        sucursales = cur.fetchall()

        # 4. Obtener el stock
        stock_por_talla = {}
        stock_total_sucursal = {}
        stock_base_sucursal = {} # Para stock sin talla (Estándar)

        for s in sucursales:
            id_sucursal = s["id_sucursal"] # <-- Aquí se obtiene correctamente
            
            # Obtener stock POR TALLA (XS, S, M...)
            cur.execute("""
                SELECT v.talla, COALESCE(i.stock, 0) as stock
                FROM variacion_producto v
                LEFT JOIN inventario_sucursal i ON v.id_variacion = i.id_variacion AND i.id_sucursal = %s
                WHERE v.id_producto = %s AND v.talla IS NOT NULL
            """, (id_sucursal, id_producto))
            stock_tallas_sucursal = {row['talla']: row['stock'] for row in cur.fetchall()}
            stock_por_talla[id_sucursal] = stock_tallas_sucursal
            
            # Obtener stock de la variación BASE (talla IS NULL)
            cur.execute("""
                SELECT COALESCE(i.stock, 0) as stock
                FROM variacion_producto v
                LEFT JOIN inventario_sucursal i ON v.id_variacion = i.id_variacion AND i.id_sucursal = %s
                WHERE v.id_producto = %s AND v.talla IS NULL LIMIT 1;
            """, (id_sucursal, id_producto))
            stock_base_row = cur.fetchone()
            
            # --- ▼▼▼ CORRECCIÓN AQUÍ ▼▼▼ ---
            # Usar s['id_sucursal'] en lugar de s.id_sucursal
            stock_base_sucursal[s['id_sucursal']] = stock_base_row['stock'] if stock_base_row else 0
            
            # Calcular el stock TOTAL de la sucursal
            # Usar s['id_sucursal'] aquí también
            stock_total_sucursal[s['id_sucursal']] = sum(stock_tallas_sucursal.values()) + stock_base_sucursal[s['id_sucursal']]
            

        # 5. Calcular stock total del producto
        stock_total_producto = sum(stock_total_sucursal.values())
        
        return render_template(
            "productos/ver_stock.html",
            producto=producto,
            sucursales=sucursales,
            usa_tallas=usa_tallas,
            tallas_disponibles=tallas_disponibles,
            stock_por_talla=stock_por_talla,
            stock_total_sucursal=stock_total_sucursal,
            stock_total_producto=stock_total_producto,
            stock_base_sucursal=stock_base_sucursal # Pasa el stock base
        )
    
    except Exception as e:
        print(f"Error en ver_stock: {e}"); traceback.print_exc()
        flash("Error al cargar stock", "danger")
        return redirect(url_for("crud_productos"))
    finally:
        if cur: cur.close()
        if conn: return_db_connection(conn) # Devuelve al pool


# --- Actualizar Stock Tallas Estándar ▼▼▼ ---

@app.route("/productos/<int:id_producto>/actualizar_stock_estandar", methods=["POST"])
@login_required
def actualizar_stock_estandar(id_producto):
    """
    Actualiza el stock para la variación "base" (talla IS NULL) de un producto
    en una sucursal específica.
    """
    id_sucursal = request.form.get("id_sucursal")
    stock_estandar = request.form.get("stock_estandar", 0) # 0 si no se envía

    if not id_sucursal:
        flash("❌ Error: No se especificó una sucursal.", "danger")
        return redirect(url_for("ver_stock", id_producto=id_producto))

    conn = None; cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        # 1. Encontrar la ID de la variación base (donde talla es NULL)
        cur.execute("""
            SELECT id_variacion FROM variacion_producto
            WHERE id_producto = %s AND talla IS NULL
            LIMIT 1;
        """, (id_producto,))
        
        variacion = cur.fetchone()
        
        if not variacion:
            # Si el producto no tiene ni siquiera una variación base (creada al añadir producto),
            # esto es un error, pero podríamos crearla aquí si quisiéramos.
            # Por ahora, asumimos que se creó al añadir el producto.
            flash("❌ Error: No se encontró la variación base del producto.", "danger")
            raise Exception("No se encontró variación base (talla NULL)")

        id_variacion_base = variacion['id_variacion']

        # 2. Insertar o actualizar el stock para esa variación base en la sucursal
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
        
        # Esta validación es problemática si se reasigna stock, la comento
        # if total_nuevo > stock_max:
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
# CRUD DE CUPONES DE DESCUENTO
# ===========================

@app.route('/cupones')
@login_required
def crud_cupones():
    # 1. Obtener parámetros de la URL (GET)
    filtro_codigo = request.args.get('q', '').strip()
    filtro_estado = request.args.get('filtro_estado', '')
    
    conn = None; cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        # 2. Construcción dinámica de la consulta
        # La columna calculada 'es_activo' ayuda a simplificar la lógica en el template,
        # pero para filtrar en SQL debemos usar las condiciones crudas.
        base_query = """
            SELECT *, 
            (vigente_bool AND CURRENT_DATE BETWEEN fecha_inicio AND fecha_fin AND usos_hechos < usos_max) as es_activo 
            FROM cupon 
        """
        
        where_clauses = []
        params = []

        # Filtro por Código (Búsqueda parcial insensible a mayúsculas)
        if filtro_codigo:
            where_clauses.append("codigo_cupon ILIKE %s")
            params.append(f"%{filtro_codigo}%")
        
        # Filtro por Estado
        if filtro_estado == 'activo':
            # Activo = Vigente Y Fecha válida Y Usos disponibles
            where_clauses.append("(vigente_bool = TRUE AND CURRENT_DATE BETWEEN fecha_inicio AND fecha_fin AND usos_hechos < usos_max)")
        elif filtro_estado == 'finalizado':
            # Finalizado = Fecha fin pasó O Usos agotados
            where_clauses.append("(fecha_fin < CURRENT_DATE OR usos_hechos >= usos_max)")
        elif filtro_estado == 'pausado':
            # Pausado = Vigente_bool es falso (independiente de fechas)
            where_clauses.append("vigente_bool = FALSE")

        # Combinar cláusulas WHERE
        if where_clauses:
            base_query += " WHERE " + " AND ".join(where_clauses)

        base_query += " ORDER BY id_cupon DESC"
        
        print(f"Ejecutando Query Cupones: {base_query} | Params: {params}") # Debug

        cur.execute(base_query, tuple(params))
        cupones = cur.fetchall()
        
        # Mantener los filtros activos en la vista
        filtros_activos = {'q': filtro_codigo, 'estado': filtro_estado}
        
        return render_template("cupones/crud_cupones.html", cupones=cupones, filtros_activos=filtros_activos, now=date.today())

    except Exception as e:
        print(f"Error en crud_cupones: {e}"); traceback.print_exc()
        flash("Error al cargar cupones", "danger")
        return redirect(url_for("index_options"))
    finally:
        if cur: cur.close()
        if conn: return_db_connection(conn)
        
# ===========================
# Agregar Cupon de Descuento
# ===========================

@app.route("/cupones/add", methods=["POST"])
@login_required
def add_cupon():
    data = request.form
    conn = None; cur = None
    try:
        # 1. Validaciones básicas
        codigo = data.get("codigo_cupon").strip()
        if len(codigo) < 6 or len(codigo) > 12:
            flash("❌ El código debe tener entre 6 y 12 caracteres.", "danger")
            return redirect(url_for("crud_cupones"))

        # 2. Lógica de descuento: Porcentaje O Valor Fijo (mutuamente excluyentes)
        tipo_descuento = data.get("tipo_descuento") # 'pct' o 'fijo'
        
        # Inicializamos ambos como None (NULL en SQL)
        descuento_pct = None
        valor_fijo = None

        try:
            valor_ingresado = float(data.get("descuento_valor"))
        except (ValueError, TypeError):
            flash("❌ El valor del descuento debe ser un número válido.", "danger")
            return redirect(url_for("crud_cupones"))

        if tipo_descuento == 'pct':
            if valor_ingresado > 100:
                 flash("❌ El porcentaje no puede ser mayor a 100%.", "danger")
                 return redirect(url_for("crud_cupones"))
            descuento_pct = valor_ingresado
            # valor_fijo se queda en None (NULL)
        else:
            valor_fijo = valor_ingresado
            # descuento_pct se queda en None (NULL)

        conn = get_db_connection()
        cur = conn.cursor()
        
        # 3. Verificar duplicados (código único)
        cur.execute("SELECT 1 FROM cupon WHERE codigo_cupon = %s", (codigo,))
        if cur.fetchone():
            flash(f"❌ El código '{codigo}' ya existe.", "danger")
            return redirect(url_for("crud_cupones"))

        # 4. Insertar
        # Se añade 'descripcion' y se elimina cualquier referencia a reglas_json
        cur.execute("""
            INSERT INTO cupon (
                codigo_cupon, nombre_cupon, descripcion, descuento_pct_cupon, valor_fijo, 
                min_compra, usos_max, fecha_inicio, fecha_fin, vigente_bool, usos_hechos
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, TRUE, 0)
        """, (
            codigo, 
            data.get("nombre_cupon"),
            data.get("descripcion"), # Nuevo campo descripción (VARCHAR 200)
            descuento_pct,
            valor_fijo,
            data.get("min_compra") or 0,
            data.get("usos_max"),
            data.get("fecha_inicio"),
            data.get("fecha_fin")
        ))
        
        conn.commit()
        flash("✅ Cupón creado exitosamente", "success")
        
    except Exception as e:
        if conn: conn.rollback()
        print(f"Error al crear cupón: {e}"); traceback.print_exc()
        flash(f"❌ Error al crear cupón: {e}", "danger")
    finally:
        if cur: cur.close()
        if conn: return_db_connection(conn)
        
    return redirect(url_for("crud_cupones"))

# --- EDITAR CUPÓN  ---
@app.route("/cupones/edit/<int:id_cupon>", methods=["POST"])
@login_required
def edit_cupon(id_cupon):
    data = request.form
    conn = None; cur = None
    try:
        # Validaciones
        codigo = data.get("codigo_cupon").strip()
        if len(codigo) < 6 or len(codigo) > 12:
            flash("❌ El código debe tener entre 6 y 12 caracteres.", "danger")
            return redirect(url_for("crud_cupones"))

        # Lógica de descuento
        tipo_descuento = data.get("tipo_descuento")
        descuento_pct = None
        valor_fijo = None
        
        try:
            valor_ingresado = float(data.get("descuento_valor"))
        except (ValueError, TypeError):
            flash("❌ Valor de descuento inválido.", "danger")
            return redirect(url_for("crud_cupones"))

        if tipo_descuento == 'pct':
            if valor_ingresado > 100:
                 flash("❌ El porcentaje no puede ser mayor a 100%.", "danger")
                 return redirect(url_for("crud_cupones"))
            descuento_pct = valor_ingresado
        else:
            valor_fijo = valor_ingresado

        conn = get_db_connection()
        cur = conn.cursor()
        
        # Verificar duplicados (excluyendo el cupón actual)
        cur.execute("SELECT 1 FROM cupon WHERE codigo_cupon = %s AND id_cupon != %s", (codigo, id_cupon))
        if cur.fetchone():
            flash(f"❌ El código '{codigo}' ya está en uso por otro cupón.", "danger")
            return redirect(url_for("crud_cupones"))

        # Update
        cur.execute("""
            UPDATE cupon SET
                codigo_cupon = %s,
                nombre_cupon = %s,
                descripcion = %s,
                descuento_pct_cupon = %s,
                valor_fijo = %s,
                min_compra = %s,
                usos_max = %s,
                fecha_inicio = %s,
                fecha_fin = %s
            WHERE id_cupon = %s
        """, (
            codigo,
            data.get("nombre_cupon"),
            data.get("descripcion"),
            descuento_pct,
            valor_fijo,
            data.get("min_compra") or 0,
            data.get("usos_max"),
            data.get("fecha_inicio"),
            data.get("fecha_fin"),
            id_cupon
        ))
        
        conn.commit()
        flash("✅ Cupón actualizado exitosamente", "success")
        
    except Exception as e:
        if conn: conn.rollback()
        print(f"Error al editar cupón: {e}"); traceback.print_exc()
        flash(f"❌ Error al editar cupón: {e}", "danger")
    finally:
        if cur: cur.close()
        if conn: return_db_connection(conn)
        
    return redirect(url_for("crud_cupones"))


# ===========================
# Eliminar Cupon de Descuento
# ===========================

@app.route("/cupones/delete/<int:id_cupon>", methods=["POST"])
@login_required
def delete_cupon(id_cupon):
    conn = None; cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM cupon WHERE id_cupon = %s", (id_cupon,))
        conn.commit()
        flash("✅ Cupón eliminado", "success")
    except Exception as e:
        if conn: conn.rollback()
        print(f"Error al eliminar cupón: {e}")
        flash("❌ Error al eliminar cupón", "danger")
    finally:
        if cur: cur.close()
        if conn: return_db_connection(conn)
    return redirect(url_for("crud_cupones"))

# ===========================
# Activar o Desactivar Cupon de Descuento
# ===========================

@app.route("/cupones/toggle/<int:id_cupon>", methods=["POST"])
@login_required
def toggle_cupon(id_cupon):
    """Activa o desactiva un cupón manualmente (soft delete / pausa)"""
    conn = None; cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        # Invierte el valor booleano actual
        cur.execute("UPDATE cupon SET vigente_bool = NOT vigente_bool WHERE id_cupon = %s", (id_cupon,))
        conn.commit()
        flash("✅ Estado del cupón actualizado", "success")
    except Exception as e:
        if conn: conn.rollback()
        flash("❌ Error al actualizar estado", "danger")
    finally:
        if cur: cur.close()
        if conn: return_db_connection(conn)
    return redirect(url_for("crud_cupones"))


# ===========================
# Validar Cupón de Descuento al momento de pagar
# ===========================

# --- ▼▼▼ NUEVA RUTA: VALIDAR CUPÓN ▼▼▼ ---
@app.route('/api/validar-cupon', methods=['POST'])
def validar_cupon():
    data = request.get_json()
    codigo = data.get('codigo', '').strip()
    monto_total = data.get('total', 0)

    if not codigo:
        return jsonify({"valid": False, "message": "Ingresa un código."}), 400

    conn = None; cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        # Buscar cupón por código exacto (case sensitive)
        cur.execute("SELECT * FROM cupon WHERE codigo_cupon = %s", (codigo,))
        cupon = cur.fetchone()

        if not cupon:
            return jsonify({"valid": False, "message": "Código inválido"}), 404

        # Validaciones de lógica
        if not cupon['vigente_bool']:
            return jsonify({"valid": False, "message": "Este cupón está pausado o inactivo."}), 400
        
        hoy = date.today()
        if not (cupon['fecha_inicio'] <= hoy <= cupon['fecha_fin']):
            return jsonify({"valid": False, "message": "El cupón ha vencido o aún no inicia."}), 400
            
        if cupon['usos_hechos'] >= cupon['usos_max']:
            return jsonify({"valid": False, "message": "Este cupón ha agotado sus usos."}), 400
            
        if monto_total < cupon['min_compra']:
             # Formatear monto para mensaje
            min_fmt = "{:,.0f}".format(cupon['min_compra']).replace(',', '.')
            return jsonify({"valid": False, "message": f"El monto mínimo para este cupón es ${min_fmt}."}), 400

        # Si pasa todo, devolver datos para calcular
        return jsonify({
            "valid": True,
            "id_cupon": cupon['id_cupon'],
            "codigo": cupon['codigo_cupon'],
            "tipo": "pct" if cupon['descuento_pct_cupon'] else "fijo",
            "valor": float(cupon['descuento_pct_cupon']) if cupon['descuento_pct_cupon'] else float(cupon['valor_fijo']),
            "message": "Cupón aplicado correctamente"
        })

    except Exception as e:
        print(f"Error validando cupón: {e}")
        return jsonify({"valid": False, "message": "Error del servidor"}), 500
    finally:
        if cur: cur.close()
        if conn: return_db_connection(conn)
# --- ▲▲▲ FIN NUEVA RUTA ▲▲▲ ---




# ===========================
# HELPERS (CON POOL)
# ===========================
# --- ▼▼▼ get_user_by_email MODIFICADO ▼▼▼ ---
def get_user_by_email(email):
    conn = None; cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        # --- Añadir is_verified (tu nombre de columna) a la consulta ---
        cur.execute("""
            SELECT id_usuario, nombre_usuario, apellido_paterno, apellido_materno,
                   email_usuario, rol_usuario, password, calle, numero_calle, 
                   region, ciudad, comuna, telefono, creado_en, is_verified
            FROM usuario WHERE LOWER(email_usuario) = LOWER(%s) LIMIT 1;
        """, (email,))
        user = cur.fetchone()
        return user
    except Exception as e:
        print(f"Error en get_user_by_email: {e}"); return None
    finally:
        if cur: cur.close()
        if conn: return_db_connection(conn)
# --- ▲▲▲ FIN MODIFICACIÓN ▲▲▲ ---



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



# --- ▼▼▼ do_login MODIFICADO ▼▼▼ ---
def do_login(email, password):
    if not email or not password:
        return False, "Debes ingresar correo y contraseña."
    
    user = get_user_by_email(email) # Esta función ya trae 'is_verified'
    
    if not user or not check_password_hash(user["password"], password):
        return False, "Credenciales inválidas."
        
    # --- ¡NUEVA VALIDACIÓN! ---
    if not user["is_verified"]:
        return False, "Cuenta no verificada."
    # --- FIN NUEVA VALIDACIÓN ---

    session["user_id"] = user["id_usuario"]
    session["nombre_usuario"] = user["nombre_usuario"]
    session["apellido_paterno"] = user["apellido_paterno"]
    session["apellido_materno"] = user["apellido_materno"]
    session["email_usuario"] = user["email_usuario"]
    session["rol_usuario"] = user["rol_usuario"].strip().lower()
    return True, None
# --- ▲▲▲ FIN MODIFICACIÓN ▲▲▲ ---

def do_register(data):
    # Esta función parece no usarse, 'register' tiene su propia lógica
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
# --- ▼▼▼ /login MODIFICADO ▼▼▼ ---
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        # Envía el archivo estático login.html
        return send_from_directory(SRC_DIR, "login.html")
    
    # POST
    email = (request.form.get("email_usuario") or "").strip()
    password = (request.form.get("password") or "").strip()
    if not email or not password:
        return redirect(url_for("login") + "?error=missing&tab=login&src=login")
    
    ok, msg = do_login(email, password) 
    
    if not ok:
        if msg == "Credenciales inválidas.":
             return redirect(url_for("login") + "?error=bad_password&tab=login&src=login")
        # --- NUEVO MANEJO DE ERROR ---
        elif msg == "Cuenta no verificada.":
             return redirect(url_for("login") + "?error=not_verified&tab=login&src=login")
        # --- FIN NUEVO MANEJO ---
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



# --- ▼▼▼ /register MODIFICADO ▼▼▼ ---
@app.route("/register", methods=["POST"])
def register():
    data = request.form.to_dict()
    conn = None; cur = None
    try:
        # 1. Validaciones (tu código existente)
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
        
        # Validar teléfono y email
        cur.execute("SELECT 1 FROM usuario WHERE telefono = %s LIMIT 1;", (data.get("telefono"),))
        if cur.fetchone() is not None:
            return redirect(url_for("login") + "?error=telefono_exists&tab=register&src=register")
        
        email_usuario = data.get("email_usuario")
        cur.execute("SELECT 1 FROM usuario WHERE email_usuario = %s LIMIT 1;", (email_usuario,))
        if cur.fetchone() is not None:
            return redirect(url_for("login") + "?error=email_exists&tab=register&src=register")

        hashed_password = generate_password_hash(data["password"])
        
        # --- AÑADIR is_verified=FALSE a la consulta ---
        cur.execute("""
            INSERT INTO usuario (
                nombre_usuario, apellido_paterno, apellido_materno, email_usuario,
                password, rol_usuario, calle, numero_calle, region, ciudad, comuna, telefono,
                is_verified 
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
        """, (
            data["nombre_usuario"], data["apellido_paterno"], data["apellido_materno"],
            email_usuario, hashed_password, 'cliente', data["calle"], data["numero_calle"],
            data["region"], data["ciudad"], data["comuna"], data["telefono"],
            False # <-- is_verified = FALSE
        ))
        conn.commit()
        
        # 3. Generar Token y Enviar Email
        try:
            token = s.dumps(email_usuario, salt='email-confirm')
            # _external=True crea una URL absoluta (ej: http://localhost:5000/...)
            verification_url = url_for('verify_email', token=token, _external=True)
            

            # Crear el mensaje de correo
            msg = Message(
                subject="Confirma tu cuenta en Aurora",
                recipients=[email_usuario],
                sender=("Aurora", app.config['MAIL_USERNAME']),
                charset="utf-8"
            )
# Forzamos un ID único seguro para evitar que use tu nombre de usuario de Windows con tildes
            msg.msgId = make_msgid(domain='aurora.local')

            # Necesitarás crear este archivo HTML en la carpeta 'templates/email/'
            msg.html = render_template(
                "email/template_verificacion.html", 
                nombre=data["nombre_usuario"],
                url_verificacion=verification_url
            )
            mail.send(msg)
            print(f"Email de verificacion enviado a {email_usuario}")

        except Exception as e:
            print(f"Error al enviar correo: {e}"); traceback.print_exc()
            pass # No detener el registro si el correo falla, pero loguear el error

        # 4. Redirigir al Login con mensaje de éxito
        # (Ya NO hacemos auto-login)
        return redirect(url_for("login") + "?success=registered&tab=login")

    except Exception as e:
        if conn: conn.rollback()
        print(f"Error al registrar usuario: {e}"); traceback.print_exc()
        return redirect(url_for("login") + f"?error=unknown&tab=register&src=register&msg={e}")
    finally:
        if cur: cur.close()
        if conn: return_db_connection(conn)
# --- ▲▲▲ FIN MODIFICACIÓN ▲▲▲ ---



# --- NUEVA RUTA DE VERIFICACIÓN de email al correo del usuario (REAL)  ---
@app.route("/verify-email/<token>")
def verify_email(token):
    try:
        # Cargar el token (expira en 1 hora = 3600 segundos)
        email = s.loads(token, salt='email-confirm', max_age=3600)
    except SignatureExpired:
        # El token es válido pero ha expirado
        return redirect(url_for("login") + "?error=token_expired&tab=login")
    except (BadTimeSignature, Exception):
        # El token no es válido
        return redirect(url_for("login") + "?error=token_invalid&tab=login")

    conn = None; cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Actualizar la base de datos
        cur.execute("""
            UPDATE usuario 
            SET is_verified = TRUE 
            WHERE email_usuario = %s;
        """, (email,))
        
        conn.commit()
        
        # Redirigir a login con mensaje de éxito
        return redirect(url_for("login") + "?success=verified&tab=login")

    except Exception as e:
        if conn: conn.rollback()
        print(f"Error al verificar email en DB: {e}"); traceback.print_exc()
        return redirect(url_for("login") + "?error=db_error&tab=login")
    finally:
        if cur: cur.close()
        if conn: return_db_connection(conn)
# --- ▲▲▲ FIN NUEVA RUTA ▲▲▲ ---


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
        
        
# ===========================
# RECUPERACIÓN DE CONTRASEÑA
# ===========================

from email.header import Header
import unicodedata # Para limpiar tildes del email

# Asegúrate de tener: import unicodedata

@app.route('/api/forgot-password', methods=['POST'])
def forgot_password():
    raw_email = request.json.get('email')
    if not raw_email:
        return jsonify({"error": "Ingresa tu correo electrónico."}), 400

    # 1. Limpieza de email (Mantenemos esto)
    email = ''.join(c for c in unicodedata.normalize('NFD', raw_email) if unicodedata.category(c) != 'Mn')
    
    print(f"DEBUG - Enviando a: {email}") 

    user = get_user_by_email(email)
    if not user:
        return jsonify({"success": True, "message": "Si el correo existe, recibirás un enlace."})

    try:
        token = s.dumps(email, salt='password-reset')
        link = url_for('reset_password_page', token=token, _external=True)

        # 2. DEFINICIÓN EN MODO SEGURO (SOLO ASCII)
        asunto_seguro = "Recuperacion de Contrasena Aurora"
        remitente_nombre = "Aurora Soporte" 

        msg = Message(
            subject=asunto_seguro, 
            recipients=[email],
            sender=(remitente_nombre, app.config['MAIL_USERNAME'])
        )

        # --- SOLUCIÓN DEL ERROR CRÍTICO ---
        # Forzamos un ID seguro para que Python NO use el nombre de tu PC (que tiene tildes)
        msg.msgId = make_msgid(domain='aurora.local')
        # ----------------------------------

        # 3. El cuerpo SI puede tener acentos
        msg.charset = 'utf-8' 
        
        msg.html = render_template("email/reset_password.html", link=link, nombre=user['nombre_usuario'])
        msg.body = f"Hola {user['nombre_usuario']},\n\nPara recuperar tu clave ingresa aqui: {link}"

        mail.send(msg)
        
        return jsonify({"success": True, "message": "Correo enviado. Revisa tu bandeja de entrada."})

    except Exception as e:
        print(f"Error CRITICO: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": "Error al enviar el correo."}), 500
    
    
# ==========================================
# ESTA ES LA FUNCIÓN QUE TE FALTA EN APP.PY
# ==========================================
@app.route('/reset-password/<token>', methods=['GET'])
def reset_password_page(token):
    try:
        # Verificamos el token (salt debe coincidir con el que usaste al generar)
        email = s.loads(token, salt='password-reset', max_age=900) # 15 min validez
        return render_template("usuarios/reset_password.html", token=token, email=email)
    except SignatureExpired:
        return "<h1>El enlace ha expirado.</h1><p>Por favor solicita uno nuevo.</p>"
    except BadTimeSignature:
        return "<h1>Enlace inválido.</h1>"

# ==========================================
# 3. Procesar cambio de contraseña (POST) 
# (ESTA ES LA QUE TE FALTABA PARA SOLUCIONAR EL ERROR 404)
# ==========================================
@app.route('/api/reset-password', methods=['POST'])
def reset_password_action():
    data = request.get_json()
    token = data.get('token')
    new_password = data.get('password')

    if not token or not new_password:
        return jsonify({"error": "Faltan datos."}), 400

    try:
        # 1. Verificar token nuevamente para obtener el email
        email = s.loads(token, salt='password-reset', max_age=900)
        
        # 2. Validar seguridad de la contraseña (Opcional: usa tu función validar_password si la tienes importada)
        # ok, msg = validar_password(new_password)
        # if not ok: return jsonify({"error": msg}), 400

        # 3. Encriptar nueva contraseña
        hashed_password = generate_password_hash(new_password)
        
        # 4. Actualizar en Base de Datos
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Verificamos que el usuario exista
        cur.execute("SELECT id_usuario FROM usuario WHERE email_usuario = %s", (email,))
        if not cur.fetchone():
             return jsonify({"error": "Usuario no encontrado."}), 404

        # Actualizamos la contraseña
        cur.execute("UPDATE usuario SET password = %s WHERE email_usuario = %s", (hashed_password, email))
        conn.commit()
        
        return jsonify({"success": True, "message": "Contraseña actualizada."})

    except SignatureExpired:
        return jsonify({"error": "El enlace ha expirado. Solicita uno nuevo."}), 400
    except (BadTimeSignature, Exception) as e:
        print(f"Error reset password: {e}")
        return jsonify({"error": "Enlace inválido o error del servidor."}), 400
    finally:
        if 'cur' in locals() and cur: cur.close()
        if 'conn' in locals() and conn: return_db_connection(conn)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login")) # Redirige a la página de login HTML

@app.route("/perfil")
@login_required
def perfil():
    conn = None; cur = None # Usar pool para perfil también
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        # Puedes hacer una consulta a la DB aquí si quieres datos frescos
        # O simplemente usar la sesión
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
    coleccion = (request.args.get("coleccion") or "").strip()   # 🔥 NUEVO

    print("\n--- [API Productos Public Recibido] ---")
    print(f"q: '{q}'")
    print(f"categoria: '{categoria}'")
    print(f"coleccion: '{coleccion}'")

    conn = None
    cur = None

    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        base_sql = """
            SELECT
                p.id_producto, p.sku, p.nombre_producto, p.descripcion_producto,
                p.categoria_producto, p.precio_producto, p.imagen_url,
                p.coleccion_producto,   -- 🔥 IMPORTANTE
                (SELECT COALESCE(SUM(i_sub.stock), 0)
                 FROM variacion_producto v_sub
                 JOIN inventario_sucursal i_sub ON i_sub.id_variacion = v_sub.id_variacion
                 WHERE v_sub.id_producto = p.id_producto) AS stock,
                o.descuento_pct,
                o.fecha_fin
            FROM producto p
            LEFT JOIN oferta_producto op ON p.id_producto = op.id_producto
            LEFT JOIN oferta o ON op.id_oferta = o.id_oferta
                 AND CURRENT_DATE BETWEEN o.fecha_inicio AND o.fecha_fin
                 AND o.vigente_bool = TRUE
        """

        where_clauses = []
        params = []

        # --- Filtro por búsqueda ---
        if q:
            where_clauses.append("(p.sku ILIKE %s OR p.nombre_producto ILIKE %s)")
            params.extend([f"%{q}%", f"%{q}%"])

        # --- Filtro por categoría ---
        if categoria:
            where_clauses.append("TRIM(LOWER(p.categoria_producto)) = LOWER(%s)")
            params.append(categoria)
            print(f"→ Filtro aplicado: categoria = {categoria}")

        # --- 🔥 NUEVO — filtro por colección ---
        if coleccion:
            where_clauses.append("TRIM(LOWER(p.coleccion_producto)) = LOWER(%s)")
            params.append(coleccion)
            print(f"→ Filtro aplicado: coleccion = {coleccion}")

        # Combinar WHERE si corresponde
        if where_clauses:
            base_sql += " WHERE " + " AND ".join(where_clauses)

        base_sql += " ORDER BY p.id_producto;"

        print("SQL FINAL:")
        print(cur.mogrify(base_sql, tuple(params)).decode("utf-8"))

        cur.execute(base_sql, tuple(params))
        rows = cur.fetchall()

        print(f"Productos encontrados: {len(rows)}")
        print("------------------------------------\n")

        data = []
        processed = set()

        # --- Procesador de ofertas ---
        for r in rows:
            pid = r["id_producto"]
            if pid in processed:
                continue

            producto = dict(r)
            precio_original = float(producto["precio_producto"])
            descuento = producto.get("descuento_pct")

            if descuento is not None:
                try:
                    d = float(descuento)
                    producto["precio_oferta"] = round(precio_original * (1 - d / 100))
                    producto["descuento_pct"] = d
                except:
                    producto["precio_oferta"] = None
            else:
                producto["precio_oferta"] = None

            data.append(producto)
            processed.add(pid)

        return jsonify(data), 200

    except Exception as e:
        print("❌ Error en /api/productos_public:", e)
        traceback.print_exc()
        return jsonify({"error": "Error al cargar productos"}), 500

    finally:
        if cur:
            cur.close()
        if conn:
            return_db_connection(conn)

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

# ===========================
# RUTAS DE PEDIDOS (LA VERSIÓN CORRECTA Y ÚNICA CON ENVÍO)
# ===========================
@app.route('/api/crear-pedido', methods=['POST'])
@login_required
def crear_pedido():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No json"}), 400

    print(f"📦 [DEBUG] Datos recibidos: {data}") 

    cart_items = data.get('items')
    total = data.get('total')
    user_id = session.get('user_id')
    id_cupon = data.get('id_cupon') 
    tipo_entrega = data.get('tipo_entrega')
    costo_envio = data.get('costo_envio', 0)

    # FECHA
    fecha_entrega = data.get('fecha_entrega')
    if not fecha_entrega or fecha_entrega.strip() == "":
        fecha_entrega = None 

    # BLOQUE HORARIO
    bloque_horario = data.get('bloque_horario')
    if tipo_entrega == 'retiro':
        bloque_horario = "Retiro Estándar"
    elif not bloque_horario or bloque_horario.strip() == "":
        bloque_horario = "Horario por definir"

    datos_contacto = data.get('datos_contacto') 

    # SUCURSAL
    sucursal_id = data.get('sucursal_id')
    if not sucursal_id or str(sucursal_id).strip() == "":
        if tipo_entrega == 'despacho':
            print("⚠️ [WARN] No llegó sucursal_id. Asignando 1.")
            sucursal_id = 1
        else:
            sucursal_id = None
    else:
        try:
            sucursal_id = int(sucursal_id)
        except:
            sucursal_id = 1 if tipo_entrega == 'despacho' else None

    if tipo_entrega == 'retiro' and not sucursal_id:
        return jsonify({"error": "Debe seleccionar una sucursal para retiro"}), 400

    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        # INSERTAR PEDIDO
        sql_pedido = """
            INSERT INTO pedido (
                id_usuario, total, estado_pedido, id_sucursal, id_cupon, 
                tipo_entrega, costo_envio, fecha_entrega, bloque_horario, datos_contacto
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id_pedido;
        """

        datos_contacto_json = json.dumps(datos_contacto) if datos_contacto else None

        cur.execute(sql_pedido, (
            user_id, total, 'pendiente', sucursal_id, id_cupon,
            tipo_entrega, costo_envio, fecha_entrega, bloque_horario, datos_contacto_json
        ))

        id_pedido_nuevo = cur.fetchone()['id_pedido']

        # =====================================
        # INSERTAR DETALLES — FIX APLICADO
        # =====================================
        for item in cart_items:
            sku = item.get("sku")

            # 1. Buscar variación y producto
            cur.execute("""
                SELECT v.id_variacion, p.id_producto
                FROM variacion_producto v
                JOIN producto p ON p.id_producto = v.id_producto
                WHERE v.sku_variacion = %s
            """, (sku,))
            row = cur.fetchone()

            id_var = row['id_variacion'] if row else None

            # Insertar detalle
            cur.execute("""
                INSERT INTO detalle_pedido (id_pedido, sku_producto, cantidad, precio_unitario, id_variacion)
                VALUES (%s, %s, %s, %s, %s)
            """, (
                id_pedido_nuevo,
                sku,
                item.get('qty'),
                item.get('price'),
                id_var
            ))

        conn.commit()
        return jsonify({"id_pedido": id_pedido_nuevo}), 201

    except Exception as e:
        if conn: conn.rollback()
        print(f"❌ [ERROR] {e}"); traceback.print_exc()
        return jsonify({"error": str(e)}), 500
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
            cur.execute("SELECT id_sucursal, id_cupon FROM pedido WHERE id_pedido = %s", (id_pedido,))
            pedido_data = cur.fetchone()
            id_sucursal_venta = pedido_data['id_sucursal']
            id_cupon_usado = pedido_data['id_cupon']
            
            
            # --- NUEVO: DESCONTAR USO DE CUPÓN ---
            if id_cupon_usado:
                cur.execute("UPDATE cupon SET usos_hechos = usos_hechos + 1 WHERE id_cupon = %s", (id_cupon_usado,))
                print(f"Cupón ID {id_cupon_usado} usado. Contador incrementado.")

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
# RUTA DE REPORTES (KPI)
# ===========================

@app.route('/api/admin/reportes/kpi_ventas', methods=['GET'])
@admin_required # Asegura que solo admin/soporte puedan ver esto
def get_reporte_kpi_ventas():
    """
    Calcula los KPIs de ventas (mes actual vs mes pasado)
    Acepta un 'sucursal_id' opcional para filtrar.
    """
    sucursal_id_str = request.args.get('sucursal_id')
    print(f"[Reportes] Solicitando KPI de ventas para sucursal: {sucursal_id_str}")

    conn = None
    cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        # --- 1. Calcular Ventas Mes Actual ---
        sql_actual = """
            SELECT COALESCE(SUM(pago.monto), 0) as total
            FROM pago
            JOIN pedido ON pago.id_pedido = pedido.id_pedido
            WHERE pago.estado_pago = 'aprobado'
            AND pago.fecha_pago >= date_trunc('month', CURRENT_DATE)
        """
        params_actual = []
        if sucursal_id_str and sucursal_id_str != 'all':
            sql_actual += " AND pedido.id_sucursal = %s"
            params_actual.append(int(sucursal_id_str))
            
        cur.execute(sql_actual, tuple(params_actual))
        ventas_actual = cur.fetchone()['total']

        # --- 2. Calcular Ventas Mes Pasado ---
        sql_pasado = """
            SELECT COALESCE(SUM(pago.monto), 0) as total
            FROM pago
            JOIN pedido ON pago.id_pedido = pedido.id_pedido
            WHERE pago.estado_pago = 'aprobado'
            AND pago.fecha_pago >= date_trunc('month', CURRENT_DATE) - INTERVAL '1 month'
            AND pago.fecha_pago < date_trunc('month', CURRENT_DATE)
        """
        params_pasado = []
        if sucursal_id_str and sucursal_id_str != 'all':
            sql_pasado += " AND pedido.id_sucursal = %s"
            params_pasado.append(int(sucursal_id_str))

        cur.execute(sql_pasado, tuple(params_pasado))
        ventas_pasado = cur.fetchone()['total']

        # --- 3. Calcular Porcentaje de Cambio ---
        porcentaje_cambio = 0
        if ventas_pasado > 0:
            porcentaje_cambio = ((ventas_actual - ventas_pasado) / ventas_pasado) * 100
        elif ventas_actual > 0:
            porcentaje_cambio = 100 # Si el mes pasado fue 0 y este no, es 100% de aumento

        return jsonify({
            "ventas_mes_actual": float(ventas_actual),
            "ventas_mes_pasado": float(ventas_pasado),
            "porcentaje_cambio": round(porcentaje_cambio, 2)
        })

    except Exception as e:
        print(f"Error en /api/admin/reportes/kpi_ventas: {e}"); traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    finally:
        if cur: cur.close()
        if conn: return_db_connection(conn)


# ===========================
# RUTA DE REPORTES (KPI): Gráficos interactivos
# ===========================

# --- ▼▼▼ NUEVA RUTA DE REPORTES (GRÁFICO ANUAL) ▼▼▼ ---

@app.route('/api/admin/reportes/ventas_mensuales', methods=['GET'])
@admin_required
def get_reporte_ventas_mensuales():
    """
    Calcula las ventas totales por mes para el año actual y el año pasado.
    Acepta un 'sucursal_id' opcional.
    """
    sucursal_id_str = request.args.get('sucursal_id')
    print(f"[Reportes] Solicitando gráfico de ventas mensuales para sucursal: {sucursal_id_str}")

    conn = None
    cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        # --- 1. Datos Año Actual ---
        sql_actual = """
            SELECT 
                date_trunc('month', pago.fecha_pago) as mes,
                COALESCE(SUM(pago.monto), 0) as total
            FROM pago
            JOIN pedido ON pago.id_pedido = pedido.id_pedido
            WHERE 
                pago.estado_pago = 'aprobado'
                AND pago.fecha_pago >= date_trunc('year', CURRENT_DATE)
                AND pago.fecha_pago < date_trunc('year', CURRENT_DATE) + INTERVAL '1 year'
        """
        params_actual = []
        if sucursal_id_str and sucursal_id_str != 'all':
            sql_actual += " AND pedido.id_sucursal = %s"
            params_actual.append(int(sucursal_id_str))
        sql_actual += " GROUP BY mes"
        
        cur.execute(sql_actual, tuple(params_actual))
        rows_actual = cur.fetchall()

        # --- 2. Datos Año Pasado ---
        sql_pasado = """
            SELECT 
                date_trunc('month', pago.fecha_pago) as mes,
                COALESCE(SUM(pago.monto), 0) as total
            FROM pago
            JOIN pedido ON pago.id_pedido = pedido.id_pedido
            WHERE 
                pago.estado_pago = 'aprobado'
                AND pago.fecha_pago >= date_trunc('year', CURRENT_DATE) - INTERVAL '1 year'
                AND pago.fecha_pago < date_trunc('year', CURRENT_DATE)
        """
        params_pasado = []
        if sucursal_id_str and sucursal_id_str != 'all':
            sql_pasado += " AND pedido.id_sucursal = %s"
            params_pasado.append(int(sucursal_id_str))
        sql_pasado += " GROUP BY mes"
        
        cur.execute(sql_pasado, tuple(params_pasado))
        rows_pasado = cur.fetchall()

        # --- 3. Formatear datos para Chart.js ---
        labels = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
        data_actual = [0.0] * 12
        data_pasado = [0.0] * 12

        for row in rows_actual:
            # .month devuelve 1 para Enero, 2 para Febrero, etc.
            mes_index = row['mes'].month - 1 
            data_actual[mes_index] = float(row['total'])

        for row in rows_pasado:
            mes_index = row['mes'].month - 1
            data_pasado[mes_index] = float(row['total'])

        return jsonify({
            "labels": labels,
            "datasets": [
                {
                    "label": "Este Año",
                    "data": data_actual,
                    "backgroundColor": "rgba(13, 110, 253, 0.7)",
                    "borderColor": "rgba(13, 110, 253, 1)",
                    "borderWidth": 2,
                    "fill": True # Para gráfico de área
                },
                {
                    "label": "Año Pasado",
                    "data": data_pasado,
                    "backgroundColor": "rgba(220, 53, 69, 0.7)",
                    "borderColor": "rgba(220, 53, 69, 1)",
                    "borderWidth": 2,
                    "fill": True # Para gráfico de área
                }
            ]
        })

    except Exception as e:
        print(f"Error en /api/admin/reportes/ventas_mensuales: {e}"); traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    finally:
        if cur: cur.close()
        if conn: return_db_connection(conn)

# --- ▲▲▲ FIN NUEVA RUTA ▲▲▲ ---



# ===========================
# Reportes: RUTAS DE REPORTES DE PEDIDOS (KPI) 
# ===========================

# --- ▼▼▼ NUEVAS RUTAS DE REPORTES DE PEDIDOS ▼▼▼ ---

@app.route('/api/admin/reportes/kpi_pedidos', methods=['GET'])
@admin_required
def get_reporte_kpi_pedidos():
    """
    Calcula el KPI de pedidos (mes actual vs mes pasado)
    Acepta un 'sucursal_id' opcional para filtrar.
    """
    sucursal_id_str = request.args.get('sucursal_id')
    print(f"[Reportes] Solicitando KPI de pedidos para sucursal: {sucursal_id_str}")

    conn = None
    cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        # --- 1. Calcular Pedidos Mes Actual ---
        sql_actual = """
            SELECT COUNT(DISTINCT pedido.id_pedido) as total
            FROM pedido
            JOIN pago ON pago.id_pedido = pedido.id_pedido
            WHERE pago.estado_pago = 'aprobado'
            AND pago.fecha_pago >= date_trunc('month', CURRENT_DATE)
        """
        params_actual = []
        if sucursal_id_str and sucursal_id_str != 'all':
            sql_actual += " AND pedido.id_sucursal = %s"
            params_actual.append(int(sucursal_id_str))
            
        cur.execute(sql_actual, tuple(params_actual))
        pedidos_actual = cur.fetchone()['total']

        # --- 2. Calcular Pedidos Mes Pasado ---
        sql_pasado = """
            SELECT COUNT(DISTINCT pedido.id_pedido) as total
            FROM pedido
            JOIN pago ON pago.id_pedido = pedido.id_pedido
            WHERE pago.estado_pago = 'aprobado'
            AND pago.fecha_pago >= date_trunc('month', CURRENT_DATE) - INTERVAL '1 month'
            AND pago.fecha_pago < date_trunc('month', CURRENT_DATE)
        """
        params_pasado = []
        if sucursal_id_str and sucursal_id_str != 'all':
            sql_pasado += " AND pedido.id_sucursal = %s"
            params_pasado.append(int(sucursal_id_str))

        cur.execute(sql_pasado, tuple(params_pasado))
        pedidos_pasado = cur.fetchone()['total']

        # --- 3. Calcular Porcentaje de Cambio ---
        porcentaje_cambio = 0
        if pedidos_pasado > 0:
            porcentaje_cambio = ((pedidos_actual - pedidos_pasado) / pedidos_pasado) * 100
        elif pedidos_actual > 0:
            porcentaje_cambio = 100 

        return jsonify({
            "pedidos_mes_actual": int(pedidos_actual),
            "pedidos_mes_pasado": int(pedidos_pasado),
            "porcentaje_cambio": round(porcentaje_cambio, 2)
        })

    except Exception as e:
        print(f"Error en /api/admin/reportes/kpi_pedidos: {e}"); traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    finally:
        if cur: cur.close()
        if conn: return_db_connection(conn)

@app.route('/api/admin/reportes/lista_pedidos_mes', methods=['GET'])
@admin_required
def get_lista_pedidos_mes():
    """
    Obtiene la lista de pedidos aprobados de este mes para el Modal 1.
    """
    sucursal_id_str = request.args.get('sucursal_id')
    conn = None
    cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        sql = """
            SELECT 
                p.id_pedido, 
                u.nombre_usuario, 
                u.apellido_paterno,
                (SELECT SUM(dp.cantidad) FROM detalle_pedido dp WHERE dp.id_pedido = p.id_pedido) as total_items
            FROM pedido p
            JOIN usuario u ON p.id_usuario = u.id_usuario
            JOIN pago pa ON p.id_pedido = pa.id_pedido
            WHERE 
                pa.estado_pago = 'aprobado'
                AND pa.fecha_pago >= date_trunc('month', CURRENT_DATE)
        """
        params = []
        if sucursal_id_str and sucursal_id_str != 'all':
            sql += " AND p.id_sucursal = %s"
            params.append(int(sucursal_id_str))
            
        sql += " GROUP BY p.id_pedido, u.nombre_usuario, u.apellido_paterno ORDER BY p.id_pedido DESC;"
        
        cur.execute(sql, tuple(params))
        pedidos = cur.fetchall()
        
        return jsonify([dict(row) for row in pedidos])

    except Exception as e:
        print(f"Error en /api/admin/reportes/lista_pedidos_mes: {e}"); traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    finally:
        if cur: cur.close()
        if conn: return_db_connection(conn)


# ===========================
# Reportes: RUTAS DE REPORTES DE CLIENTES (KPI) 
# ===========================

# --- ▼▼▼ NUEVAS RUTAS DE REPORTES DE CLIENTES ▼▼▼ ---

@app.route('/api/admin/reportes/kpi_clientes', methods=['GET'])
@admin_required
def get_reporte_kpi_clientes():
    """
    Calcula el KPI de nuevos clientes (mes actual vs mes pasado)
    - Si sucursal_id es 'all', cuenta todos los usuarios nuevos.
    - Si sucursal_id es específico, cuenta los usuarios nuevos QUE COMPRARON en esa sucursal.
    """
    sucursal_id_str = request.args.get('sucursal_id')
    print(f"[Reportes] Solicitando KPI de clientes para sucursal: {sucursal_id_str}")

    conn = None
    cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        # --- 1. Calcular Clientes Mes Actual ---
        sql_actual = ""
        params_actual = []

        if sucursal_id_str and sucursal_id_str != 'all':
            # Clientes nuevos (este mes) que compraron en esta sucursal
            sql_actual = """
                SELECT COUNT(DISTINCT u.id_usuario) as total
                FROM usuario u
                JOIN pedido p ON u.id_usuario = p.id_usuario
                WHERE u.creado_en >= date_trunc('month', CURRENT_DATE)
                  AND p.id_sucursal = %s;
            """
            params_actual.append(int(sucursal_id_str))
        else:
            # Todos los clientes nuevos (este mes)
            sql_actual = """
                SELECT COUNT(id_usuario) as total
                FROM usuario
                WHERE creado_en >= date_trunc('month', CURRENT_DATE);
            """

        cur.execute(sql_actual, tuple(params_actual))
        clientes_actual = cur.fetchone()['total']

        # --- 2. Calcular Clientes Mes Pasado ---
        sql_pasado = ""
        params_pasado = []

        if sucursal_id_str and sucursal_id_str != 'all':
            sql_pasado = """
                SELECT COUNT(DISTINCT u.id_usuario) as total
                FROM usuario u
                JOIN pedido p ON u.id_usuario = p.id_usuario
                WHERE u.creado_en >= date_trunc('month', CURRENT_DATE) - INTERVAL '1 month'
                  AND u.creado_en < date_trunc('month', CURRENT_DATE)
                  AND p.id_sucursal = %s;
            """
            params_pasado.append(int(sucursal_id_str))
        else:
            sql_pasado = """
                SELECT COUNT(id_usuario) as total
                FROM usuario
                WHERE creado_en >= date_trunc('month', CURRENT_DATE) - INTERVAL '1 month'
                  AND creado_en < date_trunc('month', CURRENT_DATE);
            """
        
        cur.execute(sql_pasado, tuple(params_pasado))
        clientes_pasado = cur.fetchone()['total']

        # --- 3. Calcular Porcentaje de Cambio ---
        porcentaje_cambio = 0
        if clientes_pasado > 0:
            porcentaje_cambio = ((clientes_actual - clientes_pasado) / clientes_pasado) * 100
        elif clientes_actual > 0:
            porcentaje_cambio = 100  

        return jsonify({
            "clientes_mes_actual": int(clientes_actual),
            "clientes_mes_pasado": int(clientes_pasado),
            "porcentaje_cambio": round(porcentaje_cambio, 2)
        })

    except Exception as e:
        print(f"Error en /api/admin/reportes/kpi_clientes: {e}"); traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    finally:
        if cur: cur.close()
        if conn: return_db_connection(conn)

@app.route('/api/admin/reportes/lista_nuevos_clientes', methods=['GET'])
@admin_required
def get_lista_nuevos_clientes():
    """
    Obtiene la lista de nuevos clientes de este mes.
    - 'all': Todos los nuevos clientes.
    - 'specific': Clientes nuevos que compraron en esa sucursal.
    """
    sucursal_id_str = request.args.get('sucursal_id')
    conn = None
    cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        sql = ""
        params = []

        if sucursal_id_str and sucursal_id_str != 'all':
            # Clientes nuevos con su dirección, que compraron en esta sucursal
            sql = """
                SELECT DISTINCT 
                    u.id_usuario, u.nombre_usuario, u.apellido_paterno, u.apellido_materno, 
                    u.email_usuario, u.creado_en, u.region, u.ciudad, u.comuna, 
                    u.calle, u.numero_calle
                FROM usuario u
                JOIN pedido p ON u.id_usuario = p.id_usuario
                WHERE u.creado_en >= date_trunc('month', CURRENT_DATE)
                  AND p.id_sucursal = %s
                ORDER BY u.creado_en DESC;
            """
            params.append(int(sucursal_id_str))
        else:
            # Todos los clientes nuevos
            sql = """
                SELECT 
                    id_usuario, nombre_usuario, apellido_paterno, apellido_materno, 
                    email_usuario, creado_en
                FROM usuario 
                WHERE creado_en >= date_trunc('month', CURRENT_DATE)
                ORDER BY creado_en DESC;
            """
        
        cur.execute(sql, tuple(params))
        clientes = cur.fetchall()
        
        return jsonify([dict(row) for row in clientes])

    except Exception as e:
        print(f"Error en /api/admin/reportes/lista_nuevos_clientes: {e}"); traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    finally:
        if cur: cur.close()
        if conn: return_db_connection(conn)


@app.route('/api/admin/reportes/historial_cliente/<int:id_usuario>', methods=['GET'])
@admin_required
def get_historial_pedidos_cliente(id_usuario):
    """
    Obtiene el historial de pedidos de un cliente específico para el Modal 2.
    Filtra por sucursal si se provee el 'sucursal_id'.
    """
    sucursal_id_str = request.args.get('sucursal_id')
    conn = None
    cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        # --- 1. Obtener info del Usuario ---
        cur.execute("""
            SELECT 
                id_usuario, nombre_usuario, apellido_paterno, apellido_materno, 
                email_usuario, region, ciudad, comuna, calle, numero_calle
            FROM usuario 
            WHERE id_usuario = %s;
        """, (id_usuario,))
        usuario_info = cur.fetchone()

        if not usuario_info:
            return jsonify({"error": "Usuario no encontrado"}), 404

        # --- 2. Obtener historial de Pedidos ---
        sql_pedidos = """
            SELECT 
                p.id_pedido, p.creado_en, p.total, p.estado_pedido, 
                s.nombre_sucursal,
                (SELECT COUNT(*) FROM detalle_pedido dp WHERE dp.id_pedido = p.id_pedido) as item_count,
                (SELECT STRING_AGG(pr.nombre_producto, ', ') 
                 FROM detalle_pedido dp 
                 LEFT JOIN variacion_producto v ON dp.id_variacion = v.id_variacion
                 LEFT JOIN producto pr ON v.id_producto = pr.id_producto
                 WHERE dp.id_pedido = p.id_pedido
                 LIMIT 3
                ) as productos_preview
            FROM pedido p
            LEFT JOIN sucursal s ON p.id_sucursal = s.id_sucursal
            WHERE p.id_usuario = %s
              AND p.estado_pedido IN ('pagado', 'enviado', 'entregado')
        """
        params_pedidos = [id_usuario]

        if sucursal_id_str and sucursal_id_str != 'all':
            sql_pedidos += " AND p.id_sucursal = %s"
            params_pedidos.append(int(sucursal_id_str))
        
        sql_pedidos += " ORDER BY p.creado_en DESC;"
        
        cur.execute(sql_pedidos, tuple(params_pedidos))
        pedidos = cur.fetchall()

        # --- 3. Combinar todo ---
        resultado = {
            "usuario": dict(usuario_info),
            "pedidos": [dict(p) for p in pedidos],
            "total_pedidos": len(pedidos)
        }
        
        return jsonify(resultado)

    except Exception as e:
        print(f"Error en /api/admin/reportes/historial_cliente/{id_usuario}: {e}"); traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    finally:
        if cur: cur.close()
        if conn: return_db_connection(conn)

# --- ▲▲▲ FIN NUEVAS RUTAS DE REPORTES DE CLIENTES ▲▲▲ ---

@app.route('/api/admin/reportes/pedidos_recientes', methods=['GET'])
@admin_required
def get_pedidos_recientes():
    """
    Obtiene una lista paginada de pedidos recientes para la tabla del dashboard.
    """
    sucursal_id_str = request.args.get('sucursal_id')
    limit = request.args.get('limit', 5) 
    
    conn = None
    cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        # --- CONSULTA CORREGIDA ---
        sql = """
            SELECT 
                p.id_pedido,
                CONCAT_WS(' ', u.nombre_usuario, u.apellido_paterno, u.apellido_materno) as cliente_nombre,
                u.email_usuario as email,
                u.telefono,
                p.creado_en,
                p.estado_pedido, -- Para el "Estado Envío"
                pa.estado_pago,  -- Para el "Estado Pago"
                p.total
            FROM pedido p
            JOIN usuario u ON p.id_usuario = u.id_usuario
            LEFT JOIN (
                -- Subconsulta para obtener solo el estado del ÚLTIMO pago de cada pedido
                SELECT DISTINCT ON (id_pedido) id_pedido, estado_pago
                FROM pago
                ORDER BY id_pedido, fecha_pago DESC
            ) pa ON p.id_pedido = pa.id_pedido
        """
        
        params = []
        where_clauses = [] # Empezar de cero

        if sucursal_id_str and sucursal_id_str != 'all':
            where_clauses.append("p.id_sucursal = %s")
            params.append(int(sucursal_id_str))
        
        if where_clauses:
            sql += " WHERE " + " AND ".join(where_clauses)
            
        sql += " ORDER BY p.creado_en DESC LIMIT %s"
        params.append(int(limit))
        
        cur.execute(sql, tuple(params))
        pedidos = cur.fetchall()
        
        return jsonify([dict(row) for row in pedidos])

    except Exception as e:
        print(f"Error en /api/admin/reportes/pedidos_recientes: {e}"); traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    finally:
        if cur: cur.close()
        if conn: return_db_connection(conn)


# --- ▼▼▼ NUEVAS RUTAS PARA GENERACIÓN DE INFORMES (CSV) ▼▼▼ ---

def get_report_data(tipo_reporte, mes, sucursal_id_str):
    """
    Función helper para obtener los datos y cabeceras del informe.
    """
    conn = None
    cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        headers = []
        data = []
        
        # --- Lógica de Fechas ---
        # 'actual' o 'pasado'
        if mes == 'pasado':
            fecha_inicio = "date_trunc('month', CURRENT_DATE) - INTERVAL '1 month'"
            fecha_fin = "date_trunc('month', CURRENT_DATE)"
        else: # 'actual'
            fecha_inicio = "date_trunc('month', CURRENT_DATE)"
            fecha_fin = "date_trunc('month', CURRENT_DATE) + INTERVAL '1 month'"

        # --- Lógica de Sucursal ---
        filtro_sucursal_sql = ""
        params = []
        if sucursal_id_str and sucursal_id_str != 'all':
            filtro_sucursal_sql = " AND p.id_sucursal = %s"
            params.append(int(sucursal_id_str))

        # --- Lógica de Reporte ---
        if tipo_reporte == 'ventas':
            headers = ["ID Pedido", "ID Pago", "Fecha Pago", "Monto", "Metodo Pago", "Sucursal"]
            sql = f"""
                SELECT 
                    p.id_pedido, pa.id_pago, pa.fecha_pago, pa.monto, pa.metodo_pago, s.nombre_sucursal
                FROM pago pa
                JOIN pedido p ON pa.id_pedido = p.id_pedido
                LEFT JOIN sucursal s ON p.id_sucursal = s.id_sucursal
                WHERE pa.estado_pago = 'aprobado'
                  AND pa.fecha_pago >= {fecha_inicio}
                  AND pa.fecha_pago < {fecha_fin}
                  {filtro_sucursal_sql.replace('p.id_sucursal', 'pa.id_sucursal' if 'pa.' in filtro_sucursal_sql else 'p.id_sucursal')}
                ORDER BY pa.fecha_pago DESC;
            """
            cur.execute(sql, tuple(params))
            data = cur.fetchall()

        elif tipo_reporte == 'pedidos':
            headers = ["ID Pedido", "Fecha Pedido", "Cliente", "Email", "Total", "Items", "Estado", "Sucursal"]
            sql = f"""
                SELECT 
                    p.id_pedido, p.creado_en, 
                    CONCAT(u.nombre_usuario, ' ', u.apellido_paterno) as cliente,
                    u.email_usuario, p.total,
                    (SELECT SUM(dp.cantidad) FROM detalle_pedido dp WHERE dp.id_pedido = p.id_pedido) as total_items,
                    p.estado_pedido, s.nombre_sucursal
                FROM pedido p
                JOIN usuario u ON p.id_usuario = u.id_usuario
                LEFT JOIN sucursal s ON p.id_sucursal = s.id_sucursal
                WHERE p.creado_en >= {fecha_inicio}
                  AND p.creado_en < {fecha_fin}
                  AND p.estado_pedido IN ('pagado', 'enviado', 'entregado')
                  {filtro_sucursal_sql}
                ORDER BY p.creado_en DESC;
            """
            cur.execute(sql, tuple(params))
            data = cur.fetchall()

        elif tipo_reporte == 'clientes':
            headers = ["ID Usuario", "Nombre", "Apellido", "Email", "Telefono", "Region", "Comuna", "Fecha Registro"]
            # El filtro de sucursal para clientes los filtra por *dónde compraron*
            if sucursal_id_str and sucursal_id_str != 'all':
                sql = f"""
                    SELECT DISTINCT
                        u.id_usuario, u.nombre_usuario, u.apellido_paterno, u.email_usuario,
                        u.telefono, u.region, u.comuna, u.creado_en
                    FROM usuario u
                    JOIN pedido p ON u.id_usuario = p.id_usuario
                    WHERE u.creado_en >= {fecha_inicio}
                      AND u.creado_en < {fecha_fin}
                      {filtro_sucursal_sql}
                    ORDER BY u.creado_en DESC;
                """
                cur.execute(sql, tuple(params))
            else:
                # Si es 'all', solo trae todos los usuarios nuevos sin join
                sql = f"""
                    SELECT 
                        id_usuario, nombre_usuario, apellido_paterno, email_usuario,
                        telefono, region, comuna, creado_en
                    FROM usuario
                    WHERE creado_en >= {fecha_inicio}
                      AND creado_en < {fecha_fin}
                    ORDER BY creado_en DESC;
                """
                cur.execute(sql) # Sin params
            
            data = cur.fetchall()

        return headers, data
    
    except Exception as e:
        print(f"Error en get_report_data: {e}"); traceback.print_exc()
        return [], []
    finally:
        if cur: cur.close()
        if conn: return_db_connection(conn)
        
        # --- Función para obtener pedidos recientes ---
def get_recent_orders_data(sucursal_id='all', limit=10):
    conn = None
    cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        query = """
            SELECT
                p.id_pedido,
                u.id_usuario,
                u.nombre_usuario,
                u.apellido_paterno,
                u.apellido_materno,
                u.email_usuario,
                u.telefono_usuario,
                p.creado_en AS fecha_pedido,
                p.estado_pedido,
                p.total,
                p.metodo_pago,
                p.transaccion_id,
                -- Datos de dirección para el detalle
                du.calle,
                du.numero_calle,
                du.comuna,
                du.ciudad,
                du.region,
                -- Productos en el pedido para preview (limitado a los primeros 3)
                STRING_AGG(pr.nombre_producto, ', ' ORDER BY pip.id_producto_en_pedido) AS productos_preview
            FROM
                pedido p
            JOIN
                usuario u ON p.id_usuario = u.id_usuario
            LEFT JOIN
                direccion_usuario du ON u.id_usuario = du.id_usuario AND du.es_principal = TRUE
            LEFT JOIN (
                SELECT 
                    pip.id_pedido, 
                    pip.id_producto_en_pedido,
                    pr.nombre_producto
                FROM 
                    producto_en_pedido pip
                JOIN 
                    producto pr ON pip.id_producto = pr.id_producto
            ) pip ON p.id_pedido = pip.id_pedido
        """
        params = []
        where_clauses = []

        if sucursal_id and sucursal_id != 'all':
            where_clauses.append("p.id_sucursal = %s")
            params.append(int(sucursal_id))

        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)

        query += """
            GROUP BY
                p.id_pedido, u.id_usuario, u.nombre_usuario, u.apellido_paterno,
                u.apellido_materno, u.email_usuario, u.telefono_usuario,
                p.creado_en, p.estado_pedido, p.total, p.metodo_pago, p.transaccion_id,
                du.calle, du.numero_calle, du.comuna, du.ciudad, du.region
            ORDER BY
                p.creado_en DESC
            LIMIT %s;
        """
        params.append(int(limit))

        cur.execute(query, tuple(params))
        pedidos = cur.fetchall()
        return pedidos

    except Exception as e:
        print(f"Error al obtener pedidos recientes: {e}")
        traceback.print_exc()
        return []
    finally:
        if cur: cur.close()
        if conn: return_db_connection(conn)


# --- Nuevo Endpoint para Pedidos Recientes ---
@app.route('/api/admin/pedidos_recientes', methods=['GET'])
@admin_required
def get_pedidos_recientes_api():
    try:
        sucursal_id = request.args.get('sucursal_id', 'all')
        limit = request.args.get('limit', 10) # Default a 10
        pedidos = get_recent_orders_data(sucursal_id, limit)
        
        # Formatear datos para el frontend si es necesario
        formatted_pedidos = []
        for p in pedidos:
            formatted_pedidos.append({
                "id_pedido": p['id_pedido'],
                "id_usuario": p['id_usuario'],
                "nombre_usuario": p['nombre_usuario'],
                "apellido_paterno": p['apellido_paterno'],
                "apellido_materno": p['apellido_materno'],
                "email_usuario": p['email_usuario'],
                "telefono_usuario": p['telefono_usuario'],
                "fecha_pedido": p['fecha_pedido'].isoformat() if p['fecha_pedido'] else None,
                "estado_pedido": p['estado_pedido'],
                "total": p['total'],
                "metodo_pago": p['metodo_pago'],
                "transaccion_id": p['transaccion_id'],
                "calle": p['calle'],
                "numero_calle": p['numero_calle'],
                "comuna": p['comuna'],
                "ciudad": p['ciudad'],
                "region": p['region'],
                "productos_preview": p['productos_preview']
            })
        
        return jsonify(formatted_pedidos)

    except Exception as e:
        print(f"Error en /api/admin/pedidos_recientes: {e}"); traceback.print_exc()
        return jsonify({"error": str(e)}), 500



@app.route('/api/admin/reportes/generar_informe', methods=['GET'])
@admin_required
def generar_informe_csv():
    """
    Genera y devuelve un archivo CSV basado en los parámetros.
    """
    try:
        # 1. Obtener parámetros
        tipo_reporte = request.args.get('tipo_reporte')
        mes = request.args.get('mes')
        sucursal_id = request.args.get('sucursal_id')
        
        # Obtener datos de la sucursal (para el nombre del archivo)
        sucursal_nombre = "Todas"
        if sucursal_id and sucursal_id != 'all':
            conn_s = None
            cur_s = None
            try:
                conn_s = get_db_connection()
                cur_s = conn_s.cursor(cursor_factory=psycopg2.extras.DictCursor)
                cur_s.execute("SELECT nombre_sucursal FROM sucursal WHERE id_sucursal = %s", (int(sucursal_id),))
                sucursal_row = cur_s.fetchone()
                if sucursal_row:
                    sucursal_nombre = sucursal_row['nombre_sucursal'].replace(' ', '_')
            except Exception as e:
                print(f"Error al buscar nombre de sucursal: {e}")
            finally:
                if cur_s: cur_s.close()
                if conn_s: return_db_connection(conn_s)

        # 2. Obtener los datos
        headers, data = get_report_data(tipo_reporte, mes, sucursal_id)
        
        if not headers or not data:
             # Devolver un error simple si no hay datos
             return jsonify({"error": "No se encontraron datos para este informe."}), 404

        # 3. Obtener datos del pie de página
        # Obtener partes del nombre
        nombre = session.get("nombre_usuario", "")
        apellido_p = session.get("apellido_paterno", "")
        apellido_m = session.get("apellido_materno", "")
        
        # Unir solo las partes que existen
        partes_nombre = [nombre, apellido_p, apellido_m]
        nombre_completo = " ".join(parte for parte in partes_nombre if parte)
        
        # Usar el nombre completo o el fallback
        nombre_admin = nombre_completo if nombre_completo else "Usuario no identificado"
        
        fecha_generacion = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ip_usuario = request.remote_addr
        
        # 4. Crear el archivo CSV en memoria
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Escribir cabecera
        writer.writerow(headers)
        
        # Escribir datos
        for row in data:
            writer.writerow(row)
            
        # Escribir pie de página
        writer.writerow([])
        writer.writerow(["---", "---", "---"])
        writer.writerow(["Informe Generado por:", nombre_admin])
        writer.writerow(["Fecha de Generacion:", fecha_generacion])
        writer.writerow(["Ubicacion (IP):", ip_usuario])

        # 5. Preparar la respuesta
        
        # --- Traducción para el nombre del archivo ---
        if tipo_reporte == 'ventas':
            tipo_es = "Ventas"
        elif tipo_reporte == 'pedidos':
            tipo_es = "Pedidos"
        elif tipo_reporte == 'clientes':
            tipo_es = "Clientes"
        else:
            tipo_es = "Reporte"

        if mes == 'pasado':
            mes_es = "Mes Pasado"
        else:
            mes_es = "Mes Actual"
            
        num_aleatorio = random.randint(1000, 9999)

        filename = f"Reporte {tipo_es} {mes_es} número {num_aleatorio}.csv"
        
        response = make_response(output.getvalue())
        
        response.headers["Content-Disposition"] = f"attachment; filename=\"{filename}\""
        response.headers["Content-type"] = "text/csv; charset=utf-8"
        
        # --- ¡ESTA ES LA LÍNEA DE CORRECCIÓN! ---
        # Permite que el navegador (JS) lea la cabecera Content-Disposition
        response.headers["Access-Control-Expose-Headers"] = "Content-Disposition"

        return response

    except Exception as e:
        print(f"Error en /api/admin/reportes/generar_informe: {e}"); traceback.print_exc()
        return jsonify({"error": str(e)}), 500
# --- ▲▲▲ FIN NUEVAS RUTAS DE INFORMES ▲▲▲ ---


# ===============================================
# --- RUTAS PARA DASHBOARD (main_menu.html) ---
# ===============================================

# --- Rutas para "Ventas Hoy" ---

@app.route('/api/admin/dashboard/kpi_ventas_hoy', methods=['GET'])
@admin_required
def get_dashboard_kpi_ventas_hoy():
    """
    Calcula las ventas totales de HOY (sysdate) y las compara con AYER.
    Filtra por sucursal_id si se provee.
    """
    sucursal_id_str = request.args.get('sucursal_id')
    conn = None
    cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        params_hoy = ['aprobado']
        params_ayer = ['aprobado']
        
        filtro_sql = ""
        if sucursal_id_str and sucursal_id_str != 'all':
            filtro_sql = " AND p.id_sucursal = %s"
            params_hoy.append(int(sucursal_id_str))
            params_ayer.append(int(sucursal_id_str))

        # --- 1. Ventas de HOY (Aprobadas) ---
        cur.execute(f"""
            SELECT COALESCE(SUM(pa.monto), 0) as total
            FROM pago pa
            LEFT JOIN pedido p ON pa.id_pedido = p.id_pedido
            WHERE pa.estado_pago = %s
            AND pa.fecha_pago >= date_trunc('day', CURRENT_DATE)
            AND pa.fecha_pago < date_trunc('day', CURRENT_DATE) + INTERVAL '1 day'
            {filtro_sql};
        """, tuple(params_hoy))
        ventas_hoy = cur.fetchone()['total']

        # --- 2. Ventas de AYER (Aprobadas) ---
        cur.execute(f"""
            SELECT COALESCE(SUM(pa.monto), 0) as total
            FROM pago pa
            LEFT JOIN pedido p ON pa.id_pedido = p.id_pedido
            WHERE pa.estado_pago = %s
            AND pa.fecha_pago >= date_trunc('day', CURRENT_DATE) - INTERVAL '1 day'
            AND pa.fecha_pago < date_trunc('day', CURRENT_DATE)
            {filtro_sql};
        """, tuple(params_ayer))
        ventas_ayer = cur.fetchone()['total']

        # --- 3. Calcular Porcentaje de Cambio ---
        porcentaje_vs_ayer = 0
        if ventas_ayer > 0:
            porcentaje_vs_ayer = ((ventas_hoy - ventas_ayer) / ventas_ayer) * 100
        elif ventas_hoy > 0:
            porcentaje_vs_ayer = 100

        return jsonify({
            "ventas_hoy": float(ventas_hoy),
            "ventas_ayer": float(ventas_ayer),
            "porcentaje_vs_ayer": round(porcentaje_vs_ayer, 2)
        })

    except Exception as e:
        print(f"Error en /api/admin/dashboard/kpi_ventas_hoy: {e}"); traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    finally:
        if cur: cur.close()
        if conn: return_db_connection(conn)


@app.route('/api/admin/dashboard/chart_ventas', methods=['GET'])
@admin_required
def get_dashboard_chart_ventas():
    """
    Obtiene los datos de ventas para el gráfico de comparación.
    Acepta ?periodo=ayer|semana|mes
    Acepta ?sucursal_id=...
    """
    periodo = request.args.get('periodo', 'ayer')
    sucursal_id_str = request.args.get('sucursal_id')
    conn = None
    cur = None
    
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        filtro_sql = ""
        params = ['aprobado']
        if sucursal_id_str and sucursal_id_str != 'all':
            filtro_sql = " AND p.id_sucursal = %s"
            params.append(int(sucursal_id_str))

        # --- 1. Ventas de HOY (Base) ---
        cur.execute(f"""
            SELECT COALESCE(SUM(pa.monto), 0) as total
            FROM pago pa
            LEFT JOIN pedido p ON pa.id_pedido = p.id_pedido
            WHERE pa.estado_pago = %s
            AND pa.fecha_pago >= date_trunc('day', CURRENT_DATE)
            AND pa.fecha_pago < date_trunc('day', CURRENT_DATE) + INTERVAL '1 day'
            {filtro_sql};
        """, tuple(params))
        ventas_hoy = float(cur.fetchone()['total'])

        labels = ["Hoy"]
        data = [ventas_hoy]
        
        params_comp = ['aprobado']
        if sucursal_id_str and sucursal_id_str != 'all':
            params_comp.append(int(sucursal_id_str))

        # --- 2. Ventas del Periodo de Comparación ---
        query_comp = ""
        if periodo == 'ayer':
            query_comp = f"""
                SELECT COALESCE(SUM(pa.monto), 0) as total
                FROM pago pa
                LEFT JOIN pedido p ON pa.id_pedido = p.id_pedido
                WHERE pa.estado_pago = %s
                AND pa.fecha_pago >= date_trunc('day', CURRENT_DATE) - INTERVAL '1 day'
                AND pa.fecha_pago < date_trunc('day', CURRENT_DATE)
                {filtro_sql};
            """
            labels.append("Ayer")

        elif periodo == 'semana':
            query_comp = f"""
                SELECT COALESCE(SUM(pa.monto), 0) as total
                FROM pago pa
                LEFT JOIN pedido p ON pa.id_pedido = p.id_pedido
                WHERE pa.estado_pago = %s
                AND pa.fecha_pago >= date_trunc('week', CURRENT_DATE)
                AND pa.fecha_pago < date_trunc('day', CURRENT_DATE)
                {filtro_sql};
            """
            labels.append("Semana (acum.)")
            
        elif periodo == 'mes':
            query_comp = f"""
                SELECT COALESCE(SUM(pa.monto), 0) as total
                FROM pago pa
                LEFT JOIN pedido p ON pa.id_pedido = p.id_pedido
                WHERE pa.estado_pago = %s
                AND pa.fecha_pago >= date_trunc('month', CURRENT_DATE)
                AND pa.fecha_pago < date_trunc('day', CURRENT_DATE)
                {filtro_sql};
            """
            labels.append("Mes (acum.)")
        
        if query_comp:
            cur.execute(query_comp, tuple(params_comp))
            ventas_comparacion = float(cur.fetchone()['total'])
            data.append(ventas_comparacion)
        else: # Fallback por si el periodo no es válido
            labels.append("Ayer")
            data.append(0)


        return jsonify({"labels": labels, "data": data})

    except Exception as e:
        print(f"Error en /api/admin/dashboard/chart_ventas: {e}"); traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    finally:
        if cur: cur.close()
        if conn: return_db_connection(conn)


@app.route('/api/admin/dashboard/lista_ventas_hoy', methods=['GET'])
@admin_required
def get_dashboard_lista_ventas_hoy():
    """
    Obtiene la lista de pedidos (ventas) aprobados de HOY para el modal.
    Filtra por sucursal_id si se provee.
    """
    sucursal_id_str = request.args.get('sucursal_id')
    conn = None
    cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        params = ['aprobado']
        filtro_sql = ""
        if sucursal_id_str and sucursal_id_str != 'all':
            filtro_sql = " AND p.id_sucursal = %s"
            params.append(int(sucursal_id_str))

        cur.execute(f"""
            SELECT 
                p.id_pedido,
                p.creado_en,
                CONCAT_WS(' ', u.nombre_usuario, u.apellido_paterno) as cliente_nombre,
                (
                    SELECT STRING_AGG(pr.nombre_producto, ', ')
                    FROM detalle_pedido dp
                    LEFT JOIN variacion_producto v ON dp.sku_producto = v.sku_variacion
                    LEFT JOIN producto pr ON v.id_producto = pr.id_producto
                    WHERE dp.id_pedido = p.id_pedido
                    LIMIT 3
                ) as productos_preview
            FROM pedido p
            JOIN usuario u ON p.id_usuario = u.id_usuario
            JOIN pago pa ON p.id_pedido = pa.id_pedido
            WHERE pa.estado_pago = %s
            AND pa.fecha_pago >= date_trunc('day', CURRENT_DATE)
            AND pa.fecha_pago < date_trunc('day', CURRENT_DATE) + INTERVAL '1 day'
            {filtro_sql}
            GROUP BY p.id_pedido, u.nombre_usuario, u.apellido_paterno
            ORDER BY p.creado_en DESC;
        """, tuple(params))
        
        ventas = cur.fetchall()
        return jsonify([dict(row) for row in ventas])

    except Exception as e:
        print(f"Error en /api/admin/dashboard/lista_ventas_hoy: {e}"); traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    finally:
        if cur: cur.close()
        if conn: return_db_connection(conn)

# --- Rutas para "Productos con bajo stock" ---

@app.route('/api/admin/dashboard/kpi_bajo_stock', methods=['GET'])
@admin_required
def get_dashboard_kpi_bajo_stock():
    """
    Calcula el KPI: Conteo de productos con stock total <= 20.
    Filtra por sucursal_id si se provee.
    """
    sucursal_id_str = request.args.get('sucursal_id')
    conn = None
    cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        filtro_sql = ""
        params = []
        if sucursal_id_str and sucursal_id_str != 'all':
            # Si filtramos por sucursal, el stock total es SOLO de esa sucursal
            filtro_sql = " WHERE i.id_sucursal = %s"
            params.append(int(sucursal_id_str))

        cur.execute(f"""
            SELECT COUNT(*) as conteo_total
            FROM (
                SELECT 
                    p.id_producto, 
                    COALESCE(SUM(i.stock), 0) as total_stock
                FROM producto p
                LEFT JOIN variacion_producto v ON p.id_producto = v.id_producto
                LEFT JOIN inventario_sucursal i ON v.id_variacion = i.id_variacion
                {filtro_sql} 
                GROUP BY p.id_producto
                HAVING COALESCE(SUM(i.stock), 0) <= 20
            ) as productos_bajo_stock;
        """, tuple(params))
        
        conteo_bajo_stock = cur.fetchone()['conteo_total']

        return jsonify({
            "conteo_bajo_stock": int(conteo_bajo_stock)
        })

    except Exception as e:
        print(f"Error en /api/admin/dashboard/kpi_bajo_stock: {e}"); traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    finally:
        if cur: cur.close()
        if conn: return_db_connection(conn)


@app.route('/api/admin/dashboard/stock_por_categoria', methods=['GET'])
@admin_required
def get_dashboard_stock_por_categoria():
    """
    Obtiene la lista de categorías y el conteo de productos con bajo stock en c/u.
    Filtra por sucursal_id si se provee.
    """
    sucursal_id_str = request.args.get('sucursal_id')
    conn = None
    cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        filtro_sql = ""
        params = []
        if sucursal_id_str and sucursal_id_str != 'all':
            filtro_sql = " WHERE i.id_sucursal = %s"
            params.append(int(sucursal_id_str))

        cur.execute(f"""
            WITH StockPorProducto AS (
                SELECT 
                    p.id_producto, 
                    COALESCE(p.categoria_producto, 'Sin Categoría') as categoria,
                    COALESCE(SUM(i.stock), 0) as total_stock
                FROM producto p
                LEFT JOIN variacion_producto v ON p.id_producto = v.id_producto
                LEFT JOIN inventario_sucursal i ON v.id_variacion = i.id_variacion
                {filtro_sql}
                GROUP BY p.id_producto, p.categoria_producto
            )
            SELECT 
                categoria,
                COUNT(*) as total_productos,
                SUM(CASE WHEN total_stock <= 20 THEN 1 ELSE 0 END) as conteo_bajo_stock
            FROM StockPorProducto
            GROUP BY categoria
            ORDER BY categoria;
        """, tuple(params))
        
        categorias = cur.fetchall()
        return jsonify([dict(row) for row in categorias])

    except Exception as e:
        print(f"Error en /api/admin/dashboard/stock_por_categoria: {e}"); traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    finally:
        if cur: cur.close()
        if conn: return_db_connection(conn)


@app.route('/api/admin/dashboard/productos_por_categoria', methods=['GET'])
@admin_required
def get_dashboard_productos_por_categoria():
    """
    Obtiene todos los productos de una categoría específica, con su stock total.
    Acepta ?categoria=...
    Filtra por sucursal_id si se provee.
    """
    categoria = request.args.get('categoria')
    sucursal_id_str = request.args.get('sucursal_id')
    
    if not categoria:
        return jsonify({"error": "Se requiere una categoría"}), 400
        
    conn = None
    cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        filtro_sucursal_sql = ""
        params = []
        
        if categoria == 'Sin Categoría':
            filtro_sql = " WHERE p.categoria_producto IS NULL"
        else:
            filtro_sql = " WHERE p.categoria_producto = %s"
            params.append(categoria)
        
        if sucursal_id_str and sucursal_id_str != 'all':
            filtro_sucursal_sql = " AND i.id_sucursal = %s"
            params.append(int(sucursal_id_str))
            
        sql = f"""
            SELECT 
                p.id_producto, 
                p.nombre_producto, 
                p.imagen_url, 
                COALESCE(SUM(i.stock), 0) as total_stock
            FROM producto p
            LEFT JOIN variacion_producto v ON p.id_producto = v.id_producto
            LEFT JOIN inventario_sucursal i ON v.id_variacion = i.id_variacion
            {filtro_sql} {filtro_sucursal_sql}
            GROUP BY p.id_producto, p.nombre_producto, p.imagen_url
            ORDER BY total_stock ASC, p.nombre_producto;
        """
        
        cur.execute(sql, tuple(params))
        productos = cur.fetchall()
        
        return jsonify([dict(row) for row in productos])

    except Exception as e:
        print(f"Error en /api/admin/dashboard/productos_por_categoria: {e}"); traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    finally:
        if cur: cur.close()
        if conn: return_db_connection(conn)

# --- Rutas para "Nuevos Clientes" ---

@app.route('/api/admin/dashboard/kpi_nuevos_clientes', methods=['GET'])
@admin_required
def get_dashboard_kpi_nuevos_clientes():
    """
    Calcula el KPI de nuevos clientes de HOY vs AYER.
    Filtra por sucursal_id si se provee (basado en dónde compraron).
    """
    sucursal_id_str = request.args.get('sucursal_id')
    conn = None
    cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        params_hoy = []
        params_ayer = []
        
        # Si filtramos por sucursal, la consulta es más compleja
        if sucursal_id_str and sucursal_id_str != 'all':
            filtro_sql = " AND p.id_sucursal = %s"
            params_hoy.append(int(sucursal_id_str))
            params_ayer.append(int(sucursal_id_str))
            
            # Clientes de HOY (que compraron en sucursal)
            cur.execute(f"""
                SELECT COUNT(DISTINCT u.id_usuario) as total
                FROM usuario u
                JOIN pedido p ON u.id_usuario = p.id_usuario
                WHERE u.creado_en >= date_trunc('day', CURRENT_DATE)
                AND u.creado_en < date_trunc('day', CURRENT_DATE) + INTERVAL '1 day'
                {filtro_sql};
            """, tuple(params_hoy))
            clientes_hoy = cur.fetchone()['total']

            # Clientes de AYER (que compraron en sucursal)
            cur.execute(f"""
                SELECT COUNT(DISTINCT u.id_usuario) as total
                FROM usuario u
                JOIN pedido p ON u.id_usuario = p.id_usuario
                WHERE u.creado_en >= date_trunc('day', CURRENT_DATE) - INTERVAL '1 day'
                AND u.creado_en < date_trunc('day', CURRENT_DATE)
                {filtro_sql};
            """, tuple(params_ayer))
            clientes_ayer = cur.fetchone()['total']

        else:
            # Conteo global (más simple)
            cur.execute("""
                SELECT COUNT(id_usuario) as total
                FROM usuario
                WHERE creado_en >= date_trunc('day', CURRENT_DATE)
                AND creado_en < date_trunc('day', CURRENT_DATE) + INTERVAL '1 day';
            """)
            clientes_hoy = cur.fetchone()['total']

            cur.execute("""
                SELECT COUNT(id_usuario) as total
                FROM usuario
                WHERE creado_en >= date_trunc('day', CURRENT_DATE) - INTERVAL '1 day'
                AND creado_en < date_trunc('day', CURRENT_DATE);
            """)
            clientes_ayer = cur.fetchone()['total']

        # Calcular Porcentaje de Cambio
        porcentaje_vs_ayer = 0
        if clientes_ayer > 0:
            porcentaje_vs_ayer = ((clientes_hoy - clientes_ayer) / clientes_ayer) * 100
        elif clientes_hoy > 0:
            porcentaje_vs_ayer = 100

        return jsonify({
            "clientes_hoy": int(clientes_hoy),
            "clientes_ayer": int(clientes_ayer),
            "porcentaje_vs_ayer": round(porcentaje_vs_ayer, 2)
        })

    except Exception as e:
        print(f"Error en /api/admin/dashboard/kpi_nuevos_clientes: {e}"); traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    finally:
        if cur: cur.close()
        if conn: return_db_connection(conn)


@app.route('/api/admin/dashboard/lista_nuevos_clientes', methods=['GET'])
@admin_required
def get_dashboard_lista_nuevos_clientes():
    """
    Obtiene la lista de nuevos clientes según el período (hoy, semana, mes).
    Filtra por sucursal_id si se provee.
    """
    sucursal_id_str = request.args.get('sucursal_id')
    periodo = request.args.get('periodo', 'hoy')
    conn = None
    cur = None
    
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        # Definir el rango de fechas según el período
        if periodo == 'semana':
            fecha_inicio_sql = "date_trunc('week', CURRENT_DATE)"
            fecha_fin_sql = "date_trunc('week', CURRENT_DATE) + INTERVAL '1 week'"
        elif periodo == 'mes':
            fecha_inicio_sql = "date_trunc('month', CURRENT_DATE)"
            fecha_fin_sql = "date_trunc('month', CURRENT_DATE) + INTERVAL '1 month'"
        else: # 'hoy' o default
            fecha_inicio_sql = "date_trunc('day', CURRENT_DATE)"
            fecha_fin_sql = "date_trunc('day', CURRENT_DATE) + INTERVAL '1 day'"

        # Definir la consulta base y los parámetros
        sql = """
            SELECT DISTINCT
                u.id_usuario, 
                CONCAT_WS(' ', u.nombre_usuario, u.apellido_paterno, u.apellido_materno) as cliente_nombre,
                u.email_usuario, 
                u.creado_en
            FROM usuario u
        """
        params = []
        
        if sucursal_id_str and sucursal_id_str != 'all':
            # Si hay sucursal, unimos con pedidos
            sql += " JOIN pedido p ON u.id_usuario = p.id_usuario"
            sql += " WHERE p.id_sucursal = %s"
            params.append(int(sucursal_id_str))
            # Y añadimos el filtro de fecha
            sql += f" AND u.creado_en >= {fecha_inicio_sql} AND u.creado_en < {fecha_fin_sql}"
        else:
            # Si no hay sucursal, solo filtramos por fecha
            sql += f" WHERE u.creado_en >= {fecha_inicio_sql} AND u.creado_en < {fecha_fin_sql}"
        
        sql += " ORDER BY u.creado_en DESC;"
        
        cur.execute(sql, tuple(params))
        clientes = cur.fetchall()
        
        return jsonify([dict(row) for row in clientes])

    except Exception as e:
        print(f"Error en /api/admin/dashboard/lista_nuevos_clientes: {e}"); traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    finally:
        if cur: cur.close()
        if conn: return_db_connection(conn)

# --- ▲▲▲ FIN NUEVAS RUTAS ▲▲▲ ---

# ===============================================
# --- NUEVA RUTA PARA REGISTRAR PAGO DE MERCADOPAGO ---
# ===============================================


# --- 1. RUTA PARA REGISTRAR PAGO MERCADOPAGO (CON DESCUENTO STOCK) ---
@app.route('/api/mercadopago/registrar-pago-mp', methods=['POST'])
def registrar_pago_mercadopago():
    data = request.get_json()
    print(f"Recibiendo pago MP: {data}")
    
    id_pedido = data.get('external_reference')
    estado_mp = data.get('status')
    payment_id = data.get('payment_id')

    if not id_pedido or not estado_mp:
        return jsonify({"error": "Datos incompletos"}), 400

    conn = None; cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        # Estado DB
        estado_db = 'aprobado' if estado_mp == 'approved' else 'rechazado'
        estado_ped_db = 'pagado' if estado_mp == 'approved' else 'rechazado'

        # Obtener monto
        cur.execute("SELECT total FROM pedido WHERE id_pedido = %s", (id_pedido,))
        row = cur.fetchone()
        if not row: raise Exception("Pedido no encontrado")
        monto = row['total']

        # Insertar Pago
        cur.execute("""
            INSERT INTO pago (id_pedido, monto, metodo_pago, estado_pago, transaccion_id, observaciones)
            VALUES (%s, %s, 'MercadoPago', %s, %s, %s) RETURNING id_pago
        """, (id_pedido, monto, estado_db, payment_id, json.dumps(data)))
        
        # Actualizar Pedido
        cur.execute("UPDATE pedido SET estado_pedido = %s WHERE id_pedido = %s", (estado_ped_db, id_pedido))

        # Descontar Stock
        if estado_db == 'aprobado':
            cur.execute("SELECT id_sucursal FROM pedido WHERE id_pedido = %s", (id_pedido,))
            suc_row = cur.fetchone()
            if suc_row and suc_row['id_sucursal']:
                id_suc = suc_row['id_sucursal']
                cur.execute("SELECT sku_producto, cantidad FROM detalle_pedido WHERE id_pedido = %s", (id_pedido,))
                items = cur.fetchall()
                for it in items:
                    cur.execute("SELECT id_variacion FROM variacion_producto WHERE sku_variacion = %s", (it['sku_producto'],))
                    var_row = cur.fetchone()
                    if var_row:
                        cur.execute("UPDATE inventario_sucursal SET stock = stock - %s WHERE id_variacion = %s AND id_sucursal = %s", 
                                    (it['cantidad'], var_row['id_variacion'], id_suc))

        conn.commit()
        return jsonify({"success": True}), 201
    except Exception as e:
        if conn: conn.rollback()
        print(f"Error MP backend: {e}"); traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    finally:
        if cur: cur.close()
        if conn: return_db_connection(conn)

# --- 2. DETALLE PEDIDO (ADMIN) ACTUALIZADO ---
@app.route('/api/admin/reportes/detalle_pedido/<int:id_pedido>', methods=['GET'])
@admin_required
def get_detalle_pedido(id_pedido):
    conn = None; cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        # ---------------------------
        # Datos del pedido + Usuario
        # ---------------------------
        cur.execute("""
            SELECT 
                p.id_pedido,
                p.total,
                p.creado_en,
                p.estado_pedido,
                p.tipo_entrega,
                p.costo_envio,
                p.fecha_entrega,
                p.bloque_horario,
                p.datos_contacto,

                pa.metodo_pago,
                pa.transaccion_id,

                -- Datos completos del cliente
                u.nombre_usuario,
                u.apellido_paterno,
                u.apellido_materno,
                u.email_usuario,
                u.telefono,
                u.calle,
                u.numero_calle,
                u.comuna,
                u.ciudad,
                u.region,

                s.nombre_sucursal

            FROM pedido p
            JOIN usuario u ON p.id_usuario = u.id_usuario
            LEFT JOIN sucursal s ON p.id_sucursal = s.id_sucursal
            LEFT JOIN pago pa ON p.id_pedido = pa.id_pedido AND pa.estado_pago = 'aprobado'

            WHERE p.id_pedido = %s
            ORDER BY pa.fecha_pago DESC NULLS LAST
            LIMIT 1;
        """, (id_pedido,))
        
        pedido_info = cur.fetchone()
        if not pedido_info:
            return jsonify({"error": "Pedido no encontrado"}), 404

        # ---------------------------
        # Items del pedido
        # ---------------------------
        cur.execute("""
            SELECT 
                dp.cantidad,
                dp.precio_unitario,
                dp.sku_producto,
                v.talla,
                v.color,
                pr.nombre_producto,
                pr.imagen_url
            FROM detalle_pedido dp
            LEFT JOIN variacion_producto v ON dp.sku_producto = v.sku_variacion
            LEFT JOIN producto pr ON v.id_producto = pr.id_producto
            WHERE dp.id_pedido = %s;
        """, (id_pedido,))
        
        items_pedido = cur.fetchall()

        return jsonify({
            "pedido": dict(pedido_info),
            "items": [dict(item) for item in items_pedido]
        })

    except Exception as e:
        print(f"❌ Error detalle pedido: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

    finally:
        if cur: cur.close()
        if conn: return_db_connection(conn)

# --- 3. API CHILEXPRESS (NECESARIA PARA LOS SELECTS DE CARRITO) ---

@app.route('/api/chilexpress/regiones', methods=['GET'])
def get_regiones():
    # URL de ejemplo de API pública o mock. Ajusta si tienes una real.
    url = "https://testservices.wschilexpress.com/georeference/api/v1/regions"
    try:
        resp = requests.get(url)
        if resp.status_code == 200:
            return jsonify(resp.json())
        return jsonify({"error": "Error al obtener regiones", "status": resp.status_code}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/chilexpress/comunas', methods=['GET'])
def get_comunas():
    region_code = request.args.get('regionCode')
    if not region_code: return jsonify({"error": "Falta regionCode"}), 400
    
    url = f"https://testservices.wschilexpress.com/georeference/api/v1/coverage-areas?RegionCode={region_code}&type=0"
    try:
        resp = requests.get(url)
        if resp.status_code == 200:
            return jsonify(resp.json())
        return jsonify({"error": "Error al obtener comunas", "status": resp.status_code}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ===========================
# Ruta de ver los pedidos
# ===========================


@app.route('/api/mis_pedidos', methods=['GET'])
def api_mis_pedidos():
    user_id = session.get('user_id')

    if not user_id:
        return jsonify({"error": "No hay sesión activa"}), 401

    conn = get_db_connection()
    cur = conn.cursor()

    # 1. Obtener pedidos del usuario
    cur.execute("""
        SELECT id_pedido, creado_en, estado_pedido, total
        FROM pedido
        WHERE id_usuario = %s
        AND estado_pedido IN ('pagado', 'enviado', 'entregado')
        ORDER BY creado_en DESC;
    """, (user_id,))
    pedidos = cur.fetchall()

    resultado = []

    for pedido in pedidos:
        id_pedido, fecha, estado, total = pedido

        # 2. Obtener productos dentro del pedido
        cur.execute("""
            SELECT dp.cantidad, dp.precio_unitario, pr.nombre_producto, pr.imagen_url, vp.talla
            FROM detalle_pedido dp
            JOIN variacion_producto vp ON dp.id_variacion = vp.id_variacion
            JOIN producto pr ON pr.id_producto = vp.id_producto
            WHERE dp.id_pedido = %s;
        """, (id_pedido,))

        productos = [
            {
                "nombre": p[2],
                "cantidad": p[0],
                "precio_unitario": float(p[1]),
                "imagen_url": p[3],
                "talla": p[4] or "N/A"

            }
            for p in cur.fetchall()
        ]


        # 3. Armar estructura final del pedido
        resultado.append({
            "id_pedido": id_pedido,
            "fecha": fecha,
            "estado_pedido": estado,  
            "total": float(total),
            "productos": productos
        })


    cur.close()
    conn.close()

    return jsonify(resultado), 200

# Implementacion producto en admin_producto
@app.route("/api/admin/productos/<int:id_producto>/detalle", methods=["GET"])
def admin_detalle_producto(id_producto):
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        # ----------------------------------------------------------------
        # 1. PRODUCTO GENERAL
        # ----------------------------------------------------------------
        cur.execute("""
            SELECT 
                p.id_producto,
                p.sku,
                p.nombre_producto,
                p.descripcion_producto,
                p.categoria_producto,
                p.precio_producto,
                p.imagen_url
            FROM producto p
            WHERE p.id_producto = %s
        """, (id_producto,))
        
        prod = cur.fetchone()
        if not prod:
            return jsonify({"error": "Producto no encontrado"}), 404
        
        producto_dict = dict(prod)

        # ----------------------------------------------------------------
        # 2. VARIACIONES
        # ----------------------------------------------------------------
        cur.execute("""
            SELECT 
                id_variacion,
                talla,
                color,
                sku_variacion
            FROM variacion_producto
            WHERE id_producto = %s
            ORDER BY talla, color
        """, (id_producto,))
        
        variaciones = [dict(row) for row in cur.fetchall()]

        # ----------------------------------------------------------------
        # 3. STOCK POR SUCURSAL
        # ----------------------------------------------------------------
        cur.execute("""
            SELECT 
                s.nombre_sucursal,
                v.talla,
                i.stock
            FROM variacion_producto v
            JOIN inventario_sucursal i ON i.id_variacion = v.id_variacion
            JOIN sucursal s ON s.id_sucursal = i.id_sucursal
            WHERE v.id_producto = %s
            ORDER BY s.nombre_sucursal, v.talla
        """, (id_producto,))

        stock_sucursales = []
        for row in cur.fetchall():
            stock_sucursales.append({
                "sucursal": row["nombre_sucursal"],
                "talla": row["talla"],
                "stock": row["stock"]
            })

        # ----------------------------------------------------------------
        # RESPUESTA FINAL SIN VENTAS
        # ----------------------------------------------------------------
        return jsonify({
            "producto": producto_dict,
            "variaciones": variaciones,
            "stock_sucursales": stock_sucursales
        })

    except Exception as e:
        print("❌ Error en admin_detalle_producto:", e)
        traceback.print_exc()
        return jsonify({"error": "Error al obtener detalle del producto"}), 500

    finally:
        if cur: cur.close()
        if conn: return_db_connection(conn)

@app.route("/api/admin/pedidos", methods=["GET"])
def admin_list_pedidos():
    try:
        status = request.args.get("status")
        q = request.args.get("q", "")

        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        query = """
            SELECT 
                p.id_pedido,
                CONCAT(u.nombre_usuario, ' ', u.apellido_paterno) AS cliente,
                p.creado_en AS fecha,
                COALESCE(p.estado_pedido, 'pendiente') AS estado,
                p.total
            FROM pedido p
            JOIN usuario u ON u.id_usuario = p.id_usuario
            WHERE 1=1
        """

        params = []

        # Filtro por estado (si no es "todos")
        if status and status != "todos":
            query += " AND LOWER(p.estado_pedido) = LOWER(%s)"
            params.append(status)

        # Filtro búsqueda por cliente o id_pedido
        if q:
            query += " AND (CAST(p.id_pedido AS TEXT) ILIKE %s OR u.nombre_usuario ILIKE %s)"
            params.extend([f"%{q}%", f"%{q}%"])

        query += " ORDER BY p.creado_en DESC"

        cur.execute(query, params)
        pedidos = [dict(row) for row in cur.fetchall()]

        return jsonify(pedidos)

    except Exception as e:
        print("❌ Error:", e)
        return jsonify({"error": "Error obteniendo pedidos"}), 500

    finally:
        if conn: return_db_connection(conn)


@app.route("/api/admin/pedidos/<int:id_pedido>", methods=["GET"])
def admin_detalle_pedido(id_pedido):
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        # ----------------------------------------
        # PEDIDO GENERAL
        # ----------------------------------------
        cur.execute("""
            SELECT 
                p.id_pedido,
                p.creado_en,
                p.estado_pedido,
                p.total,
                u.nombre_usuario,
                u.apellido_paterno
            FROM pedido p
            JOIN usuario u ON u.id_usuario = p.id_usuario
            WHERE p.id_pedido = %s
        """, (id_pedido,))

        ped = cur.fetchone()
        if not ped:
            return jsonify({"error": "Pedido no encontrado"}), 404

        pedido = {
            "id_pedido": ped["id_pedido"],
            "cliente": f"{ped['nombre_usuario']} {ped['apellido_paterno']}",
            "fecha": ped["creado_en"],
            "estado": ped["estado_pedido"],
            "total": float(ped["total"]),
        }

        # ----------------------------------------
        # ITEMS DEL PEDIDO
        # ----------------------------------------
        cur.execute("""
            SELECT 
                dp.cantidad,
                dp.precio_unitario,
                v.talla,
                v.color,
                v.sku_variacion,
                pr.nombre_producto
            FROM detalle_pedido dp
            JOIN variacion_producto v ON v.id_variacion = dp.id_variacion
            JOIN producto pr ON pr.id_producto = v.id_producto
            WHERE dp.id_pedido = %s
        """, (id_pedido,))

        items = []
        for row in cur.fetchall():
            items.append({
                "producto": row["nombre_producto"],
                "talla": row["talla"],
                "color": row["color"],
                "sku": row["sku_variacion"],
                "cantidad": row["cantidad"],
                "precio_unitario": float(row["precio_unitario"]),
            })

        return jsonify({
            "pedido": pedido,
            "items": items
        })

    except Exception as e:
        print("❌ Error obteniendo detalle:", e)
        traceback.print_exc()
        return jsonify({"error": "Error al obtener detalle del pedido"}), 500

    finally:
        if conn: return_db_connection(conn)

@app.route("/api/admin/pedidos/bulk_estado", methods=["PUT"])
def bulk_update_estado():
    try:
        data = request.get_json()
        ids = data.get("ids", [])
        estado = data.get("estado")

        if not ids or not estado:
            return jsonify({"error": "Datos inválidos"}), 400

        conn = get_db_connection()
        cur = conn.cursor()

        query = """
            UPDATE pedido 
            SET estado_pedido = %s
            WHERE id_pedido = ANY(%s)
        """
        cur.execute(query, (estado, ids))

        conn.commit()

        return jsonify({"ok": True})

    except Exception as e:
        print("❌ Error bulk:", e)
        return jsonify({"error": str(e)}), 500

    finally:
        if conn: return_db_connection(conn)

# -----------------------------------------
# KPI: Pedidos Pendientes
# -----------------------------------------
@app.route("/api/admin/dashboard/kpi_pedidos_pendientes")
@admin_required
def kpi_pedidos_pendientes():
    sucursal_id = request.args.get("sucursal_id", "all")
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    try:
        base_query = """
            SELECT COUNT(*) AS pendientes
            FROM pedido
            WHERE estado_pedido = 'pagado'
        """

        params = ()

        if sucursal_id != "all":
            base_query += " AND id_sucursal = %s"
            params = (sucursal_id,)

        cur.execute(base_query, params)
        result = cur.fetchone()

        return jsonify({"pendientes": result["pendientes"]})

    finally:
        cur.close()
        return_db_connection(conn)




# -----------------------------------------
# MODAL LISTA DE PEDIDOS PENDIENTES
# -----------------------------------------
@app.route("/api/admin/dashboard/lista_pedidos_pendientes")
@admin_required
def lista_pedidos_pendientes():
    sucursal_id = request.args.get("sucursal_id", "all")
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    try:
        base_query = """
            SELECT 
                p.id_pedido,
                p.creado_en,
                p.estado_pedido,
                
                -- Nombre completo como lo espera el frontend
                CONCAT(u.nombre_usuario, ' ', u.apellido_paterno, ' ', u.apellido_materno) AS cliente,

                s.nombre_sucursal,

                (
                    SELECT STRING_AGG(
                        COALESCE(dp.sku_producto, 'SIN SKU'), ', '
                    )
                    FROM detalle_pedido dp 
                    WHERE dp.id_pedido = p.id_pedido
                ) AS productos_preview

            FROM pedido p
            JOIN usuario u ON u.id_usuario = p.id_usuario
            LEFT JOIN sucursal s ON s.id_sucursal = p.id_sucursal

            -- SOLO pedidos pagados pero aún NO entregados
            WHERE p.estado_pedido IN ('pagado', 'preparado')
        """

        params = ()
        if sucursal_id != "all":
            base_query += " AND p.id_sucursal = %s"
            params = (sucursal_id,)

        base_query += " ORDER BY p.creado_en ASC"

        cur.execute(base_query, params)
        rows = cur.fetchall()

        return jsonify([dict(r) for r in rows])

    except Exception as e:
        print("❌ ERROR lista_pedidos_pendientes:", e)
        return jsonify({"error": str(e)}), 500

    finally:
        cur.close()
        return_db_connection(conn)

@app.route("/api/sucursales_publicas")
def obtener_sucursales_publicas():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    try:
        cur.execute("""
            SELECT 
                id_sucursal,
                nombre_sucursal,
                direccion_sucursal,
                comuna_sucursal,
                region_sucursal,
                telefono_sucursal,
                latitud_sucursal,
                longitud_sucursal,
                horario_json
            FROM sucursal
            WHERE latitud_sucursal IS NOT NULL
            AND longitud_sucursal IS NOT NULL;
        """)

        rows = cur.fetchall()
        return jsonify([dict(r) for r in rows])

    finally:
        cur.close()
        return_db_connection(conn)

# ===========================
# RUN (SIN CAMBIOS)
# ===========================
if __name__ == "__main__":
    app.run(host="localhost", port=5000, debug=True)