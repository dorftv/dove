import ue from"./BXdE7me6.js";import{R as de,q as W,$ as Y,W as X,X as fe,E as O,ae as pe,N as M,v as H,L as ge,l as x,_ as me,f as Q,ac as Z,o as U,g as ye,c as be,C as he,af as xe,S as F,x as we,k as S,O as ve,j as ke,G as Se,ag as Ae,a2 as Oe,F as _e}from"./BPCzIZfy.js";function P(e){return X()?(fe(e),!0):!1}function A(e){return typeof e=="function"?e():de(e)}const Ce=typeof window<"u"&&typeof document<"u";typeof WorkerGlobalScope<"u"&&globalThis instanceof WorkerGlobalScope;const Ee=Object.prototype.toString,je=e=>Ee.call(e)==="[object Object]",D=()=>{};function G(e,r){function n(...t){return new Promise((a,o)=>{Promise.resolve(e(()=>r.apply(this,t),{fn:r,thisArg:this,args:t})).then(a).catch(o)})}return n}const ee=e=>e();function ze(e,r={}){let n,t,a=D;const o=l=>{clearTimeout(l),a(),a=D};return l=>{const u=A(e),i=A(r.maxWait);return n&&o(n),u<=0||i!==void 0&&i<=0?(t&&(o(t),t=null),Promise.resolve(l())):new Promise((s,d)=>{a=r.rejectOnCancel?d:s,i&&!t&&(t=setTimeout(()=>{n&&o(n),t=null,s(l())},i)),n=setTimeout(()=>{t&&o(t),t=null,s(l())},u)})}}function Te(e=ee){const r=O(!0);function n(){r.value=!1}function t(){r.value=!0}const a=(...o)=>{r.value&&e(...o)};return{isActive:pe(r),pause:n,resume:t,eventFilter:a}}function Fe(e){return e||H()}function Ie(e,r=200,n={}){return G(ze(r,n),e)}function Ne(e,r,n={}){const{eventFilter:t=ee,...a}=n;return M(e,G(t,r),a)}function $e(e,r,n={}){const{eventFilter:t,...a}=n,{eventFilter:o,pause:c,resume:l,isActive:u}=Te(t);return{stop:Ne(e,r,{...a,eventFilter:o}),pause:c,resume:l,isActive:u}}function De(e,r=!0,n){Fe()?W(e,n):r?e():Y(e)}function R(e){var r;const n=A(e);return(r=n==null?void 0:n.$el)!=null?r:n}const z=Ce?window:void 0;function J(...e){let r,n,t,a;if(typeof e[0]=="string"||Array.isArray(e[0])?([n,t,a]=e,r=z):[r,n,t,a]=e,!r)return D;Array.isArray(n)||(n=[n]),Array.isArray(t)||(t=[t]);const o=[],c=()=>{o.forEach(s=>s()),o.length=0},l=(s,d,g,y)=>(s.addEventListener(d,g,y),()=>s.removeEventListener(d,g,y)),u=M(()=>[R(r),A(a)],([s,d])=>{if(c(),!s)return;const g=je(d)?{...d}:d;o.push(...n.flatMap(y=>t.map(b=>l(s,y,b,g))))},{immediate:!0,flush:"post"}),i=()=>{u(),c()};return P(i),i}function Re(){const e=O(!1),r=H();return r&&W(()=>{e.value=!0},r),e}function We(e){const r=Re();return x(()=>(r.value,!!e()))}const E=typeof globalThis<"u"?globalThis:typeof window<"u"?window:typeof global<"u"?global:typeof self<"u"?self:{},j="__vueuse_ssr_handlers__",Me=He();function He(){return j in E||(E[j]=E[j]||{}),E[j]}function Be(e,r){return Me[e]||r}function Le(e){return e==null?"any":e instanceof Set?"set":e instanceof Map?"map":e instanceof Date?"date":typeof e=="boolean"?"boolean":typeof e=="string"?"string":typeof e=="object"?"object":Number.isNaN(e)?"any":"number"}const Ue={boolean:{read:e=>e==="true",write:e=>String(e)},object:{read:e=>JSON.parse(e),write:e=>JSON.stringify(e)},number:{read:e=>Number.parseFloat(e),write:e=>String(e)},any:{read:e=>e,write:e=>String(e)},string:{read:e=>e,write:e=>String(e)},map:{read:e=>new Map(JSON.parse(e)),write:e=>JSON.stringify(Array.from(e.entries()))},set:{read:e=>new Set(JSON.parse(e)),write:e=>JSON.stringify(Array.from(e))},date:{read:e=>new Date(e),write:e=>e.toISOString()}},V="vueuse-storage";function I(e,r,n,t={}){var a;const{flush:o="pre",deep:c=!0,listenToStorageChanges:l=!0,writeDefaults:u=!0,mergeDefaults:i=!1,shallow:s,window:d=z,eventFilter:g,onError:y=f=>{console.error(f)},initOnMounted:b}=t,p=(s?ge:O)(typeof r=="function"?r():r);if(!n)try{n=Be("getDefaultStorage",()=>{var f;return(f=z)==null?void 0:f.localStorage})()}catch(f){y(f)}if(!n)return p;const h=A(r),_=Le(h),v=(a=t.serializer)!=null?a:Ue[_],{pause:ie,resume:B}=$e(p,()=>se(p.value),{flush:o,deep:c,eventFilter:g});d&&l&&De(()=>{J(d,"storage",C),J(d,V,ce),b&&C()}),b||C();function L(f,m){d&&d.dispatchEvent(new CustomEvent(V,{detail:{key:e,oldValue:f,newValue:m,storageArea:n}}))}function se(f){try{const m=n.getItem(e);if(f==null)L(m,null),n.removeItem(e);else{const w=v.write(f);m!==w&&(n.setItem(e,w),L(m,w))}}catch(m){y(m)}}function le(f){const m=f?f.newValue:n.getItem(e);if(m==null)return u&&h!=null&&n.setItem(e,v.write(h)),h;if(!f&&i){const w=v.read(m);return typeof i=="function"?i(w,h):_==="object"&&!Array.isArray(w)?{...h,...w}:w}else return typeof m!="string"?m:v.read(m)}function C(f){if(!(f&&f.storageArea!==n)){if(f&&f.key==null){p.value=h;return}if(!(f&&f.key!==e)){ie();try{(f==null?void 0:f.newValue)!==v.write(p.value)&&(p.value=le(f))}catch(m){y(m)}finally{f?Y(B):B()}}}}function ce(f){C(f.detail)}return p}function st(e,r,n={}){const{window:t=z,...a}=n;let o;const c=We(()=>t&&"ResizeObserver"in t),l=()=>{o&&(o.disconnect(),o=void 0)},u=x(()=>Array.isArray(e)?e.map(d=>R(d)):[R(e)]),i=M(u,d=>{if(l(),c.value&&t){o=new ResizeObserver(r);for(const g of d)g&&o.observe(g,a)}},{immediate:!0,flush:"post"}),s=()=>{l(),i()};return P(s),{isSupported:c,stop:s}}const k=new Map;function lt(e){const r=X();function n(l){var u;const i=k.get(e)||new Set;i.add(l),k.set(e,i);const s=()=>a(l);return(u=r==null?void 0:r.cleanups)==null||u.push(s),s}function t(l){function u(...i){a(u),l(...i)}return n(u)}function a(l){const u=k.get(e);u&&(u.delete(l),u.size||o())}function o(){k.delete(e)}function c(l,u){var i;(i=k.get(e))==null||i.forEach(s=>s(l,u))}return{on:n,once:t,off:a,emit:c,reset:o}}function Je(e,r){const n={...e};for(const t of r)delete n[t];return n}function Ve(e,r,n){typeof r=="string"&&(r=r.split(".").map(a=>{const o=Number(a);return isNaN(o)?a:o}));let t=e;for(const a of r){if(t==null)return n;t=t[a]}return t!==void 0?t:n}const qe=Q({props:{name:{type:String,required:!0},dynamic:{type:Boolean,default:!1}},setup(e){const r=Z();return{dynamic:x(()=>{var t,a;return e.dynamic||((a=(t=r.ui)==null?void 0:t.icons)==null?void 0:a.dynamic)})}}});function Ke(e,r,n,t,a,o){const c=ue;return e.dynamic?(U(),ye(c,{key:0,name:e.name},null,8,["name"])):(U(),be("span",{key:1,class:he(e.name)},null,2))}const ct=me(qe,[["render",Ke]]),ut=(e,r,n,t,a=!1)=>{const o=xe(),c=Z(),l=x(()=>{var g;const i=F(r),s=F(n),d=F(t);return we((i==null?void 0:i.strategy)||((g=c.ui)==null?void 0:g.strategy),d?{wrapper:d}:{},i||{},a?Ve(c.ui,e,{}):{},s||{})}),u=x(()=>Je(o,["class"]));return{ui:l,attrs:u}},T={base:"invisible before:visible before:block before:rotate-45 before:z-[-1] before:w-2 before:h-2",ring:"before:ring-1 before:ring-gray-200 dark:before:ring-gray-800",rounded:"before:rounded-sm",background:"before:bg-gray-200 dark:before:bg-gray-800",shadow:"before:shadow",placement:"group-data-[popper-placement*='right']:-left-1 group-data-[popper-placement*='left']:-right-1 group-data-[popper-placement*='top']:-bottom-1 group-data-[popper-placement*='bottom']:-top-1"};({...T});const te={wrapper:"relative",base:"relative block w-full disabled:cursor-not-allowed disabled:opacity-75 focus:outline-none border-0",form:"form-input",rounded:"rounded-md",placeholder:"placeholder-gray-400 dark:placeholder-gray-500",file:{base:"file:cursor-pointer file:rounded-l-md file:absolute file:left-0 file:inset-y-0 file:font-medium file:m-0 file:border-0 file:ring-1 file:ring-gray-300 dark:file:ring-gray-700 file:text-gray-900 dark:file:text-white file:bg-gray-50 hover:file:bg-gray-100 dark:file:bg-gray-800 dark:hover:file:bg-gray-700/50",padding:{"2xs":"ps-[85px]",xs:"ps-[87px]",sm:"ps-[96px]",md:"ps-[98px]",lg:"ps-[100px]",xl:"ps-[109px]"}},size:{"2xs":"text-xs",xs:"text-xs",sm:"text-sm",md:"text-sm",lg:"text-sm",xl:"text-base"},gap:{"2xs":"gap-x-1",xs:"gap-x-1.5",sm:"gap-x-1.5",md:"gap-x-2",lg:"gap-x-2.5",xl:"gap-x-2.5"},padding:{"2xs":"px-2 py-1",xs:"px-2.5 py-1.5",sm:"px-2.5 py-1.5",md:"px-3 py-2",lg:"px-3.5 py-2.5",xl:"px-3.5 py-2.5"},leading:{padding:{"2xs":"ps-7",xs:"ps-8",sm:"ps-9",md:"ps-10",lg:"ps-11",xl:"ps-12"}},trailing:{padding:{"2xs":"pe-7",xs:"pe-8",sm:"pe-9",md:"pe-10",lg:"pe-11",xl:"pe-12"}},color:{white:{outline:"shadow-sm bg-white dark:bg-gray-900 text-gray-900 dark:text-white ring-1 ring-inset ring-gray-300 dark:ring-gray-700 focus:ring-2 focus:ring-primary-500 dark:focus:ring-primary-400"},gray:{outline:"shadow-sm bg-gray-50 dark:bg-gray-800 text-gray-900 dark:text-white ring-1 ring-inset ring-gray-300 dark:ring-gray-700 focus:ring-2 focus:ring-primary-500 dark:focus:ring-primary-400"}},variant:{outline:"shadow-sm bg-transparent text-gray-900 dark:text-white ring-1 ring-inset ring-{color}-500 dark:ring-{color}-400 focus:ring-2 focus:ring-{color}-500 dark:focus:ring-{color}-400",none:"bg-transparent focus:ring-0 focus:shadow-none"},icon:{base:"flex-shrink-0 text-gray-400 dark:text-gray-500",color:"text-{color}-500 dark:text-{color}-400",loading:"animate-spin",size:{"2xs":"h-4 w-4",xs:"h-4 w-4",sm:"h-5 w-5",md:"h-5 w-5",lg:"h-5 w-5",xl:"h-6 w-6"},leading:{wrapper:"absolute inset-y-0 start-0 flex items-center",pointer:"pointer-events-none",padding:{"2xs":"px-2",xs:"px-2.5",sm:"px-2.5",md:"px-3",lg:"px-3.5",xl:"px-3.5"}},trailing:{wrapper:"absolute inset-y-0 end-0 flex items-center",pointer:"pointer-events-none",padding:{"2xs":"px-2",xs:"px-2.5",sm:"px-2.5",md:"px-3",lg:"px-3.5",xl:"px-3.5"}}},default:{size:"sm",color:"white",variant:"outline",loadingIcon:"i-heroicons-arrow-path-20-solid"}},q={container:"z-20 group",trigger:"flex items-center w-full",width:"w-full",height:"max-h-60",base:"relative focus:outline-none overflow-y-auto scroll-py-1",background:"bg-white dark:bg-gray-800",shadow:"shadow-lg",rounded:"rounded-md",padding:"p-1",ring:"ring-1 ring-gray-200 dark:ring-gray-700",empty:"text-sm text-gray-400 dark:text-gray-500 px-2 py-1.5",option:{base:"cursor-default select-none relative flex items-center justify-between gap-1",rounded:"rounded-md",padding:"px-1.5 py-1.5",size:"text-sm",color:"text-gray-900 dark:text-white",container:"flex items-center gap-1.5 min-w-0",active:"bg-gray-100 dark:bg-gray-900",inactive:"",selected:"pe-7",disabled:"cursor-not-allowed opacity-50",empty:"text-sm text-gray-400 dark:text-gray-500 px-2 py-1.5",icon:{base:"flex-shrink-0 h-5 w-5",active:"text-gray-900 dark:text-white",inactive:"text-gray-400 dark:text-gray-500"},selectedIcon:{wrapper:"absolute inset-y-0 end-0 flex items-center",padding:"pe-2",base:"h-5 w-5 text-gray-900 dark:text-white flex-shrink-0"},avatar:{base:"flex-shrink-0",size:"2xs"},chip:{base:"flex-shrink-0 w-2 h-2 mx-1 rounded-full"}},transition:{leaveActiveClass:"transition ease-in duration-100",leaveFromClass:"opacity-100",leaveToClass:"opacity-0"},popper:{placement:"bottom-end"},default:{selectedIcon:"i-heroicons-check-20-solid",trailingIcon:"i-heroicons-chevron-down-20-solid"},arrow:{...T,ring:"before:ring-1 before:ring-gray-200 dark:before:ring-gray-700",background:"before:bg-white dark:before:bg-gray-700"}};({...te});const dt={...te,form:"form-select",placeholder:"text-gray-400 dark:text-gray-500",default:{size:"sm",color:"white",variant:"outline",loadingIcon:"i-heroicons-arrow-path-20-solid",trailingIcon:"i-heroicons-chevron-down-20-solid"}};({...q,option:{...q.option},arrow:{...T}});const ft={wrapper:"relative inline-flex",container:"z-20 group",width:"max-w-xs",background:"bg-white dark:bg-gray-900",color:"text-gray-900 dark:text-white",shadow:"shadow",rounded:"rounded",ring:"ring-1 ring-gray-200 dark:ring-gray-800",base:"[@media(pointer:coarse)]:hidden h-6 px-2 py-1 text-xs font-normal truncate relative",shortcuts:"hidden md:inline-flex flex-shrink-0 gap-0.5",middot:"mx-1 text-gray-700 dark:text-gray-200",transition:{enterActiveClass:"transition ease-out duration-200",enterFromClass:"opacity-0 translate-y-1",enterToClass:"opacity-100 translate-y-0",leaveActiveClass:"transition ease-in duration-150",leaveFromClass:"opacity-100 translate-y-0",leaveToClass:"opacity-0 translate-y-1"},popper:{strategy:"fixed"},default:{openDelay:0,closeDelay:0},arrow:{...T,base:"[@media(pointer:coarse)]:hidden invisible before:visible before:block before:rotate-45 before:z-[-1] before:w-2 before:h-2"}},pt=(e,r)=>{const n=S("form-events",void 0),t=S("form-group",void 0),a=S("form-inputs",void 0);t&&(e!=null&&e.id&&(t.inputId.value=e==null?void 0:e.id),a&&(a.value[t.name.value]=t.inputId.value));const o=O(!1);function c(s,d){n&&n.emit({type:s,path:d})}function l(){c("blur",t==null?void 0:t.name.value),o.value=!0}function u(){c("change",t==null?void 0:t.name.value)}const i=Ie(()=>{(o.value||t!=null&&t.eagerValidation.value)&&c("input",t==null?void 0:t.name.value)},300);return{inputId:x(()=>(e==null?void 0:e.id)??(t==null?void 0:t.inputId.value)),name:x(()=>(e==null?void 0:e.name)??(t==null?void 0:t.name.value)),size:x(()=>{var d;const s=r.size[t==null?void 0:t.size.value]?t==null?void 0:t.size.value:null;return(e==null?void 0:e.size)??s??((d=r==null?void 0:r.default)==null?void 0:d.size)}),color:x(()=>{var s;return(s=t==null?void 0:t.error)!=null&&s.value?"red":e==null?void 0:e.color}),emitFormBlur:l,emitFormInput:i,emitFormChange:u}},Ye=Symbol.for("nuxt:client-only"),Xe="data-n-ids",Qe="-";function gt(e){var a,o,c,l,u,i;if(typeof e!="string")throw new TypeError("[nuxt] [useId] key must be a string.");e=`n${e.slice(1)}`;const r=ve(),n=H();if(!n)throw new TypeError("[nuxt] `useId` must be called within a component setup function.");r._id||(r._id=0),n._nuxtIdIndex||(n._nuxtIdIndex={}),(a=n._nuxtIdIndex)[e]||(a[e]=0);const t=e+Qe+n._nuxtIdIndex[e]++;if(r.payload.serverRendered&&r.isHydrating&&!S(Ye,!1)){const s=((o=n.vnode.el)==null?void 0:o.nodeType)===8&&((l=(c=n.vnode.el)==null?void 0:c.nextElementSibling)!=null&&l.getAttribute)?(u=n.vnode.el)==null?void 0:u.nextElementSibling:n.vnode.el,d=JSON.parse(((i=s==null?void 0:s.getAttribute)==null?void 0:i.call(s,Xe))||"{}");if(d[t])return d[t]}return e+"_"+r._id++}let re=Symbol("headlessui.useid"),Ze=0;function mt(){return S(re,()=>`${++Ze}`)()}function yt(e){ke(re,e)}function N(e){var r;if(e==null||e.value==null)return null;let n=(r=e.value.$el)!=null?r:e.value;return n instanceof Node?n:null}function ne(e,r,...n){if(e in r){let a=r[e];return typeof a=="function"?a(...n):a}let t=new Error(`Tried to handle "${e}" but there is no handler defined. Only defined handlers are: ${Object.keys(r).map(a=>`"${a}"`).join(", ")}.`);throw Error.captureStackTrace&&Error.captureStackTrace(t,ne),t}function K(e,r){if(e)return e;let n=r??"button";if(typeof n=="string"&&n.toLowerCase()==="button")return"button"}function bt(e,r){let n=O(K(e.value.type,e.value.as));return W(()=>{n.value=K(e.value.type,e.value.as)}),Se(()=>{var t;n.value||N(r)&&N(r)instanceof HTMLButtonElement&&!((t=N(r))!=null&&t.hasAttribute("type"))&&(n.value="button")}),n}var Pe=(e=>(e[e.None=0]="None",e[e.RenderStrategy=1]="RenderStrategy",e[e.Static=2]="Static",e))(Pe||{}),Ge=(e=>(e[e.Unmount=0]="Unmount",e[e.Hidden=1]="Hidden",e))(Ge||{});function et({visible:e=!0,features:r=0,ourProps:n,theirProps:t,...a}){var o;let c=oe(t,n),l=Object.assign(a,{props:c});if(e||r&2&&c.static)return $(l);if(r&1){let u=(o=c.unmount)==null||o?0:1;return ne(u,{0(){return null},1(){return $({...a,props:{...c,hidden:!0,style:{display:"none"}}})}})}return $(l)}function $({props:e,attrs:r,slots:n,slot:t,name:a}){var o,c;let{as:l,...u}=tt(e,["unmount","static"]),i=(o=n.default)==null?void 0:o.call(n,t),s={};if(t){let d=!1,g=[];for(let[y,b]of Object.entries(t))typeof b=="boolean"&&(d=!0),b===!0&&g.push(y);d&&(s["data-headlessui-state"]=g.join(" "))}if(l==="template"){if(i=ae(i??[]),Object.keys(u).length>0||Object.keys(r).length>0){let[d,...g]=i??[];if(!rt(d)||g.length>0)throw new Error(['Passing props on "template"!',"",`The current component <${a} /> is rendering a "template".`,"However we need to passthrough the following props:",Object.keys(u).concat(Object.keys(r)).map(p=>p.trim()).filter((p,h,_)=>_.indexOf(p)===h).sort((p,h)=>p.localeCompare(h)).map(p=>`  - ${p}`).join(`
`),"","You can apply a few solutions:",['Add an `as="..."` prop, to ensure that we render an actual element instead of a "template".',"Render a single element as the child so that we can forward the props onto that element."].map(p=>`  - ${p}`).join(`
`)].join(`
`));let y=oe((c=d.props)!=null?c:{},u,s),b=Ae(d,y,!0);for(let p in y)p.startsWith("on")&&(b.props||(b.props={}),b.props[p]=y[p]);return b}return Array.isArray(i)&&i.length===1?i[0]:i}return Oe(l,Object.assign({},u,s),{default:()=>i})}function ae(e){return e.flatMap(r=>r.type===_e?ae(r.children):[r])}function oe(...e){if(e.length===0)return{};if(e.length===1)return e[0];let r={},n={};for(let t of e)for(let a in t)a.startsWith("on")&&typeof t[a]=="function"?(n[a]!=null||(n[a]=[]),n[a].push(t[a])):r[a]=t[a];if(r.disabled||r["aria-disabled"])return Object.assign(r,Object.fromEntries(Object.keys(n).map(t=>[t,void 0])));for(let t in n)Object.assign(r,{[t](a,...o){let c=n[t];for(let l of c){if(a instanceof Event&&a.defaultPrevented)return;l(a,...o)}}});return r}function ht(e){let r=Object.assign({},e);for(let n in r)r[n]===void 0&&delete r[n];return r}function tt(e,r=[]){let n=Object.assign({},e);for(let t of r)t in n&&delete n[t];return n}function rt(e){return e==null?!1:typeof e.type=="string"||typeof e.type=="object"||typeof e.type=="function"}var nt=(e=>(e[e.None=1]="None",e[e.Focusable=2]="Focusable",e[e.Hidden=4]="Hidden",e))(nt||{});let xt=Q({name:"Hidden",props:{as:{type:[Object,String],default:"div"},features:{type:Number,default:1}},setup(e,{slots:r,attrs:n}){return()=>{var t;let{features:a,...o}=e,c={"aria-hidden":(a&2)===2?!0:(t=o["aria-hidden"])!=null?t:void 0,style:{position:"fixed",top:1,left:1,width:1,height:0,padding:0,margin:-1,overflow:"hidden",clip:"rect(0, 0, 0, 0)",whiteSpace:"nowrap",borderWidth:"0",...(a&4)===4&&(a&2)!==2&&{display:"none"}}};return et({ourProps:c,theirProps:o,slot:{},attrs:n,slots:r,name:"Hidden"})}}});var at=(e=>(e.Space=" ",e.Enter="Enter",e.Escape="Escape",e.Backspace="Backspace",e.Delete="Delete",e.ArrowLeft="ArrowLeft",e.ArrowUp="ArrowUp",e.ArrowRight="ArrowRight",e.ArrowDown="ArrowDown",e.Home="Home",e.End="End",e.PageUp="PageUp",e.PageDown="PageDown",e.Tab="Tab",e))(at||{});function wt(){const e=I("inputPreview",!0),r=I("mixerPreview",!0),n=I("darkMode",!1);return{inputPreview:e,mixerPreview:r,darkMode:n}}export{et as A,ht as E,mt as I,Pe as N,Ge as S,tt as T,ct as _,T as a,R as b,pt as c,gt as d,lt as e,ne as f,Ve as g,xt as h,te as i,nt as j,at as k,bt as l,yt as m,wt as n,N as o,st as p,dt as s,ft as t,ut as u};