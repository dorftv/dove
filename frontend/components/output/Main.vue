
<template>
  <div v-if="output.type.startsWith('preview')">
    {{ output.name }} {{ output.type }} {{ output.state }}
  </div>
</template>

<script setup>
const props = defineProps({
  output: Object,
})
</script>

<style>

</style>