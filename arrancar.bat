@echo off
chcp 65001 > nul
title Casa de la Cultura

:: ── Comprobar que el entorno está preparado ───────────
if not exist venv_demo\Scripts\python.exe (
    echo.
    echo ERROR: El entorno no está preparado.
    echo Ejecuta primero preparar_demo.bat en un PC con Python.
    echo.
    pause & exit /b 1
)

if not exist db.sqlite3 (
    echo.
    echo ERROR: No se encuentra la base de datos ^(db.sqlite3^).
    echo Ejecuta primero preparar_demo.bat en un PC con Python.
    echo.
    pause & exit /b 1
)

:: ── Arrancar ──────────────────────────────────────────
echo.
echo Arrancando Casa de la Cultura...

:: Abrir el navegador (espera 2s para que el servidor esté listo)
start "" cmd /c "timeout /t 2 > nul && start http://localhost:8000"

:: Iniciar el servidor (esta ventana debe quedar abierta)
venv_demo\Scripts\python manage.py runserver --noreload

echo.
echo El servidor se ha detenido. Cierra esta ventana.
pause
