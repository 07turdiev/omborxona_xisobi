@echo off
REM Frontend'ni ishga tushiradi. Ikki marta bosib ochsa ham bo'ladi.
cd /d "%~dp0front"
echo Frontend ishga tushmoqda... http://localhost:5173
set NODE_OPTIONS=--use-system-ca
npm run dev
pause
