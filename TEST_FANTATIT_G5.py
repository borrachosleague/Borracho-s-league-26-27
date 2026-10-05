import json
import os
import urllib.request
import urllib.error
from pprint import pprint

# TEST FANTATIT - BORRACHOS LEAGUE
# Sola lettura: usa esclusivamente GET e NON modifica formazioni.
COMPETITION_ID = 324951
DIVISION = "A"
GIORNATA_SERIE_A = 5

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CREDENTIALS_FILE = os.path.abspath(os.path.join(BASE_DIR, "..", "PRIVATO BORRACHOS", "DATI_FANTACALCIO.txt"))

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

def walk_players(obj, out, path=""):
    """Raccoglie ricorsivamente oggetti che sembrano riferirsi a un giocatore."""
    if isinstance(obj, dict):
        if obj.get("pid") is not None:
            out.append({
                "path": path or "$",
                "pid": obj.get("pid"),
                "nome": obj.get("plyr") or obj.get("nome") or obj.get("name"),
                "m": obj.get("m"),
                "scr": obj.get("scr"),
                "cscr": obj.get("cscr"),
                "ptype": obj.get("ptype"),
                "bonus": obj.get("b"),
                "raw": obj,
            })
        for k, v in obj.items():
            walk_players(v, out, f"{path}.{k}" if path else k)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            walk_players(v, out, f"{path}[{i}]")

def main():
    print("============================================")
    print(" TEST FANTATIT - BORRACHOS LEAGUE")
    print(" Giornata Serie A:", GIORNATA_SERIE_A)
    print("============================================")
    app_key, bearer = read_credentials(CREDENTIALS_FILE)

    mine = fetch_json(MY_LINEUP_URL, app_key, bearer)
    dto = mine.get("teamLineupDto") or (mine.get("data") or {}).get("teamLineupDto") or {}
    current_mday = int(dto.get("mday") or 0)
    current_cmday = int(dto.get("cmday") or 0)
    print(f"API corrente: giornata Borrachos={current_mday}, Serie A={current_cmday}")

    teams = unwrap_list(fetch_json(TEAMS_URL, app_key, bearer))
    calendar = unwrap_list(fetch_json(CALENDAR_URL, app_key, bearer))
    team_names = {int(t["id"]): str(t.get("n") or t["id"]).strip() for t in teams}

    # Trova nel calendario la giornata Borrachos associata alla G5 Serie A.
    # Prima prova campi espliciti; se non presenti, stampa le chiavi per diagnosi.
    candidates = []
    for d in calendar:
        vals = []
        for key in ("competitionMatchDay", "cmday", "serieAMatchDay", "realMatchDay"):
            try:
                if d.get(key) is not None:
                    vals.append(int(d.get(key)))
            except Exception:
                pass
        if GIORNATA_SERIE_A in vals:
            candidates.append(d)

    if candidates:
        day = candidates[0]
        mday = int(day.get("matchDay"))
    else:
        # Nel campionato Borrachos normalmente il calendario lega procede in parallelo.
        # Usiamo G5 come primo tentativo e, se l'endpoint non la accetta, l'errore sarà esplicito.
        mday = GIORNATA_SERIE_A
        day = next((d for d in calendar if int(d.get("matchDay", 0) or 0) == mday), None)

    if not day:
        print("\nNon trovo la giornata nel calendario. Prime chiavi disponibili:")
        for d in calendar[:3]:
            print(d)
        raise RuntimeError("Giornata non individuata.")

    print(f"Test: giornata Borrachos={mday}, giornata Serie A={GIORNATA_SERIE_A}")
    print(f"Partite trovate nel calendario: {len(day.get('matches', []))}")

    raw_dump = {
        "competitionId": COMPETITION_ID,
        "mday": mday,
        "cmday": GIORNATA_SERIE_A,
        "partite": []
    }

    for nmatch, match in enumerate(day.get("matches", []), 1):
        hid, aid = int(match["tIdH"]), int(match["tIdA"])
        hn, an = team_names.get(hid, str(hid)), team_names.get(aid, str(aid))
        url = (
            "https://apileague.fantacalcio.it/gaming/v1/teamLineup/"
            f"{COMPETITION_ID}/{mday}/{GIORNATA_SERIE_A}/{hid}/{aid}"
        )
        detail = fetch_json(url, app_key, bearer)
        print("\n" + "="*72)
        print(f"PARTITA {nmatch}: {hn} - {an} | cal={detail.get('cal')}")
        print("="*72)

        raw_dump["partite"].append({
            "casa": hn, "trasferta": an, "detail": detail
        })

        for side_key, team_name in (("home", hn), ("away", an)):
            sd = detail.get(side_key) or {}
            starts = sd.get("starts") or []
            bench = sd.get("bench") or []
            lply = sd.get("lply")

            print(f"\n--- {team_name} ---")
            print(f"starts={len(starts)} | bench={len(bench)} | lply tipo={type(lply).__name__}")
            print("STARTS pid:", [p.get("pid") for p in starts if isinstance(p, dict)])

            found = []
            walk_players(lply, found, "lply")
            print(f"Giocatori trovati ricorsivamente dentro lply: {len(found)}")
            for x in found:
                print(
                    f"  {x['path']} | pid={x['pid']} | nome={x['nome']} | "
                    f"m={x['m']} | scr={x['scr']} | cscr={x['cscr']} | ptype={x['ptype']}"
                )

            # Mostra lply completo: è il dato decisivo per capire gli effettivi.
            print("LPLY RAW:")
            print(json.dumps(lply, ensure_ascii=False, indent=2))

    out = os.path.join(BASE_DIR, "TEST_FANTATIT_G5_RAW.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(raw_dump, f, ensure_ascii=False, indent=2)
    print("\n============================================")
    print("TEST TERMINATO - nessun dato modificato.")
    print("Dump completo salvato in:")
    print(out)
    print("============================================")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("\nERRORE:", e)
        input("Premi INVIO per chiudere...")
