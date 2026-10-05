import json
import openpyxl
import os
import sys
import urllib.request
import urllib.error
from collections import defaultdict

# === CONFIGURAZIONE ===
COMPETITION_ID = 324951
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = BASE_DIR
CREDENTIALS_FILE = os.path.abspath(os.path.join(BASE_DIR, "..", "PRIVATO BORRACHOS", "DATI_FANTACALCIO.txt"))
BORRACHOS_FILE = os.path.join(DATA_DIR, "BORRACHOSLEAGUE 26.27.xlsm")
OUTPUT_FILE = os.path.join(BASE_DIR, "dati.json")
STAT_FILE = os.path.join(DATA_DIR, "nuovo statistiche.xlsm")

TEAMS_URL = (
    "https://apileague.fantacalcio.it/onboarding/v1/league/competition/"
    f"teams?page=1&pageSize=50&competitionId={COMPETITION_ID}"
)
CALENDAR_URL = (
    "https://apileague.fantacalcio.it/onboarding/v1/league/competition/"
    f"calendar/{COMPETITION_ID}"
)
PLAYERS_URL = "https://apileague.fantacalcio.it/onboarding/v1/league/players"

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
        raise RuntimeError("Nel file credenziali servono APP_KEY=... e BEARER=...")
    return app_key, bearer

def fetch_json(url, app_key, bearer):
    req = urllib.request.Request(
        url,
        headers={
            "App_key": app_key,
            "Authorization": "Bearer " + bearer,
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0",
        },
        method="GET",
    )
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

def parse_result(value):
    try:
        a, b = str(value).split("-", 1)
        return int(a.strip()), int(b.strip())
    except Exception:
        return 0, 0

for _label, _path in [("BORRACHOSLEAGUE 26.27.xlsm", BORRACHOS_FILE), ("nuovo statistiche.xlsm", STAT_FILE)]:
    if not os.path.exists(_path):
        raise RuntimeError(f"{_label} non trovato: {_path}")

print("Aggiornamento Borracho's League...")
app_key, bearer = read_credentials(CREDENTIALS_FILE)
print("Scarico squadre, classifica e calendario da Fantacalcio...")
teams_api = unwrap_list(fetch_json(TEAMS_URL, app_key, bearer))
calendar_api = unwrap_list(fetch_json(CALENDAR_URL, app_key, bearer))

team_names = {int(t["id"]): str(t["n"]).strip() for t in teams_api}

# Rose ufficiali della lega: il campo "cal" di ogni team contiene gli ID
# Fantacalcio dei 25 giocatori, separati da ";". Questa è la fonte corretta
# per avere sempre tutte le 10 rose, anche per chi non ha ancora statistiche.
league_players_payload = fetch_json(PLAYERS_URL, app_key, bearer)
league_players = league_players_payload.get("players", []) if isinstance(league_players_payload, dict) else []
league_player_by_id = {
    int(p["id"]): p for p in league_players
    if isinstance(p, dict) and p.get("id") is not None
}
roster_ufficiali = []
for t in teams_api:
    squadra = str(t.get("n") or "").strip()
    raw_ids = str(t.get("cal") or "").strip()
    ids = [int(x) for x in raw_ids.split(";") if x.strip().isdigit()]
    for pid in ids:
        p = league_player_by_id.get(pid, {})
        nome = str(p.get("name") or "").strip()
        if nome:
            roster_ufficiali.append({"id": pid, "nome": nome, "squadra": squadra})
print(f"Rose ufficiali API: {len(roster_ufficiali)} giocatori")
stats_api = {
    tid: {
        "nome": name, "g": 0, "v": 0, "n": 0, "p": 0,
        "gf": 0, "gs": 0, "dr": 0, "pt": 0, "pt_totali": 0.0
    }
    for tid, name in team_names.items()
}
risultati = []

