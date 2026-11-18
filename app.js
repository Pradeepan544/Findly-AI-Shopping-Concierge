const $=id=>document.getElementById(id);
const form=$('form'),input=$('input'),messages=$('messages'),stateBox=$('state'),productsBox=$('products');
function addMessage(text,who='bot'){const row=document.createElement('div');row.className='msg '+(who==='user'?'user':'botmsg');const p=document.createElement('p');p.textContent=text;row.appendChild(p);messages.appendChild(row);messages.scrollTop=messages.scrollHeight}
function escapeHTML(v){return String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
function safeURL(v){try{let u=new URL(v);return ['https:','http:'].includes(u.protocol)?u.href:'#'}catch{return '#'}}
function value(obj){return obj&&typeof obj==='object'?obj.value:obj}
function money(v){return v==null?'—':'₹'+Number(v).toLocaleString('en-IN',{maximumFractionDigits:0})}
function renderState(s={}){
 const budgetLabel=(()=>{const lo=value(s.budget_min),hi=value(s.budget_max);if(lo!=null&&hi!=null)return '₹'+Number(lo).toLocaleString('en-IN')+'–₹'+Number(hi).toLocaleString('en-IN');if(lo!=null)return 'Above ₹'+Number(lo).toLocaleString('en-IN');if(hi!=null)return 'Up to ₹'+Number(hi).toLocaleString('en-IN');return null})();
 const fields=[['Category',s.category],['Budget',budgetLabel],['Brand',s.brand_preference],['Features',s.features?.length?s.features.map(x=>x.value).join(', '):null],['Purpose',s.purpose],['Minimum rating',s.min_rating],['Review volume',s.min_rating_count]];
 let count=fields.filter(x=>value(x[1])!==null&&value(x[1])!==undefined&&value(x[1])!=='').length;
 $('filled').textContent=count+'/7';
 stateBox.innerHTML=fields.map(([label,item])=>{let v=Array.isArray(item)?item:(value(item));let src=item&&item.source?item.source:null;return `<div class="stateitem"><span>${label}</span><b>${v==null||v===''?'Not specified':escapeHTML(v)}${src?`<small class="source">${src}</small>`:''}</b></div>`}).join('');
}
function renderProducts(items=[]){
 $('matches').textContent=items.length?items.length+' found':'—';
 if(!items.length){productsBox.innerHTML='<p class="placeholder">No products matched all current filters. Try relaxing one requirement.</p>';return}
 productsBox.innerHTML=items.map(p=>`<article class="product"><img src="${safeURL(p.image)}" onerror="this.style.visibility='hidden'" alt=""><div><h4>${escapeHTML(p.name)}</h4><div class="price">${money(p.price)}</div><div class="meta">★ ${p.rating??'N/A'} · ${Number(p.rating_count??0).toLocaleString('en-IN')} ratings</div><a href="${safeURL(p.link)}" target="_blank" rel="noopener">View product ↗</a></div></article>`).join('');
}
async function sendMessage(text){
 if(!text.trim())return;addMessage(text,'user');input.value='';$('suggestions').style.display='none';$('send').disabled=true;$('send').textContent='Thinking…';
 try{
  const response=await fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:text})});
  const data=await response.json();if(!response.ok)throw new Error(data.error||'Request failed');
  addMessage(data.assistant);renderState(data.state);
  if(data.ready)renderProducts(data.products);
 }catch(err){addMessage('I ran into a problem: '+err.message)}
 finally{$('send').disabled=false;$('send').textContent='Send ↑';input.focus()}
}
form.addEventListener('submit',e=>{e.preventDefault();sendMessage(input.value)});
document.querySelectorAll('.suggestions button').forEach(b=>b.addEventListener('click',()=>sendMessage(b.textContent)));
$('reset').addEventListener('click',async()=>{await fetch('/api/reset',{method:'POST'});messages.innerHTML='';addMessage("Hi! I'm Findly. Tell me what you're shopping for — in your own words. You can mention a product, budget, brand or features that matter.");renderState({});renderProducts([]);$('suggestions').style.display='flex'});
