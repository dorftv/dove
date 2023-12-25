
import type OutputPaneVue from '~/components/create/OutputPane.vue';
<template>
  <div>
    {{ output.uid }} {{ output.type }} {{ output.state }}
  </div>
</template>

<script setup>
const props = defineProps({
  output: Object,
})
</script>

<style>

</style>