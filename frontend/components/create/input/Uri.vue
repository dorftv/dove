<template>
  <div>
    <UContainer>
      <UForm  :state="state" class="p-4 space-y-4" @submit="submitForm">
        <UFormGroup label="Uri ( for files, SRT, RTMP, HLS, ...)">
          <UInput v-model="uri" />
        </UFormGroup>

        <UCheckbox v-model="loop" name="loop" label="Loop (content replays once finished)" />
        <div>
          <URange v-model="volume" name="range" />
          Volume: {{  volume  }}          
        </div>
        <UButton type="submit" label="Create Input" @click="$emit('close', false)" />
        <UButton color="red" label="Cancel" @click="$emit('close', false)" />  
      </UForm>
    </UContainer>
  </div>
</template>

<script setup>



const uri = ref('')
const volume = ref(80)
const loop = ref(false)

const formData = ref({
    uri: '',
    loop: '',
    volume: '',    
})

const submitForm = async () => {
    const { data: responseData } = await useFetch('/api/inputs', {
        method: 'put',
        body: { 
          type: 'urisrc',
          uri: formData.value.uri,
          //uid: (Math.random() + 1).toString(36).substring(7),
          //uri: 'http://localhost:88/preview/playlist.m3u8',
          //uri: formData.value.uri,
          //loop: formData.value.loop,
          //volume: formData.value.volume,


        }
    })
    console.log(formData.value.uri)
    console.log(responseData.value)
}

</script>
