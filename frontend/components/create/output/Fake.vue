<template>
      <div>
            <h2></h2>    
        <UFormGroup label="Uri" required="true">
          <UInput v-model="state.uri" required="true"/>
        </UFormGroup>
   
  </div>
</template>

<script setup>



import { reactive, watchEffect } from 'vue';

const emit = defineEmits(['update:formData']);

const state = reactive({
  type: 'fakesink',
  uri: '',
  streamid: ''
});

// Emit formData updates when the reactive state changes
watchEffect(() => {
  emit('update:formData', state);
});



</script>
