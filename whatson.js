/* What's On: Today/Tonight · Tomorrow · This Week · Weekend, at the top of the front page */
(function(){
const H=x=>String(x==null?'':x).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const SKIP=/^(sports)$/i;
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
const PLACE=(()=>{const t=(location.hostname+' '+document.title).toLowerCase();return /jamestown/.test(t)?'Jamestown':/hurricane|rhode/.test(t)?'Rhode Island':/boston|rambler/.test(t)?'Boston':/scream|new york|nyc/.test(t)?'New York City':'the Area'})();
const CATS=[['Live Music',/^(live|rock|indie|jazz|pop|electronic|folk|r&b|latin|metal|hip-hop|punk|experimental|world|goth|country)$/i],['Classical Music & Opera',/^classical$/i],['Theater & Dance',/^(theater|dance)$/i],['Comedy',/^comedy$/i],['Film Screenings',/^film$/i],['Lectures, Talks & Book Events',/^talks$/i],['Art Exhibits & Museums',/^arts$/i],['Children & Family Activities',/^family$/i],['Fitness, Outdoors & Social Groups',/^recreation$/i],['Volunteer Opportunities',/^volunteer$/i],['Community Events',/^community$/i],['Church Services & Worship',/^worship$/i],['Recovery & Support Meetings',/^support$/i]];
function cat(g){for(const c of CATS)if(c[1].test(g||''))return c[0];return 'Other Activities'}
function row(e,multi){const name=String(e.artists||'').split(/\s+[|@]\s+/)[0];const u=/^https?:/.test(e.url||'')?e.url:'';
 return '<a class="wo-r"'+(u?' href="'+H(u)+'" target="_blank" rel="noopener"':' href="#cal"')+'><span class="wo-t">'+(multi?H(dayLbl(e.date))+' · ':'')+H(String(e.time||'TBA').replace(/:00/g,''))+'</span><span class="wo-n"><b>'+H(name)+'</b> <small>'+H(e.venue||'')+'</small></span></a>'}
let OPEN={};
function render(box){const R=ranges(),r=R[tab],L=list(r),multi=r.from!==r.to;
 const g={};L.forEach(e=>{const c=cat(e.genre);(g[c]=g[c]||[]).push(e)});
 const order=CATS.map(c=>c[0]).concat('Other Activities').filter(k=>g[k]);
 const secs=order.map((k,i)=>'<details class="wo-d" data-k="'+H(k)+'"'+((k in OPEN?OPEN[k]:i===0)?' open':'')+'><summary>'+H(k)+'<span>'+g[k].length+'</span></summary>'+g[k].map(e=>row(e,multi)).join('')+'</details>').join('');
 box.innerHTML='<div class="wo-h"><span class="wo-k">All Activities in '+H(PLACE)+'</span><select class="wo-s" aria-label="When">'+R.map((x,i)=>'<option value="'+i+'"'+(i===tab?' selected':'')+'>'+H(x.k)+'</option>').join('')+'</select>'+(L.length?'<span class="wo-c"><b>'+L.length+'</b> listed</span>':'')+'</div>'+
  '<div class="wo-l">'+(secs||'<p class="wo-e">Nothing listed yet. See the full calendar for what’s coming up.</p>')+'</div>'+
  '<div class="wo-f"><a href="#cal" class="wo-all">Full event calendar →</a></div>'}
function mount(){const slot=document.getElementById('coverSlot');if(!slot)return;let box=document.getElementById('whatsOn');
 const front=slot.offsetParent!==null&&slot.childElementCount>0;
 if(!front){if(box)box.style.display='none';return}
 if(!box){box=document.createElement('section');box.id='whatsOn';box.setAttribute('aria-label','All activities');slot.parentNode.insertBefore(box,slot);
  box.addEventListener('change',e=>{if(e.target.classList.contains('wo-s')){tab=+e.target.value;render(box)}});box.addEventListener('toggle',e=>{const d=e.target;if(d.classList&&d.classList.contains('wo-d'))OPEN[d.dataset.k]=d.open},true);
  box.addEventListener('click',e=>{
   const a=e.target.closest('a[href="#cal"]');if(a){e.preventDefault();try{go('cal')}catch(_){location.hash='cal'}}});render(box)}
 box.style.display=''}
fetch('data/cal.json',{cache:'no-cache'}).then(r=>r.json()).then(d=>{EV=(d.events||[]).filter(e=>e&&e.date&&!SKIP.test(e.genre||''));
 /* default to Weekend on Fri-Sun evenings when today is empty */
 mount();setInterval(mount,1500);setInterval(()=>{const b=document.getElementById('whatsOn');if(b&&b.style.display!=='none')render(b)},300000)}).catch(()=>{});
})();
