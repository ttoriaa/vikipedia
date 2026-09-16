import * as THREE from './vendor/three.module.js';

// Original procedural BMW-inspired coupe. +Z is forward; dimensions retain
// the driving demo's existing collision footprint.
export function buildCar(scene){
 const car=new THREE.Group(),body=new THREE.Group();scene.add(car);car.add(body);
 const paint=new THREE.MeshStandardMaterial({color:0xf3f5f7,metalness:.35,roughness:.3});
 const black=new THREE.MeshStandardMaterial({color:0x101722,roughness:.38});
 const glass=new THREE.MeshStandardMaterial({color:0x263b50,metalness:.55,roughness:.18});
 const chrome=new THREE.MeshStandardMaterial({color:0xbfcbd5,metalness:.8,roughness:.24});
 const red=new THREE.MeshBasicMaterial({color:0xff344e});
 const light=new THREE.MeshBasicMaterial({color:0xe9faff});
 const add=(geometry,material,x,y,z,parent=body)=>{const m=new THREE.Mesh(geometry,material);m.position.set(x,y,z);m.castShadow=true;m.receiveShadow=true;parent.add(m);return m;};
 const box=(w,h,d,m,x,y,z,parent=body)=>add(new THREE.BoxGeometry(w,h,d),m,x,y,z,parent);
 function quad(points,material){const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.Float32BufferAttribute(points.flat(),3));g.setIndex([0,1,2,0,2,3]);g.computeVertexNormals();const m=new THREE.Mesh(g,material);m.material.side=THREE.DoubleSide;body.add(m);return m;}
 // Long hood, rear-set cabin, broad shoulders and black lower aero trim.
 box(1.88,.38,3.65,paint,0,.7,0);
 box(1.9,.13,3.7,black,0,.46,0);
 box(1.77,.13,1.23,paint,0,.95,1.13);
 box(1.8,.12,.63,paint,0,.95,-1.46);
 box(1.35,.1,1.13,black,0,1.46,-.3);
 quad([[-.86,.95,.53],[.86,.95,.53],[.66,1.42,.24],[-.66,1.42,.24]],glass);
 quad([[.86,.96,-1.17],[-.86,.96,-1.17],[-.66,1.42,-.87],[.66,1.42,-.87]],glass);
 for(const s of [-1,1]){
  quad([[s*.87,.96,.48],[s*.87,.96,-1.14],[s*.68,1.42,-.85],[s*.68,1.42,.21]],glass);
  const pillar=box(.07,.5,.07,paint,s*.75,1.19,-.5);pillar.rotation.z=s*.36;
  box(.08,.07,1.55,paint,s*.9,.95,-.31);
  box(.09,.06,.25,chrome,s*.955,.87,-.51);
  box(.24,.11,.24,black,s*1.0,1.03,.33);
  box(.1,.13,2.05,black,s*.97,.45,-.03);
  // Raised wheel arches and shoulder line.
  for(const z of [-1.14,1.12])box(.17,.14,.9,paint,s*.91,.84,z);
 }
 // Two tall kidneys with chrome surrounds and vertical black slats.
 for(const s of [-1,1]){
  box(.43,.46,.06,chrome,s*.245,.71,1.851);
  box(.35,.38,.07,black,s*.245,.71,1.889);
  for(const dx of [-.09,0,.09])box(.018,.34,.018,chrome,s*.245+dx,.71,1.931);
  box(.36,.19,.07,black,s*.69,.83,1.855);
  for(const dx of [-.09,.09]){
   const ring=add(new THREE.TorusGeometry(.064,.015,4,12),light,s*.69+dx,.85,1.902);ring.scale.y=.7;
  }
  box(.31,.13,.045,black,s*.73,.53,1.875);
  box(.49,.045,.05,red,s*.62,.9,-1.85);
  box(.04,.13,.05,red,s*.85,.855,-1.85);
  for(const dx of [-.08,.08]){const pipe=add(new THREE.CylinderGeometry(.055,.055,.16,12),chrome,s*.64+dx,.45,-1.9);pipe.rotation.x=Math.PI/2;}
 }
 box(1.74,.055,.17,black,0,1.06,-1.7);
 box(1.64,.09,.09,black,0,.39,1.87);
 // Subtle M-colored grille accents.
 [0x4dc9f6,0x244697,0xe43c4c].forEach((c,i)=>box(.025,.28,.018,new THREE.MeshBasicMaterial({color:c}),-.36+i*.035,.72,1.944));
 const canvas=document.createElement('canvas');canvas.width=canvas.height=128;const ctx=canvas.getContext('2d');
 ctx.fillStyle='#d9e1e8';ctx.beginPath();ctx.arc(64,64,63,0,Math.PI*2);ctx.fill();
 ctx.fillStyle='#101722';ctx.beginPath();ctx.arc(64,64,58,0,Math.PI*2);ctx.fill();
 for(let i=0;i<4;i++){ctx.fillStyle=i%2?'#fff':'#168bd0';ctx.beginPath();ctx.moveTo(64,64);ctx.arc(64,64,39,i*Math.PI/2,(i+1)*Math.PI/2);ctx.fill();}
 ctx.fillStyle='#fff';ctx.font='bold 15px Arial';ctx.textAlign='center';ctx.fillText('BMW',64,22);
 const texture=new THREE.CanvasTexture(canvas);texture.colorSpace=THREE.SRGBColorSpace;
 const badge=new THREE.MeshBasicMaterial({map:texture,transparent:true,toneMapped:false});
 const roundel=add(new THREE.CircleGeometry(.13,24),badge,0,1.021,1.61);roundel.rotation.x=-Math.PI/2;
 const rear=add(new THREE.CircleGeometry(.1,24),badge,0,.91,-1.857);rear.rotation.y=Math.PI;
 const wheels=[];
 for(const s of [-1,1])for(const z of [-1.14,1.12]){
  const pivot=new THREE.Group();pivot.position.set(s*.99,.48,z);car.add(pivot);
  const tire=add(new THREE.CylinderGeometry(.43,.43,.25,24),black,0,0,0,pivot);tire.rotation.z=Math.PI/2;
  const hub=new THREE.Group();pivot.add(hub);
  const rim=add(new THREE.CylinderGeometry(.32,.32,.27,20),chrome,0,0,0,hub);rim.rotation.z=Math.PI/2;
  const inset=add(new THREE.CylinderGeometry(.26,.26,.28,20),black,0,0,0,hub);inset.rotation.z=Math.PI/2;
  for(let k=0;k<5;k++)for(const offset of [-.065,.065]){
   const angle=k*Math.PI*2/5+offset;
   const spoke=box(.3,.035,.54,chrome,0,0,0,hub);spoke.rotation.x=angle;
  }
  const cap=add(new THREE.CircleGeometry(.08,20),badge,s*.158,0,0,hub);cap.rotation.y=s*Math.PI/2;
  wheels.push({pivot,tire,hub,front:z>0});
 }
 return {car,body,wheels};
}
