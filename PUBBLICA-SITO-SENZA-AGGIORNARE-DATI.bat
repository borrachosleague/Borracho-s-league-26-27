@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title Borrachos League - Pubblica senza aggiornare dati
echo.
echo === CONTROLLO REPOSITORY INTERNO ===
if not exist ".git\HEAD" (
 echo ERRORE: questa cartella non contiene il repository Git interno.
 goto ERRORE
)
rem La presenza di .git\HEAD conferma il repository interno.
rem Evitiamo confronti fra percorsi con separatori diversi (Git usa /).
for /f "delims=" %%B in ('git branch --show-current') do set "BRANCH=%%B"
if /i not "%BRANCH%"=="main" (
 echo ERRORE: ramo attivo non e' main.
 goto ERRORE
)
git diff --cached --quiet
if errorlevel 1 (
 echo ERRORE: ci sono gia' modifiche preparate per il commit.
 echo Non le includo automaticamente: controlla git status.
 goto ERRORE
)
echo.
echo === CONTROLLO GITHUB ===
git fetch origin
if errorlevel 1 goto ERRORE
git merge-base --is-ancestor origin/main HEAD
if errorlevel 1 (
 echo ERRORE: GitHub contiene commit non presenti in locale.
 echo Pubblicazione interrotta. Nessun pull/rebase automatico.
 goto ERRORE
)
echo Modalita ridotta: nessuna rigenerazione dati.
echo.
echo === PREPARO SOLO I FILE DEL SITO ===
git add -A -- index.html asta.html aggiorna.py aggiorna_live.py dati.json live.json README.md "3d" "assets" "loghi finiti" "templates"
if errorlevel 1 goto ERRORE
for %%F in (*.webp *.png *.jpg *.jpeg *.gif *.svg *.css *.js *.woff *.woff2 *.ttf) do (
 if exist "%%F" git add -A -- "%%F"
)
git diff --cached --quiet
if not errorlevel 1 (
 echo Nessuna modifica da pubblicare.
 goto APERTURA
)
echo.
echo === FILE DA PUBBLICARE ===
git diff --cached --name-status
echo.
echo ATTENZIONE: controlla anche eventuali righe D (cancellazioni).
choice /C SN /M "Confermi il commit e la pubblicazione su GitHub?"
if errorlevel 2 (
 git reset -q
 echo Pubblicazione annullata. I file locali restano invariati.
 goto FINE
)
git commit -m "Pubblicazione sito %date% %time%"
if errorlevel 1 goto ERRORE
git push origin main
if errorlevel 1 (
 echo ERRORE PUSH: commit salvato localmente, non pubblicato.
 goto ERRORE
)
:APERTURA
echo.
echo Operazione completata. Apro il sito.
start "" "https://borrachosleague.github.io/Borracho-s-league-26-27/"
goto FINE
:ERRORE
echo.
echo Operazione interrotta. Nessun push forzato.
:FINE
echo.
pause
exit /b
