"""Trova un esempio per ciascuna posizione bonus ancora da identificare.
Sola lettura API; nessuna modifica ai dati o alle formazioni.
"""
import json
import os
import aggiorna_live as live

TARGETS = [4, 5, 8, 9, 10, 11, 12, 13, 14]
def main():
    app, token = live.read_credentials(live.CREDENTIALS_FILE)
    cal = live.unwrap_list(live.fetch_json(live.CALENDAR_URL,app,token))
    mine = live.fetch_json(live.MY_LINEUP_URL,app,token)
    dto = mine.get("teamLineupDto") or (mine.get("data") or {}).get("teamLineupDto") or {}
    current=int(dto.get("mday") or 0); offset=int(dto.get("cmday") or 0)-current
    names={}
    f=os.path.join(live.BASE_DIR,"live_names.json")
    if os.path.isfile(f):
        with open(f,encoding="utf-8") as fp: names=json.load(fp).get("nomi",{})
    examples={}
    for d in sorted(cal,key=lambda x:int(x.get("matchDay") or 0),reverse=True):
        mday=int(d.get("matchDay") or 0)
        if not 0<mday<current: continue
        cmday=mday+offset
        for match in d.get("matches") or []:
            h,a=int(match["tIdH"]),int(match["tIdA"])
            url=f"https://apileague.fantacalcio.it/gaming/v1/teamLineup/{live.COMPETITION_ID}/{mday}/{cmday}/{h}/{a}"
            try: detail=live.fetch_json(url,app,token)
            except Exception: continue
            if not detail.get("cal"):continue
            for t in ("home","away"):
                side=detail.get(t) or {}
                for group in ("starts","bench"):
                    for p in side.get(group) or []:
                        if not isinstance(p,dict) or not isinstance(p.get("b"),str):continue
                        vals=p["b"].split(";")
                        if len(vals)!=16:continue
                        pid=str(p.get("pid"))
                        for i in TARGETS:
                            if i not in examples and vals[i].strip() in ("1","1.0"):
                                examples[i]=(mday,cmday,pid,names.get(pid) or p.get("nome") or "Giocatore "+pid,p.get("scr"),p.get("cscr"),p["b"])
        if len(examples)==len(TARGETS):break
    print("POSIZIONI DA VERIFICARE (numerate da 1):")
    for i in TARGETS:
        x=examples.get(i)
        if x:
            m,c,pid,n,v,fv,code=x
            print(f"POSIZIONE {i+1}: {n} (PID {pid}), Borrachos {m}, Serie A PRESUNTA {c}, voto {v}, FV {fv}")
            print("  CODICE:",code)
        else:print(f"POSIZIONE {i+1}: nessun valore 1 trovato nelle giornate consultate")
    print("La giornata Serie A e' stimata dall'offset attuale: verificare eventuali turni irregolari.")
if __name__=="__main__":main()
