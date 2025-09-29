import os
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, session, send_from_directory
import psycopg2
import psycopg2.extras
from psycopg2 import errors
from werkzeug.security import generate_password_hash, check_password_hash
from flask_cors import CORS


app = Flask(__name__)
app.secret_key = "supersecretkey"

# Configuración PostgreSQL
app.config['PG_HOST'] = "localhost"
app.config['PG_DATABASE'] = "aurora"
app.config['PG_USER'] = "postgres"
app.config['PG_PASSWORD'] = "duoc"

#Función para abrir la conexión con la Base de dats
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

# Obtengo datos de la BDD para los productos y sucursales
# Esta ruta alimenta las tablas de la interfaz

# 1.- Me conecto a la BDD
# 2.- TRaigo todos los productos y sucursales
# 3.- Renderizo el template "index.html" con los daots
# 4.- Finalmente, el usuario ve la página con el resultado esperado, que es ver la tabla de productos y sucursales
@app.route("/")
def index():
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

    # Sucursales
    cur.execute("SELECT * FROM sucursal ORDER BY id_sucursal;")
    sucursales = cur.fetchall()

    cur.close()
    conn.close()
    return render_template("index.html", productos=productos, sucursales=sucursales)

# ---------------------------
# Productos
# ---------------------------

#########################
### Agregar Producto: ###
#########################

# - Recibo datos del formulario
# - Inserto un nuevo producto en la BDD
# - Genero un "mensaje flash" para informar al usuario al momento de añadir un producto nuevo

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
    return redirect(url_for("index"))

###########################
### Editar Producto: ###
###########################

# Actualiza un producto existente en la BDD según el ID
# Recibo los datos del modal de edición
# - 
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
    return redirect(url_for("index"))



###########################
### Eliminar Producto: ###
###########################

# - Borra un producto según su id
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
# Productos
# ---------------------------


###########################
### Editar Stock: ###
###########################

# Permite cambiar la cantidad de stock de un producto en una sucursal
# - Crea una "variación del producto si no existe"


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
    return redirect(url_for("index"))

# ---------------------------
# Sucursales
# ---------------------------

# AÑADIR SUCURSAL: Inserta una nueva sucursal

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


# EDITAR SUCURSAL: Actualiza los datos de la sucursal ya creada

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
    return redirect(url_for("index"))


# ELIMINAR SUCURSAL: Elimina una sucursal creada según ID.

@app.route("/eliminar_sucursal/<int:id_sucursal>", methods=["POST"])
def eliminar_sucursal(id_sucursal):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM sucursal WHERE id_sucursal = %s", (id_sucursal,))
    conn.commit()
    cur.close()
    conn.close()
    flash("Sucursal eliminada con éxito")
    return redirect(url_for("index"))


# ===========================
# Paths para servir login.html y assets
# ===========================
BASE_DIR = os.path.abspath(os.path.dirname(__file__))                     # ...\Capston\Aurora\Api-Aurora
SRC_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "src"))            # ...\Capston\Aurora\src
PUBLIC_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "Public"))      # ...\Capston\Aurora\Public

# ===========================
# HELPERS
# ===========================
def get_user_by_email(email):
    """Obtiene el usuario por email (o None)."""
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute("""
        SELECT id_usuario, nombre_usuario, email_usuario, rol_usuario, password, creado_en
        FROM usuario
        WHERE LOWER(email_usuario) = LOWER(%s)
        LIMIT 1;
    """, (email,))
    user = cur.fetchone()
    cur.close()
    conn.close()
    return user

def create_user(nombre, email, password_plano, rol='cliente'):
    """Crea un usuario con password hasheada. 
    Evita avanzar la secuencia si el email ya existe (pre-check) y
    mantiene el UNIQUE como respaldo."""
    email_norm = (email or "").strip().lower()
    nombre_norm = (nombre or "").strip()
    rol_norm = 'cliente'  # forzado por requerimiento
    password_hash = generate_password_hash(password_plano)

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    try:
        # --- PRECHECK: si ya existe, NO intentamos INSERT (la secuencia no avanza) ---
        cur.execute("SELECT 1 FROM usuario WHERE LOWER(email_usuario)=LOWER(%s) LIMIT 1;", (email_norm,))
        if cur.fetchone():
            return False, "El correo ya está registrado."

        # --- INSERT real (aquí sí avanzará la secuencia, pero solo en intentos válidos) ---
        cur.execute("""
            INSERT INTO usuario (nombre_usuario, email_usuario, rol_usuario, password, creado_en)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id_usuario;
        """, (nombre_norm, email_norm, rol_norm, password_hash, datetime.utcnow()))
        new_id = cur.fetchone()[0]
        conn.commit()
        return True, new_id

    except errors.UniqueViolation:
        # Respaldo ante condición de carrera: otro proceso insertó el mismo email entre el precheck y el insert
        conn.rollback()
        return False, "El correo ya está registrado."
    except Exception as e:
        conn.rollback()
        return False, f"Error al registrar: {str(e)}"
    finally:
        cur.close()
        conn.close()


