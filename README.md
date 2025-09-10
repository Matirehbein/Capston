#  Aurora - E-commerce

Aurora es un proyecto web de moda y belleza.  
Incluye páginas de **colecciones**, **productos**, **ofertas**, **login** y más, con un diseño responsivo y simple de ejecutar.
En donde se centra un ChatBot con IA, para poder ayudar al sistema y soporte de ayudas.

---

##  Requisitos

- [Node.js](https://nodejs.org/) (v18 o superior recomendado)
- npm (incluido con Node)

---

##  Instalación y ejecución

1. Clonar el repositorio:
   ```bash
   git clone https://github.com/Matirehbein/Aurora
   cd aurora/Aurora

2. Instalar
    npm install

3. Ejecutar en la Terminal
    cd C:\Users\mati\Desktop\Aurora-main\Aurora

    npm run dev
    npm start

4. Abrir el servidor 
    http://localhost:3000/src/index.html
    
---

## Instalación en un entorno externo de la app de Flask (CRUD)

1. Ir a la ruta del proyecto:
    ```bash
    cd "ruta_de_mi_proyecto\Aurora\Api-Aurora"

2. Crear un entorno virtual:
    ```bash
    python -m venv venv

3. Activar el entorno virtual:
    ```bash
    .\venv\Scripts\Activate

4. Instalar Flask y psycopg2:
    ```bash
    pip install flask psycopg2-binary

5. (OPCIONAL) Guardar dependencias en un archivo:
    ```bash
    pip freeze > requeriments.txt

6. Ejecutar el servidor Flask:
    ```bash
    python app.py

---

7. O también, en vez de instalar todas las dependencias anteriores hasta el punto 4, se puede ejecutar lo siguiente en la terminal:
   ```bash
   pip install -r requirements.txt 

8.- Luego, ejecutar el servidor Flask:
   ```bash
    python app.py
