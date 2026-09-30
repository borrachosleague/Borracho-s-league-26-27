@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title Borrachos League - Aggiorna e pubblica

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

echo === 2. AGGIORNAMENTO DATI ===
python aggiorna.py
if errorlevel 1 (
 echo ERRORE DATI - GitHub non viene modificato.
 pause
 exit /b 1
)

echo === 3. PREPARO MODIFICHE ===
git add -A
git diff --cached --quiet
if not errorlevel 1 goto APERTURA

echo === 4. COMMIT ===
git commit -m "Aggiornamento sito %date% %time%"
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

:APERTURA
echo === OPERAZIONE COMPLETATA ===
echo Aggiornamento completato.
echo Apro il sito Borrachos League...
start "" "https://borrachosleague.github.io/Borracho-s-league-26-27/"
timeout /t 2 /nobreak >nul
exit
