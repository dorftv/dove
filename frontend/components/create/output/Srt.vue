<template>
      <div>
            <h2></h2>    
        <UFormGroup label="Uri" required>
          <UInput v-model="state.uri" placeholder="Server Uri, or complete connection string."/>
        </UFormGroup>
   
        <UInput v-model="state.streamid" name="streamid" label="StreamId" placeholder="StreamID"/>
  </div>
</template>

<script setup>



import { reactive, watchEffect } from 'vue';

const emit = defineEmits(['update:formData']);

const state = reactive({
  type: 'srtsink',
  uri: '',
  streamid: ''
});

// Emit formData updates when the reactive state changes
watchEffect(() => {
  emit('update:formData', state);
});



</script>
