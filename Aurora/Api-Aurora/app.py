from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
import psycopg2
import psycopg2.extras
import os
from flask import Flask, render_template

template_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")
app = Flask(__name__, template_folder=template_dir)

import os
print(os.path.exists(os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates/index.html")))

# Obtiene la ruta absoluta donde está app.py
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Fuerza a Flask a buscar templates en la carpeta 'templates' dentro de BASE_DIR
app = Flask(__name__, template_folder=os.path.join(BASE_DIR, 'templates'))

# Conexión global
conn = psycopg2.connect(
    dbname="aurora",
    user="postgres",
    password="duoc",
    host="localhost",
    port="5432"
)




app = Flask(__name__)
app.secret_key = "supersecretkey"

# Configuración conexión PostgreSQL
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
    cur.execute("SELECT * FROM producto_simple ORDER BY id;")
    productos = cur.fetchall()
    cur.close()
    conn.close()
    return render_template("index.html", productos=productos)

@app.route("/add", methods=["POST"])
def add_producto():
    nombre = request.form["nombre"]
    precio = request.form["precio"]

    conn = get_db_connection()
    cur = conn.cursor()

    # Insertamos en producto (variaciones e inventario los manejarías aparte)
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



# ===========================
# RUN
# ===========================
if __name__ == '__main__':
    app.run(host='127.0.0.1', port=3000, debug=True)

