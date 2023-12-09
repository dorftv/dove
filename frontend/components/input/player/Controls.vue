<template>
  <div>
    <Icon name="i-ic:baseline-delete-forever" color="black" size="24" @click="submitForm"/>    
  </div>    
</template>

<script setup>
const props = defineProps({
  uid: Object
})

const submitForm = async () => {
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