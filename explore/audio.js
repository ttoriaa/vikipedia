// Original procedural soundscapes. No streaming or external media dependencies.
export const soundscapes=['rain','vlog','sport','nature','quiet'];
export class DriveAudio{
 constructor(contextFactory=()=>new AudioContext()){this.enabled=false;this.music=.3;this.effects=.3;this.scene='vlog';this.ctx=null;this.contextFactory=contextFactory;this.nextNote=0;this.step=0;}
 gain(value,destination){const g=this.ctx.createGain();g.gain.value=value;g.connect(destination);return g;}
 oscillator(type,f,destination){const o=this.ctx.createOscillator();o.type=type;o.frequency.value=f;o.connect(destination);o.start();return o;}
 async unlock(){
  if(!this.ctx){
   this.ctx=this.contextFactory();const c=this.ctx;
   const limiter=c.createDynamicsCompressor();limiter.threshold.value=-12;limiter.knee.value=12;limiter.ratio.value=8;limiter.attack.value=.003;limiter.release.value=.2;limiter.connect(c.destination);
   this.master=this.gain(0,limiter);this.background=this.gain(0,this.master);this.engineGain=this.gain(0,this.master);
   const engineFilter=c.createBiquadFilter();engineFilter.type='lowpass';engineFilter.frequency.value=420;engineFilter.Q.value=.65;engineFilter.connect(this.engineGain);this.engineFilter=engineFilter;
   this.engine=this.oscillator('sawtooth',48,this.gain(.3,engineFilter));this.engineBass=this.oscillator('sine',24,this.gain(.6,engineFilter));this.engineHarmonic=this.oscillator('triangle',96,this.gain(.15,engineFilter));
   const buffer=c.createBuffer(1,c.sampleRate*6,c.sampleRate),data=buffer.getChannelData(0);let brown=0;
   for(let i=0;i<data.length;i++){brown=(brown+.025*(Math.random()*2-1))/1.025;data[i]=brown*3.5;}
   this.noise=c.createBufferSource();this.noise.buffer=buffer;this.noise.loop=true;
   this.rain=this.gain(0,this.background);this.wind=this.gain(0,this.background);this.melody=this.gain(0,this.background);
   const rainFilter=c.createBiquadFilter();rainFilter.type='highpass';rainFilter.frequency.value=550;this.noise.connect(rainFilter);rainFilter.connect(this.rain);
   const windFilter=c.createBiquadFilter();windFilter.type='lowpass';windFilter.frequency.value=430;this.noise.connect(windFilter);windFilter.connect(this.wind);this.noise.start();this.nextNote=c.currentTime;
  }
  if(this.ctx.state==='suspended'&&this.ctx.resume&&!(globalThis.OfflineAudioContext&&this.ctx instanceof OfflineAudioContext))await this.ctx.resume();
 }
 async setEnabled(value){if(value){await this.unlock();this.enabled=true;}else this.enabled=false;if(this.ctx)this.master.gain.setTargetAtTime(this.enabled?.75:0,this.ctx.currentTime,.12);}
 setScene(scene){this.scene=soundscapes.includes(scene)?scene:'vlog';this.step=0;if(this.ctx){this.nextNote=this.ctx.currentTime+.08;this.mix();}}
 mix(){if(!this.ctx)return;const now=this.ctx.currentTime;this.rain.gain.setTargetAtTime(this.scene==='rain'?1.8:0,now,.3);this.wind.gain.setTargetAtTime(this.scene==='nature'?.35:this.scene==='sport'?.08:0,now,.4);this.melody.gain.setTargetAtTime(this.scene==='vlog'?1:0,now,.2);}
 note(f,when,duration,volume,destination,type='sine'){
  const c=this.ctx,o=c.createOscillator(),g=c.createGain();o.type=type;o.frequency.setValueAtTime(f,when);o.connect(g);g.connect(destination);
  g.gain.setValueAtTime(0,when);g.gain.linearRampToValueAtTime(volume,when+.015);g.gain.exponentialRampToValueAtTime(.0001,when+duration);o.onended=()=>{o.disconnect();g.disconnect();};o.start(when);o.stop(when+duration+.04);return o;
 }
 schedule(now){
  if(this.nextNote<now-.2)this.nextNote=now;
  while(this.nextNote<now+.12){
   if(this.scene==='vlog'){
    const chords=[[261.63,329.63,392,493.88],[220,261.63,329.63,392],[174.61,220,261.63,329.63],[196,246.94,293.66,392]];
    const chord=chords[Math.floor(this.step/16)%4],pattern=[0,2,1,3,2,1,3,2],beat=this.step%16;
    this.note(chord[pattern[this.step%8]],this.nextNote,.65,.085,this.melody,'triangle');
    if(beat%4===0)this.note(chord[0]/2,this.nextNote,.9,.11,this.melody);
    if(beat===4||beat===12)this.note(1100,this.nextNote,.045,.025,this.melody,'triangle');
    this.nextNote+=60/92/2;
   }else if(this.scene==='nature'){
    const f=1350+(this.step%4)*180,bird=this.note(f,this.nextNote,.24,.045,this.wind);bird.frequency.exponentialRampToValueAtTime(f*1.6,this.nextNote+.1);bird.frequency.exponentialRampToValueAtTime(f*.85,this.nextNote+.22);this.nextNote+=this.step%2?.25:3.4;
   }else this.nextNote=now+.3;
   this.step++;
  }
 }
 update(speed,paused,near,allowBackground=!paused){
  if(!this.ctx)return;const now=this.ctx.currentTime,velocity=Math.abs(speed),sport=this.scene==='sport';this.mix();
  this.background.gain.setTargetAtTime(this.enabled&&allowBackground?this.music:0,now,.2);
  const rpm=45+velocity*(sport?12:7),gear=sport?Math.floor(velocity/4):0,f=rpm-gear*22;
  this.engine.frequency.setTargetAtTime(f,now,.12);this.engineBass.frequency.setTargetAtTime(f/2,now,.12);this.engineHarmonic.frequency.setTargetAtTime(f*2,now,.12);this.engineFilter.frequency.setTargetAtTime(sport?450+velocity*65:260+velocity*20,now,.15);
  const audible=this.enabled&&allowBackground&&(!paused||sport);
  this.engineGain.gain.setTargetAtTime(audible?this.effects*(sport?.19+velocity*.012:.025+velocity*.004):0,now,.15);
  if(this.enabled&&allowBackground)this.schedule(now);else this.nextNote=now;
 }
 tone(f=440,duration=.14){if(this.enabled&&this.ctx)this.note(f,this.ctx.currentTime,duration,this.effects*.2,this.master);}
}
