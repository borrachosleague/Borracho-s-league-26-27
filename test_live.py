import json
import os
import urllib.request
import urllib.error

# Test SOLO LETTURA: recupera il dettaglio di tutti i 5 incontri
# della giornata Borrachos usando l'endpoint che restituisce entrambe le formazioni.
COMPETITION_ID = 324951
DIVISION = "A"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CREDENTIALS_FILE = os.path.abspath(os.path.join(BASE_DIR, "..", "PRIVATO BORRACHOS", "DATI_FANTACALCIO.txt"))
OUTPUT_FILE = os.path.join(BASE_DIR, "test_live_giornata.json")
TEAMS_URL = f"https://apileague.fantacalcio.it/onboarding/v1/league/competition/teams?page=1&pageSize=50&competitionId={COMPETITION_ID}"
CALENDAR_URL = f"https://apileague.fantacalcio.it/onboarding/v1/league/competition/calendar/{COMPETITION_ID}"
MY_LINEUP_URL = f"https://apileague.fantacalcio.it/gaming/v1/teamLineup/visualizza/{DIVISION}/{COMPETITION_ID}"

def read_credentials(path):
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
    raise RuntimeError("Formato API inatteso.")

def main():
    app_key, bearer = read_credentials(CREDENTIALS_FILE)
    mine = fetch_json(MY_LINEUP_URL, app_key, bearer)
    dto = mine.get("teamLineupDto") or {}
    mday = int(dto["mday"])
    cmday = int(dto["cmday"])
    print(f"LIVE BORRACHOS - mday {mday}, Serie A {cmday}")

    teams = unwrap_list(fetch_json(TEAMS_URL, app_key, bearer))
    team_names = {int(t["id"]): str(t.get("n") or t["id"]) for t in teams}
    calendar = unwrap_list(fetch_json(CALENDAR_URL, app_key, bearer))
    day = next((d for d in calendar if int(d.get("matchDay", 0)) == mday), None)
    if not day:
        raise RuntimeError(f"Giornata Borrachos {mday} non trovata nel calendario.")

    output = {"idcomp": COMPETITION_ID, "mday": mday, "cmday": cmday, "partite": []}
    for match in day.get("matches", []):
        home = int(match["tIdH"])
        away = int(match["tIdA"])
        url = f"https://apileague.fantacalcio.it/gaming/v1/teamLineup/{COMPETITION_ID}/{mday}/{cmday}/{home}/{away}"
        print(f"- {team_names.get(home, home)} - {team_names.get(away, away)} ... ", end="", flush=True)
        detail = fetch_json(url, app_key, bearer)
        output["partite"].append({
            "home_id": home,
            "home": team_names.get(home, str(home)),
            "away_id": away,
            "away": team_names.get(away, str(away)),
            "detail": detail,
        })
        print("OK")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"Salvato: {OUTPUT_FILE}")
    print(f"Partite recuperate: {len(output['partite'])}")

if __name__ == "__main__":
    main()
