<template>
      <div>
          <div class="p-4">
            <h2></h2>    
      <UForm  :state="state" @submit="submitUriCreate" class="space-y-4" >
        <UFormGroup label="Uri ( for files, SRT, RTMP, HLS, ...)" required="true">
          <UInput v-model="uri" required="true"/>
        </UFormGroup>
   
        <UCheckbox v-model="loop" name="loop" label="Loop (content replays once finished)" />
        <div>
          <URange v-model="volume" name="range" :min="0" :max="1" :step="0.05" />
          Volume: {{  volume  * 100 }}          
        </div>
          <UInput v-model="name" size="md" placeholder="Give a name. Default Input X" />
        <UButton type="submit" label="Create Input" @click="$emit('close', false)" />
        <UButton color="red" label="Cancel" @click="$emit('close', false)" />  
      </UForm>
  </div>
  </div>
</template>

<script setup>

const formData = ref({
  type: 'urisrc',
  uri: '',
})


const uri = ref('')
const volume = ref(0.8)
const loop = ref(false)


const vol = Number(volume) / 100
console.log(vol)
const submitUriCreate = async () => {
    const { data: responseData } = await useFetch('/api/inputs', {
        method: 'put',
        body: { 
          type: 'urisrc',
          uri: uri,
          loop: loop,
          volume: volume
        

          //uid: (Math.random() + 1).toString(36).substring(7),
          //uri: 'http://localhost:88/preview/playlist.m3u8',
          //uri: formData.value.uri,
          


        }
    })
    console.log(responseData.value)
}

</script>
