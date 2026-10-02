@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title Borrachos League - Pubblica modifiche sito

echo === PUBBLICAZIONE RAPIDA - SENZA AGGIORNARE I DATI ===
echo.
echo Questo BAT NON esegue aggiorna.py
echo Questo BAT NON esegue aggiorna_live.py
echo.

echo === 1. CONTROLLO GITHUB ===
git fetch origin
if errorlevel 1 (
 echo ERRORE CONNESSIONE GITHUB.
 pause
 exit /b 1
)

for /f %%A in ('git rev-list --count HEAD..origin/main') do set "REMOTE_AHEAD=%%A"
if not "%REMOTE_AHEAD%"=="0" (
 echo GitHub contiene modifiche piu recenti. Sincronizzo...
 git pull --rebase --autostash origin main
 if errorlevel 1 (
  echo ERRORE SINCRONIZZAZIONE. Nessun push eseguito.
  echo NON usare push --force.
  pause
  exit /b 1
 )
)

echo === 2. CONTROLLO FILE MODIFICATI ===
git status --short
echo.

echo === 3. PREPARO SOLO LE MODIFICHE ESISTENTI ===
git add -A
git diff --cached --quiet
if not errorlevel 1 goto NESSUNA_MODIFICA

echo === 4. COMMIT ===
git commit -m "Modifica sito %date% %time%"
if errorlevel 1 (
 echo ERRORE COMMIT.
 pause
 exit /b 1
)

echo === 5. PUSH ===
git push origin main
if errorlevel 1 (
 echo ERRORE GIT - pubblicazione non completata.
 echo Nessun push forzato e' stato eseguito.
 pause
 exit /b 1
)

goto APERTURA

:NESSUNA_MODIFICA
echo Nessun file modificato da pubblicare.

:APERTURA
echo.
echo === OPERAZIONE COMPLETATA ===
echo I dati NON sono stati rigenerati.
echo Apro/aggiorno il sito Borrachos...
start "" "https://borrachosleague.github.io/Borracho-s-league-26-27/"
timeout /t 4 /nobreak >nul
exit
