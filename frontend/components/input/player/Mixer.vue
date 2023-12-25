<template>
  <div>
    {{  input.uid }}
    Mixer:
    <Icon name="heroicons:scissors" color="red" size="24px" @click="submitCut"/>   
    <Icon name="zondicons:add-solid" color="red" size="24px" @click="submitOverlay"/>
    <Icon name="lets-icons:remove-fill" color="red" size="24px" @click="submitOverlayRemove"/>


   {{mixer.uid}}
  </div>
</template>
<script setup>
const props = defineProps({
  input: Object,
  mixer: Object
})

const submitCut = async () => {
    const { data: responseData } = await useFetch('/api/cut', {
        method: 'post',
        body: { 
          src: props.input.uid,
          target: props.mixer.uid,
        }
    })
}
const submitOverlay = async () => {
    const { data: responseData } = await useFetch('/api/overlay', {
        method: 'post',
        body: { 
          src: props.input.uid,
          target: props.mixer.uid,
        }
    })
}
const submitOverlayRemove = async () => {
    const { data: responseData } = await useFetch('/api/remove', {
        method: 'post',
        body: { 
          src: props.input.uid,
          target: props.mixer.uid,
        }
    })
}
</script>

<style>

</style>