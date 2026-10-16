# Diagnostica sola lettura: indici dei bonus/malus delle giornate concluse.
# Nessun token viene stampato; nessun file viene modificato.
import aggiorna_live as live

def main():
    if not live.CREDENTIALS_FILE:
        raise RuntimeError("File credenziali mancante")
    app, bearer = live.read_credentials(live.CREDENTIALS_FILE)
    calendar = live.unwrap_list(live.fetch_json(live.CALENDAR_URL, app, bearer))
    mine = live.fetch_json(live.MY_LINEUP_URL, app, bearer)
    dto = mine.get("teamLineupDto") or (mine.get("data") or {}).get("teamLineupDto") or {}
    current = int(dto.get("mday") or 0)
    current_seriea = int(dto.get("cmday") or 0)
    days = sorted((d for d in calendar if int(d.get("matchDay") or 0) < current), key=lambda d: int(d.get("matchDay") or 0), reverse=True)
    if not days:
        print("Nessuna giornata precedente disponibile")
        return
    # L'offset e' rilevato dalla giornata attuale, senza assumere il numero di giornata Serie A.
    offset = current_seriea - current
    found = 0
    for day in days[:3]:
        mday = int(day["matchDay"])
        cmday = mday + offset
        print(f"\nGiornata Borrachos {mday} / Serie A stimata {cmday}")
        for match in day.get("matches", []):
            h, a = int(match["tIdH"]), int(match["tIdA"])
            url = f"https://apileague.fantacalcio.it/gaming/v1/teamLineup/{live.COMPETITION_ID}/{mday}/{cmday}/{h}/{a}"
            try:
                detail = live.fetch_json(url, app, bearer)
            except Exception as e:
                print("Partita",h,a,": errore",str(e).split(":")[0]); continue
            if not detail.get("cal"):
                print("Partita",h,a,": non calcolata")
                continue
            for team in (detail.get("home") or {}, detail.get("away") or {}):
                for player in (team.get("starts") or [])+(team.get("bench") or []):
                    if not isinstance(player, dict): continue
                    raw=player.get("b")
                    if not isinstance(raw,str): continue
                    parts=raw.split(";")
                    active=[f"{i}={value}" for i,value in enumerate(parts) if value.strip() not in ("","0","0.0")]
                    if active:
                        print("PID", player.get("pid"), "indici", ", ".join(active), "voto",player.get("scr"),"fv",player.get("cscr"))
                        found += 1
        if found: break
    if not found: print("Nessun bonus/malus non nullo recuperato nelle giornate controllate.")
    print("\nConfrontare gli ID e gli indici con gli eventi ufficiali: non attribuire significati prima della verifica.")

if __name__=="__main__":
    main()
