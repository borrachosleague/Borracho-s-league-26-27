@echo off
echo OPERAZIONE BLOCCATA: aggiornamenti automatici Fantacalcio disattivati.
echo Non utilizzare questo BAT. Usare soltanto PUBBLICA-SITO-SENZA-AGGIORNARE-DATI.bat per file locali gia autorizzati.
pause
exit /b 1
@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0"
title BORRACHOS - Aggiorna e pubblica in sicurezza
set "URL=https://borrachosleague.github.io/Borracho-s-league-26-27/"
set "LIVE_OK=1"
echo.
echo ===== BORRACHOS LEAGUE - AGGIORNAMENTO COMPLETO =====
where git >nul 2>&1 || (echo ERRORE: Git non trovato.& goto ERRORE)
where python >nul 2>&1 || (echo ERRORE: Python non trovato.& goto ERRORE)
git rev-parse --is-inside-work-tree >nul 2>&1 || (echo ERRORE: cartella non Git.& goto ERRORE)
for /f "delims=" %%B in ('git branch --show-current') do set "BRANCH=%%B"
if /i not "%BRANCH%"=="main" (echo ERRORE: il ramo attivo non e' main.& goto ERRORE)
if not exist "aggiorna.py" (echo ERRORE: manca aggiorna.py.& goto ERRORE)
if not exist "aggiorna_live.py" (echo ERRORE: manca aggiorna_live.py.& goto ERRORE)

echo.
echo [1/5] Sincronizzazione sicura con GitHub...
rem --autostash conserva temporaneamente modifiche tracciate durante il rebase.
rem In caso di conflitto Git si ferma: non sovrascriviamo i file.
git diff --cached --quiet
if errorlevel 1 (echo ERRORE: modifiche gia preparate per commit. Operazione interrotta.& goto ERRORE)
git fetch origin || goto ERRORE
rem Sincronizzazione fast-forward senza merge o rebase.
git pull --ff-only origin main
if errorlevel 1 (
 echo ERRORE: sincronizzazione non completata. Non proseguire prima di risolvere il conflitto Git.
 goto ERRORE
)

echo.
echo [2/5] Generazione dati del sito...
python aggiorna.py
if errorlevel 1 (echo ERRORE: aggiorna.py non riuscito.& goto ERRORE)
if not exist "dati.json" (echo ERRORE: dati.json non generato.& goto ERRORE)

echo.
echo [3/5] Generazione dati Live statici...
python aggiorna_live.py
if errorlevel 1 (
 echo ATTENZIONE: aggiornamento LIVE fallito. Proseguo con gli altri dati.
 set "LIVE_OK=0"
)
if not exist "live.json" (
 echo ATTENZIONE: live.json assente. Proseguo senza LIVE.
 set "LIVE_OK=0"
)

echo.
echo [4/5] Preparazione delle modifiche...
rem Selezioniamo solo i file del sito: gli Excel locali NON vanno pubblicati.
rem Gli script diagnostici e __pycache__ restano locali.
git add -u -- index.html asta.html aggiorna.py aggiorna_live.py dati.json README.md apri-sito-online-DEFINITIVO.bat PUBBLICA-SITO-SENZA-AGGIORNARE-DATI.bat
if errorlevel 1 goto ERRORE
if "%LIVE_OK%"=="1" (
 git add -u -- live.json
 if errorlevel 1 goto ERRORE
 if exist "live_names.json" (
  git add -- live_names.json
  if errorlevel 1 goto ERRORE
 )
)
for %%D in (assets "3d" "loghi finiti" templates) do (
 if exist "%%~D" git add -A -- "%%~D"
 if errorlevel 1 goto ERRORE
)
for %%F in (*.html *.css *.js *.webp *.png *.jpg *.jpeg *.gif *.svg *.woff *.woff2) do (
 if exist "%%F" git add -- "%%F"
 if errorlevel 1 goto ERRORE
)
if "%LIVE_OK%"=="0" echo NOTA: LIVE non aggiornato, ma i dati ordinari possono essere pubblicati.

git diff --cached --quiet
if not errorlevel 1 (
 echo Nessuna modifica da pubblicare.
 goto APERTURA
)
echo.
echo File che verranno pubblicati:
git diff --cached --name-status
echo.
choice /C SN /N /M "Confermi la pubblicazione? [S/N] "
if errorlevel 2 (
 echo Pubblicazione annullata. Nessun file eliminato.
 goto FINE
)
echo.
echo [5/5] Commit e invio a GitHub...
git commit -m "Aggiornamento Borrachos %date% %time%"
if errorlevel 1 goto ERRORE
git push origin main
if errorlevel 1 (
 echo ERRORE: commit locale creato ma push non riuscito.
 goto ERRORE
)
:APERTURA
echo.
echo OK: pubblicazione completata.
if "%LIVE_OK%"=="0" echo ATTENZIONE: LIVE non aggiornato, verificare fase [3/5].
echo Apro il sito pubblicato.
start "" "%URL%"
goto FINE
:ERRORE
echo.
echo OPERAZIONE INTERROTTA: controlla il messaggio sopra.
echo Nessun push forzato, nessun reset distruttivo.
echo Se compare un conflitto Git, non rilanciare il BAT: mandami il testo dell'errore.
:FINE
echo.
pause
endlocal
exit /b
