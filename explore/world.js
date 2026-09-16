import * as THREE from './vendor/three.module.js';
import {zones} from './catalog.js';
import {buildCar} from './car.js';
export {zones};
export function buildWorld(host,quality){
 const scene=new THREE.Scene();scene.background=new THREE.Color('#e8e4df');
 const renderer=new THREE.WebGLRenderer({antialias:true,powerPreference:'high-performance'});renderer.setPixelRatio(Math.min(devicePixelRatio,quality==='high'?1.6:1));renderer.shadowMap.enabled=quality==='high';renderer.shadowMap.type=THREE.PCFShadowMap;renderer.outputColorSpace=THREE.SRGBColorSpace;renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=1.3;host.append(renderer.domElement);
 const camera=new THREE.OrthographicCamera(-60,60,40,-40,.1,250);const focus=new THREE.Vector3(-5,0,0);camera.position.set(48,58,66);camera.lookAt(focus);
 const hemi=new THREE.HemisphereLight(0xfff8e9,0xb4a9c3,2.5);scene.add(hemi);const sun=new THREE.DirectionalLight(0xffedcd,3.2);sun.position.set(-25,50,20);sun.castShadow=true;sun.shadow.mapSize.set(2048,2048);Object.assign(sun.shadow.camera,{left:-65,right:65,top:55,bottom:-55,near:1,far:140});sun.shadow.normalBias=.035;sun.shadow.bias=-.0002;scene.add(sun);
 const materials=new Map();function mat(color){if(!materials.has(color))materials.set(color,new THREE.MeshStandardMaterial({color,roughness:.82}));return materials.get(color)}
 const obstacles=[],animated=[];
 function mesh(geo,color,x,y,z,parent=scene){const m=new THREE.Mesh(geo,mat(color));m.position.set(x,y,z);m.castShadow=true;m.receiveShadow=true;parent.add(m);return m}
 function box(w,h,d,c,x,y,z,parent=scene){return mesh(new THREE.BoxGeometry(w,h,d),c,x,y,z,parent)}
 function cyl(r,h,c,x,y,z,parent=scene,segments=20){return mesh(new THREE.CylinderGeometry(r,r,h,segments),c,x,y,z,parent)}
 function block(w,h,d,c,x,z){const m=box(w,h,d,c,x,h/2+.15,z);obstacles.push({x,z,w,d});return m}
 function label(text,sub,w=10,h=2){const canvas=document.createElement('canvas');canvas.width=1024;canvas.height=256;const ctx=canvas.getContext('2d');ctx.fillStyle='#fff9eb';ctx.fillRect(0,0,1024,256);ctx.textAlign='center';ctx.fillStyle='#584463';ctx.font='bold 76px "Segoe UI",sans-serif';ctx.fillText(text,512,115);ctx.fillStyle='#9782a3';ctx.font='27px "Segoe UI",sans-serif';ctx.fillText(sub,512,185);const texture=new THREE.CanvasTexture(canvas);texture.colorSpace=THREE.SRGBColorSpace;return new THREE.Mesh(new THREE.PlaneGeometry(w,h),new THREE.MeshBasicMaterial({map:texture,side:THREE.DoubleSide}))}
 // A handcrafted toy-like island; all models generated locally, no external assets.
 box(82,2,68,0xbeb5af,0,-1.25,0);box(81,.6,67,0xe0dec9,0,-.15,0);
 const bg=box(1000,.2,1000,0xe8e4df,0,-3,0);bg.castShadow=false;
 // Asphalt loop and central avenue.
 [ [-27,0,7,43],[27,0,7,43],[0,-18,61,7],[0,18,61,7],[0,0,7,40] ].forEach(([x,z,w,d])=>box(w,.06,d,0xbcb8b0,x,.2,z));
 for(let n=-28;n<=28;n+=5){box(2,.02,.13,0xf5eedb,n,.25,-18);box(2,.02,.13,0xf5eedb,n,.25,18)}
 for(let n=-13;n<=13;n+=5){[-27,27,0].forEach(x=>box(.13,.02,2,0xf5eedb,x,.25,n))}
 // Raised planting beds and pavilion bases.
 box(17,.4,10,0xcad0b5,-18,.25,5);box(17,.4,10,0xd2c4d9,18,.25,3);
 // Welcome plaza and sculpture.
 cyl(5.6,.25,0xede5d7,0,.25,15);cyl(3,.25,0xe7ded2,-9,.25,2);cyl(1.7,.6,0xcbb8dd,-9,.6,2);
 const sculpture=new THREE.Group();sculpture.position.set(-9,3.3,2);scene.add(sculpture);const knot=mesh(new THREE.TorusKnotGeometry(1.6,.48,80,10),0x9873bc,0,0,0,sculpture);animated.push({kind:'rotate',obj:knot});obstacles.push({x:-9,z:2,w:3.5,d:3.5});
 const title=label('VIKIPEDIA',"LET'S ROLL.",13,3.25);title.rotation.x=-Math.PI/2;title.position.set(-7,.29,25);scene.add(title);
 // Automotive pavilion.
 block(15,1.1,9,0xb2c7b3,-24,-26);block(13,4,6,0x93b6a7,-24,-26);
 box(15,.45,9,0xdbe6d6,-24,4.4,-26);box(10,2.5,.1,0x405e5b,-24,2.4,-22.94);
 const autoSign=label('CHARGE LAB','DATA → INSIGHT',11,2.75);autoSign.position.set(-24,5.7,-23);scene.add(autoSign);
 for(let i=0;i<3;i++){const x=-31+i*5;block(1.6,2.6,1,0xf3efda,x,-20.6);box(.95,.8,.08,0x658b84,x,2,-20.04);box(.6,.12,.09,0xbef1b4,x,2.03,-19.98);const cable=mesh(new THREE.TorusGeometry(.6,.07,6,16,Math.PI*1.5),0x455c58,x+.8,1.3,-20.1);cable.rotation.z=.6}
 // AI pavilion: glass cube, floating network sculpture.
 block(14,.6,9,0xc1afd1,23,-25);block(12,4.2,7,0xb8a3cc,23,-25);box(13,.4,8,0xdacbe5,23,4.6,-25);box(10,2.8,.1,0x635674,23,2.7,-21.45);
 const aiSign=label('AI STUDIO','THINK. CONNECT. CREATE.',10,2.5);aiSign.position.set(23,5.9,-21.3);scene.add(aiSign);
 const nodes=new THREE.Group();nodes.position.set(23,7.7,-25);scene.add(nodes);[[0,0,0],[-2.2,1.3,0],[2.2,1,0],[0,2.5,0]].forEach(([x,y,z],i)=>{mesh(new THREE.IcosahedronGeometry(i? .55:.8,0),i?0xd6edb1:0x9271b9,x,y,z,nodes);if(i){const points=[new THREE.Vector3(),new THREE.Vector3(x,y,z)];nodes.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(points),new THREE.LineBasicMaterial({color:0x9779b0})))}});animated.push({kind:'rotate',obj:nodes});
 // Podcast studio: warm terracotta stage and a giant microphone.
 block(12,.6,8,0xd5bba0,27,26);block(10,4.2,6,0xc89578,27,26);box(11,.45,7,0xe5c3a1,27,4.6,26);box(7.8,2.5,.1,0x83584d,27,2.6,22.95);
 const podSign=label('ON AIR','SHIMAI PODCAST',8,2);podSign.position.set(27,5.8,22.8);scene.add(podSign);
 cyl(.65,.3,0x624b50,19,.6,25);cyl(.13,3,0x806574,19,2,25);const mic=mesh(new THREE.CapsuleGeometry(.65,1.15,4,8),0x756178,19,4.1,25);mic.rotation.z=-.15;
 const hoop=mesh(new THREE.TorusGeometry(1.1,.1,6,20,Math.PI),0xdac4ad,19,3.9,25);hoop.rotation.z=Math.PI;
 obstacles.push({x:19,z:25,w:2,d:2});
 // Small decorative objects: trees, rocks, cones, solar panels and benches.
 function tree(x,z,s=1){cyl(.18*s,1.8*s,0xa58a72,x,.9*s,z);mesh(new THREE.IcosahedronGeometry(1.5*s,0),0xa5b59a,x,2.9*s,z);mesh(new THREE.IcosahedronGeometry(1*s,0),0xc0c9a2,x+.6*s,3.3*s,z-.2);obstacles.push({x,z,w:.8*s,d:.8*s})}
 [[-35,-28,1],[-37,-10,1.1],[-36,9,1],[-33,26,1.2],[-20,28,.8],[-14,-28,.9],[5,-28,.9],[36,-26,.9],[37,-7,1.1],[35,8,.8],[10,27,.9],[-20,4,.7],[-14,5,.7],[13,4,.8],[20,4,.65]].forEach(t=>tree(...t));
 for(let i=0;i<7;i++){const x=-34+i*2.5,z=24;box(.6,.13,.6,0xeee1c6,x,.4,z);mesh(new THREE.ConeGeometry(.22,.8,8),0xcc9a75,x,.85,z)}
 [[-18,9],[14,9],[-17,-8],[9,-8]].forEach(([x,z])=>{box(3,.25,1,0xaf927c,x,.9,z);box(3,.75,.15,0xbca087,x,1.3,z+.45);box(.18,.8,.7,0x655b5b,x-1,.5,z);box(.18,.8,.7,0x655b5b,x+1,.5,z);obstacles.push({x,z,w:3,d:1})});
 for(let i=0;i<18;i++){const x=-36+i*4.2;mesh(new THREE.DodecahedronGeometry(.35+(i%3)*.12,0),0xc2b8ae,x,.35,-31)}
 // New stations reuse the existing roads and open plazas.
 // The game pavilion has a start gate and a checkered finish line.
 [-31,-21].forEach(x=>block(.7,4,.7,0x778ba3,x,24));box(11,.85,.9,0x748ba6,-26,4.35,24);
 const gameSign=label('///M PLAYGROUND','CHESS / 2048 / SUDOKU / SNAKE',10,2.5);gameSign.position.set(-26,5.9,24.1);scene.add(gameSign);
 for(let i=0;i<10;i++)for(let j=0;j<2;j++)box(1,.035,.6,(i+j)%2?0x5c6070:0xfaf3e5,-30.5+i,.29,21+j*.6);
 // Knowledge pavilion: books behind a planted reading plaza.
 for(let i=0;i<5;i++)block(.8,2+(i%3)*.35,1.5,[0xb1baa0,0xc0a9d2,0xd9bb93][i%3],-22+i,-4);
 const booksSign=label('TOKEN GARDEN','A PLACE FOR GROWING IDEAS',8,2);booksSign.position.set(-20,4.2,-4);scene.add(booksSign);
 // C7 gallery at the north end of the avenue.
 block(10,.6,5,0xb5c4c7,0,-27);[-4,-1.3,1.3,4].forEach(x=>block(.55,3.2,.6,0xcfd9d7,x,-26));box(11,.45,5.5,0x98b4b9,0,3.7,-27);
 const c7Sign=label('C7 / OTA','REGULATION GALLERY',9,2.25);c7Sign.position.set(0,5.1,-25);scene.add(c7Sign);
 // Market station: billboard data bars, original illustrative geometry.
 block(5,.6,2,0xc4b59a,15,7);box(5,2.5,.4,0x776b5c,15,2,7);[1,1.8,1.3,2].forEach((h,i)=>box(.6,h,.08,0xcdddab,13.5+i,1+h/2,7.25));
 const marketSign=label('MARKET WATCH','OBSERVE. CONNECT. UNDERSTAND.',8,2);marketSign.position.set(15,4.2,7);scene.add(marketSign);
 // Entry pads have clear drive-up interaction points.
 const pads=[];zones.forEach(z=>{const pad=cyl(2.9,.08,z.color,z.x,.31,z.z);const ring=mesh(new THREE.TorusGeometry(3,.08,6,48),0xfbf6e9,z.x,.38,z.z);ring.rotation.x=-Math.PI/2;pads.push(pad);const pole=cyl(.09,2.3,0x958592,z.x+3.5,1.3,z.z);const flag=box(1.5,.9,.08,z.color,z.x+4.1,2.1,z.z);obstacles.push({x:z.x+3.5,z:z.z,w:.4,d:.4});});
 const {car,body,wheels}=buildCar(scene);
 function resize(){const w=innerWidth,h=innerHeight,aspect=w/h;const vertical=aspect<1?56:43;camera.left=-vertical*aspect;camera.right=vertical*aspect;camera.top=vertical;camera.bottom=-vertical;camera.updateProjectionMatrix();renderer.setSize(w,h)}resize();addEventListener('resize',resize);
 function setQuality(q){renderer.setPixelRatio(Math.min(devicePixelRatio,q==='high'?1.6:1));renderer.shadowMap.enabled=q==='high';scene.traverse(o=>{if(o.material)o.material.needsUpdate=true});}
 const aim=new THREE.Vector3(),projected=new THREE.Vector3();
 function update(s,dt,time,reduceMotion,steer=0){car.position.set(s.x,.1,s.z);car.rotation.y=s.heading;body.rotation.z=reduceMotion?0:steer*s.speed*.002;wheels.forEach(w=>{w.pivot.rotation.y=w.front?-steer*.35:0;w.tire.rotation.x+=s.speed*dt*1.8;w.hub.rotation.x=w.tire.rotation.x});animated.forEach(a=>{if(!reduceMotion)a.obj.rotation.y+=dt*.22});
  const mobile=innerWidth<650;aim.set(mobile?s.x*.75:-5+s.x*.3,0,mobile?s.z*.75:s.z*.3);focus.lerp(aim,reduceMotion?1:1-Math.exp(-2*dt));camera.position.copy(focus).add(new THREE.Vector3(48,58,66));camera.lookAt(focus);renderer.render(scene,camera);
 }
 function screenPoint(x,y,z){projected.set(x,y,z).project(camera);return{x:(projected.x+1)*innerWidth/2,y:(1-projected.y)*innerHeight/2}}
 return {renderer,scene,camera,car,obstacles,update,screenPoint,setQuality,info:()=>({calls:renderer.info.render.calls,triangles:renderer.info.render.triangles})};
}

