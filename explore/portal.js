import {zones} from './catalog.js?v=20260916c';
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
export function installPortal({openPanel,content,panel,showProject,mark,started}){
 panel.addEventListener('close',()=>{content.replaceChildren();panel.classList.remove('viewer','profile-panel')});
 function resources(z){return z.resources.length?`<section class="related"><h3>这个展区还有</h3>${z.resources.map((r,i)=>`<button class="resource" data-resource="${i}"><span>${esc(r.title)}<small>${esc(r.desc)}</small></span><b>在园区内打开 ↗</b></button>`).join('')}</section>`:''}
 function viewSite(site,backZone){
  openPanel(`<div class="viewer-bar"><div><span class="eyebrow">VIKIPEDIA / IN-WORLD BROWSER</span><h2>${esc(site.title)}</h2></div><button id="viewer-back">← 返回展区</button><a href="${esc(site.url)}" target="_blank" rel="noreferrer">新标签打开 ↗</a></div><div class="viewer-note">正在浏览外部项目 · 关闭面板即可回到原来的停车位置。若页面无法显示，请使用右侧的新标签入口。</div><iframe id="project-frame" title="${esc(site.title)}" src="${esc(site.url)}" sandbox="allow-scripts allow-same-origin allow-forms allow-popups allow-popups-to-escape-sandbox allow-downloads allow-pointer-lock" allow="fullscreen; gamepad" referrerpolicy="strict-origin-when-cross-origin"></iframe>`);
  panel.classList.add('viewer');content.querySelector('#viewer-back').onclick=()=>backZone?.id==='home'?panel.close():showProject(backZone);
 }
 function showHome(){
  if(!started())return;
  mark(zones[0]);
  viewSite({...zones[0],title:"WELCOME TO VICKIE'S WORLD"},zones[0]);
 }
 function enrich(z){
  const anchor=content.querySelector('a.primary');if(!anchor)return;
  anchor.insertAdjacentHTML('beforebegin',`<button id="view-in-world" class="primary">${z.id==='gaming'?'在园区里开始游戏':'在园区内打开项目'} ↗</button> `);anchor.textContent='新标签打开 ↗';anchor.className='secondary-link';
  anchor.insertAdjacentHTML('afterend',resources(z));content.querySelector('#view-in-world').onclick=()=>viewSite(z,z);content.querySelectorAll('[data-resource]').forEach(b=>b.onclick=()=>viewSite(z.resources[+b.dataset.resource],z));
 }
 return {showHome,enrich,viewSite};
}
