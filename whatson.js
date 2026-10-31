/* What's On: Today/Tonight · Tomorrow · This Week · Weekend, at the top of the front page */
(function(){
const H=x=>String(x==null?'':x).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const SKIP=/^(worship|support|sports)$/i;
const TZ='America/New_York';
const ymd=d=>d.toLocaleDateString('en-CA',{timeZone:TZ});
const add=(d,n)=>new Date(d.getTime()+n*864e5);
function mins(t){const m=String(t||'').match(/(\d{1,2})(?::(\d{2}))?\s*(am|pm)/i);if(!m)return 9999;let h=+m[1]%12;if(/pm/i.test(m[3]))h+=12;return h*60+(+m[2]||0)}
function nowMins(){const p=new Date().toLocaleTimeString('en-US',{timeZone:TZ,hour12:false,hour:'2-digit',minute:'2-digit'}).split(':');return (+p[0])*60+(+p[1])}
let EV=null,tab=0;
function ranges(){const n=new Date(),td=ymd(n),tm=ymd(add(n,1));
 const dow=new Date(td+'T12:00:00').getDay();/* 0 Sun .. 6 Sat */
 const fri=dow===0?ymd(add(n,-2)):dow===6?ymd(add(n,-1)):ymd(add(n,5-dow));const sun=ymd(add(new Date(fri+'T12:00:00'),2));
 const late=nowMins()>=17*60;
 return [
  {k:late?'Tonight':'Today',from:td,to:td},
  {k:'Tomorrow',from:tm,to:tm},
  {k:'This Week',from:td,to:ymd(add(n,6))},
  {k:'This Weekend',from:fri<td?td:fri,to:sun}]}
function list(r){const td=ymd(new Date()),nm=nowMins();
 return EV.filter(e=>e.date>=r.from&&e.date<=r.to&&!(e.date===td&&mins(e.time)<9999&&mins(e.time)<nm-90))
  .sort((a,b)=>a.date<b.date?-1:a.date>b.date?1:mins(a.time)-mins(b.time))}
function dayLbl(ds){const d=new Date(ds+'T12:00:00');return d.toLocaleDateString('en-US',{weekday:'short'}).toUpperCase()+' '+d.getDate()}
function render(box){const R=ranges(),r=R[tab],L=list(r),multi=r.from!==r.to;
 const rows=L.slice(0,8).map(e=>{const name=String(e.artists||'').split(/\s+[|@]\s+/)[0];const u=/^https?:/.test(e.url||'')?e.url:'';
  return '<a class="wo-r"'+(u?' href="'+H(u)+'" target="_blank" rel="noopener"':' href="#cal"')+'><span class="wo-t">'+(multi?'<i>'+H(dayLbl(e.date))+'</i>':'')+H(String(e.time||'All day').replace(/:00/g,''))+'</span><span class="wo-n"><b>'+H(name)+'</b><small>'+H(e.venue||'')+'</small></span></a>'}).join('');
 box.innerHTML='<div class="wo-h"><span class="wo-k">What’s on</span><span class="wo-tabs" role="tablist">'+R.map((x,i)=>'<button type="button" role="tab" aria-selected="'+(i===tab)+'" data-i="'+i+'">'+H(x.k)+'</button>').join('')+'</span></div>'+
  '<div class="wo-l">'+(rows||'<p class="wo-e">Nothing listed yet. See the full calendar for what’s coming up.</p>')+'</div>'+
  '<div class="wo-f"><a href="#cal" class="wo-all">'+(L.length>8?(L.length-8)+' more · ':'')+'Full calendar →</a></div>'}
function mount(){const slot=document.getElementById('coverSlot');if(!slot)return;let box=document.getElementById('whatsOn');
 const front=slot.offsetParent!==null&&slot.childElementCount>0;
 if(!front){if(box)box.style.display='none';return}
 if(!box){box=document.createElement('section');box.id='whatsOn';box.setAttribute('aria-label','What’s on');slot.parentNode.insertBefore(box,slot);
  box.addEventListener('click',e=>{const b=e.target.closest('.wo-tabs button');if(b){tab=+b.dataset.i;render(box);return}
   const a=e.target.closest('a[href="#cal"]');if(a){e.preventDefault();try{go('cal')}catch(_){location.hash='cal'}}});render(box)}
 box.style.display=''}
fetch('data/cal.json',{cache:'no-cache'}).then(r=>r.json()).then(d=>{EV=(d.events||[]).filter(e=>e&&e.date&&!SKIP.test(e.genre||''));
 /* default to Weekend on Fri-Sun evenings when today is empty */
 mount();setInterval(mount,1500);setInterval(()=>{const b=document.getElementById('whatsOn');if(b&&b.style.display!=='none')render(b)},300000)}).catch(()=>{});
})();
