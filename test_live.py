import json
import os
import urllib.request
import urllib.error

# Test SOLO LETTURA per il futuro LIVE BORRACHOS.
# Non modifica formazioni e non invia POST.
COMPETITION_ID = 324951
DIVISION = "A"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CREDENTIALS_FILE = os.path.abspath(os.path.join(BASE_DIR, "..", "PRIVATO BORRACHOS", "DATI_FANTACALCIO.txt"))
OUTPUT_FILE = os.path.join(BASE_DIR, "test_formazione_live.json")
URL = "https://apileague.fantacalcio.it/gaming/v1/teamLineup/visualizza/A/324951"

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

def main():
    app_key, bearer = read_credentials(CREDENTIALS_FILE)
    req = urllib.request.Request(URL, headers={
        "App_key": app_key,
        "Authorization": "Bearer " + bearer,
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0",
    }, method="GET")
    print("LIVE BORRACHOS - test formazione (sola lettura)")
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {e.code}: {body}") from None
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    dto = payload.get("teamLineupDto") if isinstance(payload, dict) else None
    info = payload.get("lineUpInfo") if isinstance(payload, dict) else None
    print("OK risposta ricevuta.")
    if isinstance(dto, dict):
        print("mday:", dto.get("mday"), "| cmday:", dto.get("cmday"), "| modulo:", dto.get("mdl"))
        print("titolari:", len(dto.get("starts") or []), "| panchina:", len(dto.get("bench") or []))
    else:
        print("teamLineupDto non presente o formato differente.")
    print("lineUpInfo presente:", info is not None)
    print("Salvato:", OUTPUT_FILE)

if __name__ == "__main__":
    main()
