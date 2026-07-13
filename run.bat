@echo off 
chcp 65001 < nul 
color 4 
title Run Server

cd /d "%~dp0"

echo ________________________________________
echo.
echo.
echo          FILE STORAGE SERVER
echo.
echo ________________________________________
echo.
echo Запуск с правами администратора...
echo.

net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [ОШИБКА] Запустите файл от имени администратора!
    echo.
    echo Нажмите правой кнопкой мыши на этом файле и выберите
    echo "Запуск от имени администратора"
    echo.
    pause
    exit /b 1
)

echo [OK] Права администратора получены
echo.

echo [ЗАПУСК] python application.py
python application.py

if %errorlevel% neq 0 (
    echo.
    echo [ОШИБКА] Не удалось запустить приложение
    echo Возможно, не установлены зависимости.
    echo Выполните: pip install -r requirements.txt
    echo.
    pause
)

pause