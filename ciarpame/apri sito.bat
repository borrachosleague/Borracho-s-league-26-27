@echo off
cd /d "E:\--- fantacalcio tot uff\26-27"

set "PYTHON=C:\Users\Marco\AppData\Local\Python\pythoncore-3.14-64\python.exe"

echo === Kill server vecchi ===
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000" ^| findstr "LISTENING"') do taskkill /F /PID %%a >nul 2>&1
timeout /t 2 /nobreak >nul

echo === Avvio server ===
start /min cmd /k "%PYTHON% -m http.server 8000"
timeout /t 2 /nobreak >nul

echo === Aggiorna dati ===
"%PYTHON%" aggiorna.py
if errorlevel 1 (
    echo ERRORE!
    pause
    exit /b 1
)

echo === Apri sito ===
start http://localhost:8000

echo Fatto!
pause   