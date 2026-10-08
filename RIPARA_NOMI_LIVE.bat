@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo RIPARAZIONE NOMI GIOCATORI LIVE BORRACHOS
echo.
python "RIPARA_NOMI_LIVE.py"
if errorlevel 1 (
 echo.
 echo ERRORE: nessun aggiornamento LIVE eseguito.
 pause
 exit /b 1
)
echo.
echo Rigenero live.json...
python "aggiorna_live.py"
if errorlevel 1 (
 echo.
 echo ERRORE: live.json non aggiornato. Verificare i messaggi sopra.
 pause
 exit /b 1
)
echo.
echo OK. Ora pubblica usando il BAT COMPLETO originale del sito.
pause
