@echo off
echo ==============================
echo Iniciando servidor Flask y npm
echo ==============================

:: Activar entorno virtual y correr Flask
start cmd /k "cd Api-Aurora && ..\.venv\Scripts\activate && python app.py"

:: Abrir npm en otra ventana
start cmd /k "cd src && npm run dev"

echo Servidores iniciados:
echo  - Flask en http://127.0.0.1:3000
echo  - npm en http://localhost:3000