for day in calendar_api:
    giornata = int(day.get("matchDay", 0))
    calculated = bool(day.get("calculated", False))
    partite = []
    for match in day.get("matches", []):
        hid, aid = int(match["tIdH"]), int(match["tIdA"])
        home, away = team_names[hid], team_names[aid]
        pt_h, pt_a = float(match.get("ptH") or 0), float(match.get("ptA") or 0)
        result = str(match.get("result", "-"))
        gh, ga = parse_result(result) if calculated and result != "-" else (0, 0)

        if calculated and result != "-":
            sh, sa = int(match.get("standingPtH") or 0), int(match.get("standingPtA") or 0)
            h, a = stats_api[hid], stats_api[aid]
            h["g"] += 1; a["g"] += 1
            h["gf"] += gh; h["gs"] += ga
            a["gf"] += ga; a["gs"] += gh
            h["pt"] += sh; a["pt"] += sa
            h["pt_totali"] += pt_h; a["pt_totali"] += pt_a
            if sh > sa:
                h["v"] += 1; a["p"] += 1
            elif sa > sh:
                a["v"] += 1; h["p"] += 1
            else:
                h["n"] += 1; a["n"] += 1

        partite.append({
            "casa": home,
            "pt_casa": pt_h if calculated else 0,
            "gol_casa": gh,
            "gol_trasferta": ga,
            "pt_trasferta": pt_a if calculated else 0,
            "trasferta": away
        })
    risultati.append({"giornata": giornata, "partite": partite})

for s in stats_api.values():
    s["dr"] = s["gf"] - s["gs"]
    s["pt_totali"] = round(s["pt_totali"], 2)

# Classifica Borracho's League:
# punti > fantapunti > differenza reti > gol fatti
squadre = sorted(
    stats_api.values(),
    key=lambda s: (s["pt"], s["pt_totali"], s["dr"], s["gf"]),
    reverse=True
)
risultati.sort(key=lambda x: x["giornata"])

# === 1.5 STATISTICHE SQUADRE ===
wb_stat = openpyxl.load_workbook(STAT_FILE, data_only=True)
ws_stat = wb_stat.worksheets[0]

stat_squadre = []
colonne_stat = []

# Leggi intestazioni (riga 3, colonne D-Z = 4-26)
# Leggi intestazioni (riga 3, colonne D-AB = 4-28)
for c in range(4, 29):
    val = ws_stat.cell(row=3, column=c).value
    if val is not None:
        colonne_stat.append(str(val).strip())
    else:
        colonne_stat.append("")

# Se le intestazioni di AA/AB sono vuote, assegna etichette
if not colonne_stat[23]:
    colonne_stat[23] = "pt max"
if not colonne_stat[24]:
    colonne_stat[24] = "pt min"

# Leggi dati (righe 5-14)
for r in range(5, 15):
    nome = ws_stat.cell(row=r, column=2).value
    if nome is None or not str(nome).strip():
        continue
    dati = {}
    for c in range(4, 29):
        key = colonne_stat[c - 4]
        val = ws_stat.cell(row=r, column=c).value
        try:
            dati[key] = float(str(val).replace(",", ".")) if val is not None else 0
        except (ValueError, TypeError):
            dati[key] = 0
    stat_squadre.append({"nome": str(nome).strip(), "dati": dati})   
  


# === 1.6 CLASSIFICA F1 E BATTLE ROYALE (Foglio4) ===
ws_f1 = wb_stat["Foglio4"]

f1_scores = {}
for r in range(4, 14):
    nome = ws_f1.cell(row=r, column=1).value
    val = ws_f1.cell(row=r, column=2).value
    if nome is not None and str(nome).strip():
        try:
            f1_scores[str(nome).strip()] = float(str(val).replace(",", ".")) if val is not None else 0
        except (ValueError, TypeError):
            f1_scores[str(nome).strip()] = 0

br_scores = {}
for r in range(19, 29):
    nome = ws_f1.cell(row=r, column=1).value
    val = ws_f1.cell(row=r, column=2).value
    if nome is not None and str(nome).strip():
        try:
            br_scores[str(nome).strip()] = float(str(val).replace(",", ".")) if val is not None else 0
        except (ValueError, TypeError):
            br_scores[str(nome).strip()] = 0

