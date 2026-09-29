@echo off
cd /d "E:\--- fantacalcio tot uff\26-27"
set "PYTHON=C:\Users\Marco\AppData\Local\Python\pythoncore-3.14-64\python.exe"
echo === 1. AGGIORNAMENTO DATI ===
"%PYTHON%" aggiorna.py
if errorlevel 1 (
 echo ERRORE: dati non aggiornati. Pubblicazione annullata.
 pause
 exit /b 1
)
echo === 2. PUBBLICAZIONE SU GITHUB ===
git add .
git diff --cached --quiet
if errorlevel 1 (
 git commit -m "Update %date% %time%"
 if errorlevel 1 goto :errore
 git push
 if errorlevel 1 goto :errore
) else (
 echo Nessuna modifica da pubblicare.
)
start "" https://borrachosleague.github.io/Borracho-s-league-26-27/
pause
exit /b 0
:errore
echo ERRORE GIT: pubblicazione non completata.
pause
exit /b 1
