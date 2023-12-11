
import type OutputPaneVue from '~/components/create/OutputPane.vue';
<template>
  <div>
    {{ output.uid }} {{ output.type }} {{ output.status }}
  </div>
</template>

<script setup>
const props = defineProps({
  output: Object,
})
</script>

<style>

</style>