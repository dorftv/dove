import{s as p,t as u,u as o,v as f,w as d,f as g,T as n,l as a,D as m}from"./BGsF8phL.js";import{H as k,a as P}from"./DThv06pj.js";import"./BIRhU5EG.js";import"./BXdE7me6.js";import"./BPCzIZfy.js";import"./qsMMcMsd.js";import"./BIqbwXUM.js";import"./sKL9cp8e.js";class I{constructor(t,e){this.m=t,this.b=e,t.textTracks.onaddtrack=this.Wc.bind(this),d(this.cd.bind(this))}Wc(t){const e=t.track;if(!e||b(this.m,e))return;const i=new g({id:e.id,kind:e.kind,label:e.label,language:e.language,type:"vtt"});i[n.T]={track:e},i[n.M]=2,i[n.te]=!0;let s=0;const h=l=>{if(e.cues)for(let c=s;c<e.cues.length;c++)i.addCue(e.cues[c],l),s++};h(t),e.oncuechange=h,this.b.textTracks.add(i,t),i.setMode(e.mode,t)}cd(){var t;this.m.textTracks.onaddtrack=null;for(const e of this.b.textTracks){const i=(t=e[n.T])==null?void 0:t.track;i!=null&&i.oncuechange&&(i.oncuechange=null)}}}function b(r,t){return Array.from(r.children).find(e=>e.track===t)}class T{constructor(t,e){this.m=t,this.a=e,this.B=(i,s)=>{this.a.delegate.c("picture-in-picture-change",i,s)},a(this.m,"enterpictureinpicture",this.Jg.bind(this)),a(this.m,"leavepictureinpicture",this.Kg.bind(this))}get active(){return document.pictureInPictureElement===this.m}get supported(){return o(this.m)}async enter(){return this.m.requestPictureInPicture()}exit(){return document.exitPictureInPicture()}Jg(t){this.B(!0,t)}Kg(t){this.B(!1,t)}}class x{constructor(t,e){this.m=t,this.a=e,this.I="inline",a(this.m,"webkitpresentationmodechanged",this.Ua.bind(this))}get Se(){return u(this.m)}async kc(t){this.I!==t&&this.m.webkitSetPresentationMode(t)}Ua(t){var i;const e=this.I;this.I=this.m.webkitPresentationMode,(i=this.a.player)==null||i.dispatch(new m("video-presentation-change",{detail:this.I,trigger:t})),["fullscreen","picture-in-picture"].forEach(s=>{(this.I===s||e===s)&&this.a.delegate.c(`${s}-change`,this.I===s,t)})}}class y{constructor(t){this.fa=t}get active(){return this.fa.I==="fullscreen"}get supported(){return this.fa.Se}async enter(){this.fa.kc("fullscreen")}async exit(){this.fa.kc("inline")}}class w{constructor(t){this.fa=t}get active(){return this.fa.I==="picture-in-picture"}get supported(){return this.fa.Se}async enter(){this.fa.kc("picture-in-picture")}async exit(){this.fa.kc("inline")}}class L extends k{constructor(t,e){super(t,e),this.$$PROVIDER_TYPE="VIDEO",p(()=>{if(this.airPlay=new P(t,e),u(t)){const i=new x(t,e);this.fullscreen=new y(i),this.pictureInPicture=new w(i)}else o(t)&&(this.pictureInPicture=new T(t,e))},this.scope)}get type(){return"video"}setup(){super.setup(),f(this.video)&&new I(this.video,this.b),this.b.textRenderers.Fe(this.video),d(()=>{this.b.textRenderers.Fe(null)}),this.type==="video"&&this.b.delegate.c("provider-setup",this)}get video(){return this.a}}export{L as VideoProvider};