import{J as c,l as a,e as o,d as n,R as h,b as l}from"./Bz1vVLBW.js";class d{constructor(t){this.Lb=t,this.sc=c(""),this.referrerPolicy=null,t.setAttribute("frameBorder","0"),t.setAttribute("aria-hidden","true"),t.setAttribute("allow","autoplay; fullscreen; encrypted-media; picture-in-picture; accelerometer; gyroscope"),this.referrerPolicy!==null&&t.setAttribute("referrerpolicy",this.referrerPolicy)}get iframe(){return this.Lb}setup(){a(window,"message",this.Xi.bind(this)),a(this.Lb,"load",this.gd.bind(this)),o(this.Mb.bind(this))}Mb(){const t=this.sc();if(!t.length){this.Lb.setAttribute("src","");return}const s=n(()=>this.mg());this.Lb.setAttribute("src",h(t,s))}se(t,s){var i;(i=this.Lb.contentWindow)==null||i.postMessage(JSON.stringify(t),s??"*")}Xi(t){var e;const s=this.Nb();if((t.source===null||t.source===((e=this.Lb)==null?void 0:e.contentWindow))&&(!l(s)||s===t.origin)){try{const r=JSON.parse(t.data);r&&this.te(r,t);return}catch{}t.data&&this.te(t.data,t)}}}export{d as E};