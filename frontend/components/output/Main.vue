
<template>
  <div v-if="!output.type.startsWith('preview')">
    {{ output.name }} {{ output.type }} {{ output.state }}
    <Icon name="uil:trash" color="red" size="24px" @click="submitRemove"/>   

  </div>
</template>

<script setup>
const props = defineProps({
  output: Object,
})

const submitRemove = async () => {
    const { data: responseData } = await useFetch('/api/outputs', {
        method: 'delete',
        body: { 
          uid: props.output.uid,
        }
    })
}

</script>

<style>

</style>