for sq in stat_squadre:
    sq["dati"]["f1"] = f1_scores.get(sq["nome"], 0)
    sq["dati"]["br"] = br_scores.get(sq["nome"], 0)

colonne_stat.append("f1")
colonne_stat.append("br")

wb_stat.close()   
# === 2. GIOCATORI (INSER DATA) ===
wb_borr = openpyxl.load_workbook(BORRACHOS_FILE, read_only=True, data_only=True)
ws_data = wb_borr["INSER DATA"]

last_row = 1
for row in ws_data.iter_rows(min_row=2, max_col=5, values_only=True):
    if row[4] is not None and str(row[4]).strip():
        last_row += 1
    else:
        break

giocatori = defaultdict(lambda: {
    "voti": [], "fvoti": [], "gol": 0, "assist": 0,
    "golsub": 0, "rigseg": 0, "rigsba": 0, "rigpar": 0,
    "amm": 0, "esp": 0, "autogol": 0, "cleansheet": 0,
    "squadra": "", "ruolo": ""
})
# Statistiche TOTALI dei giocatori: tutte le prestazioni, indipendentemente dalla formazione schierata
giocatori_totali = defaultdict(lambda: {
    "voti": [], "fvoti": [], "gol": 0, "assist": 0,
    "golsub": 0, "rigseg": 0, "rigsba": 0, "rigpar": 0,
    "amm": 0, "esp": 0, "autogol": 0, "cleansheet": 0,
    "squadra": "", "ruolo": ""
})

# Gol per reparto per squadra
gol_reparto = defaultdict(lambda: {"d": 0, "c": 0, "a": 0})   

for row in ws_data.iter_rows(min_row=2, max_row=last_row + 1, values_only=True):
    nome = row[4]
    if nome is None:
        continue
    nome = str(nome).strip()
    if not nome:
        continue

    fantasquadra = row[17]
    if fantasquadra is None or not str(fantasquadra).strip():
        continue

    if nome not in giocatori:
        giocatori[nome] = {
            "voti": [], "fvoti": [], "gol": 0, "assist": 0,
            "golsub": 0, "rigseg": 0, "rigsba": 0, "rigpar": 0,
            "amm": 0, "esp": 0, "autogol": 0, "cleansheet": 0,
            "squadra": str(fantasquadra).strip(), "ruolo": ""
        }

    g = giocatori[nome]
    g["squadra"] = str(fantasquadra).strip()

    ruolo = row[3]
    g["ruolo"] = str(ruolo).strip().lower() if ruolo is not None else ""

    # TOTALI: usa Voto (F) e fanta voto generale (V), senza filtro FantaTit
    gt = giocatori_totali[nome]
    gt["squadra"] = str(fantasquadra).strip()
    gt["ruolo"] = g["ruolo"]

    voto_tot = row[5]
    if voto_tot is not None:
        try:
            v = float(str(voto_tot).replace(",", "."))
            if v > 0:
                gt["voti"].append(v)
        except (ValueError, TypeError):
            pass

    fvoto_tot = row[21]
    if fvoto_tot is not None:
        try:
            fv = float(str(fvoto_tot).replace(",", "."))
            if fv > 0:
                gt["fvoti"].append(fv)
        except (ValueError, TypeError):
            pass

    for idx, chiave in [
        (18, "gol"), (14, "assist"), (7, "golsub"), (10, "rigseg"),
        (9, "rigsba"), (8, "rigpar"), (11, "autogol"), (12, "amm"),
        (13, "esp"), (16, "cleansheet")
    ]:
        val_tot = row[idx]
        if val_tot is not None:
            try:
                gt[chiave] += int(float(str(val_tot).replace(",", ".")))
            except (ValueError, TypeError):
                pass

    tit = row[19]
    try:
        tit_val = int(float(str(tit).replace(",", "."))) if tit is not None else 0
    except (ValueError, TypeError):
        tit_val = 0

    if tit_val != 1:
        continue

    voto = row[5]
    if voto is not None:
        try:
            v = float(str(voto).replace(",", "."))
            if v > 0:
                g["voti"].append(v)
        except (ValueError, TypeError):
            pass

    fvoto = row[20]
    if fvoto is not None:
        try:
            fv = float(str(fvoto).replace(",", "."))
            if fv > 0:
                g["fvoti"].append(fv)
        except (ValueError, TypeError):
            pass

    val = row[18]
    if val is not None:
        try: g["gol"] += int(float(str(val).replace(",", ".")))
        except: pass
    # Gol per reparto
    if val is not None:
        try:
            goli = int(float(str(val).replace(",", ".")))
            if goli > 0:
                ruolo_key = g["ruolo"][:1].lower() if g["ruolo"] else ""
                if ruolo_key in ("d", "c", "a"):
                    gol_reparto[g["squadra"]][ruolo_key] += goli
        except: pass   
    val = row[14]
    if val is not None:
        try: g["assist"] += int(float(str(val).replace(",", ".")))
        except: pass

    val = row[7]
    if val is not None:
        try: g["golsub"] += int(float(str(val).replace(",", ".")))
        except: pass

    val = row[10]
    if val is not None:
        try: g["rigseg"] += int(float(str(val).replace(",", ".")))
        except: pass

    val = row[9]
    if val is not None:
        try: g["rigsba"] += int(float(str(val).replace(",", ".")))
        except: pass

    val = row[8]
    if val is not None:
        try: g["rigpar"] += int(float(str(val).replace(",", ".")))
        except: pass

    val = row[11]
    if val is not None:
        try: g["autogol"] += int(float(str(val).replace(",", ".")))
        except: pass

    val = row[12]
    if val is not None:
        try: g["amm"] += int(float(str(val).replace(",", ".")))
        except: pass

    val = row[13]
    if val is not None:
        try: g["esp"] += int(float(str(val).replace(",", ".")))
        except: pass

    val = row[16]
    if val is not None:
        try: g["cleansheet"] += int(float(str(val).replace(",", ".")))
        except: pass

