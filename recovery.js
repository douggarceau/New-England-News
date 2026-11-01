/* Recovery & Support Meetings page: its own section, kept out of the activities lists */
(function(){
const H=x=>String(x==null?'':x).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const DAYS=['Sunday','Monday','Tuesday','Wednesday','Thursday','Friday','Saturday'],DN=['sun','mon','tue','wed','thu','fri','sat'];
const TZ='America/New_York',ymd=d=>d.toLocaleDateString('en-CA',{timeZone:TZ});
function mins(t){const m=String(t||'').match(/(\d{1,2})(?::(\d{2}))?\s*(am|pm)/i);if(!m)return 9999;let h=+m[1]%12;if(/pm/i.test(m[3]))h+=12;return h*60+(+m[2]||0)}
let ROWS=null,ORGS=[],ST={town:'',day:new Date(new Date().toLocaleString('en-US',{timeZone:TZ})).getDay()};
function wk(w){return w==='every'||!w?'Every':w==='last'?'Last':w==='1st'?'1st':w==='2nd'?'2nd':w==='3rd'?'3rd':w==='4th'?'4th':w}
Promise.all([
 fetch('data/meetings.json',{cache:'no-cache'}).then(r=>r.ok?r.json():[]).catch(()=>[]),
 fetch('data/cal.json',{cache:'no-cache'}).then(r=>r.json()).catch(()=>({events:[]})),
 fetch('data/directory.json',{cache:'no-cache'}).then(r=>r.json()).catch(()=>({items:[]}))
]).then(([M,C,D])=>{
 const rows=M.map(m=>({day:DN.indexOf(m.d),w:m.w,t:m.t,n:m.n,v:m.v,h:m.h,u:m.u}));
 const seen=new Set(rows.map(r=>r.day+'|'+r.t+'|'+String(r.n).toLowerCase()));
 const today=ymd(new Date()),lim=ymd(new Date(Date.now()+7*864e5));
 (C.events||[]).filter(e=>e.genre==='support'&&e.date>=today&&e.date<lim).forEach(e=>{const d=new Date(e.date+'T12:00:00').getDay();const k=d+'|'+e.time+'|'+String(e.artists).toLowerCase();if(seen.has(k))return;seen.add(k);rows.push({day:d,w:'every',t:e.time,n:e.artists,v:e.venue,h:e.hood,u:e.url,date:e.date})});
 ROWS=rows;ORGS=(D.items||[]).filter(x=>/recovery and support/i.test(x.c||'')&&!/^Recovery and support meetings in /.test(x.n));
 if(typeof STATE!=='undefined'&&STATE.view==='recovery')try{render()}catch(_){}
});
window.vRecovery=function(){
 if(!ROWS)return '<h2 class="room">Recovery &amp; Support Meetings</h2><p>Loading…</p>';
 const towns=[...new Set(ROWS.map(r=>r.h).filter(Boolean))].sort();
 const L=ROWS.filter(r=>r.day===ST.day&&(!ST.town||r.h===ST.town)).sort((a,b)=>mins(a.t)-mins(b.t));
 const rows=L.map(r=>{const u=/^https?:/.test(r.u||'')?r.u:'';return '<a class="rc-r"'+(u?' href="'+H(u)+'" target="_blank" rel="noopener"':'')+'><span class="rc-t">'+H(r.t||'Time TBA')+'</span><span class="rc-n"><b>'+H(r.n)+'</b><small>'+H([r.v,r.h].filter(Boolean).join(' · '))+(r.w&&r.w!=='every'?' · '+H(wk(r.w))+' '+DAYS[r.day]+' of the month':'')+'</small></span></a>'}).join('');
 const orgs=ORGS.map(o=>'<li><b>'+H(o.n)+'</b>'+(o.p?' · <a href="tel:'+H(o.p.replace(/[^0-9+]/g,''))+'">'+H(o.p)+'</a>':'')+(o.w?' · <a href="'+H(o.w)+'" target="_blank" rel="noopener">Website</a>':'')+'</li>').join('');
 return '<h2 class="room">Recovery &amp; Support Meetings</h2><div class="intro"><b>Meetings and help lines</b><p>Recovery, grief, caregiver and health support groups, taken from each group\'s own published meeting list. Lists change often, so confirm with the group before you go. In an emergency call 911; for a mental health crisis call or text 988.</p></div>'+
 '<div id="recov"><div class="rc-bar"><label>Day <select id="rcDay">'+DAYS.map((d,i)=>'<option value="'+i+'"'+(i===ST.day?' selected':'')+'>'+d+'</option>').join('')+'</select></label>'+(towns.length>1?'<label>Town <select id="rcTown"><option value="">All towns</option>'+towns.map(t=>'<option'+(t===ST.town?' selected':'')+'>'+H(t)+'</option>').join('')+'</select></label>':'')+'<span class="rc-c"><b>'+L.length+'</b> meetings</span></div>'+
 '<div class="rc-l">'+(rows||'<p class="rc-e">No meetings listed for this day and town.</p>')+'</div>'+(orgs?'<h3 class="rc-h">Help lines and organizations</h3><ul class="rc-o">'+orgs+'</ul>':'')+'</div>'};
document.addEventListener('change',e=>{if(e.target.id==='rcDay'){ST.day=+e.target.value;render()}else if(e.target.id==='rcTown'){ST.town=e.target.value;render()}});
function addBtn(){const nav=document.getElementById('nav');if(!nav||nav.querySelector('[data-go="recovery"]'))return;const b=document.createElement('button');b.className='nb';b.dataset.go='recovery';b.type='button';b.textContent='Recovery & Support Meetings';nav.appendChild(b)}
addBtn();document.addEventListener('DOMContentLoaded',addBtn);
})();
