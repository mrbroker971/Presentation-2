/* Slide 06: two-way hover and click-to-lock, independent from the Reveal lifecycle. */
(() => {
 const slide=document.querySelector('section.atlas-v2'); if(!slide)return;
 const els=[...slide.querySelectorAll('[data-region]')];
 const names=Object.fromEntries([...slide.querySelectorAll('.atlas-item')].map(el=>[el.dataset.region,el.querySelector('strong').textContent]));
 const output=slide.querySelector('.atlas-selected'); let pinned=null;
 function activate(id){
  slide.classList.toggle('is-interacting',Boolean(id));
  els.forEach(el=>{let active=el.dataset.region===id; el.classList.toggle('active',active);el.setAttribute('aria-pressed',String(active));});
  output.textContent=id?names[id]:'Выберите эмират';
 }
 els.forEach(el=>{
  el.addEventListener('pointerenter',e=>{if(e.pointerType!=='touch')activate(el.dataset.region)});
  el.addEventListener('pointerleave',e=>{if(e.pointerType!=='touch')activate(pinned)});
  el.addEventListener('focus',()=>activate(el.dataset.region));
  el.addEventListener('blur',()=>activate(pinned));
  el.addEventListener('click',e=>{e.stopPropagation();pinned=pinned===el.dataset.region?null:el.dataset.region;activate(pinned)});
  if(el.tagName.toLowerCase()==='polygon')el.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();el.dispatchEvent(new MouseEvent('click',{bubbles:true}))}});
 });
 slide.addEventListener('click',e=>{if(!e.target.closest('[data-region]')){pinned=null;activate(null)}});
 if(window.Reveal&&typeof Reveal.on==='function')Reveal.on('slidechanged',e=>{if(e.previousSlide===slide){pinned=null;activate(null)}});
 activate(null);
})();
