@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title Borrachos League - Pubblica senza aggiornare dati

echo === 1. CONTROLLO GITHUB ===
git fetch origin
if errorlevel 1 (
 echo.
 echo ERRORE CONNESSIONE GITHUB.
 goto FINE
)

for /f %%A in ('git rev-list --count HEAD..origin/main') do set "REMOTE_AHEAD=%%A"
if not "%REMOTE_AHEAD%"=="0" (
 echo GitHub contiene modifiche piu recenti. Sincronizzo...
 git pull --rebase --autostash origin main
 if errorlevel 1 (
  echo.
  echo ERRORE SINCRONIZZAZIONE. Nessun push eseguito.
  echo NON usare push --force.
  goto FINE
 )
)

echo.
echo === 2. PREPARO MODIFICHE ===
git add -A
git diff --cached --quiet
if not errorlevel 1 (
 echo Nessuna modifica da pubblicare.
 goto APERTURA
)

echo.
echo === 3. COMMIT ===
git commit -m "Aggiornamento sito senza rigenerare dati %date% %time%"
if errorlevel 1 (
 echo.
 echo ERRORE COMMIT.
 goto FINE
)

echo.
echo === 4. PUSH ===
git push origin main
if errorlevel 1 (
 echo.
 echo ERRORE GIT - pubblicazione non completata.
 echo Nessun push forzato e' stato eseguito.
 goto FINE
)

:APERTURA
echo.
echo ==============================================
echo PUBBLICAZIONE COMPLETATA
echo dati.json e live.json NON sono stati rigenerati.
echo ==============================================
echo.
echo Apro/aggiorno il sito Borrachos...
start "" "https://borrachosleague.github.io/Borracho-s-league-26-27/"

:FINE
echo.
echo ==============================================
echo FINE OPERAZIONE
echo La finestra resta aperta per leggere i messaggi.
echo Premi un tasto per chiuderla.
echo ==============================================
pause >nul
exit /b
