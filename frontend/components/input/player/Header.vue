<template>
  <div class="container">
    Input: {{ uid }}
    <UIcon name="i-heroicons-trash" size="md" inline="inline-flex" color="red" @click="submitRemove"/>
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