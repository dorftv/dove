
<template>
    <div>
        <div class="p-4">
          <h2>Test Source ( Video and Audio )</h2>
          <UForm :validate="validate" :state="state" class="space-y-4" @submit="submitForm">
          <UInput v-model="uri" size="md" />
          <UCheckbox v-model="loop" name="loop" label="Loop (content replays once finished)" />
          <div>
          <URange v-model="volume" name="range" />
            Volume: {{  volume  }}
           </div>
          
          <UButton type="submit" label="Create Input" @click="$emit('close', false)" />
          <UButton color="red" label="Cancel" @click="$emit('close', false)" />
          
    
  </UForm>
        </div>
    </div>
  </template>

<script setup>

const volume = ref(80)



const formData = ref({
    uid: '',
    uri: '',
})


const submitForm = async () => {
    const { data: responseData } = await useFetch('/api/input/add', {
        method: 'post',
        body: { 
          uid: (Math.random() + 1).toString(36).substring(7),
          uri: 'http://localhost:88/preview/playlist.m3u8',
          //uid: formData.value.uid,
          //uri: formData.value.email,

        }
    })
    console.log(responseData.value)
}

</script>
