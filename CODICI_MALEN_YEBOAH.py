# ACCESSI AUTOMATICI FANTACALCIO DISABILITATI IL 16/10/2026.
# Diagnostica storica conservata, ma esecuzione vietata senza autorizzazione.
print('BLOCCATO: questo script effettuava accessi automatici a Fantacalcio.')
raise SystemExit(1)

# Lettura sola lettura dei codici bonus/malus richiesti, senza salvare file.
import aggiorna_live as live

def run():
    if not live.CREDENTIALS_FILE:
        print("Credenziali non trovate"); return
    app, token = live.read_credentials(live.CREDENTIALS_FILE)
    cal=live.unwrap_list(live.fetch_json(live.CALENDAR_URL, app, token))
    targets=[(4,6,5585,"Malen"),(3,5,6904,"Yeboah J.")]
    for mday,cmday,pid,nome in targets:
        day=next((x for x in cal if int(x.get("matchDay") or 0)==mday),None)
        if not day: print(nome,": giornata non disponibile");continue
        found=False
        for match in day.get("matches",[]):
            h,a=int(match["tIdH"]),int(match["tIdA"])
            url=f"https://apileague.fantacalcio.it/gaming/v1/teamLineup/{live.COMPETITION_ID}/{mday}/{cmday}/{h}/{a}"
            try: d=live.fetch_json(url,app,token)
            except Exception as e:
                print("Errore lettura partita:",type(e).__name__);continue
            for t in ("home","away"):
                side=d.get(t) or {}
                for p in (side.get("starts") or [])+(side.get("bench") or []):
                    if isinstance(p,dict) and str(p.get("pid"))==str(pid):
                        print(f"{nome} | Borrachos {mday} | Serie A {cmday} | PID {pid}")
                        print("CODICE:",p.get("b","non disponibile"))
                        print("Voto:",p.get("scr"),"Fantavoto:",p.get("cscr"))
                        found=True
        if not found: print(f"{nome}: non presente nelle formazioni recuperate per la giornata {mday}")
if __name__=="__main__":run()
