import json
import os
import openpyxl
from collections import defaultdict
from html.parser import HTMLParser
from urllib.request import Request, urlopen
import re
import unicodedata
from pathlib import Path
import os

# === CONFIGURAZIONE ===
PROJECT_DIR = Path(__file__).resolve().parent
DATA_DIR = PROJECT_DIR.parent
CLASSIFICA_FILE = str(PROJECT_DIR / "esportazioni" / "classifica" / "Classifica_Serie-Aperol.xlsx")
BORRACHOS_FILE = str(DATA_DIR / "BORRACHOSLEAGUE 26.27.xlsm")
CALENDARIO_FILE = str(PROJECT_DIR / "esportazioni" / "classifica" / "Calendario_Serie-Aperol.xlsx")
OUTPUT_FILE = str(PROJECT_DIR / "dati.json")

# === 1. CLASSIFICA SQUADRE ===
wb_class = openpyxl.load_workbook(CLASSIFICA_FILE, read_only=True)
ws_class = wb_class.active

squadre = []
for row in ws_class.iter_rows(min_row=2, values_only=True):
    if row[1] is None:
        continue
    try:
        int(row[0])
    except (ValueError, TypeError):
        continue
    squadre.append({
        "nome": str(row[1]).strip(),
        "g": int(row[3] or 0),
        "v": int(row[4] or 0),
        "n": int(row[5] or 0),
        "p": int(row[6] or 0),
        "gf": int(row[7] or 0),
        "gs": int(row[8] or 0),
        "dr": int(row[9] or 0),
        "pt": int(row[10] or 0),
        "pt_totali": float(str(row[11]).replace(",", ".")) if row[11] else 0
    })


# === 1.5 STATISTICHE SQUADRE ===
STAT_FILE = str(DATA_DIR / "nuovo statistiche.xlsm")

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

if "tot best" in colonne_stat and "pt best" in colonne_stat:
    i1 = colonne_stat.index("tot best")
    i2 = colonne_stat.index("pt best")
    colonne_stat[i1], colonne_stat[i2] = colonne_stat[i2], colonne_stat[i1]   

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
ws_f1 = wb_stat.worksheets[2]

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
# === 1.7 QUOTAZIONI UFFICIALI FANTACALCIO.IT 2026/27 ===
# Fonte pubblica: https://www.fantacalcio.it/quotazioni-fantacalcio/2026-27
# QI = quotazione iniziale Classic, QA = quotazione attuale Classic.
class _TableParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows, self.row, self.cell = [], None, None
    def handle_starttag(self, tag, attrs):
        if tag == "tr": self.row = []
        elif tag in ("td", "th") and self.row is not None: self.cell = []
    def handle_data(self, data):
        if self.cell is not None: self.cell.append(data)
    def handle_endtag(self, tag):
        if tag in ("td", "th") and self.cell is not None and self.row is not None:
            self.row.append(" ".join("".join(self.cell).split()))
            self.cell = None
        elif tag == "tr" and self.row is not None:
            if self.row: self.rows.append(self.row)
            self.row = None

def _norm_nome(s):
    s = unicodedata.normalize("NFD", str(s or "").lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]", "", s)

def carica_quotazioni():
    url = "https://www.fantacalcio.it/quotazioni-fantacalcio/2026-27"
    try:
        req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        html = urlopen(req, timeout=20).read().decode("utf-8", "ignore")
        parser = _TableParser()
        parser.feed(html)
        out = {}
        for cells in parser.rows:
            # Nella tabella ufficiale: Calciatore, Sq, QI Classic, QA Classic, FVM...
            clean = [c.strip().replace("*", "").strip() for c in cells if c.strip()]
            team_i = next((i for i,c in enumerate(clean) if re.fullmatch(r"[A-Z]{3}", c)), None)
            if team_i is None or team_i < 1 or len(clean) <= team_i + 2:
                continue
            nome = clean[team_i - 1]
            try:
                qi = int(float(clean[team_i + 1].replace(",", ".")))
                qa = int(float(clean[team_i + 2].replace(",", ".")))
            except (ValueError, TypeError):
                continue
            out[_norm_nome(nome)] = {"qi": qi, "qa": qa}
        print(f"OK {len(out)} quotazioni Fantacalcio.it")
        return out
    except Exception as e:
        print(f"ATTENZIONE: quotazioni non aggiornate: {e}")
        return {}

