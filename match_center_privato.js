/* BORRACHOS MATCH CENTER — archivio riservato online (v6, 18/10/2026: accesso unico dalla Home)
   Formazioni, voti e bonus/malus arrivano da Supabase SOLO dopo l'accesso squadra + password.
   Lettura protetta da RLS (tabella mc_giornate); nulla di riservato è nel repository o in dati.json.
   Punteggi ufficiali: restano quelli di dati.json. Rendering e regole invariati rispetto alla v4. */
(function(){
 'use strict';
 const SCHEMA='borrachos.matchcenter.privato.v2';
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
 // ---------- Supabase (progetto Borrachos, chiave pubblica "publishable": NON segreta) ----------
 const SB_URL='https://tlgzvgdxhtiavobyyxze.supabase.co', SB_KEY='sb_publishable_a0DVw4Juvcxls3mJVFfGKQ_CMYTG9mL';
 // Sessione del Match Center separata da quella dell'asta (chiave diversa da sb-...-auth-token).
 const SESS_KEY='borrachos_mc_sessione_v1', POLL_MS=60000, EMAIL_DOMAIN='borrachosleague.github.io';
 // Account tecnici Supabase Auth (creati dall'amministratore, nessuna email personale richiesta).
 const SQUADRE=[
  ['tricchetracht','TRICCHETRACHT'],['sesto-asensio','SESTO ASENSIO'],['atl-improvvisato','ATL IMPROVVISATO'],
  ['san-gria','SAN GRIA'],['pesciculini','PESCICULINI'],['partizan-degrado','PARTIZAN DEGRADO'],
  ['asparaghese','ASPARAGHESE'],['shark','SHARK'],['as-pipperia','AS PIPPERIA'],['internaziona-nale','INTERNAZIONA NALE']];
 const emailDi=slug=>'mc-'+slug+'@'+EMAIL_DOMAIN;
 let sess=null, firma='', timer=null, ui=null, busy=false;

 function leggiSessione(){try{const s=JSON.parse(localStorage.getItem(SESS_KEY)||'null');return s&&s.refresh_token?s:null}catch(e){return null}}
 function salvaSessione(s){sess=s;try{s?localStorage.setItem(SESS_KEY,JSON.stringify(s)):localStorage.removeItem(SESS_KEY)}catch(e){}}
 function erroreRete(e){return Error(e&&e.name==='AbortError'?'Supabase non risponde (timeout)':'Connessione a Supabase non riuscita')}
 async function http(path,opt){
  const ctl=typeof AbortController==='function'?new AbortController():null, t=ctl&&setTimeout(()=>ctl.abort(),20000);
  let r;try{r=await fetch(SB_URL+path,Object.assign({cache:'no-store',signal:ctl&&ctl.signal},opt))}catch(e){throw erroreRete(e)}finally{if(t)clearTimeout(t)}
  let body=null;try{body=await r.json()}catch(e){}
  return {status:r.status,ok:r.ok,body};
 }
 function sessioneDa(b,squadra){return{access_token:b.access_token,refresh_token:b.refresh_token,expires_at:b.expires_at||Math.floor(Date.now()/1000)+(b.expires_in||3600),squadra}}
 async function accedi(slug,password){
  const r=await http('/auth/v1/token?grant_type=password',{method:'POST',headers:{apikey:SB_KEY,'Content-Type':'application/json'},body:JSON.stringify({email:emailDi(slug),password})});
  if(r.status===429)throw Error('Troppi tentativi: riprova tra qualche minuto');
  if(!r.ok||!r.body||!r.body.access_token)throw Error(r.status===400?'Squadra o password errata':'Accesso non riuscito ('+r.status+')');
  if(r.body.user&&r.body.user.is_anonymous)throw Error('Account non valido');
  salvaSessione(sessioneDa(r.body,slug));
 }
 async function cambiaPassword(attuale,nuova){
  if(!sess)throw Error('Accedi prima');
  if(nuova.length<10)throw Error('La nuova password deve avere almeno 10 caratteri');
  if(nuova===attuale)throw Error('La nuova password è uguale a quella attuale');
  try{await accedi(sess.squadra,attuale)}catch(e){throw Error(/errata/.test(e.message)?'Password attuale errata':e.message)}
  const r=await http('/auth/v1/user',{method:'PUT',headers:{apikey:SB_KEY,Authorization:'Bearer '+sess.access_token,'Content-Type':'application/json'},body:JSON.stringify({password:nuova})});
  if(!r.ok){const c=r.body&&(r.body.error_code||r.body.code);throw Error(c==='weak_password'?'Password troppo debole: usa lettere, numeri e simboli':c==='same_password'?'La nuova password è uguale a quella attuale':'Cambio non riuscito ('+r.status+')')}
 }
 async function token(){
  if(!sess)throw Error('NON_CONNESSO');
  if(sess.expires_at-90>Date.now()/1000)return sess.access_token;
  const r=await http('/auth/v1/token?grant_type=refresh_token',{method:'POST',headers:{apikey:SB_KEY,'Content-Type':'application/json'},body:JSON.stringify({refresh_token:sess.refresh_token})});
  if(!r.ok||!r.body||!r.body.access_token){if(r.status>=400&&r.status<500){esci('Sessione scaduta o accesso revocato: rientra con la password.',true);throw Error('SESSIONE')}throw Error('Rinnovo sessione non riuscito ('+r.status+')')}
  salvaSessione(sessioneDa(r.body,sess.squadra));return sess.access_token;
 }
 async function rest(path){
  const r=await http('/rest/v1/'+path,{headers:{apikey:SB_KEY,Authorization:'Bearer '+await token(),Accept:'application/json'}});
  if(r.status===401||r.status===403){esci('Sessione non più valida: rientra con la password.',true);throw Error('SESSIONE')}
  if(!r.ok)throw Error('Lettura dati non riuscita ('+r.status+')');
  return r.body;
 }
 function confrontaUfficiali(data){
  const diff=[];
  if(typeof mcArchivio==='undefined'||!mcArchivio)return diff;
  for(const day of data.giornate){
   const real=mcArchivio.find(x=>Number(x.giornata)===day.giornata);
   if(!real){diff.push('G'+day.giornata+' non ancora nei risultati ufficiali');continue}
   for(const p of day.partite){
    const r=real.partite.find(r=>key(day.giornata,r.casa,r.trasferta)===key(day.giornata,p.casa.nome,p.trasferta.nome));
    if(!r){diff.push('G'+day.giornata+' '+p.casa.nome+' - '+p.trasferta.nome+' non trovata');continue}
    if(Math.abs(Number(r.pt_casa)-p.casa.totale)>1e-6)diff.push('G'+day.giornata+' '+p.casa.nome+' '+p.casa.totale+' vs ufficiale '+r.pt_casa);
    if(Math.abs(Number(r.pt_trasferta)-p.trasferta.totale)>1e-6)diff.push('G'+day.giornata+' '+p.trasferta.nome+' '+p.trasferta.totale+' vs ufficiale '+r.pt_trasferta);
   }
  }
  return diff;
 }
 function quando(iso){try{return new Date(iso).toLocaleString('it-IT',{day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit'})}catch(e){return iso}}
 async function sincronizza(forza){
  if(busy||!sess)return;busy=true;
  try{
   const me=await rest('mc_membri?select=squadra,is_admin,attivo');
   if(!Array.isArray(me)||!me.length||!me[0].attivo){esci('Accesso al Match Center non autorizzato o revocato per questa squadra.',true);return}
   const meta=await rest('mc_giornate?select=giornata,versione,aggiornato_il&order=giornata');
   const nuovaFirma=JSON.stringify(meta);
   if(!forza&&nuovaFirma===firma)return;
   if(!meta.length){byMatch=new Map();firma=nuovaFirma;redraw();stato('Connesso come '+me[0].squadra+'. Nessuna giornata ancora pubblicata.');return}
   const rows=await rest('mc_giornate?select=giornata,dati&order=giornata');
   const data={schema:SCHEMA,giornate:rows.map(r=>r.dati)};
   const found=verify(data), diff=confrontaUfficiali(data);
   byMatch=found;firma=nuovaFirma;redraw();
   const ultimo=meta.reduce((a,b)=>a.aggiornato_il>b.aggiornato_il?a:b);
   stato('Connesso come '+me[0].squadra+' · '+data.giornate.length+' giornate · aggiornato '+quando(ultimo.aggiornato_il)+
    (diff.length?' · ⚠ '+diff.length+' differenze con i risultati ufficiali (valgono quelli ufficiali): '+diff.slice(0,2).join('; '):''),diff.length>0);
  }catch(e){
   if(e.message!=='SESSIONE'&&e.message!=='NON_CONNESSO')stato('Aggiornamento non riuscito: '+e.message+'. Restano visibili i dati già caricati.',true);
  }finally{busy=false}
 }
 function avviaPolling(){
  if(timer)clearInterval(timer);
  timer=setInterval(()=>document.hidden?null:sincronizza(false),POLL_MS);
 }
 function esci(motivo,err){
  if(timer){clearInterval(timer);timer=null}
  const rt=sess&&sess.access_token;
  salvaSessione(null);firma='';byMatch=new Map();redraw();
  if(rt)fetch(SB_URL+'/auth/v1/logout',{method:'POST',headers:{apikey:SB_KEY,Authorization:'Bearer '+rt}}).catch(()=>{});
  mostraLogin();stato(motivo||'Disconnesso. I dati riservati sono stati rimossi da questa pagina.',err);
 }
 function stato(t,err){if(!ui)return;ui.status.textContent=t;ui.status.style.color=err?'#ff9191':'#f3db84'}
 function mostraLogin(){if(!ui)return;ui.login.style.display='flex';ui.connesso.style.display='none';ui.chiudiCp()}
 function mostraConnesso(){if(!ui)return;ui.login.style.display='none';ui.connesso.style.display='flex'}
 function redraw(){
  if(typeof mcArchivio==='undefined'||!mcArchivio||!mcArchivio.length||typeof mcRenderGiornata!=='function')return;
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
  const btnCss='background:#201b23;color:#ffd54a;border:2px solid #ffd54a;border-radius:9px;font-weight:800;padding:10px 15px;cursor:pointer';
  const fldCss='background:#120f14;color:#fff;border:2px solid #6b5a2a;border-radius:9px;padding:9px 11px;font-weight:700;font-size:15px;min-width:0';
  const rowCss='display:flex;flex-wrap:wrap;align-items:center;justify-content:center;gap:9px';
  const panel=document.createElement('div');panel.id='mc-private-tools';
  panel.style.cssText='display:flex;flex-direction:column;align-items:center;gap:9px;margin:12px auto 18px;text-align:center;max-width:640px;padding:0 4px';
  const login=document.createElement('form');login.style.cssText=rowCss;login.setAttribute('autocomplete','on');
  const sel=document.createElement('select');sel.style.cssText=fldCss;sel.setAttribute('aria-label','Squadra');
  const o0=document.createElement('option');o0.value='';o0.textContent='Scegli la tua squadra';sel.append(o0);
  for(const [slug,nome] of SQUADRE){const o=document.createElement('option');o.value=slug;o.textContent=nome;sel.append(o)}
  const pwd=document.createElement('input');pwd.type='password';pwd.placeholder='Password';pwd.style.cssText=fldCss;pwd.setAttribute('autocomplete','current-password');pwd.setAttribute('aria-label','Password');
  const entra=document.createElement('button');entra.type='submit';entra.textContent='🔒 ENTRA NEL MATCH CENTER';entra.style.cssText=btnCss;
  login.append(sel,pwd,entra);
  // v6: si entra solo dalla Home (logo squadra + password unica asta/Match Center)
  for(const el of [sel,pwd,entra])el.style.display='none';
  const vaiHome=document.createElement('button');vaiHome.type='button';vaiHome.textContent='🏠 ENTRA DALLA HOME';vaiHome.style.cssText=btnCss;
  vaiHome.onclick=()=>{if(typeof showPage==='function'){showPage('home');window.scrollTo(0,0)}};
  login.append(vaiHome);
  const connesso=document.createElement('div');connesso.style.cssText=rowCss+';display:none';
  const agg=document.createElement('button');agg.type='button';agg.textContent='↻ AGGIORNA';agg.style.cssText=btnCss;
  const out=document.createElement('button');out.type='button';out.textContent='✕ ESCI';out.style.cssText=btnCss;
  const cp=document.createElement('button');cp.type='button';cp.textContent='🔑 CAMBIA PASSWORD';cp.style.cssText=btnCss;
  connesso.append(agg,out);
  const cpForm=document.createElement('form');cpForm.style.cssText=rowCss+';display:none';
  const mk=(ph,ac)=>{const i=document.createElement('input');i.type='password';i.placeholder=ph;i.style.cssText=fldCss;i.setAttribute('autocomplete',ac);i.setAttribute('aria-label',ph);return i};
  const pOld=mk('Password attuale','current-password'),pNew=mk('Nuova password (min. 10)','new-password'),pNew2=mk('Ripeti nuova password','new-password');
  const salva=document.createElement('button');salva.type='submit';salva.textContent='SALVA';salva.style.cssText=btnCss;
  const annulla=document.createElement('button');annulla.type='button';annulla.textContent='ANNULLA';annulla.style.cssText=btnCss;
  cpForm.append(pOld,pNew,pNew2,salva,annulla);
  const chiudiCp=()=>{cpForm.style.display='none';pOld.value=pNew.value=pNew2.value=''};
  cp.onclick=()=>{cpForm.style.display=cpForm.style.display==='none'?'flex':'none'};
  annulla.onclick=chiudiCp;
  cpForm.onsubmit=async ev=>{
   if(ev&&ev.preventDefault)ev.preventDefault();
   if(pNew.value!==pNew2.value){stato('Le due nuove password non coincidono',true);return}
   salva.disabled=true;stato('Cambio password in corso…');
   try{await cambiaPassword(pOld.value,pNew.value);chiudiCp();stato('Password cambiata. Usa la nuova password dal prossimo accesso.')}
   catch(e){stato('PASSWORD NON CAMBIATA: '+e.message,true)}finally{salva.disabled=false}
  };
  const status=document.createElement('div');status.id='mc-private-status';status.style.cssText='color:#f3db84;font-size:13px;font-weight:700';status.setAttribute('role','status');
  panel.append(login,connesso,cpForm,status);picker.insertAdjacentElement('afterend',panel);
  ui={login,connesso,status,sel,pwd,entra,cpForm,chiudiCp};
  login.onsubmit=async ev=>{
   if(ev&&ev.preventDefault)ev.preventDefault();
   if(!sel.value){stato('Scegli la tua squadra',true);return}
   if(!pwd.value){stato('Inserisci la password',true);return}
   entra.disabled=true;stato('Accesso in corso…');
   try{await accedi(sel.value,pwd.value);pwd.value='';mostraConnesso();await sincronizza(true);if(sess)avviaPolling();ripulisciVecchioArchivio()}
   catch(e){stato('ACCESSO NEGATO: '+e.message,true)}finally{entra.disabled=false}
  };
  agg.onclick=()=>{stato('Aggiornamento…');sincronizza(true)};
  out.onclick=()=>{if(typeof window.borrachosEsciTutto==='function')window.borrachosEsciTutto();else esci()};
  document.addEventListener('visibilitychange',()=>{if(!document.hidden&&sess)sincronizza(false)});
  sess=leggiSessione();
  if(sess){const i=SQUADRE.findIndex(s=>s[0]===sess.squadra);if(i>=0)sel.selectedIndex=i+1;mostraConnesso();stato('Riconnessione…');sincronizza(true).then(()=>{if(sess)avviaPolling()})}
  else{mostraLogin();stato('Area riservata ai 10 partecipanti: entra dalla Home cliccando il logo della tua squadra.')}
 }
 // v6: funzioni usate dal login unico della Home
 window.BorrachosMC={
  accedi:async(slug,password)=>{await accedi(slug,password)},
  sessione:()=>leggiSessione(),
  attiva:async()=>{sess=leggiSessione();if(!sess)return;if(ui){const i=SQUADRE.findIndex(s=>s[0]===sess.squadra);if(i>=0)ui.sel.selectedIndex=i+1}
   mostraConnesso();stato('Connessione…');await sincronizza(true);if(sess)avviaPolling();ripulisciVecchioArchivio()},
  esci:()=>{if(sess||leggiSessione()){sess=sess||leggiSessione();esci('Sei uscito.')}else{salvaSessione(null)}}
 };
 // L'archivio caricato a mano nelle versioni precedenti (IndexedDB) non serve più: lo elimina dal dispositivo.
 function ripulisciVecchioArchivio(){try{if(window.indexedDB)indexedDB.deleteDatabase('borrachos_match_center_privato')}catch(e){}}
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
