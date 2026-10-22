/* Vector map built from real geographic polygons; no image overlay. */
(() => {
 const slide=document.querySelector('.uae-real-slide');if(!slide)return;
 const svg=slide.querySelector('#uae-real-svg'), container=slide.querySelector('#uae-real-geometry');
 const rows=[...slide.querySelectorAll('.uae-menu-row')], status=slide.querySelector('.uae-map-current');
 const ids={AEAZ:'abu-dhabi',AEDU:'dubai',AESH:'sharjah',AEAJ:'ajman',AEUQ:'uaq',AERK:'rak',AEFU:'fujairah'};
 const names={ 'abu-dhabi':'Абу-Даби', dubai:'Дубай',sharjah:'Шарджа',ajman:'Аджман',uaq:'Умм-эль-Кайвайн',rak:'Рас-эль-Хайма',fujairah:'Фуджейра'};
 const colors=Object.fromEntries(rows.map(el=>[el.dataset.region,el.style.getPropertyValue('--c')]));
 let pinned=null, current=null;
 function setActive(id){current=id;slide.classList.toggle('is-hovered',!!id);slide.querySelectorAll('[data-region]').forEach(el=>{let on=el.dataset.region===id;el.classList.toggle('active',on); if(el.matches('button'))el.setAttribute('aria-pressed',String(on))});status.textContent=id?names[id]:'Наведите на эмират';}
 function register(el){let id=el.dataset.region;el.addEventListener('pointerenter',e=>{if(e.pointerType!=='touch')setActive(id)});el.addEventListener('pointerleave',e=>{if(e.pointerType!=='touch')setActive(pinned)});el.addEventListener('focus',()=>setActive(id));el.addEventListener('blur',()=>setActive(pinned));el.addEventListener('click',e=>{e.stopPropagation();pinned=pinned===id?null:id;setActive(pinned)});if(el.tagName.toLowerCase()==='path')el.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();el.dispatchEvent(new Event('click',{bubbles:true}))}})}
 rows.forEach(register);slide.addEventListener('click',e=>{if(!e.target.closest('[data-region]')){pinned=null;setActive(null)}});
 if(window.Reveal&&typeof Reveal.on==='function')Reveal.on('slidechanged',e=>{if(e.previousSlide===slide){pinned=null;setActive(null)}});
 // Geographic coordinate projection; lat/lon WGS84, preserving longitudes' horizontal distances at UAE latitude.
 const W=980,H=760,lon0=51.34,lon1=56.64,lat0=22.35,lat1=26.37;
 const cos=Math.cos(24.4*Math.PI/180), sx=(W-112)/((lon1-lon0)*cos), sy=(H-118)/(lat1-lat0),s=Math.min(sx,sy);
 const projectedWidth=(lon1-lon0)*cos*s, projectedHeight=(lat1-lat0)*s;
 const bx=(W-projectedWidth)/2+10, by=(H-projectedHeight)/2+48;
 const project=([lon,lat])=>[bx+(lon-lon0)*cos*s,by+(lat1-lat)*s];
 function ringPath(points){return points.map((p,i)=>{const [x,y]=project(p);return `${i?'L':'M'}${x.toFixed(2)},${y.toFixed(2)}`}).join(' ')+' Z';}
 function geomPath(g){let polys=g.type==='MultiPolygon'?g.coordinates:[g.coordinates];return polys.map(poly=>poly.map(ringPath).join(' ')).join(' ')}
 function build(data){let html='';let loaded=0;for(const f of data.features||[]){let id=ids[f.properties?.id]||ids[f.properties?.code]||ids[f.id]||Object.keys(ids).find(k=> (f.properties?.name||'').toLowerCase()===names[ids[k]].toLowerCase());if(!id)continue;html+=`<path d="${geomPath(f.geometry)}" class="uae-region" tabindex="0" role="button" aria-label="${names[id]}" data-region="${id}" style="--c:${colors[id]}" fill-rule="evenodd"/>`;loaded++}if(loaded<7)throw Error('Not all seven emirates found: '+loaded);container.innerHTML=html;container.querySelectorAll('[data-region]').forEach(register);setActive(null)}
 // Real administrative boundaries (Simplemaps geo data, CC BY 4.0) — not traced from an image.
 fetch('https://raw.githubusercontent.com/beckyxu-design/Carbon_Offset_Validation/main/carbon-offset-validator/public/ae.json',{mode:'cors',cache:'force-cache'}).then(r=>{if(!r.ok)throw Error('GeoJSON HTTP '+r.status);return r.json()}).then(build).catch(err=>{console.error('UAE map data:',err);container.innerHTML='<text x="480" y="380" text-anchor="middle" fill="#f6d09e" font-size="19">Не удалось загрузить географические данные</text><text x="480" y="414" text-anchor="middle" fill="#f6d09e" font-size="13">Проверьте интернет или доступ к Simplemaps</text>'});
})();
