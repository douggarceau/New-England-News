self.addEventListener('install',function(){self.skipWaiting()});
self.addEventListener('activate',function(e){e.waitUntil((async function(){
  try{var ks=await caches.keys();for(var i=0;i<ks.length;i++){await caches.delete(ks[i])}}catch(x){}
  try{await self.registration.unregister()}catch(x){}
  try{var cs=await self.clients.matchAll({type:'window'});cs.forEach(function(c){c.navigate(c.url)})}catch(x){}
})())});
