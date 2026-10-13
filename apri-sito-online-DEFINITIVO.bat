@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0"
title BORRACHOS - Aggiorna e pubblica in sicurezza
set "URL=https://borrachosleague.github.io/Borracho-s-league-26-27/"
set "FAILED=0"
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
git fetch origin || goto ERRORE
for /f "delims=" %%S in ('git status --porcelain --untracked-files=no') do set "DIRTY=1"
rem Se il ramo remoto e' avanzato, il pull con autostash gestisce anche file modificati.
git -c rebase.autoStash=true pull --rebase origin main
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
if errorlevel 1 (echo ERRORE: aggiorna_live.py non riuscito.& goto ERRORE)
if not exist "live.json" (echo ERRORE: live.json non generato.& goto ERRORE)

echo.
echo [4/5] Preparazione delle modifiche...
rem Aggiorna tutti i file gia' tracciati, compresi BAT e pagine HTML.
rem Non aggiunge __pycache__, diagnostica o altri file nuovi non richiesti.
git add -u
if errorlevel 1 goto ERRORE
rem Includi nuovi file grafici / del sito nelle cartelle previste.
for %%D in (assets "3d" "loghi finiti" templates) do if exist "%%~D" git add -A -- "%%~D"
if errorlevel 1 goto ERRORE
rem Includi eventuali nuovi file web nella cartella principale.
for %%F in (*.html *.css *.js *.webp *.png *.jpg *.jpeg *.gif *.svg *.woff *.woff2) do if exist "%%~F" git add -- "%%~F"
if errorlevel 1 goto ERRORE

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
echo OK: aggiornamento completato.
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
