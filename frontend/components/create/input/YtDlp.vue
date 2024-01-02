<template>
      <div>
            <h2></h2>    
        <UFormGroup label="Any url supported by yt-dlp" required>
          <UInput v-model="state.uri" placeholder="https://www.youtube.com/watch?v=dQw4w9WgXcQ" />
        </UFormGroup>
   
        <UCheckbox v-model="state.loop" name="loop" label="Loop (content replays once finished)" />
  </div>
</template>

<script setup>



import { reactive, watchEffect } from 'vue';

const emit = defineEmits(['update:formData']);

const state = reactive({
  type: 'ytdlpsrc',
  uri: '',
  loop: false
});

// Emit formData updates when the reactive state changes
watchEffect(() => {
  emit('update:formData', state);
});



</script>
