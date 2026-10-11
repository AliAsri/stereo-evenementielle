'use strict';
const data=window.REVIEW_DATA,$=id=>document.getElementById(id),canvas=$('canvas'),ctx=canvas.getContext('2d');
let index=0,roi=null,drag=null,lo=null,hi=null,annotations=[],playing=false,timer=null,generation=0,lastImage=null,loaded=false;
data.clips.forEach((c,i)=>{const o=document.createElement('option');o.value=i;o.textContent=c.id;$('clip').appendChild(o)});
const current=()=>data.clips[Number($('clip').value)];
function stop(){playing=false;clearTimeout(timer);$('play').textContent='Lire'}
function dirty(){ $('reviewed').checked=false;$('whole').checked=false; }
function paint(){if(!lastImage)return;ctx.drawImage(lastImage,0,0);if(roi){ctx.strokeStyle='#ffce73';ctx.lineWidth=2;ctx.strokeRect(roi[0],roi[1],roi[2]-roi[0],roi[3]-roi[1])}}
function bounds(){$('bounds').textContent=`Images ${lo===null?'?':lo+1} à ${hi===null?'?':hi+1}`}
function show(){
 loaded=false;['lower','upper','save'].forEach(id=>$(id).disabled=true);const c=current(),f=c.frames[index],g=++generation,image=new Image();
 $('slider').max=c.frames.length-1;$('slider').value=index;$('meta').textContent=` ${c.sequence} · train`;
 $('time').textContent=` ${index+1}/${c.frames.length} · fin +${(f.end_us-c.start_us)/1000} ms`;
 image.onload=()=>{if(g!==generation)return;lastImage=image;loaded=true;paint();['lower','upper','save'].forEach(id=>$(id).disabled=false);
  if(playing)timer=setTimeout(()=>{if(index===current().frames.length-1){stop();return}index++;show()},20)};
 image.onerror=()=>{if(g!==generation)return;stop();$('status').textContent='Image inaccessible : conserver la page et ses dossiers ensemble.'};image.src=f.image;
}
$('clip').onchange=()=>{stop();index=0;roi=drag=null;lo=hi=null;dirty();$('state').value='unknown';$('camera').value='unknown';$('notes').value='';bounds();show()};
$('slider').oninput=()=>{stop();index=Number($('slider').value);show()};
$('prev').onclick=()=>{stop();index=Math.max(0,index-1);show()};$('next').onclick=()=>{stop();index=Math.min(current().frames.length-1,index+1);show()};
$('play').onclick=()=>{if(playing){stop();return}playing=true;if(index===current().frames.length-1)index=0;$('play').textContent='Pause';show()};
function position(e){const b=canvas.getBoundingClientRect();return [Math.max(0,Math.min(640,(e.clientX-b.left)*640/b.width)),Math.max(0,Math.min(480,(e.clientY-b.top)*480/b.height))]}
canvas.onpointerdown=e=>{if(!loaded)return;stop();dirty();drag=position(e);canvas.setPointerCapture(e.pointerId)};
canvas.onpointermove=e=>{if(!drag)return;const p=position(e);roi=[Math.min(drag[0],p[0]),Math.min(drag[1],p[1]),Math.max(drag[0],p[0]),Math.max(drag[1],p[1])].map(Math.round);paint()};
canvas.onpointerup=canvas.onpointercancel=()=>{drag=null};
$('clear').onclick=()=>{dirty();roi=null;paint()};$('lower').onclick=()=>{stop();dirty();lo=index;bounds()};$('upper').onclick=()=>{stop();dirty();hi=index;bounds()};
$('state').onchange=$('camera').onchange=dirty;$('notes').oninput=()=>{$('reviewed').checked=false};
function list(){ $('entries').replaceChildren();annotations.forEach((a,i)=>{const row=document.createElement('div');row.textContent=`${i+1}. ${a.clip_id} · ${a.state} · images ${a.frame_interval[0]+1}–${a.frame_interval[1]+1} `;const b=document.createElement('button');b.textContent='Supprimer';b.onclick=()=>{annotations.splice(i,1);list()};row.appendChild(b);$('entries').appendChild(row)})}
$('save').onclick=()=>{
 stop();const fail=message=>{$('status').textContent=message};
 if(!loaded||!roi||roi[2]<=roi[0]||roi[3]<=roi[1])return fail('Dessinez une zone non vide sur une image chargée.');
 if(lo===null||hi===null||lo>hi)return fail('Choisissez un intervalle d’images valide.');
 if(!$('author').value.trim()||!$('notes').value.trim())return fail('Renseignez l’annotateur et les indices observés.');
 if(!$('whole').checked||!$('reviewed').checked)return fail('Confirmez la pertinence de la zone et la relecture de l’intervalle.');
 annotations.push({clip_id:current().id,state:$('state').value,camera_state:$('camera').value,roi_xyxy:roi.slice(),frame_interval:[lo,hi],
  reviewed:true,roi_valid_for_whole_interval:true,annotator:$('author').value.trim(),notes:$('notes').value.trim(),source:'manual_blind_event_clip',created_utc:new Date().toISOString()});
 list();dirty();$('status').textContent=`${annotations.length} annotation(s) en mémoire. Exportez pour conserver.`;
};
$('export').onclick=()=>{if(!annotations.length){$('status').textContent='Aucune annotation à exporter.';return}
 const document={schema:data.schema,target:data.target,manifest_id:data.manifest_id,annotations};
 const url=URL.createObjectURL(new Blob([JSON.stringify(document,null,2)],{type:'application/json'}));const a=window.document.createElement('a');a.href=url;a.download='M13_manual_review.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
};
window.onbeforeunload=e=>{if(annotations.length){e.preventDefault();e.returnValue=''}};bounds();show();
