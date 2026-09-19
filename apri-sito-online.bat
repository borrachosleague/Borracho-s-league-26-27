@echo off
echo === 1. AGGIORNAMENTO DATI ===
python aggiorna.py

echo === 2. PUBLISH SU GITHUB ===
git add .
git commit -m "Update %date%"
git push

echo === 3. APERTURA SITO ===
start https://borrachosleague.github.io/Borracho-s-league-26-27/

echo === FINITO ===
pause   