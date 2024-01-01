<template>
  <div class="">
    {{mixer.uid }}
    <Icon name="uil:trash" color="red" size="24px" @click="submitRemove"/>   
  </div>
</template>

<script setup>
const props = defineProps({
  mixer: Object,
  inputEnabled: Boolean
})
// <UButton type="submit" label="Create Input" @click="$emit('close', false)" />


const previewEnabled = useCookie('enablePreview')

function enablePreview() {
  inputEnabled = !prop.inputEnabled
}

const submitRemove = async () => {
    const { data: responseData } = await useFetch('/api/mixers', {
        method: 'delete',
        body: { 
          uid: props.mixer.uid,
        }
    })
}

</script>

<style>

</style>