<template>
  <div class="container">
    Input: {{ uid }}
    <Icon name="uil:trash" color="black" size="24px" @click="submitRemove"/>   
  </div>
</template>

<script setup>
const props = defineProps({
  uid: Object,
  inputEnabled: Boolean
})
// <UButton type="submit" label="Create Input" @click="$emit('close', false)" />


const previewEnabled = useCookie('enablePreview')

function enablePreview() {
  inputEnabled = !prop.inputEnabled
}

const submitRemove = async () => {
    const { data: responseData } = await useFetch('/api/inputs', {
        method: 'delete',
        body: { 
          uid: props.uid,
        }
    })
}

</script>

<style>

</style>