quotazioni_fc = carica_quotazioni()

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
# Statistiche TOTALI: tutte le prestazioni, anche non schierate
giocatori_totali = defaultdict(lambda: {
    "voti": [], "fvoti": [], "squadra": "", "ruolo": ""
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

    # TOTALI: Voto colonna F e Fantavoto generale colonna V
    gt = giocatori_totali[nome]
    gt["squadra"] = g["squadra"]
    gt["ruolo"] = g["ruolo"]
    try:
        vv = float(str(row[5]).replace(",", ".")) if row[5] is not None else 0
        if vv > 0: gt["voti"].append(vv)
    except (ValueError, TypeError): pass
    try:
        ff = float(str(row[21]).replace(",", ".")) if row[21] is not None else 0
        if ff > 0: gt["fvoti"].append(ff)
    except (ValueError, TypeError): pass

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
        "qi": quotazioni_fc.get(_norm_nome(nome), {}).get("qi"),
        "qa": quotazioni_fc.get(_norm_nome(nome), {}).get("qa"),
        "prestit": n_voti,
        "presfvtit": n_fvoti,
        "prestot": len(giocatori_totali[nome]["voti"]),
        "presfvtot": len(giocatori_totali[nome]["fvoti"]),
        "mediavototot": round(sum(giocatori_totali[nome]["voti"]) / len(giocatori_totali[nome]["voti"]), 2) if giocatori_totali[nome]["voti"] else 0,
        "fvototot": round(sum(giocatori_totali[nome]["fvoti"]) / len(giocatori_totali[nome]["fvoti"]), 2) if giocatori_totali[nome]["fvoti"] else 0,
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
        "esptit": g["esp"]
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

# === 3. CALENDARIO ===
wb_cal = openpyxl.load_workbook(CALENDARIO_FILE, read_only=True, data_only=True)
ws_cal = wb_cal.active

risultati = []
giornata_sin = 0
giornata_des = 0
partite_sin = []
partite_des = []

def parse_gol(val):
    if val is None:
        return 0, 0
    s = str(val).strip()
    if s == "-" or s == "":
        return 0, 0
    if "-" in s:
        parts = s.split("-")
        try:
            return int(float(parts[0].replace(",", "."))), int(float(parts[1].replace(",", ".")))
        except (ValueError, TypeError):
            return 0, 0
    try:
        n = float(s.replace(",", "."))
        if n <= 65.5: return 0, 0
        elif n <= 71.5: return 1, 0
        elif n <= 77.5: return 2, 0
        elif n <= 83.5: return 3, 0
        elif n <= 89.5: return 4, 0
        elif n <= 95.5: return 5, 0
        elif n <= 101.5: return 6, 0
        else: return 7, 0
    except (ValueError, TypeError):
        return 0, 0

def parse_pt(val):
    if val is None:
        return 0
    try:
        return float(str(val).replace(",", "."))
    except (ValueError, TypeError):
        return 0

for row in ws_cal.iter_rows(min_row=1, values_only=True):
    val_a = row[0]
    if val_a is None:
        continue
    val_a_str = str(val_a).strip()

    if "giornata" in val_a_str.lower():
        if partite_sin:
            risultati.append({"giornata": giornata_sin, "partite": partite_sin})
        if partite_des:
            risultati.append({"giornata": giornata_des, "partite": partite_des})

        import re
        m = re.search(r'(\d+)', val_a_str)
        if m:
            giornata_sin = int(m.group(1))
        else:
            giornata_sin += 1

        val_g = row[6] if len(row) > 6 else None
        if val_g is not None and "giornata" in str(val_g).lower():
            m2 = re.search(r'(\d+)', str(val_g))
            if m2:
                giornata_des = int(m2.group(1))
            else:
                giornata_des += 1

        partite_sin = []
        partite_des = []
    else:
        # Blocco sinistro (A-E): giornata dispari
        if val_a_str and row[3] is not None:
            gol_c, gol_t = parse_gol(row[4])
            partite_sin.append({
                "casa": str(val_a_str).strip(),
                "pt_casa": parse_pt(row[1]),
                "gol_casa": gol_c,
                "gol_trasferta": gol_t,
                "pt_trasferta": parse_pt(row[2]),
                "trasferta": str(row[3]).strip()
            })

        # Blocco destro (G-K): giornata pari
        val_g = row[6] if len(row) > 6 else None
        if val_g is not None and str(val_g).strip() and len(row) > 10 and row[9] is not None:
            gol_c2, gol_t2 = parse_gol(row[10])
            partite_des.append({
                "casa": str(val_g).strip(),
                "pt_casa": parse_pt(row[7]),
                "gol_casa": gol_c2,
                "gol_trasferta": gol_t2,
                "pt_trasferta": parse_pt(row[8]),
                "trasferta": str(row[9]).strip()
            })

if partite_sin:
    risultati.append({"giornata": giornata_sin, "partite": partite_sin})
if partite_des:
    risultati.append({"giornata": giornata_des, "partite": partite_des})

wb_cal.close()

# Ordina per numero giornata
risultati.sort(key=lambda x: x["giornata"])   
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

def scarica_ruoli_classic_fc():
    """Scarica il Listone/quotazioni ufficiale e costruisce nome -> ruolo Classic.
    Le statistiche restano quelle Voto Statistico; questa seconda pagina serve solo per P/D/C/A.
    """
    req = urllib.request.Request(
        QUOTAZIONI_URL,
        headers={"User-Agent": "Mozilla/5.0", "Accept": "text/html,application/xhtml+xml"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            raw = response.read().decode("utf-8", errors="replace")
    except Exception as e:
        raise RuntimeError("Impossibile scaricare i ruoli Classic dal Listone Fantacalcio: " + str(e))

    parser = _StatsTableParser()
    parser.feed(raw)
    ruoli = {}
    for cells, metas in parser.rows:
        idx_sq = None
        for i, c in enumerate(cells):
            if re.fullmatch(r"[A-Z]{3}", c or ""):
                idx_sq = i
                break
        if idx_sq is None or idx_sq < 1:
            continue
        nome = str(cells[idx_sq - 1] or "").strip()
        if not nome or nome.lower() == "calciatore":
            continue
        ruolo = _ruolo_classic_da_riga(cells, metas, idx_sq - 1)
        if ruolo:
            ruoli[_norm_nome_fc(nome)] = ruolo

    return ruoli

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
print("Scarico ruoli Classic dal Listone ufficiale Fantacalcio...")
ruoli_listone = scarica_ruoli_classic_fc()
ruoli_borracho = {_norm_nome_fc(g["nome"]): g.get("ruolo", "") for g in lista_giocatori}

for g in giocatori_seriea:
    k = _norm_nome_fc(g["nome"])
    if k in ruoli_listone:
        g["ruolo"] = ruoli_listone[k]
    elif k in ruoli_borracho:
        # Fallback per eventuali differenze di rendering/nome nel Listone.
        g["ruolo"] = ruoli_borracho[k]

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

print(f"OK {len(squadre)} squadre")
print(f"OK {len(lista_giocatori)} giocatori Borracho")
print(f"OK {len(giocatori_seriea)} giocatori Serie A")
print(f"OK {len(giocatori_svincolati)} svincolati")
print(f"OK {len(risultati)} giornate")
print(f"OK Salvato in: {OUTPUT_FILE}")
