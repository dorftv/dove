import{_ as m}from"./DJDY5riH.js";import{a as k,b as v}from"./CukKxM7P.js";import{B as y,o as g,c as u,a as l,m as d,r as b,b as c,ar as p,aD as w,_ as x,w as s,d as r,K as _,aT as P}from"./4QGAZhq4.js";import S from"./C4BUqPOh.js";import{u as V}from"./BkdM6jdI.js";var T=function(t){var e=t.dt;return`
.p-toggleswitch {
    display: inline-block;
    width: `.concat(e("toggleswitch.width"),`;
    height: `).concat(e("toggleswitch.height"),`;
}

.p-toggleswitch-input {
    cursor: pointer;
    appearance: none;
    position: absolute;
    top: 0;
    inset-inline-start: 0;
    width: 100%;
    height: 100%;
    padding: 0;
    margin: 0;
    opacity: 0;
    z-index: 1;
    outline: 0 none;
    border-radius: `).concat(e("toggleswitch.border.radius"),`;
}

.p-toggleswitch-slider {
    cursor: pointer;
    width: 100%;
    height: 100%;
    border-width: `).concat(e("toggleswitch.border.width"),`;
    border-style: solid;
    border-color: `).concat(e("toggleswitch.border.color"),`;
    background: `).concat(e("toggleswitch.background"),`;
    transition: background `).concat(e("toggleswitch.transition.duration"),", color ").concat(e("toggleswitch.transition.duration"),", border-color ").concat(e("toggleswitch.transition.duration"),", outline-color ").concat(e("toggleswitch.transition.duration"),", box-shadow ").concat(e("toggleswitch.transition.duration"),`;
    border-radius: `).concat(e("toggleswitch.border.radius"),`;
    outline-color: transparent;
    box-shadow: `).concat(e("toggleswitch.shadow"),`;
}

.p-toggleswitch-handle {
    position: absolute;
    top: 50%;
    display: flex;
    justify-content: center;
    align-items: center;
    background: `).concat(e("toggleswitch.handle.background"),`;
    color: `).concat(e("toggleswitch.handle.color"),`;
    width: `).concat(e("toggleswitch.handle.size"),`;
    height: `).concat(e("toggleswitch.handle.size"),`;
    inset-inline-start: `).concat(e("toggleswitch.gap"),`;
    margin-block-start: calc(-1 * calc(`).concat(e("toggleswitch.handle.size"),` / 2));
    border-radius: `).concat(e("toggleswitch.handle.border.radius"),`;
    transition: background `).concat(e("toggleswitch.transition.duration"),", color ").concat(e("toggleswitch.transition.duration"),", inset-inline-start ").concat(e("toggleswitch.slide.duration"),", box-shadow ").concat(e("toggleswitch.slide.duration"),`;
}

.p-toggleswitch.p-toggleswitch-checked .p-toggleswitch-slider {
    background: `).concat(e("toggleswitch.checked.background"),`;
    border-color: `).concat(e("toggleswitch.checked.border.color"),`;
}

.p-toggleswitch.p-toggleswitch-checked .p-toggleswitch-handle {
    background: `).concat(e("toggleswitch.handle.checked.background"),`;
    color: `).concat(e("toggleswitch.handle.checked.color"),`;
    inset-inline-start: calc(`).concat(e("toggleswitch.width")," - calc(").concat(e("toggleswitch.handle.size")," + ").concat(e("toggleswitch.gap"),`));
}

.p-toggleswitch:not(.p-disabled):has(.p-toggleswitch-input:hover) .p-toggleswitch-slider {
    background: `).concat(e("toggleswitch.hover.background"),`;
    border-color: `).concat(e("toggleswitch.hover.border.color"),`;
}

.p-toggleswitch:not(.p-disabled):has(.p-toggleswitch-input:hover) .p-toggleswitch-handle {
    background: `).concat(e("toggleswitch.handle.hover.background"),`;
    color: `).concat(e("toggleswitch.handle.hover.color"),`;
}

.p-toggleswitch:not(.p-disabled):has(.p-toggleswitch-input:hover).p-toggleswitch-checked .p-toggleswitch-slider {
    background: `).concat(e("toggleswitch.checked.hover.background"),`;
    border-color: `).concat(e("toggleswitch.checked.hover.border.color"),`;
}

.p-toggleswitch:not(.p-disabled):has(.p-toggleswitch-input:hover).p-toggleswitch-checked .p-toggleswitch-handle {
    background: `).concat(e("toggleswitch.handle.checked.hover.background"),`;
    color: `).concat(e("toggleswitch.handle.checked.hover.color"),`;
}

.p-toggleswitch:not(.p-disabled):has(.p-toggleswitch-input:focus-visible) .p-toggleswitch-slider {
    box-shadow: `).concat(e("toggleswitch.focus.ring.shadow"),`;
    outline: `).concat(e("toggleswitch.focus.ring.width")," ").concat(e("toggleswitch.focus.ring.style")," ").concat(e("toggleswitch.focus.ring.color"),`;
    outline-offset: `).concat(e("toggleswitch.focus.ring.offset"),`;
}

.p-toggleswitch.p-invalid > .p-toggleswitch-slider {
    border-color: `).concat(e("toggleswitch.invalid.border.color"),`;
}

.p-toggleswitch.p-disabled {
    opacity: 1;
}

.p-toggleswitch.p-disabled .p-toggleswitch-slider {
    background: `).concat(e("toggleswitch.disabled.background"),`;
}

.p-toggleswitch.p-disabled .p-toggleswitch-handle {
    background: `).concat(e("toggleswitch.handle.disabled.background"),`;
}
`)},B={root:{position:"relative"}},O={root:function(t){var e=t.instance,i=t.props;return["p-toggleswitch p-component",{"p-toggleswitch-checked":e.checked,"p-disabled":i.disabled,"p-invalid":e.$invalid}]},input:"p-toggleswitch-input",slider:"p-toggleswitch-slider",handle:"p-toggleswitch-handle"},I=y.extend({name:"toggleswitch",theme:T,classes:O,inlineStyles:B}),C={name:"BaseToggleSwitch",extends:k,props:{trueValue:{type:null,default:!0},falseValue:{type:null,default:!1},readonly:{type:Boolean,default:!1},tabindex:{type:Number,default:null},inputId:{type:String,default:null},inputClass:{type:[String,Object],default:null},inputStyle:{type:Object,default:null},ariaLabelledby:{type:String,default:null},ariaLabel:{type:String,default:null}},style:I,provide:function(){return{$pcToggleSwitch:this,$parentInstance:this}}},f={name:"ToggleSwitch",extends:C,inheritAttrs:!1,emits:["change","focus","blur"],methods:{getPTOptions:function(t){var e=t==="root"?this.ptmi:this.ptm;return e(t,{context:{checked:this.checked,disabled:this.disabled}})},onChange:function(t){if(!this.disabled&&!this.readonly){var e=this.checked?this.falseValue:this.trueValue;this.writeValue(e,t),this.$emit("change",t)}},onFocus:function(t){this.$emit("focus",t)},onBlur:function(t){var e,i;this.$emit("blur",t),(e=(i=this.formField).onBlur)===null||e===void 0||e.call(i,t)}},computed:{checked:function(){return this.d_value===this.trueValue}}},F=["data-p-checked","data-p-disabled"],z=["id","checked","tabindex","disabled","readonly","aria-checked","aria-labelledby","aria-label","aria-invalid"];function $(n,t,e,i,a,o){return g(),u("div",d({class:n.cx("root"),style:n.sx("root")},o.getPTOptions("root"),{"data-p-checked":o.checked,"data-p-disabled":n.disabled}),[l("input",d({id:n.inputId,type:"checkbox",role:"switch",class:[n.cx("input"),n.inputClass],style:n.inputStyle,checked:o.checked,tabindex:n.tabindex,disabled:n.disabled,readonly:n.readonly,"aria-checked":o.checked,"aria-labelledby":n.ariaLabelledby,"aria-label":n.ariaLabel,"aria-invalid":n.invalid||void 0,onFocus:t[0]||(t[0]=function(){return o.onFocus&&o.onFocus.apply(o,arguments)}),onBlur:t[1]||(t[1]=function(){return o.onBlur&&o.onBlur.apply(o,arguments)}),onChange:t[2]||(t[2]=function(){return o.onChange&&o.onChange.apply(o,arguments)})},o.getPTOptions("input")),null,16,z),l("div",d({class:n.cx("slider")},o.getPTOptions("slider")),[l("div",d({class:n.cx("handle")},o.getPTOptions("handle")),[b(n.$slots,"handle",{checked:o.checked})],16)],16)],16,F)}f.render=$;const L={class:"flex items-center space-x-4"},N={class:"flex items-center"},j={class:"flex items-center"},A={__name:"TogglePreview",setup(n){const{inputPreview:t,mixerPreview:e}=v();return(i,a)=>{const o=f;return g(),u("div",L,[l("div",N,[a[2]||(a[2]=l("label",{for:"inputPreview",class:"mr-2"},"Input Preview",-1)),c(o,{modelValue:p(t),"onUpdate:modelValue":a[0]||(a[0]=h=>w(t)?t.value=h:null),inputId:"inputPreview"},null,8,["modelValue"])]),l("div",j,[a[3]||(a[3]=l("label",{for:"mixerPreview",class:"mr-2"},"Mixer Preview",-1)),c(o,{modelValue:p(e),"onUpdate:modelValue":a[1]||(a[1]=h=>w(e)?e.value=h:null),inputId:"mixerPreview"},null,8,["modelValue"])])])}}},E={class:"min-h-screen flex flex-col"},D={class:"shadow-sm bg-white"},H={class:"container mx-auto px-2 py-1 flex justify-between items-center text-sm"},U={class:"flex items-center space-x-3"},K={class:"flex items-center space-x-2"},M={href:"https://github.com/dorftv/dove",class:"text-gray-600 hover:text-gray-800"},R={class:"flex-grow"},W={__name:"default",setup(n){return V({titleTemplate:t=>"DOVE - Online Video Editor",link:[{rel:"icon",type:"image/png",href:"/favicon.png"}]}),(t,e)=>{const i=m,a=A,o=S;return g(),u("div",E,[l("header",D,[l("nav",H,[c(i,{to:"/",class:"font-semibold"},{default:s(()=>e[0]||(e[0]=[r("DOVE")])),_:1}),l("ul",U,[l("li",null,[c(i,{to:"/"},{default:s(()=>e[1]||(e[1]=[r("Home")])),_:1})]),l("li",null,[c(i,{to:"/about"},{default:s(()=>e[2]||(e[2]=[r("About")])),_:1})]),l("li",null,[c(i,{to:"/help"},{default:s(()=>e[3]||(e[3]=[r("Help")])),_:1})]),l("li",null,[c(i,{to:"/websockets"},{default:s(()=>e[4]||(e[4]=[r("WS")])),_:1})]),l("li",null,[c(i,{to:"/api/debug",external:"",target:"_blank"},{default:s(()=>e[5]||(e[5]=[r("Pipelines")])),_:1})]),l("li",null,[c(i,{to:"/docs",external:"",target:"_blank"},{default:s(()=>e[6]||(e[6]=[r("API")])),_:1})])]),l("div",K,[c(a),l("a",M,[c(o,{name:"mingcute:git-lab-fill",size:"18px"})])])])]),l("main",R,[(g(),_(P,null,[b(t.$slots,"default",{},void 0,!0)],1024))])])}}},Y=x(W,[["__scopeId","data-v-049d0648"]]);export{Y as default};
