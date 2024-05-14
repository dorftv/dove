function __vite__mapDeps(indexes) {
  if (!__vite__mapDeps.viteFileDeps) {
    __vite__mapDeps.viteFileDeps = ["./uNABbe3a.js","./BGsF8phL.js","./BIRhU5EG.js","./BXdE7me6.js","./BPCzIZfy.js","./entry.B2Y61Id4.css","./qsMMcMsd.js","./Icon.8lQfE3Ql.css","./BIqbwXUM.js","./index.CQJKuM59.css","./sKL9cp8e.js"]
  }
  return indexes.map((i) => __vite__mapDeps.viteFileDeps[i])
}
import{a6 as g}from"./BPCzIZfy.js";import{R as p,I as u,B as m,S as C,d as h,n as f}from"./BGsF8phL.js";function w(){return"https://www.gstatic.com/cv/js/sender/v1/cast_sender.js?loadCastFramework=1"}function v(){var a;return!!((a=window.cast)!=null&&a.framework)}function E(){var a,e;return!!((e=(a=window.chrome)==null?void 0:a.cast)!=null&&e.isAvailable)}function l(){return s().getCastState()===cast.framework.CastState.CONNECTED}function s(){return window.cast.framework.CastContext.getInstance()}function d(){return s().getCurrentSession()}function y(){var a;return(a=d())==null?void 0:a.getSessionObj().media[0]}function A(a){var t;return((t=y())==null?void 0:t.media.contentId)===(a==null?void 0:a.src)}function S(){return{language:"en-US",autoJoinPolicy:chrome.cast.AutoJoinPolicy.ORIGIN_SCOPED,receiverApplicationId:chrome.cast.media.DEFAULT_MEDIA_RECEIVER_APP_ID,resumeSavedSession:!0,androidReceiverCompatible:!0}}function _(a){return`Google Cast Error Code: ${a}`}function k(a,e){return p(s(),a,e)}class I{constructor(){this.name="google-cast"}get cast(){return s()}mediaType(){return"video"}canPlay(e){return u&&!m&&C(e)}async prompt(e){var i;let t,o,r;try{t=await this.Pl(e),this.aa||(this.aa=new cast.framework.RemotePlayer,new cast.framework.RemotePlayerController(this.aa)),o=e.player.createEvent("google-cast-prompt-open",{trigger:t}),e.player.dispatchEvent(o),this.pm(e,"connecting",o),await this.Rl(h(e.$props.googleCast)),e.$state.remotePlaybackInfo.set({deviceName:(i=d())==null?void 0:i.getCastDevice().friendlyName}),l()&&this.pm(e,"connected",o)}catch(n){const c=n instanceof Error?n:this.Oo((n+"").toUpperCase(),"Prompt failed.");throw r=e.player.createEvent("google-cast-prompt-error",{detail:c,trigger:o??t,cancelable:!0}),e.player.dispatch(r),this.pm(e,l()?"connected":"disconnected",r),c}finally{e.player.dispatch("google-cast-prompt-close",{trigger:r??o??t})}}async load(e){if(!this.aa)throw Error("[vidstack] google cast player was not initialized");return new(await g(()=>import("./uNABbe3a.js"),__vite__mapDeps([0,1,2,3,4,5,6,7,8,9,10]),import.meta.url)).GoogleCastProvider(this.aa,e)}async Pl(e){if(v())return;const t=e.player.createEvent("google-cast-load-start");e.player.dispatch(t),await f(w()),await customElements.whenDefined("google-cast-launcher");const o=e.player.createEvent("google-cast-loaded",{trigger:t});if(e.player.dispatch(o),!E())throw this.Oo("CAST_NOT_AVAILABLE","Google Cast not available on this platform.");return o}async Rl(e){this.Tl(e);const t=await this.cast.requestSession();if(t)throw this.Oo(t.toUpperCase(),_(t))}Tl(e){var t;(t=this.cast)==null||t.setOptions({...S(),...e})}pm(e,t,o){const r={type:"google-cast",state:t};e.delegate.c("remote-playback-change",r,o)}Oo(e,t){const o=Error(t);return o.code=e,o}}const b=Object.freeze(Object.defineProperty({__proto__:null,GoogleCastLoader:I},Symbol.toStringTag,{value:"Module"}));export{d as a,y as b,_ as c,s as g,A as h,k as l,b as v};