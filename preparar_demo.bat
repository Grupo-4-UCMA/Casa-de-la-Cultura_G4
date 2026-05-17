@echo off
chcp 65001 > nul
title Casa de la Cultura — Preparación demo

echo.
echo =====================================================
echo   CASA DE LA CULTURA — Preparación del paquete demo
echo   Ejecutar UNA VEZ en cualquier Windows con Python
echo =====================================================
echo.

:: ── Comprobar Python ─────────────────────────────────
python --version > nul 2>&1
if errorlevel 1 (
    echo ERROR: Python no está instalado en este equipo.
    echo Descárgalo en https://www.python.org/downloads/
    pause & exit /b 1
)
for /f "tokens=*" %%v in ('python --version') do echo Python detectado: %%v

:: ── Entorno virtual ───────────────────────────────────
echo.
echo [1/5] Creando entorno virtual...
if exist venv_demo (
    echo       Ya existe, omitiendo creacion.
) else (
    python -m venv venv_demo
)

:: ── Dependencias ─────────────────────────────────────
echo.
echo [2/5] Instalando dependencias (puede tardar unos minutos)...
venv_demo\Scripts\pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo ERROR al instalar dependencias. Revisa requirements.txt
    pause & exit /b 1
)

:: ── Base de datos ─────────────────────────────────────
echo.
echo [3/5] Inicializando base de datos...
venv_demo\Scripts\python manage.py migrate --run-syncdb
if errorlevel 1 (
    echo ERROR al ejecutar las migraciones.
    pause & exit /b 1
)

:: ── Carga de datos ────────────────────────────────────
echo.
echo [4/5] Cargando datos (libros, usuarios, valoraciones)...
echo       Esto puede tardar 2-3 minutos, no cierres la ventana.
venv_demo\Scripts\python load_data_fast.py
if errorlevel 1 (
    echo ERROR al cargar los datos. Comprueba que data/ tiene todos los CSV.
    pause & exit /b 1
)

:: ── Motor de recomendaciones ──────────────────────────
echo.
echo [5/5] Calculando recomendaciones...
echo       Esto puede tardar 5 minutos.
venv_demo\Scripts\python train.py
if errorlevel 1 (
    echo AVISO: El motor de recomendaciones falló, pero la app puede funcionar sin él.
)

:: ── Empaquetado ZIP ───────────────────────────────────
echo.
echo Empaquetando demo en casa_cultura_demo.zip...

:: Necesita PowerShell (disponible en Windows 10/11)
powershell -Command ^
  "Compress-Archive -Force -Path ^
    'app', 'casa_cultura', 'data', 'docs', ^
    'etl', 'generar_sinopsis.py', 'recuperar_isbn.py', ^
    'manage.py', 'requirements.txt', 'README.md', ^
    'db.sqlite3', 'venv_demo', 'arrancar.bat' ^
   -DestinationPath 'casa_cultura_demo.zip'"

if errorlevel 1 (
    echo AVISO: No se pudo crear el ZIP automáticamente.
    echo Copia manualmente la carpeta entera al USB.
) else (
    echo.
    echo =====================================================
    echo   LISTO. Fichero generado: casa_cultura_demo.zip
    echo.
    echo   Copia ese ZIP al PC del cliente, descomprímelo
    echo   y haz doble clic en arrancar.bat
    echo =====================================================
)
echo.
pause
