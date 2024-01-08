import{c as T,T as o,s as y,p as G,e as m,a as u,i as P,F as j,m as w,L as b,l as N,G as R,Q as q}from"./index.1d319340.js";import{R as C}from"./vidstack-4jGm7oeB.94c92180.js";import{E as F,t as E}from"./vidstack-cgu9mlil.fc822161.js";import"./entry.79e43c98.js";import"./Button.8141d971.js";import"./Icon.525f57e6.js";import"./index.b8fe2cb5.js";import"./nuxt-link.3b1c38a7.js";const H=["bufferend","bufferstart","durationchange","ended","enterpictureinpicture","error","fullscreenchange","leavepictureinpicture","loaded","playProgress","loadProgress","pause","play","playbackratechange","qualitychange","seeked","seeking","timeupdate","volumechange","waiting"],r=class r extends F{constructor(){super(...arguments),this.$$PROVIDER_TYPE="VIMEO",this.scope=T(),this.Fa=0,this.Ga=new o(0,0),this.Hb=new o(0,0),this.E=null,this.G=null,this.rd=null,this.N=y(""),this.oc=y(!1),this.sd=null,this.V=null,this.eh=null,this.Da=new C(this.bd.bind(this)),this.cookies=!1,this.title=!0,this.byline=!0,this.portrait=!0,this.color="00ADEF"}get c(){return this.b.delegate.c}get type(){return"vimeo"}get currentSrc(){return this.V}get videoId(){return this.N()}get hash(){return this.sd}get isPro(){return this.oc()}preconnect(){const t=[this.eb(),"https://i.vimeocdn.com","https://f.vimeocdn.com","https://fresnel.vimeocdn.com"];for(const e of t)G(e,"preconnect")}setup(t){this.b=t,super.setup(t),m(this.kd.bind(this)),m(this.fh.bind(this)),m(this.gh.bind(this)),this.c("provider-setup",this)}destroy(){this.H(),this.q("destroy")}async play(){const{paused:t}=this.b.$state;if(u(t))return this.E||(this.E=E(()=>{if(this.E=null,t())return"Timed out."}),this.q("play")),this.E.promise}async pause(){const{paused:t}=this.b.$state;if(!u(t))return this.G||(this.G=E(()=>{if(this.G=null,!t())return"Timed out."}),this.q("pause")),this.G.promise}setMuted(t){this.q("setMuted",t)}setCurrentTime(t){this.q("seekTo",t)}setVolume(t){this.q("setVolume",t),this.q("setMuted",u(this.b.$state.muted))}setPlaybackRate(t){this.q("setPlaybackRate",t)}async loadSource(t){if(!P(t.src)){this.V=null,this.sd=null,this.N.set("");return}const e=t.src.match(r.jd),s=e==null?void 0:e[1],i=e==null?void 0:e[2];this.N.set(s??""),this.sd=i??null,this.V=t}kd(){this.H();const t=this.N();if(!t){this.cb.set("");return}this.cb.set(`${this.eb()}/video/${t}`)}fh(){const t=this.cb(),e=this.N(),s=r.dh,i=s.get(e);if(!e)return;const n=j();if(this.rd=n,i){n.resolve(i);return}const c=`https://vimeo.com/api/oembed.json?url=${t}`,a=new AbortController;return window.fetch(c,{mode:"cors",signal:a.signal}).then(h=>h.json()).then(h=>{var v,k;const p=/vimeocdn.com\/video\/(.*)?_/,l=(k=(v=h==null?void 0:h.thumbnail_url)==null?void 0:v.match(p))==null?void 0:k[1],f=l?`https://i.vimeocdn.com/video/${l}_1920x1080.webp`:"",d={title:(h==null?void 0:h.title)??"",duration:(h==null?void 0:h.duration)??0,poster:f,pro:h.account_type!=="basic"};s.set(e,d),n.resolve(d)}).catch(h=>{n.reject(),this.c("error",{message:`Failed to fetch vimeo video info from \`${c}\`.`,code:1,error:w(h)})}),()=>{n.reject(),a.abort()}}gh(){const t=this.oc(),{$state:e,qualities:s}=this.b;if(e.canSetPlaybackRate.set(t),s[b.Mc](!t),t)return N(s,"change",()=>{var n;if(s.auto)return;const i=(n=s.selected)==null?void 0:n.id;i&&this.q("setQuality",i)})}eb(){return"https://player.vimeo.com"}Te(){const{$iosControls:t}=this.b,{keyDisabled:e}=this.b.$props,{controls:s,playsinline:i}=this.b.$state,n=s()||t();return{title:this.title,byline:this.byline,color:this.color,portrait:this.portrait,controls:n,h:this.hash,keyboard:n&&!e(),transparent:!0,playsinline:i(),dnt:!this.cookies}}bd(){this.q("getCurrentTime")}Eb(t,e){const{currentTime:s,paused:i,seeking:n,bufferedEnd:c}=this.b.$state;if(n()&&i()&&(this.q("getBuffered"),c()>t&&this.c("seeked",t,e)),s()===t)return;const a=s(),h={currentTime:t,played:this.Fa>=t?this.Ga:this.Ga=new o(0,this.Fa=t)};this.c("time-update",h,e),Math.abs(a-t)>1.5&&(this.c("seeking",t,e),!i()&&c()<t&&this.c("waiting",void 0,e))}bb(t,e){this.c("seeked",t,e)}md(t){var s;const e=this.N();(s=this.rd)==null||s.promise.then(i=>{if(!i)return;const{title:n,poster:c,duration:a,pro:h}=i,{$iosControls:p}=this.b,{controls:l}=this.b.$state,f=l()||p();this.Da.Bb(),this.oc.set(h),this.Hb=new o(0,a),this.c("poster-change",c,t),this.c("title-change",n,t),this.c("duration-change",a,t);const d={buffered:new o(0,0),seekable:this.Hb,duration:a};this.b.delegate.jc(d,t),f||this.q("_hideOverlay"),this.q("getQualities")}).catch(i=>{e===this.N()&&this.c("error",{message:"Failed to fetch oembed data",code:2,error:w(i)})})}hh(t,e,s){switch(t){case"getCurrentTime":this.Eb(e,s);break;case"getBuffered":R(e)&&e.length&&this.Ye(e[e.length-1][1],s);break;case"setMuted":this.ab(u(this.b.$state.volume),e,s);break;case"getChapters":break;case"getQualities":this.pc(e,s);break}}ih(){for(const t of H)this.q("addEventListener",t)}Aa(t){var e;this.c("pause",void 0,t),(e=this.G)==null||e.resolve(),this.G=null}xb(t){var e;this.c("play",void 0,t),(e=this.E)==null||e.resolve(),this.E=null}jh(t){const{paused:e}=this.b.$state;e()||this.c("playing",void 0,t)}Ye(t,e){const s={buffered:new o(0,t),seekable:this.Hb};this.c("progress",s,e)}kh(t){this.c("waiting",void 0,t)}lh(t){const{paused:e}=this.b.$state;e()||this.c("playing",void 0,t)}dd(t){const{paused:e}=this.b.$state;e()&&this.c("play",void 0,t),this.c("waiting",void 0,t)}ab(t,e,s){const i={volume:t,muted:e};this.c("volume-change",i,s)}pc(t,e){this.b.qualities[q.Za]=t.some(s=>s.id==="auto")?()=>{this.q("setQuality","auto")}:void 0;for(const s of t){if(s.id==="auto")continue;const i=+s.id.slice(0,-1);isNaN(i)||this.b.qualities[b.oa]({id:s.id,width:i*(16/9),height:i,codec:"avc1,h.264",bitrate:-1},e)}this.fb(t.find(s=>s.active),e)}fb({id:t}={},e){if(!t)return;const s=t==="auto",i=this.b.qualities.toArray().find(n=>n.id===t);s?(this.b.qualities[q.Ya](s,e),this.b.qualities[b.pa](void 0,!0,e)):this.b.qualities[b.pa](i,!0,e)}mh(t,e,s){switch(t){case"ready":this.ih();break;case"loaded":this.md(s);break;case"play":this.xb(s);break;case"playProgress":this.jh(s);break;case"pause":this.Aa(s);break;case"loadProgress":this.Ye(e.seconds,s);break;case"waiting":this.dd(s);break;case"bufferstart":this.kh(s);break;case"bufferend":this.lh(s);break;case"volumechange":this.ab(e.volume,u(this.b.$state.muted),s);break;case"durationchange":this.Hb=new o(0,e.duration),this.c("duration-change",e.duration,s);break;case"playbackratechange":this.c("rate-change",e.playbackRate,s);break;case"qualitychange":this.fb(e,s);break;case"fullscreenchange":this.c("fullscreen-change",e.fullscreen,s);break;case"enterpictureinpicture":this.c("picture-in-picture-change",!0,s);break;case"leavepictureinpicture":this.c("picture-in-picture-change",!1,s);break;case"ended":this.c("end",void 0,s);break;case"error":this.U(e,s);break;case"seeked":this.bb(e.seconds,s);break}}U(t,e){var s;if(t.method==="play"){(s=this.E)==null||s.reject(t.message);return}}hd(t,e){t.event?this.mh(t.event,t.data,e):t.method&&this.hh(t.method,t.value,e)}lc(){}q(t,e){return this.gd({method:t,value:e})}H(){this.Da.ra(),this.Fa=0,this.Ga=new o(0,0),this.Hb=new o(0,0),this.E=null,this.G=null,this.rd=null,this.eh=null,this.oc.set(!1)}};r.jd=/(?:https:\/\/)?(?:player\.)?vimeo(?:\.com)?\/(?:video\/)?(\d+)(?:\?hash=(.*))?/,r.dh=new Map;let $=r;export{$ as VimeoProvider};
