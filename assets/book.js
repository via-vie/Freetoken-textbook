const articles=[...document.querySelectorAll('.chapter')],nav=[...document.querySelectorAll('nav a')];
let read=new Set;try{read=new Set(JSON.parse(localStorage.getItem('ft-book-read')||'[]'))}catch(e){}
function progress(){nav.forEach(a=>a.classList.toggle('read',read.has(a.hash.slice(1))));document.getElementById('progress').textContent=read.size+' / '+articles.length+' 章已复查'}
function show(){let id=location.hash.slice(1);if(!articles.some(x=>x.id===id))id='ch01';articles.forEach(x=>x.classList.toggle('active',x.id===id));nav.forEach(x=>x.classList.toggle('active',x.hash==='#'+id));document.title=document.getElementById(id).dataset.title+' · FreeToken 源码教材';progress()}
addEventListener('hashchange',()=>{show();window.scrollTo({top:0,behavior:'instant'})});
document.getElementById('search').oninput=e=>{const q=e.target.value.trim().toLowerCase();let n=0;nav.forEach(a=>{a.hidden=!document.querySelector(a.hash).textContent.toLowerCase().includes(q);if(!a.hidden)n++});document.getElementById('searchcount').textContent=q?n+' 章包含此词':'搜索正文、函数和术语'};
document.getElementById('menu').onclick=e=>{const on=document.getElementById('sidebar').classList.toggle('expanded');e.target.setAttribute('aria-expanded',on)};
document.querySelectorAll('.done').forEach(b=>b.onclick=()=>{const id=b.closest('article').id;read.has(id)?read.delete(id):read.add(id);try{localStorage.setItem('ft-book-read',JSON.stringify([...read]))}catch(e){}progress()});
document.querySelectorAll('.copy').forEach(b=>b.onclick=async()=>{try{await navigator.clipboard.writeText(b.nextElementSibling.textContent);b.textContent='已复制'}catch(e){b.textContent='请选中复制'}});
let font=18;document.getElementById('larger').onclick=()=>{font=Math.min(24,font+1);document.documentElement.style.setProperty('--read',font+'px')};document.getElementById('smaller').onclick=()=>{font=Math.max(15,font-1);document.documentElement.style.setProperty('--read',font+'px')};document.getElementById('print').onclick=()=>print();
const experiments=JSON.parse(document.getElementById('labdata').textContent);
const rounded=(k,v)=>typeof v==='number'&&!Number.isInteger(v)?Number(v.toFixed(3)):v;
document.querySelectorAll('.lab').forEach(el=>{const key=el.dataset.lab,data=experiments[key],rows=data.rows||data.experts||[data],buttons=el.querySelector('.labbuttons');
function select(i){el.querySelector('.laboutput').textContent=JSON.stringify(rows[i],rounded,2);el.querySelector('.labsummary').textContent=key==='hybrid'?'q='+rows[i].q+'，理想关键路径 '+rows[i].critical_ms.toFixed(3)+' ms':key==='prefill'?'层 '+rows[i].layer+' 使用缓冲 '+rows[i].buffer:key==='cache'?'第 '+rows[i].step+' 步；先比较 needed 与 before，再看 after':key==='request'?rows[i].event:'条目 '+(i+1)+' / '+rows.length;[...buttons.children].forEach((b,j)=>b.setAttribute('aria-pressed',i===j))}
rows.forEach((r,i)=>{const b=document.createElement('button');b.type='button';b.textContent=key==='hybrid'?'q='+r.q:String(i+1);b.onclick=()=>select(i);buttons.append(b)});select(0);
const full=document.createElement('details');full.innerHTML='<summary>全部输入与输出（完整精度）</summary>';const pre=document.createElement('pre');pre.textContent=JSON.stringify(data,null,2);full.append(pre);el.append(full)});
articles.at(-1).querySelector('.next').href='#ch01';articles.at(-1).querySelector('.next').textContent='回到第一章';show();window.bookReady=true;