wb_borr.close()

lista_giocatori = []
for nome, g in giocatori.items():
    n_voti = len(g["voti"])
    n_fvoti = len(g["fvoti"])
    lista_giocatori.append({
        "nome": nome,
        "squadra": g["squadra"],
        "ruolo": g["ruolo"],
        "prestit": n_voti,
        "presfvtit": n_fvoti,
        "mediavototit": round(sum(g["voti"]) / n_voti, 2) if n_voti > 0 else 0,
        "fvototit": round(sum(g["fvoti"]) / n_fvoti, 2) if n_fvoti > 0 else 0,
        "goltit": g["gol"],
        "assisttit": g["assist"],
        "golsubititit": g["golsub"],
        "cleansheettit": g["cleansheet"],
        "rigtit": g["rigseg"],
        "risgsbtit": g["rigsba"],
        "rigpartit": g["rigpar"],
        "autgoltit": g["autogol"],
        "ammtit": g["amm"],
        "esptit": g["esp"],
        "prestot": len(giocatori_totali[nome]["voti"]),
        "presfvtot": len(giocatori_totali[nome]["fvoti"]),
        "mediavototot": round(sum(giocatori_totali[nome]["voti"]) / len(giocatori_totali[nome]["voti"]), 2) if giocatori_totali[nome]["voti"] else 0,
        "fvototot": round(sum(giocatori_totali[nome]["fvoti"]) / len(giocatori_totali[nome]["fvoti"]), 2) if giocatori_totali[nome]["fvoti"] else 0,
        "goltot": giocatori_totali[nome]["gol"],
        "assisttot": giocatori_totali[nome]["assist"],
        "golsubititot": giocatori_totali[nome]["golsub"],
        "cleansheettot": giocatori_totali[nome]["cleansheet"],
        "rigtot": giocatori_totali[nome]["rigseg"],
        "risgsbtot": giocatori_totali[nome]["rigsba"],
        "rigpartot": giocatori_totali[nome]["rigpar"],
        "autgoltot": giocatori_totali[nome]["autogol"],
        "ammtot": giocatori_totali[nome]["amm"],
        "esptot": giocatori_totali[nome]["esp"]
    })
