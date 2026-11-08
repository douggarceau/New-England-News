/* Rhode Island Hurricane app: fresh news first, saved copy when offline. */
const V='rambler-v4';
const CORE=['/','/img/rambler-masthead.png'];
self.addEventListener('install',e=>{e.waitUntil(caches.open(V).then(c=>c.addAll(CORE)).catch(()=>{}));self.skipWaiting();});
self.addEventListener('activate',e=>{e.waitUntil(caches.keys().then(ks=>Promise.all(ks.filter(k=>k!==V).map(k=>caches.delete(k)))).then(()=>self.clients.claim()));});
self.addEventListener('fetch',e=>{
  const r=e.request,u=new URL(r.url);
  if(r.method!=='GET'||u.origin!==location.origin)return;
  const img=/\.(png|jpe?g|webp|gif|svg|mp3|ogg)$/i.test(u.pathname);
  if(img){
    /* stale-while-revalidate: show the saved copy now, refresh it in the background */
    const net=fetch(r).then(res=>{if(res.ok){const c=res.clone();caches.open(V).then(x=>x.put(r,c));}return res;});
    e.respondWith(caches.match(r).then(hit=>{if(hit){e.waitUntil(net.catch(()=>{}));return hit}return net;}));
    return;
  }
  e.respondWith(fetch(r).then(res=>{if(res.ok){const c=res.clone();caches.open(V).then(x=>x.put(r,c));}return res;})
    .catch(()=>caches.match(r).then(hit=>hit||(r.mode==='navigate'?caches.match('/'):undefined))));
});
