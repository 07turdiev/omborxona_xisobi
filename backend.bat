@echo off
REM Backend'ni ishga tushiradi. Ikki marta bosib ochsa ham bo'ladi.
cd /d "%~dp0back"

REM Qo'llanmagan migratsiya bilan ishga tushirish xavfli: xatolik
REM faqat birinchi sotuvda ko'rinadi.
echo Migratsiyalar tekshirilmoqda...
.venv\Scripts\python.exe manage.py migrate --check
if errorlevel 1 (
    echo.
    echo DIQQAT: qo'llanmagan migratsiya bor.
    echo Avval quyidagini bajaring:
    echo     back\.venv\Scripts\python.exe manage.py migrate
    echo.
    pause
    exit /b 1
)

echo Backend ishga tushmoqda... http://127.0.0.1:8000
.venv\Scripts\python.exe manage.py runserver
pause