def do_login(email, password):
    """Valida credenciales y setea sesión. Retorna (True, None) o (False, 'mensaje')."""
    if not email or not password:
        return False, "Debes ingresar correo y contraseña."

    user = get_user_by_email(email)
    if not user or not check_password_hash(user["password"], password):
        return False, "Credenciales inválidas."

    session["user_id"] = user["id_usuario"]
    session["nombre_usuario"] = user["nombre_usuario"]
    session["email_usuario"] = user["email_usuario"]
    session["rol_usuario"] = user["rol_usuario"]
    return True, None

def do_register(nombre, email, password):
    """Crea usuario (rol cliente por defecto) y auto-login."""
    if not nombre or not email or not password:
        return False, "Nombre, correo y contraseña son obligatorios."

    ok, result = create_user(nombre, email, password, rol="cliente")
    if not ok:
        return False, result

    # Auto-login
    ok_l, msg = do_login(email, password)
    if not ok_l:
        return False, msg
    return True, None

# ===========================
# RUTAS DE AUTENTICACIÓN
# ===========================

# GET /login: sirve el HTML desde src/ (opción 2)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return send_from_directory(SRC_DIR, "login.html")

    # POST (viene del form de login)
    email = (request.form.get("email_usuario") or "").strip()
    password = (request.form.get("password") or "").strip()

    # Validación rápida
    if not email or not password:
        # dejamos el tab de login activo y marcamos que viene de login
        return redirect(url_for("login") + "?error=missing&tab=login&src=login")

    # Buscamos al usuario para distinguir errores
    user = get_user_by_email(email)
    if not user:
        # usuario no existe
        return redirect(url_for("login") + "?error=user_not_found&tab=login&src=login")

    # contraseña incorrecta
    if not check_password_hash(user["password"], password):
        return redirect(url_for("login") + "?error=bad_password&tab=login&src=login")

    session["user_id"] = user["id_usuario"]
    session["nombre_usuario"] = user["nombre_usuario"]
    session["email_usuario"] = user["email_usuario"]
    session["rol_usuario"] = user["rol_usuario"]


    return redirect(FRONTEND_MAIN_URL)


@app.route("/register", methods=["GET", "POST"])
def register():
    # GET: si alguien entra directo, muéstrale el tab de registro en la página de login
    if request.method == "GET":
        return redirect(url_for("login") + "?tab=register")

    # POST: procesar registro
    nombre   = (request.form.get("nombre_usuario") or "").strip()
    email    = (request.form.get("email_usuario")  or "").strip()
    password = (request.form.get("password")       or "").strip()

    # Validación rápida: campos obligatorios
    if not nombre or not email or not password:
        # volvemos a /login con tab=register y codificamos el error
        return redirect(url_for("login") + "?error=missing&tab=register&src=register")

    ok, msg = do_register(nombre, email, password)  # crea usuario + auto-login (sesión en Flask)

    if not ok:
        # si el helper detectó duplicado, msg suele contener “correo”
        error_code = "email" if (msg and "correo" in msg.lower()) else "unknown"
        return redirect(url_for("login") + f"?error={error_code}&tab=register&src=register")

    # Éxito: usuario creado y sesión iniciada en Flask → redirigimos al main del FRONTEND (Node)
    return redirect(FRONTEND_MAIN_URL)


@app.route("/logout", methods=["POST", "GET"])
def logout():
    session.pop("user_id", None)
    session.pop("nombre_usuario", None)
    session.pop("email_usuario", None)
    session.pop("rol_usuario", None)
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
        <li>Email: {session.get('email_usuario')}</li>
        <li>Rol: {session.get('rol_usuario')}</li>
    </ul>
    """

@app.route("/api/session_info")
def session_info():
    if "user_id" not in session:
        return {"logged_in": False}, 200
    return {
        "logged_in": True,
        "id": session.get("user_id"),
        "nombre": session.get("nombre_usuario"),
        "email": session.get("email_usuario"),
        "rol": session.get("rol_usuario"),
    }, 200



# ===========================
# RUN
# ===========================
if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)