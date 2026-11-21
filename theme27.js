/* 2027 theme, shared by all three city sites. Site settings come from window.T27 = {a:accent, k:'kicker', n:'NAME', tz:'America/New_York'} */
window.WO_CATS=[['Live Music',/^(live|rock|indie|jazz|pop|electronic|folk|r&b|latin|metal|hip-hop|punk|experimental|world|goth|country|blues|soul|reggae|funk)$/i],['Comedy',/^comedy$/i],['Shows',/^(theater|dance|classical|opera|stage)$/i],['Film',/^film$/i],['Art',/^(arts|art)$/i],['Nightlife',/^(clubs|club|nightlife)$/i],['Food & Drink',/^(food|drink|dining)$/i],['Outdoors',/^recreation$/i],['Talks & Books',/^talks$/i]];
window.WO_OTHER='More Events';window.WO_SKIP=/^(sports|support|worship|drag)$/i;
(function(){
const C=window.T27||{};const SEC0=(location.search.match(/[?&]section=(news|tech|music|calendar|explore)/)||[])[1]||'';const STORY0=/[?&]story=/.test(location.search);const R=document.documentElement;
R.setAttribute('data-t27','');if(C.keepArt)R.setAttribute('data-keepart','');R.style.setProperty('--a',C.a||'#E10600');
const f=document.createElement('link');f.rel='stylesheet';f.href='https://fonts.googleapis.com/css2?family=Geist:wght@400;500;600;700;800&display=swap';document.head.appendChild(f);
/* calendar filter hook used by vCal: music only, or the weekend */
const MUS=/^(live|rock|indie|jazz|pop|electronic|folk|r&b|latin|metal|hip-hop|punk|experimental|world|goth|country|music|blues|soul|reggae|funk|classical|clubs)$/i;
let MODE=null,WK=null,SF=null;window.T27S=s=>SF?SF(s):true;
window.T27F=e=>{if(/^(support|recovery|worship)$/i.test(e.genre||'')||/\b(support group|recovery|anonymous|al-anon|12[- ]step|grief|bereavement|self[- ]help)\b/i.test(e.artists||''))return false;if(MODE==='music')return MUS.test(e.genre||'');if(MODE==='wk'&&WK)return e.date>=WK[0]&&e.date<=WK[1];return true};
const TZ=C.tz||'America/New_York';const ymd=d=>d.toLocaleDateString('en-CA',{timeZone:TZ});
function weekend(){const n=new Date(),td=ymd(n),dow=new Date(td+'T12:00:00').getDay();const a=(k)=>ymd(new Date(n.getTime()+k*864e5));
 const fri=dow===0?a(-2):dow===6?a(-1):a(5-dow);const sun=dow===0?td:dow===6?a(1):a(7-dow);return [fri<td?td:fri,sun]}
const ITEMS=[
 ['Now',()=>nav('front')],
 ['News',()=>nav('stories')],
 ['Music',()=>nav('cal','music',30)],
 ['Tech',()=>{SF=s=>/^tech-/.test(s.slug)||/\b(AI|robot|tech)\b/i.test(s.title||'');nav('stories')}],
 ['Calendar',()=>nav('cal',null,14)],
 ['Explore',()=>nav('visit')]];
function nav(v,mode,days){MODE=mode||null;try{STATE.genre='all';STATE.cq='';if(days)STATE.cdays=days;else STATE.cdays=14}catch(_){}
 try{go(v)}catch(e){const b=document.querySelector('#nav [data-go="'+v+'"]');if(b)b.click()}}
if(C.items)ITEMS.splice(0,ITEMS.length,...C.items.map(([t,v])=>[t,()=>nav(v)]));
let cur='Now';
function mark(){const mb=document.querySelector('#nav .more27');if(mb)mb.classList.toggle('on27',/^(Music|Tech|Explore)$/.test(cur));document.querySelectorAll('#nav .nb27').forEach(b=>{if(b.textContent===cur)b.setAttribute('aria-current','page');else b.removeAttribute('aria-current')});
 const sec=cur==='News'?'news':cur==='Tech'?'tech':cur==='Music'?'music':cur==='Calendar'?'calendar':cur==='Explore'?'explore':'';
 try{if(!/[?&]story=/.test(location.search)&&!(SEC0&&cur==='Now'&&!mark.done)){const u=sec?'?section='+sec:location.pathname;if(location.search!==(sec?'?section='+sec:''))history.replaceState(history.state,'',u)}}catch(_){}
 if(cur!=='Now')mark.done=1;document.title=(cur&&cur!=='Now'?cur+' | ':'')+(C.title||document.title.split(' | ').pop())}
function build(){const ae=document.activeElement,ss=ae&&ae.selectionStart,se=ae&&ae.selectionEnd;try{build0()}finally{if(ae&&ae!==document.body&&document.contains(ae)&&document.activeElement!==ae){try{ae.focus({preventScroll:true});if(ss!=null)ae.setSelectionRange(ss,se)}catch(_){}}}}
function build0(){
 const m=document.querySelector('header.mast');
 if(m&&!m.querySelector('.wm27')){const w=document.createElement('a');w.className='wm27';w.href='/';w.setAttribute('aria-label',(C.k||'')+' '+(C.n||''));
  w.innerHTML='<span class="k"><i></i>'+(C.k||'')+'</span><span class="n"'+(C.sz?' style="font-size:'+C.sz+'"':'')+'>'+(C.n||'')+'</span><span class="r"></span>';
  w.onclick=e=>{e.preventDefault();cur='Now';mark();nav('front')};(m.querySelector('div')||m).appendChild(w)}
 const n=document.getElementById('nav');
 if(n&&!n.querySelector('.nb27')){ITEMS.forEach(([t,fn],i)=>{const b=document.createElement('button');b.type='button';b.className='nb27';b.textContent=t;b.style.order=i;
  b.dataset.k=t.toLowerCase();b.onclick=()=>{cur=t;mark();if(t!=='Tech')SF=null;n.classList.remove('open27');fn();if(t==='News'||t==='Tech')setTimeout(()=>{const h=document.querySelector('#news27 h1');if(h){h.setAttribute('tabindex','-1');h.focus({preventScroll:true})}},60)};n.appendChild(b)});
  const mb=document.createElement('button');mb.type='button';mb.className='nb27 more27';mb.textContent='More';mb.style.order=50;mb.setAttribute('aria-expanded','false');mb.onclick=()=>{const o=n.classList.toggle('open27');mb.setAttribute('aria-expanded',String(o))};n.appendChild(mb);mark()}
 if(!document.querySelector('.skip27')){const s=document.createElement('a');s.className='skip27';s.href='#main27';s.textContent='Skip to content';document.body.insertBefore(s,document.body.firstChild)}
 const ft=document.querySelector('footer.site-footer');
 if(ft&&!ft.querySelector('.ft27')){const d=document.createElement('div');d.className='ft27';
  d.innerHTML=(C.foot||[]).map(f=>'<button type="button" '+(f[1][0]==='#'?'data-c="'+f[1].slice(1)+'"':'data-g="'+f[1]+'"')+'>'+f[0]+'</button>').join('')+'<button type="button" data-dir="1">Business Directory</button><button type="button" data-g="advertise">Advertising</button><button type="button" data-g="privacy">Privacy &amp; Contact</button><span class="cp">© '+new Date().getFullYear()+' Island News Media Productions LLC</span>';
  d.querySelectorAll('button').forEach(b=>b.onclick=()=>{if(b.dataset.dir){R.classList.toggle('dir27');return}if(b.dataset.c){const x=document.getElementById(b.dataset.c);if(x)x.click();return}cur='';mark();try{go(b.dataset.g)}catch(_){}});ft.insertBefore(d,ft.firstChild)}
 hero();dedupe();cal1();upd();labels();rails27();dress();fonts()}
/* any old serif or display face left over from earlier styling switches to the new faces */
const OLD=/Georgia|Playfair|PT Serif|Libre Caslon|Bodoni|Abril|DM Serif|Old Standard|Cinzel|Marcellus|Satisfy|Special Elite|Cormorant|Alfa Slab|Oswald|Anton|Bebas|Times|serif$/i;
function fonts(){document.addEventListener('keydown',e=>{if(e.key==='Escape')R.classList.remove('dir27')});
const RED=/^rgba?\((193, 18, 31|225, 6, 0|200, 16, 46)(, 1)?\)$/,swap=!/^#(E10600|C1121F)$/i.test(C.a||'');
document.body.querySelectorAll(':is(b,strong,span,a,h1,h2,h3,h4,p,button,div,small,i,em,li,summary,label,section,article,aside):not([data-f27])').forEach(e=>{e.dataset.f27='';const cs=getComputedStyle(e);
 if(swap){for(const [k,c] of [['border-left-color',cs.borderLeftColor],['border-top-color',cs.borderTopColor],['border-bottom-color',cs.borderBottomColor],['background-color',cs.backgroundColor],['color',cs.color]])if(RED.test(c))e.style.setProperty(k,'var(--a)','important')}
 const bi=cs.backgroundImage;if(bi&&/url\(/.test(bi)&&!/data:/.test(bi)&&e.getBoundingClientRect().width>120)e.style.setProperty('background-image','none','important');if(OLD.test(cs.fontFamily)){e.style.setProperty('font-family',parseFloat(cs.fontSize)>=17?'"Geist",system-ui,sans-serif':'"Geist",system-ui,sans-serif','important');e.style.setProperty('font-style','normal','important')}})}

/* lead story at the top of the front page, and one place per story */
function leadStory(){let L=[];try{L=STORIES}catch(_){return null}const td=ymd(new Date());
 const ok=s=>s&&s.title&&!/^today-(and-tonight|on-the-island)-/.test(s.slug)&&(!s.until||s.until>=td)&&s.topic!=='crime';
 return L.find(s=>s.lead&&ok(s))||L.filter(ok).sort((a,b)=>String(b.date||'').localeCompare(String(a.date||''))||(/^tech-/.test(b.slug)?1:0)-(/^tech-/.test(a.slug)?1:0))[0]||null}
function hero(){let v='';try{v=STATE.view}catch(_){}const old=document.getElementById('hero27');
 if(v!=='front'){if(old)old.remove();return}
 const s=leadStory();if(!s)return;if(old&&old.dataset.story===s.slug)return;if(old)old.remove();
 const anchor=document.getElementById('whatsOn')||document.getElementById('coverSlot');if(!anchor)return;
 const H=x=>String(x==null?'':x).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
 const k=/^tech-/.test(s.slug)?'Tech':s.topic==='music'?'Music':s.topic==='stage'?'On stage':'Top story';
 const b=document.createElement('a');b.href='?story='+encodeURIComponent(s.slug);b.id='hero27';b.dataset.story=s.slug;b.addEventListener('click',ev=>{if(!(ev.metaKey||ev.ctrlKey||ev.shiftKey||ev.button))ev.preventDefault()});
 b.style.setProperty('--hb',C.heroImgs?'url('+C.heroImgs[hash(s.slug)%C.heroImgs.length]+')':'url(/img/bg27/'+HBG[hash(s.slug)%HBG.length]+'.jpg)');
 b.innerHTML='<span class="hk">'+H(k)+'</span><span class="ht">'+H(s.title)+'</span>'+(s.dek?'<span class="hd">'+H(s.dek)+'</span>':'')+'<span class="hg">Read the story →</span>';
 anchor.parentNode.insertBefore(b,anchor)}
function cal1(){const w=document.getElementById('whatsOn');if(!w||w.dataset.t27a)return;const d=w.querySelector('details.wo-d');if(!d)return;w.dataset.t27a='1';if(!w.querySelector('details[open]')){d.open=true;d.classList.add('t27auto');setTimeout(()=>d.addEventListener('toggle',()=>d.classList.remove('t27auto'),{once:true}),400)}}
function layout(){const si=document.querySelector('#nav #nbSearch input');if(si){if(innerWidth<=760&&document.activeElement!==si)si.style.setProperty('width','36px','important');else si.style.removeProperty('width')}
const nt=document.getElementById('navToggle');if(nt){nt.style.setProperty('display','none','important');const n=document.getElementById('nav');if(n){n.style.setProperty('display','flex','important');n.removeAttribute('hidden');n.classList.remove('closed','collapsed')}}
let v='';try{v=STATE.view}catch(_){}
 /* 10 one main landmark around the editorial column, with headings */
 const w=document.querySelector('.wrap');const vw=document.getElementById('view');
 let m=document.getElementById('main27');
 if(w&&vw&&!m){m=document.createElement('div');m.id='main27';m.setAttribute('role','main');const first=document.getElementById('hero27')||document.getElementById('whatsOn')||document.getElementById('coverSlot')||vw;w.insertBefore(m,first)}
 if(m){['hero27','coverSlot','whatsOn','view'].forEach(id=>{const e=document.getElementById(id);if(e&&e.parentNode!==m)m.appendChild(e)});
  /* 2 news right under the lead, then activities */
  const cs=document.getElementById('coverSlot'),wo=document.getElementById('whatsOn');
  const order=[document.getElementById('hero27'),cs,wo,vw].filter(Boolean);order.forEach(e=>m.appendChild(e));
  if(vw&&vw.tagName==='MAIN')vw.setAttribute('role','region'),vw.setAttribute('aria-label','More')}
 const wm=document.querySelector('.wm27');if(wm&&!wm.getAttribute('role')){wm.setAttribute('role','heading');wm.setAttribute('aria-level','1')}
 [['.cvside .sea-h b'],['#whatsOn .wo-k'],['.jtwk .bh b'],['#hlBox .bh b'],['#beyond>h2']].forEach(([s])=>{const e=document.querySelector(s);if(e&&e.tagName!=='H2'&&!e.getAttribute('role')){e.setAttribute('role','heading');e.setAttribute('aria-level','2')}});
 /* 9 news tiles as native links */
 document.querySelectorAll('.cvside .sea-g button[data-story]').forEach(b=>{const a=document.createElement('a');for(const at of b.attributes)if(at.name!=='type')a.setAttribute(at.name,at.value);a.href='?story='+encodeURIComponent(b.dataset.story);a.innerHTML=b.innerHTML;a.addEventListener('click',ev=>{if(!(ev.metaKey||ev.ctrlKey||ev.shiftKey||ev.button))ev.preventDefault()});b.replaceWith(a)});
 /* 3 side columns start level with the lead */
 const hr=null;const ls=null;if(false){const sp=ls.querySelector('.lspot');if(sp){const d=Math.round(hr.getBoundingClientRect().top-sp.getBoundingClientRect().top);if(Math.abs(d)>4){const cur=parseFloat(ls.dataset.dy||'0');ls.dataset.dy=String(cur+d);ls.style.setProperty('transform','translateY('+(cur+d)+'px)','important')}}}
 /* 4 say how many are shown and link to all of them */
 const d=document.querySelector('#whatsOn details.t27auto');if(d&&!d.querySelector('.t27more')){const rows=d.querySelectorAll('.wo-r').length;if(rows>5){const nm=(d.querySelector('summary')||{}).textContent||'';const cat=nm.replace(/\d+/g,'').trim();const x=document.createElement('div');x.className='t27more';
  x.innerHTML='<span>Showing 5 of '+rows+'</span><button type="button">View all '+rows+' '+cat.toLowerCase()+' events →</button>';x.querySelector('button').onclick=()=>{cur='Calendar';mark();/music/i.test(cat)?nav('cal','music',30):nav('cal',null,14)};d.appendChild(x)}}
 /* 7 honest label */
 const wk=document.querySelector('.jtwk .bh>span');if(wk&&wk.textContent!=='Selected events, next 7 days')wk.textContent='Selected events, next 7 days'}
const N27={shown:12};
function news27(){let v='';try{v=STATE.view}catch(_){}R.classList.toggle('sec27',v!=='front');if(!(v==='cal'&&cur==='Music'))R.classList.remove('music27');if(v!=='stories')return;const host=document.getElementById('view');if(!host||host.querySelector('#news27'))return;
 let L=[];try{L=STORIES.slice()}catch(_){return}const td=ymd(new Date());
 L=L.filter(s=>s&&s.title&&!/^today-(and-tonight|on-the-island)-/.test(s.slug)&&(!s.until||s.until>=td)&&(!window.T27S||T27S(s)));
 L.sort((a,b)=>String(b.date||'').localeCompare(String(a.date||'')));
 const E=x=>String(x==null?'':x).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
 const day=d=>{if(!d)return '';const x=new Date(d+'T12:00:00');return x.toLocaleDateString('en-US',{month:'short',day:'numeric'})};
 const yd=ymd(new Date(Date.now()-864e5)),wk=ymd(new Date(Date.now()-6*864e5));
 const grp=d=>d>=td?'Today':d>=yd?'Yesterday':d>=wk?'Earlier this week':'Older';
 const isTech=cur==='Tech';const title=isTech?'Tech':'News';
 const lead=L.find(s=>s.lead)||L[0];const rest=L.filter(s=>s!==lead);
 const row=s=>'<a class="row27" href="?story='+encodeURIComponent(s.slug)+'" data-story="'+E(s.slug)+'"><h3 style="font-size:20px!important;line-height:1.25!important">'+E(s.title)+'</h3>'+(s.dek?'<p>'+E(s.dek)+'</p>':'')+'<span class="m">'+day(s.date)+(s.minutes>2?' · '+s.minutes+' min read':'')+'</span></a>';
 let html='<section id="news27" aria-labelledby="n27h"><h1 id="n27h" style="font-size:clamp(34px,4vw,48px)!important">'+title+'</h1><p class="cnt">'+L.length+' stories, newest first</p>';
 if(lead)html+='<a class="lead27" href="?story='+encodeURIComponent(lead.slug)+'" data-story="'+E(lead.slug)+'"><span class="m">'+day(lead.date)+'</span><h2>'+E(lead.title)+'</h2>'+(lead.dek?'<p>'+E(lead.dek)+'</p>':'')+'<span class="go">Read the story →</span></a>';
 html+='<h2 class="lh">Latest</h2><div class="list27">';let g='';
 rest.forEach((s,i)=>{const k=grp(s.date||'');if(k!==g){g=k;html+='<h3 class="grp27" data-i="'+i+'">'+k+'</h3>'}html+=row(s).replace('class="row27"','class="row27" data-i="'+i+'"')});
 html+='</div><div class="more27w"><span class="cnt2"></span><button type="button" class="lm27">Load more</button></div>';
 if(!isTech)html+='<section class="ln27" aria-labelledby="ln27h"><h2 id="ln27h">From local newsrooms</h2><div class="ln27l"></div></section>';
 html+='</section>';host.innerHTML=html;
 const apply=()=>{const n=Math.min(N27.shown,rest.length);host.querySelectorAll('.list27 [data-i]').forEach(e=>{e.hidden=+e.dataset.i>=n});const w=host.querySelector('.more27w');w.querySelector('.cnt2').textContent='Showing '+n+' of '+rest.length;w.querySelector('.lm27').hidden=n>=rest.length};
 apply();host.querySelector('.lm27').onclick=()=>{N27.shown+=12;apply()};
 host.querySelectorAll('a[data-story]').forEach(a=>a.addEventListener('click',ev=>{if(ev.metaKey||ev.ctrlKey||ev.shiftKey||ev.button)return;ev.preventDefault();try{sessionStorage.setItem('n27',JSON.stringify({s:a.dataset.story,y:scrollY,n:N27.shown}))}catch(_){}}));
 if(!isTech)fetch('data/headlines.json?'+Math.floor(Date.now()/6e5),{cache:'no-cache'}).then(r=>r.ok?r.json():null).then(d=>{if(!d||!d.items)return;const own=new Set(L.map(s=>s.slug));
  const X=d.items.filter(x=>x&&x.h&&x.url&&!x.story&&!/^\?story=/.test(x.url)).sort((a,b)=>String(b.date||'').localeCompare(String(a.date||''))).slice(0,10);
  const box=host.querySelector('.ln27l');if(!box)return;if(!X.length){host.querySelector('.ln27').remove();return}
  box.innerHTML=X.map(x=>'<a href="'+E(x.url)+'" target="_blank" rel="noopener"><b>'+E(x.h)+'</b><span>'+E(x.outlet||'')+(x.date?' · '+day(x.date):'')+'</span></a>').join('')}).catch(()=>{});
 /* coming back from a story: same place, same focus */
 try{const s=JSON.parse(sessionStorage.getItem('n27')||'null');if(s&&s.s){sessionStorage.removeItem('n27');if(s.n>N27.shown){N27.shown=s.n;apply()}const a=host.querySelector('a[data-story="'+CSS.escape(s.s)+'"]');requestAnimationFrame(()=>{scrollTo(0,s.y);if(a)a.focus({preventScroll:true})});setTimeout(()=>{const b=document.querySelector('#news27 a[data-story="'+CSS.escape(s.s)+'"]');if(b){b.focus({preventScroll:true});if(Math.abs(scrollY-s.y)>40)scrollTo(0,s.y)}},250)}}catch(_){}}
/* ===== Music section page ===== */
const MAN=/^(midtown|east village|west village|lower east side|chelsea|harlem|east harlem|upper west side|upper east side|washington heights|gramercy|soho|tribeca|greenwich village|financial district|hell's kitchen|murray hill|flatiron|nolita|noho|inwood|morningside heights|union square|lincoln center|times square|theater district|kips bay|nomad|battery park|hudson yards|meatpacking|chinatown|little italy|manhattan|lower manhattan|hudson square|two bridges|yorkville|hamilton heights|sugar hill|alphabet city|bowery|uptown|downtown manhattan)/i;
function area27(h){h=String(h||'').trim();if(!h)return '';let a=h.split(/\s+[–—-]\s+|\s*·\s*/)[0].trim();
 if(/new york city/i.test(C.k||'')){if(/elmont|long island|nassau/i.test(h))return 'Nearby: Long Island';if(/rutherford|new jersey|newark|hoboken|jersey city|metlife/i.test(h))return 'Nearby: New Jersey';
  if(/^(brooklyn|queens|bronx|the bronx|staten island)/i.test(a))return a.replace(/^the /i,'').replace(/^bronx/i,'The Bronx');if(MAN.test(a)||MAN.test(h))return 'Manhattan'}
 return a}
const G27=[['Rock & Metal',/^(rock|metal|punk|goth|hard rock|hardcore|industrial)$/i],['Indie',/^(indie|alternative)$/i],['Pop',/^pop$/i],['Hip-Hop & R&B',/^(hip-hop|rap|r&b|soul|funk)$/i],['Electronic',/^(electronic|clubs?|dj|house|techno)$/i],['Jazz & Blues',/^(jazz|blues)$/i],['Classical & Opera',/^(classical|opera|choral|chamber)$/i],['Folk & Country',/^(folk|country|americana|bluegrass|acoustic)$/i],['Latin & World',/^(latin|world|reggae|afrobeats?)$/i],['Genre unlisted',/^(live|music|experimental|concert)$/i]];
const gname=g=>{for(const [n,r] of G27)if(r.test(g||''))return n;return null};
const M27={d:'week',g:'',a:'',q:''};let M27init=false;const MQ0=new URLSearchParams(location.search);
function music27(){let v='';try{v=STATE.view}catch(_){}if(v!=='cal'||cur!=='Music'){return}
 const host=document.getElementById('view');if(!host)return;R.classList.add('music27');
 if(!M27init){M27init=true;const u=MQ0;['d','g','a','q'].forEach(k=>{if(u.get(k))M27[k]=u.get(k)})}
 if(host.querySelector('#music27'))return;
 let U=[];try{U=up}catch(_){}const td=ymd(new Date());
 const ALL=U.filter(e=>e&&e.date>=td&&e.artists&&gname(e.genre)&&!/\b(bingo|trivia|karaoke|yoga|paint|craft|story ?time|workshop|class)\b/i.test(e.artists)&&!/^(support|worship|sports|family|community|recreation|volunteer|civic|drag)$/i.test(e.genre||''));
 {const seen=new Map();ALL.forEach(e=>{const k=e.date+'|'+String(e.venue||'').toLowerCase().replace(/[^a-z0-9]/g,'').slice(0,14)+'|'+String(e.artists).toLowerCase().split(/[,:(]| w\/ | with | and /)[0].replace(/[^a-z0-9]/g,'');const L0=seen.get(k)||[];const i=L0.findIndex(o=>!o.time||!e.time||o.time===e.time);if(i<0)L0.push(e);else if(!L0[i].time&&e.time)L0[i]=e;seen.set(k,L0)});ALL.length=0;seen.forEach(L0=>L0.forEach(e=>ALL.push(e)))}
 ALL.forEach(e=>{if(/^(paid|tba|tbd|varies|see site|n\/a)$/i.test(String(e.price||'').trim()))e.price=''});
 const E=x=>String(x==null?'':x).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
 const areas={};ALL.forEach(e=>{const a=area27(e.hood||e.venue);if(a)areas[a]=(areas[a]||0)+1});
 const AR=Object.keys(areas).sort((x,y)=>(/^Nearby/.test(x)-/^Nearby/.test(y))||areas[y]-areas[x]);
 const gcount={};ALL.forEach(e=>{const n=gname(e.genre);gcount[n]=(gcount[n]||0)+1});
 let L=[];try{L=STORIES.filter(s=>s.topic==='music'||/^nat-.*(tour|album|music)/.test(s.slug)).sort((a,b)=>String(b.date||'').localeCompare(String(a.date||'')))}catch(_){}
 const tOpt=[['tonight','Tonight'],['tomorrow','Tomorrow'],['weekend','This weekend'],['week','Next 7 days'],['all','All upcoming']];
 host.innerHTML='<section id="music27" aria-labelledby="m27h"><h1 id="m27h" style="font-size:clamp(34px,4vw,48px)!important">Music</h1>'+
  '<div class="ctl27" role="group" aria-label="Filter shows">'+
  '<div class="dt27" role="group" aria-label="Date">'+tOpt.map(([k,t])=>'<button type="button" data-d="'+k+'" aria-pressed="'+(M27.d===k)+'">'+t+'</button>').join('')+'</div>'+
  '<div class="sel27"><label>Where<select data-k="a"><option value="">Everywhere</option>'+AR.map(a=>'<option'+(M27.a===a?' selected':'')+'>'+E(a)+'</option>').join('')+'</select></label>'+
  '<label>Genre<select data-k="g"><option value="">All genres</option>'+G27.map(([n])=>gcount[n]?'<option value="'+E(n)+'"'+(M27.g===n?' selected':'')+'>'+E(n)+' ('+gcount[n]+')</option>':'').join('')+'</select></label>'+
  '<label class="q27">Search<input type="search" data-k="q" placeholder="Search artist, venue, or show" value="'+E(M27.q)+'" autocomplete="off"></label></div></div>'+
  '<div class="pick27"></div><h2 class="lh">Shows</h2><p class="cnt m27c" aria-live="polite"></p><div class="res27"></div>'+
  (L.length?'<section class="cov27" aria-labelledby="cov27h"><h2 id="cov27h" class="lh">Latest music coverage</h2>'+L.slice(0,6).map(s=>'<a class="row27" href="?story='+encodeURIComponent(s.slug)+'" data-story="'+E(s.slug)+'"><h3 style="font-size:20px!important">'+E(s.title)+'</h3>'+(s.dek?'<p>'+E(s.dek)+'</p>':'')+'</a>').join('')+'</section>':'')+
  '<p class="note27">Listings updated daily. Times and prices can change, so check with the venue.</p></section>';
 const ctl=host.querySelector('.ctl27');
 ctl.querySelectorAll('[data-d]').forEach(b=>b.onclick=()=>{M27.d=b.dataset.d;ctl.querySelectorAll('[data-d]').forEach(x=>x.setAttribute('aria-pressed',String(x===b)));draw()});
 ctl.querySelectorAll('select').forEach(s=>s.onchange=()=>{M27[s.dataset.k]=s.value;draw()});
 const qi=ctl.querySelector('input');let qt;qi.oninput=()=>{clearTimeout(qt);qt=setTimeout(()=>{M27.q=qi.value;draw()},120)};
 host.querySelectorAll('.cov27 a[data-story]').forEach(a=>a.addEventListener('click',ev=>{if(!(ev.metaKey||ev.ctrlKey||ev.shiftKey||ev.button))ev.preventDefault()}));
 const linkLabel=u=>/\.pdf(\?|$)/i.test(u||'')?'Season schedule (PDF)':/jambase\.com/i.test(u||'')?'Tour announcement':/songkick\.com/i.test(u||'')?'Event details on Songkick':/ticketmaster|axs\.com|seetickets|eventbrite|dice\.fm|etix|ticketweb|stubhub|tix\.com|boxoffice|tickets?\./i.test(u||'')?'Tickets':'Event details';
 const range=()=>{const n=new Date(),t=ymd(n),a=k=>ymd(new Date(n.getTime()+k*864e5));const dow=new Date(t+'T12:00:00').getDay();
  if(M27.d==='tonight')return [t,t];if(M27.d==='tomorrow')return [a(1),a(1)];if(M27.d==='weekend'){const fri=dow===0?a(-2):dow===6?a(-1):a(5-dow),sun=dow===0?t:dow===6?a(1):a(7-dow);return [fri<t?t:fri,sun]}if(M27.d==='week')return [t,a(6)];return [t,'9999']};
 const big=/garden|arena|center|centre|stadium|amphitheat|pavilion|hall|theat|ballroom|paramount|steel|terminal 5|beacon|apollo|town hall|ppac|showbox|moore|paramount|vets/i;
 function draw(){const [f,t]=range();const q=M27.q.trim().toLowerCase();
  const R2=ALL.filter(e=>e.date>=f&&e.date<=t&&(!M27.g||gname(e.genre)===M27.g)&&(!M27.a||area27(e.hood||e.venue)===M27.a)&&(!q||(e.artists+' '+e.venue+' '+(e.hood||'')).toLowerCase().includes(q))).sort((a,b)=>a.date.localeCompare(b.date)||(window.__tm?(__tm(a.time)??9999)-(__tm(b.time)??9999):0));
  /* address keeps the choices */
  try{const u=new URLSearchParams();u.set('section','music');if(M27.d!=='week')u.set('d',M27.d);if(M27.g)u.set('g',M27.g);if(M27.a)u.set('a',M27.a);if(M27.q)u.set('q',M27.q);history.replaceState(history.state,'','?'+u.toString())}catch(_){}
  host.querySelector('.m27c').textContent=R2.length+' show'+(R2.length===1?'':'s');
  const pk=host.querySelector('.pick27');const tn=ALL.filter(e=>e.date===td);const p=M27.d==='tonight'||M27.d==='week'?(tn.find(e=>big.test(e.venue||''))||tn[0]):null;
  pk.innerHTML=p&&!q&&!M27.g&&!M27.a?'<a class="pk27" href="'+E(p.url||'#')+'" target="_blank" rel="noopener"><span class="k">Tonight’s pick</span><span class="t">'+E(p.artists)+'</span><span class="v">'+E([p.time||'Time not listed',p.venue,area27(p.hood)].filter(Boolean).join(' · '))+(p.price?' · '+E(p.price):'')+'</span><span class="go">'+linkLabel(p.url)+' →</span></a>':'';
  const box=host.querySelector('.res27');
  if(!R2.length){const act=[];if(M27.d!=='all')act.push(['d',tOpt.find(x=>x[0]===M27.d)[1]]);if(M27.g)act.push(['g',M27.g]);if(M27.a)act.push(['a',M27.a]);if(M27.q)act.push(['q','“'+M27.q+'”']);
   box.innerHTML='<div class="empty27"><p>No shows match these filters.</p><div>'+act.map(([k,t])=>'<button type="button" data-x="'+k+'">'+E(t)+' ✕</button>').join('')+'<button type="button" data-x="all">Clear all</button></div></div>';
   box.querySelectorAll('[data-x]').forEach(b=>b.onclick=()=>{const k=b.dataset.x;if(k==='all'||k==='d')M27.d='all';if(k==='all'||k==='g')M27.g='';if(k==='all'||k==='a')M27.a='';if(k==='all'||k==='q'){M27.q='';qi.value=''}
    ctl.querySelectorAll('[data-d]').forEach(x=>x.setAttribute('aria-pressed',String(x.dataset.d===M27.d)));ctl.querySelector('select[data-k=g]').value=M27.g;ctl.querySelector('select[data-k=a]').value=M27.a;draw()});return}
  const yr=new Date().getFullYear();let html='',d='';
  R2.slice(0,300).forEach(e=>{if(e.date!==d){if(d)html+='</ul>';d=e.date;const x=new Date(e.date+'T12:00:00');const n=R2.filter(y=>y.date===d).length;
    html+='<h3 class="day27">'+x.toLocaleDateString('en-US',Object.assign({weekday:'long',month:'long',day:'numeric'},x.getFullYear()!==yr?{year:'numeric'}:{}))+' <span>'+n+' show'+(n===1?'':'s')+'</span></h3><ul class="ul27">'}
   const cov=L.find(s=>{const a=String(e.artists).toLowerCase().split(/[,:–—(]| w\/ | with /)[0].trim();return a.length>3&&String(s.title).toLowerCase().includes(a)});
   html+='<li class="sh27"><span class="tm">'+E(e.time||'Time not listed')+'</span><span class="ar"><b>'+E(e.artists)+'</b><small>'+E([e.venue,area27(e.hood)].filter(Boolean).join(' · '))+(e.price?' · '+E(e.price):'')+'</small></span><span class="lk"><a href="'+E(e.url||'#')+'" target="_blank" rel="noopener">'+linkLabel(e.url)+'</a>'+(cov?'<a href="?story='+encodeURIComponent(cov.slug)+'" data-story="'+E(cov.slug)+'">Read our coverage</a>':'')+'</span></li>'});
  if(d)html+='</ul>';box.innerHTML=html;
  box.querySelectorAll('a[data-story]').forEach(a=>a.addEventListener('click',ev=>{if(!(ev.metaKey||ev.ctrlKey||ev.shiftKey||ev.button))ev.preventDefault()}))}
 draw()}
function nohelp(){let v='';try{v=STATE.view}catch(_){}if(v==='help'){try{go('front')}catch(_){}}}
function week(){nohelp();let v='';try{v=STATE.view}catch(_){}if(v!=='front'||document.querySelector('.jtwk')||typeof jtWeek!=='function')return;const host=document.getElementById('view');if(!host)return;
 const s=document.createElement('section');s.className='box jtwk t27wk';s.innerHTML='<div class="bh"><b>This week</b><span>next 7 days</span></div><div id="jtWeek">'+jtWeek()+'</div><div style="padding:10px 14px"><button class="nb" data-go="cal">Full calendar →</button></div>';
 const b=document.getElementById('beyond');host.insertBefore(s,b||null)}
function labels(){music27();news27();week();try{layout()}catch(_){}document.querySelectorAll('#whatsOn .wo-r').forEach(r=>{const t=r.firstElementChild;if(t&&t.textContent.trim()==='TBA')t.textContent=''});
 const wk=document.querySelector('.jtwk .bh b');if(wk){const n=[...wk.childNodes].filter(x=>x.nodeType===3);n.forEach(x=>{if(/\S/.test(x.textContent)&&x.textContent.trim()!=='This week')x.textContent=' This week'})}
 document.querySelectorAll('.jtwk button,.jtwk a,.wo-f a').forEach(a=>{if(/^full .*calendar/i.test(a.textContent.trim())&&a.textContent.trim()!=='Full calendar →')a.textContent='Full calendar →'});
 const hm=document.querySelector('#hlBox .hlmore');if(hm&&!hm.dataset.t27){hm.dataset.t27='1';hm.click()}
const set=(el,t)=>{if(el&&el.firstChild&&el.textContent.trim()!==t){const n=[...el.childNodes].find(x=>x.nodeType===3&&x.textContent.trim());if(n)n.textContent=t;else el.textContent=t}};
 const h=document.querySelector('.cvside .sea-h');if(h){set(h.querySelector('b'),'News');const a=h.querySelector('button,a');if(a)set(a,'All stories →')}
 const hb=document.querySelector('#hlBox .bh b');if(hb)set(hb,'Headlines')}
function pool2(){let P=[];try{P=window.jtEvPool?jtEvPool():[]}catch(_){}let U=[];try{U=up}catch(_){}const td=ymd(new Date());const have=new Set(P.map(x=>String(x.bigText||'').toLowerCase()));
 const SK=/^(worship|support|sports|drag|recreation|community|volunteer|civic|family|fitness)$/i;
 U.filter(e=>e&&e.date>=td&&e.artists&&!SK.test(e.genre||'')).slice(0,80).forEach(e=>{const t=String(e.artists).trim();if(have.has(t.toLowerCase()))return;have.add(t.toLowerCase());P.push({bigText:t,name:e.venue||'',when:e.time||'',href:e.url||'#',ext:1,ev:e})});return P}
let R27sig='';
function fitRails(){const box=document.getElementById('rails27'),w=document.querySelector('.wrap'),c=document.getElementById('main27')||document.getElementById('view');if(!box||!w||!c)return;if(R.classList.contains('music27')){box.style.setProperty('display','none','important');return}
 const W=w.getBoundingClientRect(),M=c.getBoundingClientRect();const gl=M.left-W.left-16,gr=W.right-M.right-16;const cw=Math.min(250,gl,gr);
 if(cw<170){box.style.setProperty('display','none','important');return}box.style.setProperty('display','block','important');
 const l=box.querySelector('.l'),r=box.querySelector('.r');l.style.width=r.style.width=cw+'px';l.style.left=Math.max(6,gl-cw)+'px';r.style.right=Math.max(6,gr-cw)+'px'}
addEventListener('resize',()=>{clearTimeout(fitRails.t);fitRails.t=setTimeout(fitRails,120)});
function rails27(){const w=document.querySelector('.wrap');if(!w)return;let box=document.getElementById('rails27');
 const P=pool2();if(!P.length)return;
 const anchor=document.getElementById('hero27')||document.getElementById('main27')||document.getElementById('view');if(!anchor)return;
 const top=Math.max(0,Math.round(anchor.getBoundingClientRect().top-w.getBoundingClientRect().top));
 const H=Math.max(600,w.scrollHeight-top-40);const per=Math.max(1,Math.floor((H+12)/162));const n=Math.min(P.length,per*2);
 const sig=top+'|'+per+'|'+P.length;if(box&&R27sig===sig){fitRails();return}R27sig=sig;
 if(!box){box=document.createElement('div');box.id='rails27';box.setAttribute('aria-label','Events');box.innerHTML='<div class="c l"></div><div class="c r"></div>';w.appendChild(box)}
 box.style.top=top+'px';fitRails();
 const E=x=>String(x==null?'':x).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
 const card=e=>{const ev=e.ev||{};const d=ev.date?new Date(ev.date+'T12:00:00'):null;const when=[d?d.toLocaleDateString('en-US',{weekday:'short',month:'short',day:'numeric'}):'',ev.time||e.when||''].filter(Boolean).join(' · ');
  const g=/\.pdf(\?|$)/i.test(e.href||'')?'Schedule (PDF) →':/ticketmaster|seetickets|eventbrite|axs\.com|dice\.fm|etix|ticketweb|stubhub|tix|ticket/i.test(e.href||'')?'Tickets →':'Event details →';
  return '<a class="t27ev" href="'+E(e.href||'#')+'"'+(e.ext?' target="_blank" rel="noopener"':'')+'><span class="w">'+E(when)+'</span><span class="t">'+E(e.bigText)+'</span><span class="f"><span class="v">'+E([e.name,ev.hood].filter(Boolean).join(' · '))+'</span><span class="g">'+g+'</span></span></a>'};
 const L=[],Rr=[];P.slice(0,n).forEach((e,i)=>(i%2?Rr:L).push(card(e)));
 box.querySelector('.l').innerHTML=L.join('');box.querySelector('.r').innerHTML=Rr.join('')}
function rails(){let P=pool2();if(!P.length)return;
 const H=x=>String(x==null?'':x).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
 const K=x=>'title:'+String(x||'').replace(/\s+/g,' ').trim().toLowerCase();
 const spots=[...document.querySelectorAll('.lsrow .lspot')];const used=new Set();
 spots.forEach(sp=>{const a=sp.querySelector('a[id]');if(a&&a.querySelector('.t27ev')&&a.dataset.promoKey)used.add(a.dataset.promoKey)});
 spots.forEach(sp=>{const a=sp.querySelector('a[id]')||sp.querySelector('a');if(!a||a.querySelector('.t27ev'))return;
  let e=null;const k0=a.dataset.promoKey;if(k0&&!used.has(k0))e=P.find(x=>K(x.bigText)===k0);
  if(!e)e=P.find(x=>!used.has(K(x.bigText)));if(!e)return;const key=K(e.bigText);used.add(key);
  const ev=e.ev||{};const d=ev.date?new Date(ev.date+'T12:00:00'):null;
  const when=[d?d.toLocaleDateString('en-US',{weekday:'short',month:'short',day:'numeric'}):'',ev.time||e.when||''].filter(Boolean).join(' · ');
  sp.classList.remove('t-st','t-ad','t-adimg');sp.classList.add('t-mu');sp.dataset.frozen='1';
  a.dataset.promoKey=key;a.href=e.href||'#';if(e.ext){a.target='_blank';a.rel='noopener'}a.removeAttribute('data-story');a.setAttribute('aria-label',e.bigText||'');
  a.innerHTML='<span class="t27ev"><span class="w">'+H(when)+'</span><span class="t">'+H(e.bigText)+'</span><span class="f"><span class="v">'+H([e.name,ev.hood].filter(Boolean).join(' · '))+'</span><span class="g">'+(/\.pdf(\?|$)/i.test(e.href||'')?'Schedule (PDF) →':/ticketmaster|seetickets|eventbrite|axs\.com|dice\.fm|etix|ticketweb|stubhub|tix|ticket/i.test(e.href||'')?'Tickets →':'Event details →')+'</span></span></span>'})}

let updT=null;function upd(){const t=document.querySelector('.clsbar.top');if(!t||t.querySelector('.upd27'))return;const s=document.createElement('span');s.className='upd27';t.insertBefore(s,t.querySelector('.rec'));
 const show=d=>{if(!d)return;const x=new Date(d);if(isNaN(x))return;s.textContent='Updated '+x.toLocaleTimeString('en-US',{hour:'numeric',minute:'2-digit',timeZone:TZ})};
 const tryF=(fs)=>{if(!fs.length)return;fetch(fs[0]+'?'+Date.now(),{cache:'no-cache'}).then(r=>r.ok?r.json():null).then(d=>{if(d&&d.asof)show(d.asof);else tryF(fs.slice(1))}).catch(()=>tryF(fs.slice(1)))};tryF(['data/headlines.json','data/cal.json','data/beyond.json'])}
const HBG=['bg42-wireframe-terrain','bg44-particle-field','bg46-lidar-scan','bg50-orbit-lines','bg41-data-mesh','bg45-glass-panels'];
const hash=s=>{let h=7;for(const c of String(s))h=(h*31+c.charCodeAt(0))>>>0;return h};
function dedupe(){const hb=document.getElementById('hlBox');if(hb){const vis=[...hb.querySelectorAll('a.hlr')].some(a=>!/^\?story=/.test(a.getAttribute('href')||''));hb.style.setProperty('display',vis?'':'none',vis?'':'important')}
const h=document.getElementById('hero27');const lead=h&&h.dataset.story;
 document.querySelectorAll('.cvside .sea-g [data-story]').forEach(b=>{if(lead&&b.dataset.story===lead)b.style.setProperty('display','none','important');
  if(false){b.dataset.b27='1';b.style.setProperty('background-image','linear-gradient(90deg,rgba(12,14,18,.96) 35%,rgba(12,14,18,.6)),url(/img/bg27/'+BG[hash(b.dataset.story)%BG.length]+'.jpg)','important');b.style.setProperty('background-size','cover','important');b.style.setProperty('background-position','center','important')}})}
/* backgrounds for the flipping boxes */
const BG=['bg41-data-mesh','bg42-wireframe-terrain','bg43-graphite-gradient','bg44-particle-field','bg45-glass-panels','bg46-lidar-scan','bg47-liquid-chrome','bg48-aurora-edge','bg49-led-dot-matrix','bg50-orbit-lines'];
let bi=Math.floor(Math.random()*BG.length),bi_=bi+3;
function dress(){return;document.querySelectorAll('.bp:not([data-b27]),.ep.os:not([data-b27]),.lspot .ep:not([data-b27])').forEach(el=>{el.dataset.b27='1';el.style.setProperty('--b27','url(/img/bg27/'+BG[bi++%BG.length]+'.jpg)')})}
const go_=()=>{build();try{const m=SEC0;if(m&&!STORY0){const b=[...document.querySelectorAll('#nav .nb27')].find(x=>x.dataset.k===m);if(b){const f=()=>b.click();setTimeout(f,0);setTimeout(()=>{let v='';try{v=STATE.view}catch(_){}if(v==='front')f()},900)}}}catch(_){}new MutationObserver(()=>{clearTimeout(go_.t);go_.t=setTimeout(build,60)}).observe(document.body,{childList:true,subtree:true})};
document.readyState==='loading'?document.addEventListener('DOMContentLoaded',go_):go_();
})();
