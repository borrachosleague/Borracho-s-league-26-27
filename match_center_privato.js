/* BORRACHOS MATCH CENTER — archivio privato G1+ (17/10/2026, v4)
   I file privati restano in IndexedDB sul dispositivo, non sono caricati online. */
(function(){
 'use strict';
 const SCHEMA='borrachos.matchcenter.privato.v2', DB='borrachos_match_center_privato', STORE='archivi';
 let byMatch=new Map(), ready=false;
 function norm(x){
  let s=String(x||'').normalize('NFKD').replace(/[\u0300-\u036f]/g,'').toLowerCase().replace(/[^a-z0-9]+/g,' ').trim();
  const aliases={'tricchetracht':'tricchetracht francoforte','tricchetracht frankfurt':'tricchetracht francoforte','sesto asensio':'il sesto asensio','atl improvvisato':'atletico improvvisato','pesciculini':'pesciculini fc','internazionanale':'fc internazioanale','interna ziona nale':'fc internazioanale','internaziona nale':'fc internazioanale','asparaghese':'ac asparaghese','shark fc':'shark'};
  return aliases[s]||s;
 }
 const key=(day,a,b)=>String(day)+'|'+norm(a)+'|'+norm(b);
 function verify(data){
  if(data && data.schema && data.schema!==SCHEMA)throw Error('archivio in formato vecchio ('+data.schema+'): rigeneralo con importa_formazioni.py');
  if(!data || data.schema!==SCHEMA || !Array.isArray(data.giornate) || !data.giornate.length)throw Error('Formato archivio JSON non valido');
  const map=new Map();
  for(const day of data.giornate){
   if(!Number.isInteger(day.giornata) || day.giornata<1 || day.giornata>36 || !Array.isArray(day.partite) || day.partite.length!==5)throw Error('Giornata o numero partite non valido: '+day.giornata);
   for(const p of day.partite){
    for(const side of ['casa','trasferta']){
     const t=p[side];
     if(!t || !t.nome || !Array.isArray(t.titolari) || t.titolari.length!==11 || !Array.isArray(t.panchina) || t.panchina.length>14)throw Error('Formazione incompleta alla G'+day.giornata);
     const seen=new Set();
     for(const g of t.titolari.concat(t.panchina)){
      if(!g || typeof g.nome!=='string' || g.nome.trim().length<2 || [g.scr,g.cscr].some(v=>v!=null&&!(typeof v==='number'&&isFinite(v)&&v>=0&&v<20)))throw Error('Voti o giocatori non validi: '+t.nome+' G'+day.giornata);
      const k=norm(g.nome);if(seen.has(k))throw Error('Giocatore duplicato in '+t.nome+': '+g.nome);seen.add(k);
     }
     for(const f of ['totale','fantavoto_effettivo','pagella_effettiva','modificatore_difesa'])if(typeof t[f]!=='number'||!isFinite(t[f]))throw Error('Campo '+f+' mancante: '+t.nome+' G'+day.giornata+' (rigenera il JSON con importa_formazioni.py)');
     if(Math.abs(t.fantavoto_effettivo+t.modificatore_difesa-t.totale)>1e-6)throw Error('Totale non coerente: '+t.nome+' G'+day.giornata+' (fantavoto '+t.fantavoto_effettivo+' + mod '+t.modificatore_difesa+' ≠ '+t.totale+')');
    }
    const k=key(day.giornata,p.casa.nome,p.trasferta.nome);
    if(map.has(k))throw Error('Partita duplicata '+k);
    map.set(k,p);
   }
  }
  return map;
 }
 function dbAction(action,value){
  return new Promise((resolve,reject)=>{
   if(!window.indexedDB)return reject(Error('IndexedDB non disponibile'));
   const op=indexedDB.open(DB,1);
   op.onupgradeneeded=()=>{if(!op.result.objectStoreNames.contains(STORE))op.result.createObjectStore(STORE)};
   op.onerror=()=>reject(op.error);
   op.onsuccess=()=>{
    const db=op.result,tx=db.transaction(STORE,action==='get'?'readonly':'readwrite'),st=tx.objectStore(STORE);
    const req=action==='get'?st.get('current'):action==='put'?st.put(value,'current'):st.delete('current');
    req.onsuccess=()=>resolve(req.result);
    req.onerror=()=>reject(req.error);
    tx.oncomplete=()=>db.close();
   };
  });
 }
 function redraw(){
  if(typeof mcArchivio==='undefined'||!mcArchivio||typeof mcRenderGiornata!=='function')return;
  const day=mcGiornata||mcArchivio[mcArchivio.length-1].giornata;
  const detail=document.getElementById('live-detail');
  const open=detail&&detail.style.display==='block';
  const active=typeof livePartitaAttiva==='number'?livePartitaAttiva:0;
  mcRenderGiornata(day);
  if(open&&typeof mostraLivePartita==='function')mostraLivePartita(active);
 }
 function setup(){
  if(ready)return;
  const picker=document.querySelector('#page-live .match-day-picker');
  if(!picker)return;
  ready=true;
  const panel=document.createElement('div');panel.id='mc-private-tools';
  panel.style.cssText='display:flex;flex-wrap:wrap;align-items:center;justify-content:center;gap:9px;margin:12px auto 18px;text-align:center';
  const input=document.createElement('input');input.type='file';input.accept='.json,application/json';input.hidden=true;
  const load=document.createElement('button');load.type='button';load.textContent='📂 CARICA ARCHIVIO PRIVATO';
  const clear=document.createElement('button');clear.type='button';clear.textContent='✕ RIMUOVI DATI PRIVATI';
  for(const btn of [load,clear])btn.style.cssText='background:#201b23;color:#ffd54a;border:2px solid #ffd54a;border-radius:9px;font-weight:800;padding:10px 15px;cursor:pointer';
  const status=document.createElement('div');status.id='mc-private-status';status.style.cssText='flex-basis:100%;color:#f3db84;font-size:13px;font-weight:700';status.setAttribute('role','status');
  function msg(t,err){status.textContent=t;status.style.color=err?'#ff9191':'#f3db84'}
  msg('Seleziona il JSON dell’archivio privato: i dati rimangono soltanto su questo dispositivo.');
  load.onclick=()=>input.click();
  input.onchange=async()=>{
   try{
    const f=input.files&&input.files[0];if(!f)return;
    if(f.size>25*1024*1024)throw Error('File oltre 25 MB');
    const data=JSON.parse(await f.text()),found=verify(data);
    const diff=[];
    if(typeof mcArchivio!=='undefined'&&mcArchivio){
     for(const day of data.giornate){
      const real=mcArchivio.find(x=>Number(x.giornata)===day.giornata);
      if(!real)throw Error('Giornata '+day.giornata+' assente dai risultati ufficiali');
      for(const p of day.partite){
       const r=real.partite.find(r=>key(day.giornata,r.casa,r.trasferta)===key(day.giornata,p.casa.nome,p.trasferta.nome));
       if(!r)throw Error('Squadre non corrispondenti alla G'+day.giornata+': '+p.casa.nome+' - '+p.trasferta.nome);
       if(Math.abs(Number(r.pt_casa)-p.casa.totale)>1e-6)diff.push('G'+day.giornata+' '+p.casa.nome+' '+p.casa.totale+' vs ufficiale '+r.pt_casa);
       if(Math.abs(Number(r.pt_trasferta)-p.trasferta.totale)>1e-6)diff.push('G'+day.giornata+' '+p.trasferta.nome+' '+p.trasferta.totale+' vs ufficiale '+r.pt_trasferta);
      }
     }
    }
    byMatch=found;redraw();
    msg('Archivio attivo: '+data.giornate.length+' giornate e '+found.size+' partite. Salvato su questo browser.'+(diff.length?' ⚠ '+diff.length+' totali diversi da dati.json (restano quelli ufficiali): '+diff.slice(0,3).join('; '):''),diff.length>0);
    try{await dbAction('put',data)}catch(e){msg('Archivio attivo ora, ma salvataggio locale non riuscito: '+e.message,true)}
   }catch(e){msg('IMPORTAZIONE ANNULLATA: '+e.message,true)}finally{input.value=''}
  };
  clear.onclick=async()=>{byMatch.clear();redraw();try{await dbAction('delete');msg('Archivio privato rimosso da questo browser')}catch(e){msg('Dati rimossi dalla pagina; cancellazione locale non riuscita: '+e.message,true)}};
  panel.append(input,load,clear,status);picker.insertAdjacentElement('afterend',panel);
  dbAction('get').then(data=>{if(!data)return;
   try{byMatch=verify(data);redraw();msg('Archivio locale ripristinato: '+data.giornate.length+' giornate, '+byMatch.size+' partite')}
   catch(e){byMatch=new Map();dbAction('delete').catch(()=>{});msg('Archivio locale obsoleto rimosso ('+e.message+'). Carica il JSON rigenerato.',true)}
  }).catch(()=>{});
 }
 function install(){
  if(typeof mcPartita!=='function'){setup();return}
  const old=mcPartita;
  mcPartita=function(r){
   const result=old(r);
   const t=byMatch.get(key(mcGiornata,r.casa,r.trasferta));
   if(t){for(const side of ['casa','trasferta']){
    result[side].titolari=t[side].titolari;result[side].panchina=t[side].panchina;
    result[side].modulo=t[side].modulo;result[side].modificatore_difesa=t[side].modificatore_difesa;result[side].pagella_effettiva=t[side].pagella_effettiva;result[side].fantavoto_effettivo=t[side].fantavoto_effettivo;result[side].subentrati=t[side].subentrati||[];result[side].giocatori_effettivi=t[side].giocatori_effettivi;result[side].consegnata=true;
   }result.archivioSenzaFormazioni=false}
   return result;
  };
  // Fantavoto e modificatore vengono letti dai totali ufficiali Excel. La pagella si mostra solo quando verificabile.
  // Se il calcolo non si riconcilia col totale ufficiale, NON mostra numeri ingannevoli.
  if(typeof liveSommaTitolari==='function'){
   const originalSum=liveSommaTitolari;
   liveSommaTitolari=function(team,field){
    if(team&&Object.prototype.hasOwnProperty.call(team,'fantavoto_effettivo')){
     const v=field==='scr'?team.pagella_effettiva:team.fantavoto_effettivo;
     return typeof v==='number'?v.toFixed(1):'—';
    }
    return originalSum(team,field);
   };
  }
  if(typeof renderLiveMatch==='function'){
   const render=renderLiveMatch;
   renderLiveMatch=function(match){
    let html=render(match);
    if(!match||match.archivioSenzaFormazioni)return html;
    // Ogni riepilogo (home/away) e' sostituito separatamente: la vecchia replace() colpiva sempre la prima occorrenza.
    return html.replace(/(live-side-(home|away)">(?:(?!<\/aside>)[\s\S])*?MOD\. DIFESA<\/span><strong>)—(<\/strong>)/g,function(m,pre,lato,post){
     const t=match[lato==='home'?'casa':'trasferta'],v=t&&t.modificatore_difesa;
     return pre+((typeof v==='number')?String(v).replace('.',','):'—')+post;
    });
   };
  }
  if(typeof liveCartellini==='function'){
   const original=liveCartellini;
   const symbols={AMM:'🟨',ESP:'🟥',G:'⚽',GS:'🥅',AU:'🔴',RS:'⚽',RSb:'❌',RP:'🧤',A:'🅰️',AS:'🅰️',AG:'🅰️',GV:'🏆',PI:'🏅'};
   liveCartellini=function(p){
    let html=original(p); const ev=p&&p.bonus_malus;
    if(ev)for(const [k,v] of Object.entries(ev))if(symbols[k])html+='<span style="margin-left:4px" title="'+k+': '+v+' punti">'+symbols[k]+'</span>';
    if(p&&p.subentrato)html+='<span style="margin-left:4px" title="Subentrato dalla panchina">⇄</span>';
    return html;
   };
  }
  // Chi non e' entrato nel punteggio (grigio nell'Excel) viene attenuato.
  if(typeof liveVotoDoppio==='function'){
   const doppio=liveVotoDoppio;
   liveVotoDoppio=function(p){const h=doppio(p);return(p&&p.conta===false)?'<div style="opacity:.4" title="Non entrato nel punteggio">'+h+'</div>':h};
  }
  setup();
 }
 if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',install,{once:true});else install();
})();