lista_giocatori.sort(key=lambda x: x["mediavototit"], reverse=True)
# Aggrega gol per reparto in stat_squadre
for sq in stat_squadre:
    nome = sq["nome"]
    if nome in gol_reparto:
        sq["dati"]["gol d"] = gol_reparto[nome]["d"]
        sq["dati"]["gol c"] = gol_reparto[nome]["c"]
        sq["dati"]["gol a"] = gol_reparto[nome]["a"]
    else:
        sq["dati"]["gol d"] = 0
        sq["dati"]["gol c"] = 0
        sq["dati"]["gol a"] = 0

# Aggiungi le colonne al menu
for c in ["gol d", "gol c", "gol a"]:
    if c not in colonne_stat:
        colonne_stat.append(c)   


# === 3.5 TUTTI I GIOCATORI SERIE A - VOTO STATISTICO FC (Alvin482) ===
# Fonte pubblica Fantacalcio: pagina statistiche con fonte "statistico".
from html.parser import HTMLParser
import re
import unicodedata

STATISTICO_URL = "https://www.fantacalcio.it/statistiche-serie-a/2026-27/statistico/assist"

def _num_fc(s, default=0.0):
    try:
        return float(str(s).strip().replace(",", "."))
    except Exception:
        return default

def _norm_nome_fc(s):
    s = unicodedata.normalize("NFD", str(s or "").lower())
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    return re.sub(r"[^a-z0-9]", "", s)

class _StatsTableParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_tr = False
        self.in_cell = False
        self.cell = []
        self.cell_meta = []
        self.row = []
        self.row_meta = []
        self.rows = []

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        attrs_dict = {str(k).lower(): str(v or "") for k, v in attrs}
        if tag == "tr":
            self.in_tr = True
            self.row = []
            self.row_meta = []
        elif self.in_tr and tag in ("td", "th"):
            self.in_cell = True
            self.cell = []
            self.cell_meta = [" ".join(attrs_dict.values())]
        elif self.in_cell:
            # Fantacalcio mostra il ruolo Classic anche tramite badge/classi/attributi:
            # conserviamo i metadati degli elementi interni alla cella.
            self.cell_meta.append(" ".join(attrs_dict.values()))

    def handle_data(self, data):
        if self.in_cell:
            self.cell.append(data)

    def handle_endtag(self, tag):
        tag = tag.lower()
        if self.in_tr and tag in ("td", "th") and self.in_cell:
            txt = " ".join("".join(self.cell).split())
            meta = " ".join(self.cell_meta)
            self.row.append(txt)
            self.row_meta.append(meta)
            self.in_cell = False
        elif tag == "tr" and self.in_tr:
            if self.row:
                self.rows.append((self.row, self.row_meta))
            self.in_tr = False

def _ruolo_classic_da_riga(cells, metas, idx_nome):
    # Prima prova il testo delle celle che precedono il nome (P/D/C/A).
    for j in range(max(0, idx_nome - 4), idx_nome):
        t = str(cells[j] or "").strip().lower()
        if t in ("p", "d", "c", "a"):
            return t

    # Poi cerca nei metadati HTML di badge/classi/data-*.
    blocco = " ".join(metas[max(0, idx_nome - 4):idx_nome + 1]).lower()
    patterns = [
        ("p", r"(?:^|[\s_\-:=])(p|por|portiere|goalkeeper)(?:$|[\s_\-;])"),
        ("d", r"(?:^|[\s_\-:=])(d|dif|difensore|defender)(?:$|[\s_\-;])"),
        ("c", r"(?:^|[\s_\-:=])(c|cen|centrocampista|midfielder)(?:$|[\s_\-;])"),
        ("a", r"(?:^|[\s_\-:=])(a|att|attaccante|forward)(?:$|[\s_\-;])"),
    ]
    for ruolo, pat in patterns:
        if re.search(pat, blocco):
            return ruolo
    return ""


QUOTAZIONI_URL = "https://www.fantacalcio.it/quotazioni-fantacalcio"

