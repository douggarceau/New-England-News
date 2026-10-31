/* Show posters: margin boxes (evPoster) and the big flipping box under the cover (bigPoster).
   Everything is drawn from the calendar entry; no invented facts. */
(function(){
const H=x=>String(x==null?'':x).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const hash=s=>{let h=7;for(const c of String(s))h=(h*31+c.charCodeAt(0))>>>0;return h};
const clean=t=>String(t||'').split(/\s+[|@]\s+/)[0].split(/\s+[-–—]\s+(?=.*\b(tour|live|presents|show|concert)\b)/i)[0].replace(/\s*\b(all ages|21\+|18\+)\b.*$/i,'').replace(/\s*\((also|rescheduled)[^)]*\)/i,'').trim();
const GS={classical:'gala',theater:'marquee',jazz:'blue','r&b':'blue',electronic:'club',pop:'club','hip-hop':'club',latin:'club',family:'fair',community:'fair',worship:'fair',support:'fair',arts:'gallery'};
function kind(e,t){const g=String(e.genre||'').toLowerCase(),T=t.toLowerCase(),TV=(t+' '+(e.venue||'')).toLowerCase();
 if(/symphon|philharmon|orchestra|opera\b|ballet|nutcracker|chamber music|string quartet|choral|chorus|choir|messiah|recital|baroque|requiem/.test(T))return 'gala';
 if(GS[g])return GS[g];
 if(/symphony hall|carnegie|lincoln center|geffen hall/.test(TV))return 'gala';
 if(/broadway|musical|comedy|comedian|stand-up|improv/.test(T))return 'marquee';
 if(/jazz|blues|swing|big band/.test(T))return 'blue';
 if(/\bdj\b|dance party|rave/.test(T))return 'club';
 if(/fair|festival|parade|tree lighting|holiday|santa|pumpkin|lantern|zoo|storytime|craft|market/.test(T))return 'fair';
 if(/exhibit|gallery|museum|art show|lecture/.test(T))return 'gallery';
 return 'gig'}
function when(e){const d=e.date?new Date(e.date+'T12:00:00'):null;
 return {DW:d?d.toLocaleDateString('en-US',{weekday:'long'}):'',dw:d?d.toLocaleDateString('en-US',{weekday:'short'}).toUpperCase():'',MO:d?d.toLocaleDateString('en-US',{month:'short'}).toUpperCase():'',MON:d?d.toLocaleDateString('en-US',{month:'long'}):'',DY:d?d.getDate():'',
  tm:String(e.time||'').replace(/:00/g,'').replace(/\s*(am|pm)/gi,(m,x)=>' '+x.toUpperCase()).trim()}}
window.__epKind=(e,t)=>kind(e,t);
const KICK={gala:'In Concert',marquee:'Now Playing',gig:'Live Music',blue:'Live Jazz',club:'Live',fair:'Come One, Come All',gallery:'The Arts'};
const GIGPAL=[{bg:'#e8341c',ink:'#fff',acc:'#ffd400'},{bg:'#1b4dff',ink:'#fff',acc:'#ffd400'},{bg:'#ffcc00',ink:'#111',acc:'#e8341c'},{bg:'#0f9d6b',ink:'#fff',acc:'#ffe14d'},{bg:'#ff4fa3',ink:'#fff',acc:'#111'},{bg:'#111',ink:'#fff',acc:'#ff6a1a'}];
const GALPAL=[['#ffd400','#e3170a','#1b4dff'],['#e3170a','#1b4dff','#ffd400'],['#1b4dff','#ffd400','#e3170a']];
/* --- art --- */
function fan(col){let s='<svg class="art fan" viewBox="0 0 200 104" preserveAspectRatio="xMidYMax meet" aria-hidden="true"><g fill="none" stroke="'+col+'" stroke-width=".8">';
 for(let i=0;i<=18;i++){const a=Math.PI*(i/18),x=100-Math.cos(a)*96,y=102-Math.sin(a)*96;s+='<line x1="100" y1="102" x2="'+x.toFixed(1)+'" y2="'+y.toFixed(1)+'"/>'}
 [30,52,74,96].forEach(r=>s+='<path d="M'+(100-r)+' 102A'+r+' '+r+' 0 0 1 '+(100+r)+' 102"/>');return s+'</g><circle cx="100" cy="102" r="14" fill="'+col+'"/></svg>'}
function rule(col){return '<svg class="art rule" viewBox="0 0 120 10" aria-hidden="true"><g fill="'+col+'"><rect x="0" y="4.5" width="48" height="1"/><rect x="72" y="4.5" width="48" height="1"/><path d="M60 0l5 5-5 5-5-5z"/><circle cx="51" cy="5" r="1.5"/><circle cx="69" cy="5" r="1.5"/></g></svg>'}
function speaker(c){let s='<svg class="art spk" viewBox="0 0 100 100" aria-hidden="true"><circle cx="50" cy="50" r="48" fill="#0006"/>';[44,36,28,18].forEach((r,i)=>s+='<circle cx="50" cy="50" r="'+r+'" fill="none" stroke="'+c+'" stroke-opacity="'+(0.25+i*0.15)+'" stroke-width="'+(i===3?6:2)+'"/>');return s+'<circle cx="50" cy="50" r="8" fill="'+c+'"/></svg>'}
function bunting(h){const C=['#e3170a','#1b4dff','#ffffff','#0f9d6b','#ff8a00','#7a2bd9'];let s='<svg class="art bunt" viewBox="0 0 200 40" preserveAspectRatio="none" aria-hidden="true"><path d="M0 4 Q100 22 200 4" fill="none" stroke="#5a1606" stroke-width="1.2"/>';
 for(let i=0;i<10;i++){const x=6+i*19,y=4+Math.sin(Math.PI*(x/200))*9.5;s+='<path d="M'+x+' '+y.toFixed(1)+'l14 '+(1).toFixed(1)+'l-7 16z" fill="'+C[(i+h)%C.length]+'" stroke="#0002" stroke-width=".5"/>'}return s+'</svg>'}
function bauhaus(p,h){const r=h%3;return '<svg class="art bau" viewBox="0 0 100 100" preserveAspectRatio="xMidYMid slice" aria-hidden="true"><circle cx="'+(r===0?68:34)+'" cy="34" r="30" fill="'+p[0]+'"/><rect x="'+(r===1?52:8)+'" y="56" width="40" height="40" fill="'+p[1]+'"/><path d="M'+(r===2?40:58)+' 96 L'+(r===2?70:88)+' 44 L'+(r===2?100:118)+' 96z" fill="'+p[2]+'"/><rect x="0" y="0" width="100" height="3" fill="#111"/></svg>'}
function eq(n){let s='<span class="art eq" aria-hidden="true">';for(let i=0;i<n;i++)s+='<i style="animation-delay:-'+((i*0.37)%1.4).toFixed(2)+'s;height:'+(20+((i*53)%70))+'%"></i>';return s+'</span>'}
function sax(){return '<svg class="art horn" viewBox="0 0 100 160" aria-hidden="true"><path d="M58 4h10v8l-6 2v70c0 30-8 52-30 60-14 5-28-2-28-16 0-9 7-15 16-15 10 0 14 6 14 14l0 4c8-4 12-16 12-34V14l-6-2z" fill="#e8b818"/><g fill="#0b2a5b">'+[30,44,58,72].map(y=>'<circle cx="62" cy="'+y+'" r="3"/>').join('')+'</g></svg>'}
/* --- margin poster (landscape ~300x180) --- */
window.evPoster=function(a,s){try{
 const e=s.ev||{},t=clean(s.bigText);if(!t)return;const st=kind(e,t),h=hash(t),w=when(e);
 const L=t.length,sz=L<=12?'s1':L<=24?'s2':L<=40?'s3':'s4';
 const ven=H(e.venue||''),hood=H(e.hood||''),vl=ven+(hood&&!ven.toLowerCase().includes(hood.toLowerCase())?' · '+hood:'');
 const title='<span class="ep-t '+sz+'">'+H(t)+'</span>',k='<span class="ep-k">'+(st==='marquee'&&/comed/i.test(t)?'Live Comedy':KICK[st])+'</span>',cta='<span class="ep-cta">Tickets &amp; info →</span>';
 const dl=[w.dw,w.MO&&(w.MO+' '+w.DY),w.tm].filter(Boolean).join(' · ');let h2,sty='';
 if(st==='gala')h2=fan('#b48a2c')+k+title+'<span><span class="ep-d">'+H(dl)+'</span></span><span class="ep-v">'+vl+'</span>';
 else if(st==='marquee')h2='<span class="beam b1"></span><span class="beam b2"></span>'+k+title+'<span class="ep-foot"><span><span class="ep-d" style="display:block">'+H(dl)+'</span><span class="ep-v" style="display:block">'+vl+'</span></span>'+cta+'</span>';
 else if(st==='gig'){const P=GIGPAL[h%GIGPAL.length];sty='--bg:'+P.bg+';--ink:'+P.ink+';--acc:'+P.acc;h2=speaker(P.ink)+k+title+'<span class="ep-d">'+H(w.MO)+'<b>'+w.DY+'</b>'+H(w.tm)+'</span><span class="ep-foot"><span class="ep-v">'+vl+'</span>'+cta+'</span>'}
 else if(st==='blue')h2='<span class="ep-d">'+H(w.dw)+'<b>'+w.DY+'</b>'+H(w.MO)+'<i>'+H(w.tm)+'</i></span><span class="ep-main">'+k+title+'<span class="ep-v">'+vl+'</span></span>'+cta;
 else if(st==='club')h2=eq(18)+k+title+'<span class="ep-foot"><span><span class="ep-d" style="display:block">'+H(dl)+'</span><span class="ep-v" style="display:block">'+vl+'</span></span>'+cta+'</span>';
 else if(st==='fair')h2=bunting(h)+k+title+'<span class="ep-d">'+H(dl)+(ven?' · '+ven:'')+'</span>';
 else h2=bauhaus(GALPAL[h%3],h)+k+title+'<span class="ep-foot"><span class="ep-d">'+H(dl)+'</span><span class="ep-v">'+vl+'</span></span>';
 const box=a.parentNode;box.classList.add('evp');['border','border-top','outline'].forEach(x=>box.style.setProperty(x,'0','important'));
 a.innerHTML='<span class="ep ep-'+st+'" style="'+sty+'">'+h2+'</span>';
}catch(_){}};
/* --- big poster (portrait 2:3, the flipping box under the cover) --- */
window.bigPoster=function(e,region){try{
 const t=clean(e.artists);if(!t)return null;const st=kind(e,t),h=hash(t),w=when(e);
 const L=t.length,sz=L<=10?'x1':L<=18?'x2':L<=30?'x3':L<=48?'x4':'x5';
 const ven=H(e.venue||''),addr=H(String(e.address||'').replace(/,?\s*(Rhode Island|Massachusetts|New York),?\s*(RI|MA|NY)?\s*\d{5}.*$/i,'').replace(e.venue+', ','')),hood=H(e.hood||'');
 const title='<span class="bp-t '+sz+'">'+H(t)+'</span>';const reg=H(region||'');
 const go='<span class="bp-go">'+(e.url?'Tickets &amp; info':'See the calendar')+' →</span>';
 let b,sty='';
 if(st==='gala')b='<span class="bp-frame"></span>'+fan('#a8822f')+'<span class="bp-k">'+KICK.gala+' · '+reg+'</span>'+title+rule('#a8822f')+'<span class="bp-d">'+H(w.DW)+'<br>'+H(w.MON)+' '+w.DY+(w.tm?' · '+H(w.tm):'')+'</span><span class="bp-v">'+ven+(addr?'<small>'+addr+'</small>':'')+'</span>'+go;
 else if(st==='marquee')b='<span class="cur l"></span><span class="cur r"></span><span class="beam b1"></span><span class="beam b2"></span><span class="bp-sign"><span>'+(/comed/i.test(t)?'Live Comedy':'Now Playing')+'</span></span>'+title+'<span class="bp-d">'+H(w.dw)+' · '+H(w.MO)+' '+w.DY+(w.tm?' · '+H(w.tm):'')+'</span><span class="bp-v">'+ven+(hood?'<small>'+hood+'</small>':'')+'</span>'+go;
 else if(st==='gig'){const P=GIGPAL[h%GIGPAL.length];sty='--bg:'+P.bg+';--ink:'+P.ink+';--acc:'+P.acc;b='<span class="bp-k">'+reg+' · Live</span>'+title+speaker(P.ink)+'<span class="bp-tear"><b>'+H(w.dw)+'</b><b class="n">'+H(w.MO)+' '+w.DY+'</b>'+(w.tm?'<b>'+H(w.tm)+'</b>':'')+'</span><span class="bp-v">'+ven+(hood?' · '+hood:'')+'</span>'+go}
 else if(st==='blue')b='<span class="disc"><b>'+w.DY+'</b><i>'+H(w.MO)+'</i></span>'+'<span class="bp-k">'+KICK.blue+' · '+reg+'</span>'+title+'<span class="bars"><i></i><i></i><i></i></span><span class="bp-d">'+H(w.DW)+(w.tm?' · '+H(w.tm):'')+'</span><span class="bp-v">'+ven+(hood?'<small>'+hood+'</small>':'')+'</span>'+go;
 else if(st==='club')b='<span class="laser"></span><span class="floor"></span>'+eq(24)+'<span class="bp-k">'+reg+' · Live</span>'+title+'<span class="bp-d">'+H(w.dw)+' · '+H(w.MO)+' '+w.DY+(w.tm?' · '+H(w.tm):'')+'</span><span class="bp-v">'+ven+'</span>'+go;
 else if(st==='fair')b=bunting(h)+'<span class="bp-k">'+KICK.fair+'</span>'+title+'<span class="bp-ticket"><b>'+H(w.DW)+'</b><b class="n">'+H(w.MON)+' '+w.DY+'</b>'+(w.tm?'<b>'+H(w.tm)+'</b>':'')+'</span><span class="bp-v">'+ven+(addr?'<small>'+addr+'</small>':'')+'</span>'+go;
 else b=bauhaus(GALPAL[h%3],h)+'<span class="bp-k">'+KICK.gallery+' · '+reg+'</span>'+title+'<span class="bp-d">'+H(w.DW)+', '+H(w.MON)+' '+w.DY+(w.tm?' · '+H(w.tm):'')+'</span><span class="bp-v">'+ven+(addr?'<small>'+addr+'</small>':'')+'</span>'+go;
 return '<span class="bp bp-'+st+'" style="'+sty+'">'+b+'</span>';
}catch(_){return null}};

/* --- story & headline cards: every margin card is artwork --- */
function vinyl(lab){let s='<svg class="art vin" viewBox="0 0 100 100" aria-hidden="true"><circle cx="50" cy="50" r="49" fill="#0c0c0c"/>';for(let r=46;r>20;r-=2.2)s+='<circle cx="50" cy="50" r="'+r.toFixed(1)+'" fill="none" stroke="#ffffff'+(r%4<2?'14':'0a')+'" stroke-width=".6"/>';return s+'<path d="M50 1a49 49 0 0 1 42 24L50 50z" fill="#ffffff10"/><circle cx="50" cy="50" r="17" fill="'+lab+'"/><circle cx="50" cy="50" r="2.2" fill="#0c0c0c"/></svg>'}
function masks(c){return '<svg class="art msk" viewBox="0 0 120 80" aria-hidden="true"><g fill="none" stroke="'+c+'" stroke-width="2.2"><path d="M8 10q22-8 44 0v22c0 16-10 28-22 28S8 48 8 32z"/><path d="M68 18q22-8 44 0v22c0 16-10 28-22 28S68 56 68 40z"/></g><g fill="'+c+'"><path d="M18 26q5-4 10 0q-5 3-10 0zM32 26q5-4 10 0q-5 3-10 0zM20 42q10 9 20 0q-10 3-20 0z"/><path d="M78 34q5 4 10 0q-5-3-10 0zM92 34q5 4 10 0q-5-3-10 0zM80 56q10-9 20 0q-10-3-20 0z"/></g></svg>'}
function confetti(h){const C=['#ff4fa3','#ffd400','#1b4dff','#0f9d6b','#ff6a1a','#7a2bd9'];let s='<svg class="art cft" viewBox="0 0 300 180" preserveAspectRatio="xMidYMid slice" aria-hidden="true">';let x=h;for(let i=0;i<34;i++){x=(x*1103515245+12345)>>>0;const px=x%300,py=(x>>>9)%180,r=(x>>>17)%3,c=C[(x>>>5)%C.length];s+=r===0?'<circle cx="'+px+'" cy="'+py+'" r="3" fill="'+c+'"/>':'<rect x="'+px+'" y="'+py+'" width="7" height="3" fill="'+c+'" transform="rotate('+((x>>>11)%180)+' '+px+' '+py+')"/>'}return s+'</svg>'}
const STPAL=[['#0b1f3a','#e8b818'],['#3a0b1f','#ff8fb1'],['#0b3a2e','#7fffd4'],['#2a0b3a','#d9a4ff'],['#3a240b','#ffb347']];
window.artCard=function(a,s){try{
 const t=String(s.bigText||s.name||'').trim();if(!t)return;const h=hash(t);
 const st=(typeof STORIES!=='undefined'&&s.story)?STORIES.find(x=>x.slug===s.story):null;
 const ext=!st&&s.ext;const topic=st?String(st.topic||''):'news';
 let v=ext?'press':/music/.test(topic)?'vinyl':/stage|comedy|theat/.test(topic)?'stage':/family|people|community/.test(topic)||(st&&st.theme==='halloween')?'party':'cover';
 const L=t.length,sz=L<=34?'s1':L<=56?'s2':L<=80?'s3':'s4';
 const kick=H(String(s.tag||'').replace(/^RHODE ISLAND NEWS|^FEATURED STORY/i,m=>m.toLowerCase().includes('news')?'Local news':'Featured story'));
 const outlet=H(s.name||'');let b,sty='';
 if(v==='press')b='<span class="ac-mast">'+outlet+'</span><span class="ac-k">'+kick+'</span><span class="ac-t '+sz+'">'+H(t)+'</span><span class="ac-go">Read it at '+outlet+' ↗</span>';
 else if(v==='vinyl'){const P=STPAL[h%STPAL.length];sty='--bg:'+P[0]+';--ac:'+P[1];b=vinyl(P[1])+'<span class="ac-k">'+kick+'</span><span class="ac-t '+sz+'">'+H(t)+'</span><span class="ac-go">Read the story →</span>'}
 else if(v==='stage')b='<span class="beam b1"></span>'+masks('#e8b818')+'<span class="ac-k">'+kick+'</span><span class="ac-t '+sz+'">'+H(t)+'</span><span class="ac-go">Read the story →</span>';
 else if(v==='party')b=confetti(h)+'<span class="ac-k">'+kick+'</span><span class="ac-t '+sz+'">'+H(t)+'</span><span class="ac-go">Read the story →</span>';
 else{const P=GALPAL[h%3];sty='--c1:'+P[0]+';--c2:'+P[1];b='<span class="ac-band"></span><span class="ac-dot"></span><span class="ac-k">'+kick+'</span><span class="ac-t '+sz+'">'+H(t)+'</span><span class="ac-go">Read the story →</span>'}
 const box=a.parentNode;box.classList.add('evp');['border','border-top','outline'].forEach(x=>box.style.setProperty(x,'0','important'));
 a.innerHTML='<span class="ep ac ac-'+v+'" style="'+sty+'">'+b+'</span>';
}catch(_){}};
/* --- auto-fit titles so no word ever breaks --- */
function fit(el){if(el.dataset.fit)return;const cs=getComputedStyle(el);let f=parseFloat(cs.fontSize);if(!f||!el.clientWidth)return;el.dataset.fit=1;let n=0;
 while((el.scrollWidth>el.clientWidth+1||el.scrollHeight-el.clientHeight>f*.55)&&f>9&&n++<40){f*=.93;el.style.fontSize=f.toFixed(1)+'px'}}
function scaleAll(){document.querySelectorAll('.lsrow .lspot.evp>a>.ep').forEach(ep=>{const box=ep.parentNode;const W=box.clientWidth,Hh=box.clientHeight;if(!W||!Hh)return;const s=W/300;if(ep.dataset.sc===W+'x'+Hh)return;ep.dataset.sc=W+'x'+Hh;const S=(k,v)=>ep.style.setProperty(k,v,'important');S('width','300px');S('max-width','none');S('min-width','300px');S('height',(Hh/s).toFixed(1)+'px');S('max-height','none');S('right','auto');S('bottom','auto');S('left','0');S('top','0');S('transform-origin','0 0');S('transform','scale('+s.toFixed(4)+')')})}
function fitAll(){scaleAll();if(!fontsOk)return;document.querySelectorAll('.bp-t:not([data-fit]),.ep-t:not([data-fit]),.ac-t:not([data-fit])').forEach(fit)}
window.epFit=fitAll;let fontsOk=!document.fonts;if(document.fonts){document.fonts.ready.then(()=>{fontsOk=true;refit()});document.fonts.addEventListener&&document.fonts.addEventListener('loadingdone',()=>refit())}
function refit(){document.querySelectorAll('[data-fit]').forEach(e=>{e.style.fontSize='';delete e.dataset.fit});fitAll()}
new MutationObserver(()=>requestAnimationFrame(fitAll)).observe(document.documentElement,{childList:true,subtree:true});
addEventListener('resize',()=>{document.querySelectorAll('.ep[data-sc]').forEach(e=>delete e.dataset.sc);refit()});setInterval(scaleAll,1500);
})();
/* Top story box: alternates the story with full posters for the biggest upcoming shows */
(function(){
const BIG=/madison square|msg|barclays|radio city|beacon|td garden|fenway|gillette|mgm music hall|agganis|wang|citizens|boch|amica|ppac|providence performing|vets|ryan center|bally|stadium theatre|park theatre|carnegie|lincoln center|geffen|metropolitan opera|symphony hall|apollo|kings theatre|united palace|brooklyn paramount|terminal 5|hammerstein|emerson colonial|trinity rep|newport/i;
let i=0,on=false,timer=0;
function region(){try{const t=(window.jtEvPool()[0]||{}).tag||'';const r=t.split(' · ')[0].replace(/^(IN|ON)\s+(THE\s+)?/i,'').toLowerCase();return r==='island'?'Jamestown':r.replace(/\b\w/g,c=>c.toUpperCase())}catch(_){return ''}}
function list(){try{const P=(window.jtEvPool&&window.jtEvPool())||[];const E=P.map(p=>p.ev).filter(Boolean);const big=E.filter(e=>BIG.test(e.venue||''));return (big.length>=4?big:E).slice(0,24)}catch(_){return[]}}
function tick(){const box=document.querySelector('.cvr .cvbrk');if(!box||document.hidden||box.matches(':hover'))return;
 let ov=box.querySelector(':scope>.bpx');
 if(!ov){ov=document.createElement('span');ov.className='bpx';box.appendChild(ov);
  ov.addEventListener('click',e=>{if(!box.classList.contains('bpx-on'))return;e.preventDefault();e.stopPropagation();const u=ov.dataset.href;if(u){if(/^https?:/.test(u))window.open(u,'_blank','noopener');else{try{go('cal')}catch(_){location.hash='cal'}}}},true)}
 if(on){box.classList.remove('bpx-on');on=false;return}
 const L=list();if(!L.length)return;const e=L[i++%L.length];const h=window.bigPoster&&window.bigPoster(e,region());if(!h)return;
 ov.innerHTML=h;ov.dataset.href=e.url||'';box.classList.add('bpx-on');on=true;
 requestAnimationFrame(()=>{try{window.epFit&&window.epFit()}catch(_){}})}
setTimeout(()=>{tick();timer=setInterval(tick,9000)},9000);
})();
/* Business cards on the left: a wave flips them one by one into events, then back to businesses */
(function(){
const H2=x=>String(x==null?'':x).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const KIND=['gala','marquee','gig','blue','club','fair','gallery'];
function style(e,t){try{return (window.__epKind&&window.__epKind(e,t))||'gig'}catch(_){return 'gig'}}
function face(e,n){const t=String(e.artists||'').split(/\s+[|@]\s+/)[0].replace(/\s*\((also|rescheduled)[^)]*\)/i,'').trim();const st=style(e,t);
 const d=e.date?new Date(e.date+'T12:00:00'):null,MO=d?d.toLocaleDateString('en-US',{month:'short'}).toUpperCase():'',DY=d?d.getDate():'',DW=d?d.toLocaleDateString('en-US',{weekday:'short'}).toUpperCase():'';
 const tm=String(e.time||'').replace(/:00/g,'').replace(/\s*(am|pm)/gi,(m,x)=>' '+x.toUpperCase()).trim();
 return '<span class="fb fb-'+st+' fbv'+(n%4)+'"><span class="fb-d"><i>'+H2(MO)+'</i><b>'+DY+'</b></span><span class="fb-x"><span class="fb-t">'+H2(t)+'</span><span class="fb-v">'+H2([DW,tm,e.venue].filter(Boolean).join(' · '))+'</span></span></span>'}
function rows(){const L=document.getElementById('dirList');if(!L||!L.offsetParent)return[];const R=L.getBoundingClientRect();
 return [...L.querySelectorAll(':scope>.drow')].filter(r=>{const b=r.getBoundingClientRect();return b.height>20&&b.height<90&&b.bottom>R.top&&b.top<R.bottom})}
function flip(r,toEv,e,n){return new Promise(res=>{if(r.matches(':hover')||(r.querySelector('.dd')&&!r.querySelector('.dd').hidden)){res();return}
 r.style.transition='transform .26s ease-in';r.style.transform='perspective(700px) rotateX(90deg)';
 setTimeout(()=>{if(toEv){let f=r.querySelector(':scope>.fb');if(f)f.remove();r.insertAdjacentHTML('beforeend',face(e,n));f=r.querySelector(':scope>.fb');f.dataset.href=e.url||'';r.classList.add('evf')}else{r.classList.remove('evf');const f=r.querySelector(':scope>.fb');if(f)f.remove()}
  r.style.transition='none';r.style.transform='perspective(700px) rotateX(-90deg)';
  requestAnimationFrame(()=>requestAnimationFrame(()=>{r.style.transition='transform .26s ease-out';r.style.transform='';setTimeout(()=>{r.style.transition='';res()},280)}))},260)})}
const wait=ms=>new Promise(r=>setTimeout(r,ms));let k=0;
async function loop(){for(;;){await wait(7000);if(document.hidden||matchMedia('(prefers-reduced-motion:reduce)').matches)continue;
 const P=((window.jtEvPool&&window.jtEvPool())||[]).map(p=>p.ev).filter(Boolean);const R=rows();if(!P.length||!R.length)continue;
 for(let i=0;i<R.length;i++){await flip(R[i],true,P[(k+i)%P.length],i);await wait(260)}k+=R.length;
 await wait(6500);
 const B=[...document.querySelectorAll('#dirList>.drow.evf')];for(const r of B){await flip(r,false);await wait(260)}}}
document.addEventListener('click',e=>{const f=e.target.closest&&e.target.closest('#dirList .drow.evf>.fb');if(!f)return;e.preventDefault();e.stopPropagation();const u=f.dataset.href;if(u&&/^https?:/.test(u))window.open(u,'_blank','noopener');else{try{go('cal')}catch(_){location.hash='cal'}}},true);
setTimeout(loop,2000);
})();
