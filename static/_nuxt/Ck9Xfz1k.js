import{_ as f}from"./Bwotkfay.js";import{s as m,u as v}from"./BCnDKjR3.js";import{D as k,o as d,c as h,a as l,G as u,b as s,l as p,aC as w,_ as y,w as c,a5 as x,I as _,aQ as V,d as r}from"./DREUvbq8.js";import P from"./DYM4CXhz.js";import{u as S}from"./CDUG0DzP.js";var B=function(t){var e=t.dt;return`
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
    left: 0;
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
    display: inline-block;
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

.p-toggleswitch-slider:before {
    position: absolute;
    content: "";
    top: 50%;
    background: `).concat(e("toggleswitch.handle.background"),`;
    width: `).concat(e("toggleswitch.handle.size"),`;
    height: `).concat(e("toggleswitch.handle.size"),`;
    left: `).concat(e("toggleswitch.gap"),`;
    margin-top: calc(-1 * calc(`).concat(e("toggleswitch.handle.size"),` / 2));
    border-radius: `).concat(e("toggleswitch.handle.border.radius"),`;
    transition: background `).concat(e("toggleswitch.transition.duration"),", left ").concat(e("toggleswitch.slide.duration"),`;
}

.p-toggleswitch.p-toggleswitch-checked .p-toggleswitch-slider {
    background: `).concat(e("toggleswitch.checked.background"),`;
    border-color: `).concat(e("toggleswitch.checked.border.color"),`;
}

.p-toggleswitch.p-toggleswitch-checked .p-toggleswitch-slider:before {
    background: `).concat(e("toggleswitch.handle.checked.background"),`;
    left: calc(`).concat(e("toggleswitch.width")," - calc(").concat(e("toggleswitch.handle.size")," + ").concat(e("toggleswitch.gap"),`));
}

.p-toggleswitch:not(.p-disabled):has(.p-toggleswitch-input:hover) .p-toggleswitch-slider {
    background: `).concat(e("toggleswitch.hover.background"),`;
    border-color: `).concat(e("toggleswitch.hover.border.color"),`;
}

.p-toggleswitch:not(.p-disabled):has(.p-toggleswitch-input:hover) .p-toggleswitch-slider:before {
    background: `).concat(e("toggleswitch.handle.hover.background"),`;
}

.p-toggleswitch:not(.p-disabled):has(.p-toggleswitch-input:hover).p-toggleswitch-checked .p-toggleswitch-slider {
    background: `).concat(e("toggleswitch.checked.hover.background"),`;
    border-color: `).concat(e("toggleswitch.checked.hover.border.color"),`;
}

.p-toggleswitch:not(.p-disabled):has(.p-toggleswitch-input:hover).p-toggleswitch-checked .p-toggleswitch-slider:before {
    background: `).concat(e("toggleswitch.handle.checked.hover.background"),`;
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

.p-toggleswitch.p-disabled .p-toggleswitch-slider:before {
    background: `).concat(e("toggleswitch.handle.disabled.background"),`;
}
`)},T={root:{position:"relative"}},I={root:function(t){var e=t.instance,i=t.props;return["p-toggleswitch p-component",{"p-toggleswitch-checked":e.checked,"p-disabled":i.disabled,"p-invalid":i.invalid}]},input:"p-toggleswitch-input",slider:"p-toggleswitch-slider"},O=k.extend({name:"toggleswitch",theme:B,classes:I,inlineStyles:T}),C={name:"BaseToggleSwitch",extends:m,props:{modelValue:{type:null,default:!1},trueValue:{type:null,default:!0},falseValue:{type:null,default:!1},invalid:{type:Boolean,default:!1},disabled:{type:Boolean,default:!1},readonly:{type:Boolean,default:!1},tabindex:{type:Number,default:null},inputId:{type:String,default:null},inputClass:{type:[String,Object],default:null},inputStyle:{type:Object,default:null},ariaLabelledby:{type:String,default:null},ariaLabel:{type:String,default:null}},style:O,provide:function(){return{$pcToggleSwitch:this,$parentInstance:this}}},b={name:"ToggleSwitch",extends:C,inheritAttrs:!1,emits:["update:modelValue","change","focus","blur"],methods:{getPTOptions:function(t){var e=t==="root"?this.ptmi:this.ptm;return e(t,{context:{checked:this.checked,disabled:this.disabled}})},onChange:function(t){if(!this.disabled&&!this.readonly){var e=this.checked?this.falseValue:this.trueValue;this.$emit("update:modelValue",e),this.$emit("change",t)}},onFocus:function(t){this.$emit("focus",t)},onBlur:function(t){this.$emit("blur",t)}},computed:{checked:function(){return this.modelValue===this.trueValue}}},z=["data-p-checked","data-p-disabled"],F=["id","checked","tabindex","disabled","readonly","aria-checked","aria-labelledby","aria-label","aria-invalid"];function L(n,t,e,i,a,o){return d(),h("div",u({class:n.cx("root"),style:n.sx("root")},o.getPTOptions("root"),{"data-p-checked":o.checked,"data-p-disabled":n.disabled}),[l("input",u({id:n.inputId,type:"checkbox",role:"switch",class:[n.cx("input"),n.inputClass],style:n.inputStyle,checked:o.checked,tabindex:n.tabindex,disabled:n.disabled,readonly:n.readonly,"aria-checked":o.checked,"aria-labelledby":n.ariaLabelledby,"aria-label":n.ariaLabel,"aria-invalid":n.invalid||void 0,onFocus:t[0]||(t[0]=function(){return o.onFocus&&o.onFocus.apply(o,arguments)}),onBlur:t[1]||(t[1]=function(){return o.onBlur&&o.onBlur.apply(o,arguments)}),onChange:t[2]||(t[2]=function(){return o.onChange&&o.onChange.apply(o,arguments)})},o.getPTOptions("input")),null,16,F),l("span",u({class:n.cx("slider")},o.getPTOptions("slider")),null,16)],16,z)}b.render=L;const N={class:"flex items-center space-x-4"},A={class:"flex items-center"},E={class:"flex items-center"},$={__name:"TogglePreview",setup(n){const{inputPreview:t,mixerPreview:e}=v();return(i,a)=>{const o=b;return d(),h("div",N,[l("div",A,[a[2]||(a[2]=l("label",{for:"inputPreview",class:"mr-2"},"Input Preview",-1)),s(o,{modelValue:p(t),"onUpdate:modelValue":a[0]||(a[0]=g=>w(t)?t.value=g:null),inputId:"inputPreview"},null,8,["modelValue"])]),l("div",E,[a[3]||(a[3]=l("label",{for:"mixerPreview",class:"mr-2"},"Mixer Preview",-1)),s(o,{modelValue:p(e),"onUpdate:modelValue":a[1]||(a[1]=g=>w(e)?e.value=g:null),inputId:"mixerPreview"},null,8,["modelValue"])])])}}},j={class:"min-h-screen flex flex-col"},D={class:"shadow-sm bg-white"},H={class:"container mx-auto px-2 py-1 flex justify-between items-center text-sm"},U={class:"flex items-center space-x-3"},G={class:"flex items-center space-x-2"},K={href:"https://github.com/dorftv/dove",class:"text-gray-600 hover:text-gray-800"},M={class:"flex-grow"},Q={__name:"default",setup(n){return S({titleTemplate:t=>"DOVE - Online Video Editor",link:[{rel:"icon",type:"image/png",href:"/favicon.png"}]}),(t,e)=>{const i=f,a=$,o=P;return d(),h("div",j,[l("header",D,[l("nav",H,[s(i,{to:"/",class:"font-semibold"},{default:c(()=>e[0]||(e[0]=[r("DOVE")])),_:1}),l("ul",U,[l("li",null,[s(i,{to:"/"},{default:c(()=>e[1]||(e[1]=[r("Home")])),_:1})]),l("li",null,[s(i,{to:"/about"},{default:c(()=>e[2]||(e[2]=[r("About")])),_:1})]),l("li",null,[s(i,{to:"/help"},{default:c(()=>e[3]||(e[3]=[r("Help")])),_:1})]),l("li",null,[s(i,{to:"/websockets"},{default:c(()=>e[4]||(e[4]=[r("WS")])),_:1})]),l("li",null,[s(i,{to:"/api/debug",external:"",target:"_blank"},{default:c(()=>e[5]||(e[5]=[r("Pipelines")])),_:1})]),l("li",null,[s(i,{to:"/docs",external:"",target:"_blank"},{default:c(()=>e[6]||(e[6]=[r("API")])),_:1})])]),l("div",G,[s(a),l("a",K,[s(o,{name:"mingcute:git-lab-fill",size:"18px"})])])])]),l("main",M,[(d(),x(V,null,[_(t.$slots,"default",{},void 0,!0)],1024))])])}}},Y=y(Q,[["__scopeId","data-v-049d0648"]]);export{Y as default};
