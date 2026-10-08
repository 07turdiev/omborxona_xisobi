@echo off
rem =====================================================================
rem  MADLEN SEN - chop etish agentini kassa kompyuteriga ornatadi.
rem
rem  Ikki marta bosing. Qolganini install.ps1 bajaradi: Node.js,
rem  papka tuzilmasi, printerlar, sozlama, avtomatik ishga tushish
rem  va sinov chop etish. Administrator huquqi ozi soraladi.
rem =====================================================================

chcp 65001 > nul

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1"

if errorlevel 1 (
    echo.
    echo Ornatish boshlanmadi. Yuqoridagi xabarni oqing.
    pause
)
