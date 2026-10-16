# Controllo sola lettura: Mandas, 3a giornata Borrachos.
import aggiorna_live as l
app, bearer = l.read_credentials(l.CREDENTIALS_FILE)
cal = l.unwrap_list(l.fetch_json(l.CALENDAR_URL, app, bearer))
mine = l.fetch_json(l.MY_LINEUP_URL, app, bearer)
dto = mine.get("teamLineupDto") or (mine.get("data") or {}).get("teamLineupDto") or {}
offset = int(dto["cmday"]) - int(dto["mday"])
day = next((x for x in cal if int(x.get("matchDay") or 0) == 3), None)
if day is None:
    print("Giornata 3 non trovata")
else:
    cmday = 3 + offset
    print("Mandas (PID 6482) - Giornata Borrachos 3 - Serie A stimata", cmday)
    found = False
    for m in day.get("matches", []):
        h, a = int(m["tIdH"]), int(m["tIdA"])
        u = f"https://apileague.fantacalcio.it/gaming/v1/teamLineup/{l.COMPETITION_ID}/3/{cmday}/{h}/{a}"
        try: d = l.fetch_json(u, app, bearer)
        except Exception as e:
            print("Partita non leggibile:", type(e).__name__)
            continue
        for side in ("home", "away"):
            team = d.get(side) or {}
            for p in (team.get("starts") or []) + (team.get("bench") or []):
                if isinstance(p, dict) and str(p.get("pid")) == "6482":
                    print("CODICE:", p.get("b"))
                    print("Voto:", p.get("scr"), "Fantavoto:", p.get("cscr"))
                    found = True
    if not found: print("Mandas non presente nelle distinte recuperate")
