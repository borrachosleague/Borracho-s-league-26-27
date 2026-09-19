@echo off
echo === AGGIORNAMENTO DATI ===
python aggiorna.py

echo === PUBLISH SU GITHUB ===
git add .
git commit -m "Update %date%"
git push

echo === SITO AGGIORNATO ===
start https://borrachosleague.github.io/Borracho-s-league-26-27/
pause   