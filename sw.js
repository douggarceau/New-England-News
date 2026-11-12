/* Boston Rambler app: fresh news first, saved copy when offline. */
const V='rambler-v7';
const CORE=['/','/img/rambler-masthead.png'];
self.addEventListener('install',e=>{e.waitUntil(caches.open(V).then(c=>c.addAll(CORE)).catch(()=>{}));self.skipWaiting();});
self.addEventListener('activate',e=>{e.waitUntil(caches.keys().then(ks=>Promise.all(ks.filter(k=>k!==V).map(k=>caches.delete(k)))).then(()=>self.clients.claim()));});
self.addEventListener('fetch',e=>{
  const r=e.request,u=new URL(r.url);
  if(r.method!=='GET'||u.origin!==location.origin)return;
  /* one saved copy per file: pages and data files ignore cache-busting query strings (?d=, timestamps) so copies do not pile up */
  const img=/\.(png|jpe?g|webp|gif|svg|mp3|ogg)$/i.test(u.pathname);
  const key=(u.search&&!img)?new Request(u.origin+u.pathname):r;
  if(img){
    /* stale-while-revalidate: show the saved copy now, refresh it in the background */
    const net=fetch(r).then(res=>{if(res.ok){const c=res.clone();caches.open(V).then(x=>x.put(key,c));}return res;});
    e.respondWith(caches.match(key).then(hit=>{if(hit){e.waitUntil(net.catch(()=>{}));return hit}return net;}));
    return;
  }
  e.respondWith(fetch(r).then(res=>{if(res.ok){const c=res.clone();caches.open(V).then(x=>x.put(key,c));}return res;})
    .catch(()=>caches.match(key).then(hit=>hit||(r.mode==='navigate'?caches.match('/'):undefined))));
});
