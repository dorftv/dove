<template>
  <div class="container">
    Input: {{ uid }}
    <UIcon name="i-heroicons-trash" class="h-5 w-5" color="red" @click="submitRemove"/>
    <UIcon name="i-heroicons-video-camera-slash" class="h-5 w-5" color="red" @click="submitRemove"/>

    
  </div>
</template>

<script setup>
const props = defineProps({
  uid: Object
})

const submitRemove = async () => {
    const { data: responseData } = await useFetch('/api/input/delete', {
        method: 'post',
        body: { 
          uid: props.uid,
        }
    })
}

</script>

<style>

</style>