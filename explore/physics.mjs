export const clamp=(x,a,b)=>Math.max(a,Math.min(b,x));
export function createCarState(x=0,z=15,heading=Math.PI){return {x,z,heading,speed:0,distance:0,collisions:0};}
// Arcade vehicle: deterministic fixed-step planar motion, circle vs expanded AABB.
// Visible suspension/tires are cosmetic; not a full rigid-body vehicle simulation.
export function stepCar(s,input,dt,obstacles=[],sensitivity=1){
 const throttle=clamp(input.throttle||0,-1,1),steer=clamp(input.steer||0,-1,1);
 s.speed+=throttle*13*dt;
 if(!throttle)s.speed*=Math.exp(-1.6*dt);
 if(input.brake)s.speed*=Math.exp(-10*dt);
 s.speed=clamp(s.speed,-7,15);
 if(Math.abs(s.speed)<.015)s.speed=0;
 s.heading-=steer*sensitivity*1.75*(s.speed/12)*dt;
 const dx=Math.sin(s.heading)*s.speed*dt,dz=Math.cos(s.heading)*s.speed*dt;
 let nx=s.x+dx,nz=s.z+dz,hit=false;
 const radius=1.05;
 for(const o of obstacles){const cx=clamp(nx,o.x-o.w/2,o.x+o.w/2),cz=clamp(nz,o.z-o.d/2,o.z+o.d/2);if(Math.hypot(nx-cx,nz-cz)<radius){hit=true;break;}}
 if(Math.abs(nx)>37.5||Math.abs(nz)>30.5)hit=true;
 if(hit){s.speed=-s.speed*.16;s.collisions++;}else{s.x=nx;s.z=nz;s.distance+=Math.hypot(dx,dz);}
 return hit;
}
export function nearestZone(s,zones,radius=7){return zones.reduce((best,z)=>{const d=Math.hypot(s.x-z.x,s.z-z.z);return d<radius&&(!best||d<best.distance)?{...z,distance:d}:best},null)}
