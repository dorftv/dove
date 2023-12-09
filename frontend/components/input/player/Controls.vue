<template>
<div>
    <UButton icon="i-heroicons-play-circle" color="gray" @click="submitForm"/>
    <UButton icon="i-heroicons-stop-circle" color="gray" @click="submitForm"/>
    <UButton icon="i-heroicons-pause-circle" color="gray" @click="submitForm"/>
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
          //uid: formData.value.uid,
          //uri: formData.value.email,

        }
    })
    console.log(responseData.value)
}

</script>

<style lang="css" scoped>

</style>