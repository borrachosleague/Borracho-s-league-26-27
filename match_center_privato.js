/* BORRACHOS MATCH CENTER PRIVATO 1.0
 * Nessuna chiamata a Fantacalcio o Supabase. I dati individuali rimangono
 * nella memoria locale del browser (IndexedDB), mai inviati a GitHub.
 * Il punteggio ufficiale della partita proviene sempre da dati.json.
 */
(function () {
  'use strict';
  var SCHEMA='borrachos.matchcenter.privato.v1';
  var DB='borrachos_match_center_privato',STORE='archivi';
  var archivio=null;
  var statusNode;

  function norm(v){
    var s=String(v||'').normalize('NFKD').replace(/[\u0300-\u036f]/g,'').toLowerCase().replace(/[^a-z0-9]+/g,' ').trim();
    var names={
      'tricchetracht':'tricchetracht francoforte',
      'tricchetracht frankfurt':'tricchetracht francoforte',
      'sesto asensio':'il sesto asensio',
      'atl improvvisato':'atletico improvvisato',
      'pesciculini':'pesciculini fc',
      'internazionanale':'fc internazioanale',
      'interna ziona nale':'fc internazioanale',
      'internaziona nale':'fc internazioanale',
      'asparaghese':'ac asparaghese',
      'shark fc':'shark'
    };
    return names[s]||s;
  }
  function key(g,c,a){return String(g)+'|'+norm(c)+'|'+norm(a);}
  function validPlayer(x){
    return x && typeof x.nome==='string' && x.nome.trim().length>1 &&
      [x.scr,x.cscr].every(function(v){return v==null||(typeof v==='number'&&Number.isFinite(v)&&v>=0&&v<20);});
  }
  function validate(data){
    if(!data||data.schema!==SCHEMA||!Array.isArray(data.giornate)||!data.giornate.length)throw Error('Formato archivio non riconosciuto');
    var total=0,known={};
    data.giornate.forEach(function(g){
      if(!Number.isInteger(g.giornata)||g.giornata<1||g.giornata>36||!Array.isArray(g.partite)||g.partite.length!==5)
        throw Error('Giornata o numero partite non valido: '+g.giornata);
      g.partite.forEach(function(p){
        if(!p||!p.casa||!p.trasferta)throw Error('Partita incompleta alla G'+g.giornata);
        [p.casa,p.trasferta].forEach(function(t){
          if(!t.nome||!Array.isArray(t.titolari)||t.titolari.length!==11||!Array.isArray(t.panchina)||t.panchina.length>14)
            throw Error('Formazione non valida: '+(t.nome||'squadra sconosciuta'));
          if(!t.titolari.concat(t.panchina).every(validPlayer))throw Error('Voti o giocatori non validi: '+t.nome);
          var seen=new Set();
          t.titolari.concat(t.panchina).forEach(function(player){
            var k=norm(player.nome);
            if(seen.has(k))throw Error('Giocatore duplicato in '+t.nome+': '+player.nome);
            seen.add(k);
          });
        });
        var k=key(g.giornata,p.casa.nome,p.trasferta.nome);
        if(known[k])throw Error('Partita duplicata: '+k);
        known[k]=p; total++;
      });
    });
    return {total:total,index:known,days:data.giornate.length};
  }
  function status(message,error){
    if(statusNode){statusNode.textContent=message;statusNode.style.color=error?'#ff9d9d':'#f3db84';}
  }
  function indexedDBOpen(){
    return new Promise(function(resolve,reject){
      if(!window.indexedDB){reject(Error('Archivio browser non disponibile'));return;}
      var req=indexedDB.open(DB,1);
      req.onupgradeneeded=function(){if(!req.result.objectStoreNames.contains(STORE))req.result.createObjectStore(STORE);};
      req.onsuccess=function(){resolve(req.result);};req.onerror=function(){reject(req.error||Error('Database non disponibile'));};
    });
  }
  async function storage(mode,value){
    var db=await indexedDBOpen();
    try{
      return await new Promise(function(resolve,reject){
        var tx=db.transaction(STORE,mode==='get'?'readonly':'readwrite');
        var st=tx.objectStore(STORE);
        var req=mode==='get'?st.get('current'):mode==='put'?st.put(value,'current'):st.delete('current');
        req.onsuccess=function(){resolve(req.result);};req.onerror=function(){reject(req.error||Error('Operazione database fallita'));};
      });
    }finally{db.close();}
  }
  function rerender(){
    if(typeof mcArchivio==='undefined'||!mcArchivio||typeof mcRenderGiornata!=='function')return;
    var previous=mcGiornata;
    var detail=document.getElementById('live-detail');
    var wasOpen=detail&&detail.style.display==='block';
    var index=typeof livePartitaAttiva==='number'?livePartitaAttiva:0;
    mcRenderGiornata(previous||mcArchivio[mcArchivio.length-1].giornata);
    if(wasOpen&&typeof mostraLivePartita==='function')mostraLivePartita(index);
  }
  function activate(data){
    var v=validate(data);archivio=v.index;
    status('Archivio PRIVATO: '+v.days+' giornate, '+v.total+' partite · dati solo su questo dispositivo');
    rerender();
  }
  function buttons(){
    var picker=document.querySelector('#page-live .match-day-picker');
    if(!picker||document.getElementById('mc-private-tools'))return;
    var wrap=document.createElement('div');wrap.id='mc-private-tools';
    wrap.style.cssText='text-align:center;margin:0 auto 15px;display:flex;flex-wrap:wrap;justify-content:center;align-items:center;gap:8px';
    var input=document.createElement('input');input.id='mc-private-input';input.type='file';input.accept='.json,application/json';input.hidden=true;
    var btn=document.createElement('button');btn.type='button';btn.textContent='📂 CARICA ARCHIVIO PRIVATO';
    var clear=document.createElement('button');clear.type='button';clear.textContent='✕ RIMUOVI DATI PRIVATI';
    [btn,clear].forEach(function(x){x.style.cssText='border:1px solid #ffd54a;border-radius:8px;background:#201b23;color:#ffd54a;padding:9px 12px;font-weight:800;cursor:pointer';});
    statusNode=document.createElement('div');statusNode.id='mc-private-status';statusNode.setAttribute('role','status');statusNode.style.cssText='width:100%;color:#f3db84;font-size:12px';
    status('Nessun archivio privato caricato · risultati sempre disponibili');
    btn.onclick=function(){input.click();};
    input.onchange=async function(){
      try{
        var f=input.files&&input.files[0];if(!f)return;
        if(f.size>25*1024*1024)throw Error('Archivio troppo grande (massimo 25 MB)');
        var data=JSON.parse(await f.text());
        validate(data);
        if(typeof mcArchivio!=='undefined'&&mcArchivio){
          data.giornate.forEach(function(g){
            var real=mcArchivio.find(function(x){return Number(x.giornata)===Number(g.giornata);});
            if(!real)throw Error('Giornata '+g.giornata+' non presente nei risultati ufficiali');
            g.partite.forEach(function(p){
              if(!real.partite.some(function(r){return key(g.giornata,r.casa,r.trasferta)===key(g.giornata,p.casa.nome,p.trasferta.nome);}))
                throw Error('Partita non riconosciuta G'+g.giornata+': '+p.casa.nome+' - '+p.trasferta.nome);
            });
          });
        }
        activate(data);
        try{await storage('put',data);}catch(e){status('Archivio utilizzabile ORA, ma non memorizzato nel browser: '+e.message,true);}
      }catch(e){status('IMPORTAZIONE ANNULLATA: '+e.message,true);}finally{input.value='';}
    };
    clear.onclick=async function(){
      archivio=null;rerender();
      try{await storage('delete');status('Archivio privato rimosso da questo browser');}
      catch(e){status('Dati tolti dalla pagina. Cancellazione archivio browser non riuscita: '+e.message,true);}
    };
    wrap.appendChild(input);wrap.appendChild(btn);wrap.appendChild(clear);wrap.appendChild(statusNode);
    picker.insertAdjacentElement('afterend',wrap);
    storage('get').then(function(saved){if(saved)activate(saved);}).catch(function(){status('Archivio locale non disponibile: puoi comunque caricare il file a mano');});
  }
  function install(){
    if(typeof mcPartita!=='function')return;
    var original=mcPartita;
    mcPartita=function(r){
      var result=original(r);
      if(!archivio)return result;
      var found=archivio[key(mcGiornata,r.casa,r.trasferta)];
      if(!found)return result;
      ['casa','trasferta'].forEach(function(side){
        var t=found[side];
        result[side].titolari=t.titolari;
        result[side].panchina=t.panchina;
        result[side].consegnata=true;
        result[side].modulo=t.modulo||null;
      });
      result.archivioSenzaFormazioni=false;
      return result;
    };
    // Match Center archivio: riepilogo fedele al referto, senza sommare i soli titolari.
    // Il referto non indica quali riserve siano effettivamente conteggiate.
    if(typeof renderLiveMatch==='function'){
      var renderOriginale=renderLiveMatch;
      renderLiveMatch=function(p){
        var html=renderOriginale(p);
        if(!p||p.archivioSenzaFormazioni||!p.casa||!p.trasferta)return html;
        var teams=[p.casa,p.trasferta],n=0;
        return html.replace(/<aside class="live-side-summary live-side-[^"]+">[\\s\\S]*?<\\/aside>/g,function(blocco){
          var t=teams[n++];if(!t)return blocco;
          var mod=t.mod_dif==null?null:Number(t.mod_dif);
          var totale=Number(t.totale);
          var fmt=function(v){return Number.isFinite(v)?v.toFixed(1).replace('.',','):'—';};
          var primaMod=(Number.isFinite(totale)&&Number.isFinite(mod))?fmt(totale-mod):'—';
          return blocco
            .replace(/<span>PAGELLA<\\/span><strong>[^<]*<\\/strong>/,'<span>PAGELLA (NON DISPONIBILE)</span><strong>—</strong>')
            .replace(/<span>FANTAVOTO<\\/span><strong>[^<]*<\\/strong>/,'<span>PUNTI PRIMA MOD. DIFESA</span><strong>'+primaMod+'</strong>')
            .replace(/<span>MOD\\. DIFESA<\\/span><strong>[^<]*<\\/strong>/,'<span>MOD. DIFESA</span><strong>'+(mod===null?'—':fmt(mod))+'</strong>');
        });
      };
    }
    if(typeof liveCartellini==='function'){
      var icons={gol:'⚽',assist:'🅰️',ammonizione:'🟨',espulsione:'🟥',gol_subito:'🥅',rig_parato:'🧤',rig_sbagliato:'❌',autogol:'🔴',gol_decisivo:'🏆'};
      var base=liveCartellini;
      liveCartellini=function(p){
        var old=base(p), extra='';
        var events=p&&p.eventi;
        if(events&&typeof events==='object')Object.keys(icons).forEach(function(k){
          var n=Number(events[k]);
          if(Number.isInteger(n)&&n>0&&n<100)extra+='<span title="'+k.replace(/_/g,' ')+'" style="margin-left:3px">'+icons[k]+(n>1?'×'+n:'')+'</span>';
        });
        return old+extra;
      };
    }
    if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',buttons,{once:true});else buttons();
  }
  install();
})();