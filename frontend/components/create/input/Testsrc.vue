
<template>
    <div>
        <div class="p-4">
          <h2></h2>

          <UForm :validate="validate" :state="state" class="space-y-4" @submit="submitForm">
            <div>
              <URange v-model="pattern" name="range" :min="0" :max="28" :step="1" />
              Pattern: {{ pattern }}
            </div>
              <div>
                <URange v-model="wave" name="range" :min="0" :max="12" :step="1" />
                Wave: {{ wave }}
              </div>
              <UFormGroup label="Frequency">
            <UInput v-model="freq" size="md" placeholder="440.0" />
          </UFormGroup>


          <div>
            <URange v-model="volume" name="range" :min="0" :max="1" :step="0.01" />
            Volume: {{ volume * 100}}
           </div>
          <UInput v-model="name" size="md" placeholder="Give a name. Default Input X" />

          <UButton type="submit" label="Create Input" @click="$emit('close', false)" />
          <UButton color="red" label="Cancel" @click="$emit('close', false)" />

  </UForm>
        </div>
    </div>
  </template>

<script setup>

const volume = ref(0.8)
const pattern = ref(0)
const wave = ref(1)
const freq = ref(440.0)


const formData = ref({
    uid: '',
    uri: '',
})


const submitForm = async () => {
    const { data: responseData } = await useFetch('/api/inputs', {
        method: 'put',
        body: { 
          type: 'testsrc',
          //uid: (Math.random() + 1).toString(36).substring(7),
          width: 1280,
          height: 720,
          pattern: 1,
          wave: 1,
          volume: 0.5,
          freq: 440.0
          //uri: 'http://localhost:88/preview/playlist.m3u8',
          //uid: formData.value.uid,
          //uri: formData.value.email,

        }
    })
    console.log(responseData.value)
}

</script>