def scarica_listone_classic_fc():
    """Scarica il Listone ufficiale e restituisce ruolo Classic, QI e QA per giocatore."""
    req = urllib.request.Request(
        QUOTAZIONI_URL,
        headers={"User-Agent": "Mozilla/5.0", "Accept": "text/html,application/xhtml+xml"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            raw = response.read().decode("utf-8", errors="replace")
    except Exception as e:
        raise RuntimeError("Impossibile scaricare il Listone Fantacalcio: " + str(e))

    parser = _StatsTableParser()
    parser.feed(raw)
    listone = {}
    for cells, metas in parser.rows:
        idx_sq = None
        for i, cella in enumerate(cells):
            if re.fullmatch(r"[A-Z]{3}", cella or ""):
                idx_sq = i
                break
        # Nel Listone Classic: Nome | Sq | QI | QA | FVM/1000.
        if idx_sq is None or idx_sq < 1 or len(cells) <= idx_sq + 2:
            continue
        nome = str(cells[idx_sq - 1] or "").strip()
        if not nome or nome.lower() == "calciatore":
            continue

        ruolo = _ruolo_classic_da_riga(cells, metas, idx_sq - 1)
        qi = int(_num_fc(cells[idx_sq + 1], 0))
        qa = int(_num_fc(cells[idx_sq + 2], 0))
        # Il link del profilo Fantacalcio termina con l'ID ufficiale del giocatore,
        # es. /martinez-l/2764. Il parser conserva l'href nei metadati della cella.
        pid = None
        meta_nome = str(metas[idx_sq - 1] or "")
        m_pid = re.search(r"/(\d+)(?:[/?#\s]|$)", meta_nome)
        if m_pid:
            pid = int(m_pid.group(1))
        listone[_norm_nome_fc(nome)] = {"id": pid, "ruolo": ruolo, "qi": qi, "qa": qa}

    if len(listone) < 100:
        raise RuntimeError(
            "Listone Fantacalcio non riconosciuto correttamente "
            f"(trovati {len(listone)} giocatori). dati.json NON viene sovrascritto."
        )
    return listone

def scarica_statistiche_statistiche_fc():
    req = urllib.request.Request(
        STATISTICO_URL,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "text/html,application/xhtml+xml"
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            raw = response.read().decode("utf-8", errors="replace")
    except Exception as e:
        raise RuntimeError("Impossibile scaricare le statistiche Voto Statistico FC: " + str(e))

    parser = _StatsTableParser()
    parser.feed(raw)

    out = []
    for cells, metas in parser.rows:
        # Cerca la sigla squadra (3 lettere) e usa la cella precedente come nome.
        idx_sq = None
        for i, c in enumerate(cells):
            if re.fullmatch(r"[A-Z]{3}", c or ""):
                idx_sq = i
                break
        if idx_sq is None or idx_sq < 1 or len(cells) < idx_sq + 11:
            continue

        nome = cells[idx_sq - 1].strip()
        squadra_a = cells[idx_sq].strip()
        if not nome or nome.lower() == "calciatore":
            continue

        pv = int(_num_fc(cells[idx_sq + 1], 0))
        mv = _num_fc(cells[idx_sq + 2], 0)
        fm = _num_fc(cells[idx_sq + 3], 0)
        gol = int(_num_fc(cells[idx_sq + 4], 0))
        gs = int(_num_fc(cells[idx_sq + 5], 0))

        rig_txt = cells[idx_sq + 6]
        mrig = re.search(r"(\d+)\s*/\s*(\d+)", rig_txt)
        rig_segnati = int(mrig.group(1)) if mrig else 0
        rig_tirati = int(mrig.group(2)) if mrig else 0
        rig_sbagliati = max(0, rig_tirati - rig_segnati)

        rp = int(_num_fc(cells[idx_sq + 7], 0))
        ass = int(_num_fc(cells[idx_sq + 8], 0))
        amm = int(_num_fc(cells[idx_sq + 9], 0))
        esp = int(_num_fc(cells[idx_sq + 10], 0))

        # Ruolo Classic P/D/C/A: serve anche alla Best 11 di tutta la Serie A.
        ruolo = _ruolo_classic_da_riga(cells, metas, idx_sq - 1)
        # Fallback sicuro per i portieri se il badge ruolo non viene esposto come testo/metadato.
        if not ruolo and (gs > 0 or rp > 0):
            ruolo = "p"

        out.append({
            "nome": nome,
            "squadra": squadra_a,
            "ruolo": ruolo,
            "prestot": pv,
            "presfvtot": pv,
            "mediavototot": round(mv, 2),
            "fvototot": round(fm, 2),
            "goltot": gol,
            "assisttot": ass,
            "golsubititot": gs,
            "cleansheettot": 0,
            "rigtot": rig_segnati,
            "risgsbtot": rig_sbagliati,
            "rigpartot": rp,
            "autgoltot": 0,
            "ammtot": amm,
            "esptot": esp
        })

    if len(out) < 100:
        raise RuntimeError(
            "La pagina Fantacalcio è stata letta, ma la tabella Statistico non è stata riconosciuta "
            f"(trovati {len(out)} giocatori). dati.json NON viene sovrascritto."
        )
    return out

print("Scarico statistiche Serie A - Voto Statistico FC (Alvin482)...")
giocatori_seriea = scarica_statistiche_statistiche_fc()

# I voti/statistiche arrivano SEMPRE dalla pagina Statistico.
# Per i ruoli P/D/C/A usiamo invece il Listone ufficiale Classic, che è la fonte corretta.
print("Scarico ruoli Classic + QI/QA dal Listone ufficiale Fantacalcio...")
listone_fc = scarica_listone_classic_fc()
ruoli_borracho = {_norm_nome_fc(g["nome"]): g.get("ruolo", "") for g in lista_giocatori}

for g in giocatori_seriea:
    k = _norm_nome_fc(g["nome"])
    info = listone_fc.get(k)
    if info:
        if info.get("ruolo"):
            g["ruolo"] = info["ruolo"]
        g["id"] = info.get("id")
        g["qi"] = info["qi"]
        g["qa"] = info["qa"]
    elif k in ruoli_borracho:
        # Fallback per eventuali differenze di rendering/nome nel Listone.
        g["ruolo"] = ruoli_borracho[k]

# Anche i giocatori Borracho devono ricevere QI e QA: la Best 11 usa questa lista.
for g in lista_giocatori:
    info = listone_fc.get(_norm_nome_fc(g["nome"]))
    if info:
        g["id"] = info.get("id")
        g["qi"] = info["qi"]
        g["qa"] = info["qa"]

# Completa giocatori con le rose ufficiali API. INSER DATA contiene lo storico
# delle prestazioni e può non avere ancora una riga per chi non ha giocato:
# quei giocatori entrano comunque con statistiche a zero.
# La lista pubblica deve rappresentare la ROSA ATTUALE, mentre INSER DATA resta
# lo storico delle prestazioni. Un giocatore svincolato non deve rimanere nella
# rosa corrente solo perché compare nelle vecchie giornate di INSER DATA.
#
# Per i 250 giocatori attualmente tesserati conserviamo le statistiche storiche
# già raccolte, ma forziamo la fantasquadra alla proprietà ufficiale corrente.
# Gli ex giocatori restano fuori dalla rosa corrente: le loro vecchie righe in
# INSER DATA continuano comunque ad alimentare le statistiche storiche di squadra.
storico_by_id = {g.get("id"): g for g in lista_giocatori if g.get("id") is not None}
storico_by_nome = {_norm_nome_fc(g["nome"]): g for g in lista_giocatori}
lista_giocatori_attuali = []

for rp in roster_ufficiali:
    info = listone_fc.get(_norm_nome_fc(rp["nome"])) or {}
    g = storico_by_id.get(rp["id"]) or storico_by_nome.get(_norm_nome_fc(rp["nome"]))
    if g is not None:
        g = dict(g)
        g["squadra"] = rp["squadra"]
        if not g.get("id"):
            g["id"] = rp["id"]
        if info.get("ruolo"):
            g["ruolo"] = info["ruolo"]
        g["qi"] = info.get("qi", g.get("qi", 0))
        g["qa"] = info.get("qa", g.get("qa", 0))
        lista_giocatori_attuali.append(g)
        continue

    lista_giocatori_attuali.append({
        "nome": rp["nome"], "squadra": rp["squadra"], "ruolo": info.get("ruolo", ""),
        "prestit": 0, "presfvtit": 0, "mediavototit": 0, "fvototit": 0,
        "goltit": 0, "assisttit": 0, "golsubititit": 0, "cleansheettit": 0,
        "rigtit": 0, "risgsbtit": 0, "rigpartit": 0, "autgoltit": 0, "ammtit": 0, "esptit": 0,
        "prestot": 0, "presfvtot": 0, "mediavototot": 0, "fvototot": 0,
        "goltot": 0, "assisttot": 0, "golsubititot": 0, "cleansheettot": 0,
        "rigtot": 0, "risgsbtot": 0, "rigpartot": 0, "autgoltot": 0, "ammtot": 0, "esptot": 0,
        "id": rp["id"], "qi": info.get("qi", 0), "qa": info.get("qa", 0)
    })
# Da qui in avanti "giocatori" significa esclusivamente i 250 tesserati attuali.
lista_giocatori = lista_giocatori_attuali
if len(lista_giocatori) != len(roster_ufficiali):
    raise RuntimeError(
        f"Controllo rose fallito: API={len(roster_ufficiali)} giocatori, JSON={len(lista_giocatori)}. "
        "dati.json NON viene sovrascritto."
    )

print(f"Giocatori Borracho completi: {len(lista_giocatori)}")

conteggio_ruoli_seriea = {r: sum(1 for g in giocatori_seriea if g.get("ruolo") == r) for r in ("p", "d", "c", "a")}
senza_ruolo = [g["nome"] for g in giocatori_seriea if g.get("ruolo") not in ("p", "d", "c", "a")]
print("Ruoli Serie A:", conteggio_ruoli_seriea)
print("Giocatori senza ruolo:", len(senza_ruolo))

# Blocco di sicurezza: una Best 11 Serie A con centinaia di ruoli mancanti sarebbe falsata.
# Non sovrascriviamo dati.json finché il Listone non è stato letto correttamente.
if len(senza_ruolo) > 10:
    esempio = ", ".join(senza_ruolo[:10])
    raise RuntimeError(
        "Ruoli Classic non letti correttamente dal Listone Fantacalcio: "
        f"{len(senza_ruolo)} giocatori senza ruolo (esempio: {esempio}). "
        "dati.json NON viene sovrascritto."
    )

# Svincolati = tutti Serie A meno i giocatori presenti nelle rose Borracho.
nomi_borracho = {_norm_nome_fc(g["nome"]) for g in lista_giocatori}
giocatori_svincolati = [
    g for g in giocatori_seriea
    if _norm_nome_fc(g["nome"]) not in nomi_borracho
]


# === 4. GENERA JSON ===

colonne_stat = [c for c in colonne_stat if c != "class"]   
dati = {
    "squadre": squadre,
    "giocatori": lista_giocatori,
    "giocatori_seriea": giocatori_seriea,
    "giocatori_svincolati": giocatori_svincolati,
    "risultati": risultati,
    "stat_squadre": stat_squadre,
    "stat_colonne": colonne_stat
}   
with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(dati, f, ensure_ascii=False, indent=2)

# TEST: mostra i primi 3 punti
for s in squadre[:3]:
    print(s["nome"], s["pt"])
print(f"OK {len(squadre)} squadre")
print(f"OK {len(lista_giocatori)} giocatori Borracho")
print(f"OK {len(giocatori_seriea)} giocatori Serie A (Voto Statistico)")
print(f"OK {len(giocatori_svincolati)} svincolati")
print(f"OK {len(risultati)} giornate")
print(f"OK Salvato in: {OUTPUT_FILE}")   

