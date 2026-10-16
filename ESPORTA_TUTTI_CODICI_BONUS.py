# ACCESSI AUTOMATICI FANTACALCIO DISABILITATI IL 16/10/2026.
# Diagnostica storica conservata, ma esecuzione vietata senza autorizzazione.
print('BLOCCATO: questo script effettuava accessi automatici a Fantacalcio.')
raise SystemExit(1)

"""Esporta tutti i codici bonus/malus delle giornate concluse: sola lettura API.
Crea soltanto CSV locali per Excel italiano; non modifica il sito ne' i dati LIVE.
"""
import csv
import json
import os
from datetime import datetime
import aggiorna_live as live

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "CODICI_BONUS_TUTTE_GIORNATE.csv")
LOG = os.path.join(ROOT, "CODICI_BONUS_ESITI.csv")

def main():
    app, bearer = live.read_credentials(live.CREDENTIALS_FILE)
    calendar = live.unwrap_list(live.fetch_json(live.CALENDAR_URL, app, bearer))
    mine = live.fetch_json(live.MY_LINEUP_URL, app, bearer)
    dto = mine.get("teamLineupDto") or (mine.get("data") or {}).get("teamLineupDto") or {}
    current = int(dto.get("mday") or 0)
    current_a = int(dto.get("cmday") or 0)
    if current < 1 or current_a < 1:
        raise RuntimeError("Non posso determinare la giornata corrente")
    offset = current_a - current
    names_path = os.path.join(ROOT,"live_names.json")
    names = {}
    if os.path.isfile(names_path):
        with open(names_path,encoding="utf-8") as f:
            names = json.load(f).get("nomi",{})
    records, report = [], []
    days = sorted((x for x in calendar if 0 < int(x.get("matchDay") or 0) < current),key=lambda x:int(x.get("matchDay") or 0))
    print("Giornate concluse nel calendario:", len(days))
    print("Nota: giornata Serie A calcolata con offset corrente",offset,"; verificare le giornate con calendario irregolare.")
    for day in days:
        mday=int(day["matchDay"])
        cmday=mday+offset
        matches=day.get("matches") or []
        good=0
        print("Borrachos",mday,"/ Serie A presunta",cmday,":",len(matches),"partite")
        for match in matches:
            h,a=int(match["tIdH"]),int(match["tIdA"])
            url=f"https://apileague.fantacalcio.it/gaming/v1/teamLineup/{live.COMPETITION_ID}/{mday}/{cmday}/{h}/{a}"
            try:
                detail=live.fetch_json(url,app,bearer)
                if not detail.get("cal"):
                    report.append([mday,cmday,h,a,"NON CALCOLATA"]);continue
                good+=1
                report.append([mday,cmday,h,a,"OK"])
                for side,tid in (("home",h),("away",a)):
                    team=detail.get(side) or {}
                    for group,key in (("Titolare","starts"),("Panchina","bench")):
                        for p in team.get(key) or []:
                            if not isinstance(p,dict) or p.get("pid") is None:continue
                            raw=p.get("b")
                            if not isinstance(raw,str):continue
                            values=raw.split(";")
                            if len(values)!=16:
                                report.append([mday,cmday,h,a,"SEQUENZA DI LUNGHEZZA "+str(len(values))]);continue
                            pid=str(p["pid"])
                            active="; ".join(str(i)+"="+v for i,v in enumerate(values) if v.strip() not in ("","0","0.0"))
                            records.append([mday,cmday,tid,group,pid,names.get(pid) or p.get("plyr") or p.get("nome") or "Giocatore "+pid,p.get("scr"),p.get("cscr"),raw,active,*values])
            except Exception as exc:
                report.append([mday,cmday,h,a,"ERRORE "+str(exc).split(":")[0]])
        print("  Partite calcolate recuperate:",good,"/",len(matches))
    headers=["Giornata Borrachos","Giornata Serie A presunta","ID fantasquadra","Schieramento","PID","Giocatore","Voto","Fantavoto","Codice 16 valori","Indici non zero"]+["Indice "+str(i)+" (posizione "+str(i+1)+")" for i in range(16)]
    with open(OUT,"w",encoding="utf-8-sig",newline="") as f:
        w=csv.writer(f,delimiter=";");w.writerow(headers);w.writerows(records)
    with open(LOG,"w",encoding="utf-8-sig",newline="") as f:
        w=csv.writer(f,delimiter=";");w.writerow(["Giornata Borrachos","Giornata Serie A presunta","ID casa","ID trasferta","Esito"]);w.writerows(report)
    print("Giocatori esportati:",len(records))
    print("CREATO:",OUT)
    print("CREATO:",LOG)
    print("Controllare il file ESITI: errori, partite non calcolate e giornate Serie A presunte.")
if __name__=="__main__":main()
