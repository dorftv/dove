<template>
      <div>
            <h2></h2>    
        <UFormGroup label="Uri or file://html" required>
          <UInput v-model="state.location"  placeholder="https://dorftv.at"/>
        </UFormGroup>
   
        <UCheckbox v-model="state.background" name="background" label="Draw Background." />
  </div>
</template>

<script setup>



import { reactive, watchEffect } from 'vue';

const emit = defineEmits(['update:formData']);

const state = reactive({
  type: 'wpesrc',
  location: '',
  background: false
});

// Emit formData updates when the reactive state changes
watchEffect(() => {
  emit('update:formData', state);
});



</script>
