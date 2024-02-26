import{u as p,E as n,t as d,p as k,e as l,d as u,b as m,F as v,L as r,l as y,G as q,T as w,Q as b}from"./index.C6PdSoiH.js";import{R as T}from"./vidstack-BhYx9Fjk.DGR_fNS6.js";import{E,t as f}from"./vidstack-DPZGEOYG.CBmXRhkJ.js";import{resolveVimeoVideoId as $,getVimeoVideoInfo as P}from"./vidstack-BTBUzdbF.Cao5mZMB.js";import"./entry.DUdR0xAD.js";import"./useUserState.BoN8s23Y.js";import"./nuxt-link.CewBgbZR.js";import"./Icon.DnqVPxQI.js";import"./index.CzCfPO9Z.js";const V=["bufferend","bufferstart","durationchange","ended","enterpictureinpicture","error","fullscreenchange","leavepictureinpicture","loaded","playProgress","loadProgress","pause","play","playbackratechange","qualitychange","seeked","seeking","timeupdate","volumechange","waiting"];class Q extends E{constructor(t,e){super(t),this.b=e,this.$$PROVIDER_TYPE="VIMEO",this.scope=p(),this.Fa=0,this.Ga=new n(0,0),this.Hb=new n(0,0),this.E=null,this.G=null,this.rd=null,this.N=d(""),this.oc=d(!1),this.sd=null,this.V=null,this.eh=null,this.Da=new T(this.bd.bind(this)),this.Zk=null,this.cookies=!1,this.title=!0,this.byline=!0,this.portrait=!0,this.color="00ADEF",this.qn=!1}get c(){return this.b.delegate.c}get type(){return"vimeo"}get currentSrc(){return this.V}get videoId(){return this.N()}get hash(){return this.sd}get isPro(){return this.oc()}preconnect(){k(this.eb())}setup(){super.setup(),l(this.kd.bind(this)),l(this.fh.bind(this)),l(this.gh.bind(this)),this.c("provider-setup",this)}destroy(){this.H(),this.q("destroy")}async play(){const{paused:t}=this.b.$state;return this.E||(this.E=f(()=>{if(this.E=null,t())return"Timed out."}),this.q("play")),this.E.promise}async pause(){const{paused:t}=this.b.$state;return this.G||(this.G=f(()=>{if(this.G=null,!t())return"Timed out."}),this.q("pause")),this.G.promise}setMuted(t){this.q("setMuted",t)}setCurrentTime(t){this.q("seekTo",t),this.c("seeking",t)}setVolume(t){this.q("setVolume",t),this.q("setMuted",u(this.b.$state.muted))}setPlaybackRate(t){this.q("setPlaybackRate",t)}async loadSource(t){if(!m(t.src)){this.V=null,this.sd=null,this.N.set("");return}const{videoId:e,hash:s}=$(t.src);this.N.set(e??""),this.sd=s??null,this.V=t}kd(){this.H();const t=this.N();if(!t){this.cb.set("");return}this.cb.set(`${this.eb()}/video/${t}`),this.c("load-start")}fh(){const t=this.N();if(!t)return;const e=v(),s=new AbortController;return this.rd=e,P(t,s).then(i=>{e.resolve(i)}).catch(i=>{e.reject()}),()=>{e.reject(),s.abort()}}gh(){const t=this.oc(),{$state:e,qualities:s}=this.b;if(e.canSetPlaybackRate.set(t),s[r.Mc](!t),t)return y(s,"change",()=>{var h;if(s.auto)return;const i=(h=s.selected)==null?void 0:h.id;i&&this.q("setQuality",i)})}eb(){return"https://player.vimeo.com"}Te(){const{$iosControls:t}=this.b,{keyDisabled:e}=this.b.$props,{controls:s,playsInline:i}=this.b.$state,h=s()||t();return{title:this.title,byline:this.byline,color:this.color,portrait:this.portrait,controls:h,h:this.hash,keyboard:h&&!e(),transparent:!0,playsinline:i(),dnt:!this.cookies}}bd(){this.q("getCurrentTime")}Eb(t,e){if(this.qn&&t===0)return;const{realCurrentTime:s,realDuration:i,paused:h,bufferedEnd:a}=this.b.$state;if(s()===t)return;const o=s(),c={currentTime:t,played:this.cm(t)};this.c("time-update",c,e),Math.abs(o-t)>1.5&&(this.c("seeking",t,e),!h()&&a()<t&&this.c("waiting",void 0,e)),i()-t<.01&&(this.c("end",void 0,e),this.qn=!0,setTimeout(()=>{this.qn=!1},500))}cm(t){return this.Fa>=t?this.Ga:this.Ga=new n(0,this.Fa=t)}bb(t,e){this.c("seeked",t,e)}qd(t){var s;const e=this.N();(s=this.rd)==null||s.promise.then(i=>{if(!i)return;const{title:h,poster:a,duration:o,pro:c}=i;this.oc.set(c),this.c("title-change",h,t),this.c("poster-change",a,t),this.c("duration-change",o,t),this.md(o,t)}).catch(()=>{e===this.N()&&(this.q("getVideoTitle"),this.q("getDuration"))})}md(t,e){const{$iosControls:s}=this.b,{controls:i}=this.b.$state,h=i()||s();this.Hb=new n(0,t);const a={buffered:new n(0,0),seekable:this.Hb,duration:t};this.b.delegate.jc(a,e),h||this.q("_hideOverlay"),this.q("getQualities"),this.q("getChapters")}hh(t,e,s){switch(t){case"getVideoTitle":const i=e;this.c("title-change",i,s);break;case"getDuration":const h=e;this.b.$state.canPlay()?this.c("duration-change",h,s):this.md(h,s);break;case"getCurrentTime":this.Eb(e,s);break;case"getBuffered":q(e)&&e.length&&this.Ye(e[e.length-1][1],s);break;case"setMuted":this.ab(u(this.b.$state.volume),e,s);break;case"getChapters":this.Yk(e);break;case"getQualities":this.pc(e,s);break}}ih(){for(const t of V)this.q("addEventListener",t)}Aa(t){var e;this.Da.ra(),this.c("pause",void 0,t),(e=this.G)==null||e.resolve(),this.G=null}xb(t){var e;this.Da.Bb(),this.c("play",void 0,t),(e=this.E)==null||e.resolve(),this.E=null}jh(t){const{paused:e}=this.b.$state;e()||this.c("playing",void 0,t)}Ye(t,e){const s={buffered:new n(0,t),seekable:this.Hb};this.c("progress",s,e)}kh(t){this.c("waiting",void 0,t)}lh(t){const{paused:e}=this.b.$state;e()||this.c("playing",void 0,t)}dd(t){const{paused:e}=this.b.$state;e()&&this.c("play",void 0,t),this.c("waiting",void 0,t)}ab(t,e,s){const i={volume:t,muted:e};this.c("volume-change",i,s)}Yk(t){if(this._k(),!t.length)return;const e=new w({kind:"chapters",default:!0}),{realDuration:s}=this.b.$state;for(let i=0;i<t.length;i++){const h=t[i],a=t[i+1];e.addCue(new window.VTTCue(h.startTime,(a==null?void 0:a.startTime)??s(),h.title))}this.Zk=e,this.b.textTracks.add(e)}_k(){this.Zk&&(this.b.textTracks.remove(this.Zk),this.Zk=null)}pc(t,e){this.b.qualities[b.Za]=t.some(s=>s.id==="auto")?()=>{this.q("setQuality","auto")}:void 0;for(const s of t){if(s.id==="auto")continue;const i=+s.id.slice(0,-1);isNaN(i)||this.b.qualities[r.oa]({id:s.id,width:i*(16/9),height:i,codec:"avc1,h.264",bitrate:-1},e)}this.fb(t.find(s=>s.active),e)}fb({id:t}={},e){if(!t)return;const s=t==="auto",i=this.b.qualities.toArray().find(h=>h.id===t);s?(this.b.qualities[b.Ya](s,e),this.b.qualities[r.pa](void 0,!0,e)):this.b.qualities[r.pa](i,!0,e)}mh(t,e,s){switch(t){case"ready":this.ih();break;case"loaded":this.qd(s);break;case"play":this.xb(s);break;case"playProgress":this.jh(s);break;case"pause":this.Aa(s);break;case"loadProgress":this.Ye(e.seconds,s);break;case"waiting":this.dd(s);break;case"bufferstart":this.kh(s);break;case"bufferend":this.lh(s);break;case"volumechange":this.ab(e.volume,u(this.b.$state.muted),s);break;case"durationchange":this.Hb=new n(0,e.duration),this.c("duration-change",e.duration,s);break;case"playbackratechange":this.c("rate-change",e.playbackRate,s);break;case"qualitychange":this.fb(e,s);break;case"fullscreenchange":this.c("fullscreen-change",e.fullscreen,s);break;case"enterpictureinpicture":this.c("picture-in-picture-change",!0,s);break;case"leavepictureinpicture":this.c("picture-in-picture-change",!1,s);break;case"ended":this.c("end",void 0,s);break;case"error":this.U(e,s);break;case"seek":case"seeked":this.bb(e.seconds,s);break}}U(t,e){var s;if(t.method==="setPlaybackRate"&&this.oc.set(!1),t.method==="play"){(s=this.E)==null||s.reject(t.message);return}}hd(t,e){t.event?this.mh(t.event,t.data,e):t.method&&this.hh(t.method,t.value,e)}lc(){}q(t,e){return this.gd({method:t,value:e})}H(){this.Da.ra(),this.Fa=0,this.Ga=new n(0,0),this.Hb=new n(0,0),this.E=null,this.G=null,this.rd=null,this.eh=null,this.oc.set(!1),this._k()}}export{Q as VimeoProvider};
