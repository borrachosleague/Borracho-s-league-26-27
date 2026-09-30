import json
import os
import urllib.request
import urllib.error
from datetime import datetime

# LIVE BORRACHOS - sola lettura.
# Non invia né modifica formazioni: usa esclusivamente GET.
COMPETITION_ID = 324951
DIVISION = "A"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CREDENTIALS_FILE = os.path.abspath(os.path.join(BASE_DIR, "..", "PRIVATO BORRACHOS", "DATI_FANTACALCIO.txt"))
OUTPUT_FILE = os.path.join(BASE_DIR, "live.json")
DATA_FILE = os.path.join(BASE_DIR, "dati.json")

TEAMS_URL = (
    "https://apileague.fantacalcio.it/onboarding/v1/league/competition/"
    f"teams?page=1&pageSize=50&competitionId={COMPETITION_ID}"
)
CALENDAR_URL = (
    "https://apileague.fantacalcio.it/onboarding/v1/league/competition/"
    f"calendar/{COMPETITION_ID}"
)
MY_LINEUP_URL = (
    "https://apileague.fantacalcio.it/gaming/v1/teamLineup/visualizza/"
    f"{DIVISION}/{COMPETITION_ID}"
)

def read_credentials(path):
    if not os.path.exists(path):
        raise RuntimeError(f"File credenziali non trovato: {path}")
    values = {}
    with open(path, "r", encoding="utf-8-sig") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            values[key.strip().upper()] = value.strip().strip('"').strip("'")
    app_key = values.get("APP_KEY", "")
    bearer = values.get("BEARER", "")
    if bearer.lower().startswith("bearer "):
        bearer = bearer[7:].strip()
    if not app_key or not bearer:
        raise RuntimeError("Nel file credenziali servono APP_KEY e BEARER.")
    return app_key, bearer

def fetch_json(url, app_key, bearer):
    req = urllib.request.Request(url, headers={
        "App_key": app_key,
        "Authorization": "Bearer " + bearer,
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0",
    }, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {e.code}: {body}") from None

def unwrap_list(payload):
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("data", "items", "result"):
            if isinstance(payload.get(key), list):
                return payload[key]
    raise RuntimeError("Formato API Fantacalcio inatteso.")

PLAYER_NAMES = {}

def player_row(p):
    pid = p.get("pid")
    return {
        "pid": pid,
        "nome": PLAYER_NAMES.get(str(pid), ""),

        "m": p.get("m"),
        "scr": p.get("scr"),
        "cscr": p.get("cscr"),
        "ptype": p.get("ptype"),
        "bonus": p.get("b"),
    }

def side(side_data, name, tid):
    if not isinstance(side_data, dict):
        return {
            "id": tid, "nome": name, "consegnata": False,
            "modulo": None, "totale": None, "punti": None,
            "titolari": [], "panchina": [], "lply": None,
        }
    starts = side_data.get("starts") or []
    bench = side_data.get("bench") or []
    delivered = bool(side_data.get("act")) or bool(starts)
    return {
        "id": tid,
        "nome": name,
        "consegnata": delivered,
        "modulo": side_data.get("mdl") or side_data.get("nmdl"),
        "totale": side_data.get("tot"),
        "punti": side_data.get("points"),
        "titolari": [player_row(p) for p in starts if isinstance(p, dict)],
        "panchina": [player_row(p) for p in bench if isinstance(p, dict)],
        # Conserviamo il payload originale: durante una giornata live
        # verificheremo esattamente struttura e significato dei campi.
        "lply": side_data.get("lply"),
    }

def choose_day(calendar, mday):
    for d in calendar:
        try:
            if int(d.get("matchDay", 0)) == int(mday):
                return d
        except Exception:
            pass
    return None

def main():
    global PLAYER_NAMES
    print("LIVE BORRACHOS - aggiornamento")
    app_key, bearer = read_credentials(CREDENTIALS_FILE)

    # Il dettaglio formazione restituisce i pid ma non i nomi.
    # Recuperiamo la mappa pid->nome dall'endpoint visualizza, che contiene lineUpInfo.
    mine = fetch_json(MY_LINEUP_URL, app_key, bearer)
    info = mine.get("lineUpInfo") or (mine.get("data") or {}).get("lineUpInfo") or []
    if isinstance(info, dict):
        info = info.get("players") or info.get("items") or info.get("data") or []
    if isinstance(info, list):
        for p in info:
            if isinstance(p, dict) and p.get("pid") is not None:
                nome = p.get("plyr") or p.get("nome") or p.get("name")
                if nome:
                    PLAYER_NAMES[str(p.get("pid"))] = str(nome).strip()

    teams = unwrap_list(fetch_json(TEAMS_URL, app_key, bearer))
    calendar = unwrap_list(fetch_json(CALENDAR_URL, app_key, bearer))
    team_names = {int(t["id"]): str(t.get("n") or t["id"]).strip() for t in teams}

    dto = mine.get("teamLineupDto") or (mine.get("data") or {}).get("teamLineupDto") or {}
    if not dto.get("mday") or not dto.get("cmday"):
        raise RuntimeError("Fantacalcio non ha restituito mday/cmday.")
    mday, cmday = int(dto["mday"]), int(dto["cmday"])
    day = choose_day(calendar, mday)
    if not day:
        raise RuntimeError(f"Giornata Borrachos {mday} non trovata.")

    output = {
        "versione": 1,
        "aggiornato_il": datetime.now().astimezone().isoformat(timespec="seconds"),
        "idcomp": COMPETITION_ID,
        "giornata_borrachos": mday,
        "giornata_serie_a": cmday,
        "stato": "attesa",
        "formazioni_consegnate": 0,
        "partite": [],
    }

    any_live = False
    all_calculated = True
    for match in day.get("matches", []):
        hid, aid = int(match["tIdH"]), int(match["tIdA"])
        hn, an = team_names.get(hid, str(hid)), team_names.get(aid, str(aid))
        url = (
            "https://apileague.fantacalcio.it/gaming/v1/teamLineup/"
            f"{COMPETITION_ID}/{mday}/{cmday}/{hid}/{aid}"
        )
        print(f"- {hn} - {an} ... ", end="", flush=True)
        detail = fetch_json(url, app_key, bearer)
        home = side(detail.get("home"), hn, hid)
        away = side(detail.get("away"), an, aid)
        output["formazioni_consegnate"] += int(home["consegnata"]) + int(away["consegnata"])

        calculated = bool(detail.get("cal"))
        all_calculated = all_calculated and calculated
        if home["lply"] is not None or away["lply"] is not None:
            any_live = True

        output["partite"].append({
            "casa": home,
            "trasferta": away,
            "calcolata": calculated,
            "segno": detail.get("sign"),
            "risultato": detail.get("res"),
            "risultato_reale": detail.get("resr"),
        })
        print("OK")

    if all_calculated and output["partite"]:
        output["stato"] = "terminata"
    elif any_live:
        output["stato"] = "live"
    else:
        output["stato"] = "attesa"

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"Formazioni consegnate: {output['formazioni_consegnate']}/10")
    print(f"Stato: {output['stato'].upper()}")
    print(f"Salvato: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
