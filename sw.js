/* The Guitar Doug Report app: fresh news first, saved copy when offline. */
const V='gdr-boston-v1';
const CORE=['/','/img/gdr-masthead-tight.webp'];
self.addEventListener('install',e=>{e.waitUntil(caches.open(V).then(c=>c.addAll(CORE)).catch(()=>{}));self.skipWaiting();});
self.addEventListener('activate',e=>{e.waitUntil(caches.keys().then(ks=>Promise.all(ks.filter(k=>k!==V).map(k=>caches.delete(k)))).then(()=>self.clients.claim()));});
self.addEventListener('fetch',e=>{
  const r=e.request,u=new URL(r.url);
  if(r.method!=='GET'||u.origin!==location.origin)return;
  const img=/\.(png|jpe?g|webp|gif|svg|mp3|ogg)$/i.test(u.pathname);
  if(img){
    e.respondWith(caches.match(r).then(hit=>hit||fetch(r).then(res=>{if(res.ok){const c=res.clone();caches.open(V).then(x=>x.put(r,c));}return res;})));
    return;
  }
  e.respondWith(fetch(r).then(res=>{if(res.ok){const c=res.clone();caches.open(V).then(x=>x.put(r,c));}return res;})
    .catch(()=>caches.match(r).then(hit=>hit||(r.mode==='navigate'?caches.match('/'):undefined))));
});
