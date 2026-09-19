import json
import openpyxl
from collections import defaultdict

# === CONFIGURAZIONE ===
CLASSIFICA_FILE = r"E:\--- fantacalcio tot uff\26-27\esportazioni\classifica\Classifica_Serie-Aperol.xlsx"
BORRACHOS_FILE = r"E:\--- fantacalcio tot uff\26-27\BORRACHOSLEAGUE 26.27.xlsm"
CALENDARIO_FILE = r"E:\--- fantacalcio tot uff\26-27\CalendarioSerieAperol.xlsx"
OUTPUT_FILE = r"E:\--- fantacalcio tot uff\26-27\dati.json"

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
STAT_FILE = r"E:\--- fantacalcio tot uff\26-27\nuovo statistiche.xlsm"

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
  

# === 1.6 CLASSIFICA F1 E BATTLE ROYALE (Foglio 4) ===

# F1: righe 4-13, nome in col A, punteggio in col B
f1_scores = {}
for r in range(4, 14):
    nome = ws_f1.cell(row=r, column=1).value
    val = ws_f1.cell(row=r, column=2).value
    if nome is not None and str(nome).strip():
        try:
            f1_scores[str(nome).strip()] = float(str(val).replace(",", ".")) if val is not None else 0
        except (ValueError, TypeError):
            f1_scores[str(nome).strip()] = 0

# BR: righe 19-28, nome in col A, punteggio in col B
br_scores = {}
for r in range(19, 29):
    nome = ws_f1.cell(row=r, column=1).value
    val = ws_f1.cell(row=r, column=2).value
    if nome is not None and str(nome).strip():
        try:
            br_scores[str(nome).strip()] = float(str(val).replace(",", ".")) if val is not None else 0
        except (ValueError, TypeError):
            br_scores[str(nome).strip()] = 0
# DEBUG
print("Nomi Foglio 4 F1:", list(f1_scores.keys()))
print("Nomi Foglio 1:", [sq["nome"] for sq in stat_squadre])   

# Aggiunge i campi a stat_squadre
for sq in stat_squadre:
    sq["dati"]["f1"] = f1_scores.get(sq["nome"], 0)
    sq["dati"]["br"] = br_scores.get(sq["nome"], 0)

# Aggiunge le colonne alla lista
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
# === 4. GENERA JSON ===

colonne_stat = [c for c in colonne_stat if c != "class"]   
dati = {
    "squadre": squadre,
    "giocatori": lista_giocatori,
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
print(f"OK {len(lista_giocatori)} giocatori")
print(f"OK {len(risultati)} giornate")
print(f"OK Salvato in: {OUTPUT_FILE}")   