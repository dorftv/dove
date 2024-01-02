<template>
          <div>
          <URange v-model="state.volume" name="range" :min="0" :max="1" :step="0.05" />
          Volume: {{  state.volume  * 100 }}          
        </div>
          <UInput v-model="state.name" size="md" placeholder="Give a name. Default Input X" />

</template>

<script setup>
const emit = defineEmits(['update:formData']);

const state = reactive({
  volume: 0.8
});
// Emit formData updates when the reactive state changes
watchEffect(() => {
  emit('update:formData', state);
});

</script>

<style>

</style>