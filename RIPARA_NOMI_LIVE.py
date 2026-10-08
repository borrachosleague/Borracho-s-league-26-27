from pathlib import Path
import shutil, datetime, sys
base=Path(__file__).resolve().parent
source=base/'aggiorna_live.py'
if not source.is_file():
    sys.exit('ERRORE: aggiorna_live.py non trovato nella stessa cartella.')
s=source.read_text(encoding='utf-8-sig')
marker='    teams = unwrap_list(fetch_json(TEAMS_URL, app_key, bearer))'
flag='# FIX NOMI LIVE BORRACHOS DA LISTONE ID'
if flag in s:
    print('La correzione dei nomi e gia presente. Nessuna modifica.');sys.exit(0)
if s.count(marker)!=1:
    sys.exit('ERRORE: struttura di aggiorna_live.py diversa dal previsto; nessuna modifica.')
addition='''    # FIX NOMI LIVE BORRACHOS DA LISTONE ID
    # Il campo # del Listone Classic e l'ID Fantacalcio (pid).
    # I dati della rosa autenticata coprono solo Tricchetracht.
    import openpyxl
    listone = os.path.join(BASE_DIR, "lista_calciatori_lista calciatori_classic_borracho-s-league.xlsx")
    if not os.path.isfile(listone):
        raise RuntimeError("Listone Classic mancante: " + listone)
    wb_listone = openpyxl.load_workbook(listone, read_only=True, data_only=True)
    try:
        sheet = wb_listone["Lista calciatori"]
        iterator = sheet.iter_rows(values_only=True)
        headers = [str(v or "").strip() for v in next(iterator)]
        if "#" not in headers or "Nome" not in headers:
            raise RuntimeError("Nel Listone mancano le colonne # e Nome")
        idcol, namecol = headers.index("#"), headers.index("Nome")
        loaded = 0
        for record in iterator:
            pid, nome = record[idcol], record[namecol]
            if pid is None or not str(nome or "").strip():
                continue
            try:
                pid = str(int(pid))
            except (TypeError, ValueError):
                continue
            if not PLAYER_NAMES.get(pid):
                PLAYER_NAMES[pid] = str(nome).strip()
            loaded += 1
    finally:
        wb_listone.close()
    if loaded < 250:
        raise RuntimeError(f"Listone incompleto: solo {loaded} codici letti")
    print(f"Nomi LIVE: {len(PLAYER_NAMES)} ID disponibili (Listone: {loaded})")

'''
backup=source.with_name('aggiorna_live_PRIMA_FIX_NOMI_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S')+'.py')
shutil.copy2(source,backup)
new=s.replace(marker,addition+marker)
compile(new,str(source),'exec')
source.write_text(new,encoding='utf-8')
print('OK: aggiorna_live.py corretto. Backup:',backup.name)
