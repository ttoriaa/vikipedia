import {test} from 'node:test';
import assert from 'node:assert/strict';
import {createCarState,stepCar,nearestZone} from './physics.mjs';
const run=(s,input,seconds,obs=[])=>{for(let i=0;i<seconds*60;i++)stepCar(s,input,1/60,obs);return s};
test('forward, reverse and brake respond independently of render frame rate',()=>{const s=createCarState();run(s,{throttle:1},2);assert.ok(s.z<0);assert.ok(s.speed<=15);run(s,{brake:true},1);assert.ok(Math.abs(s.speed)<.01);run(s,{throttle:-1},2);assert.ok(s.speed<0);});
test('walls stop a full-speed car without tunneling',()=>{const s=createCarState(0,8,Math.PI),obstacles=[{x:0,z:0,w:10,d:2}];run(s,{throttle:1},8,obstacles);assert.ok(s.z>=2);assert.ok(s.collisions>0);});
test('world boundary holds, and reverse permits escape',()=>{const s=createCarState(0,-29,Math.PI);run(s,{throttle:1},6);assert.ok(s.z>=-30.5);const before=s.z;run(s,{throttle:-1},1);assert.ok(s.z>before);});
test('steering changes course and proximity selects only nearby zones',()=>{const s=createCarState();run(s,{throttle:1,steer:1},2);assert.ok(Math.abs(s.x)>3);assert.equal(nearestZone(s,[{id:'far',x:100,z:100}]),null);assert.equal(nearestZone(s,[{id:'close',x:s.x,z:s.z}]).id,'close');});
