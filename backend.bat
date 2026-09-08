@echo off
REM Backend'ni ishga tushiradi. Ikki marta bosib ochsa ham bo'ladi.
cd /d "%~dp0back"
echo Backend ishga tushmoqda... http://127.0.0.1:8000
.venv\Scripts\python.exe manage.py runserver
pause
