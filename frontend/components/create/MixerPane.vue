

<template>
  <div>
    <UButton class="ma-0 pa-0"
  icon="i-heroicons-pencil-square"
  size="sm"
  color="primary"
  variant="solid"
  label="Add Mixer"
  :trailing="false"
  @click="isOpen = true"
/>
    <UModal v-model="isOpen" :transition="false">
      <UContainer>
      <UForm  class="p-4 space-y-4" @submit="submitCreateMixer">

      <div class="p-4">
        <UInput size="md" />
        <UButton  type="submit" label="Create Mixer" @click="isOpen = false"   />
        <UButton color="red" label="Cancel" @click="isOpen = false" />
      </div>
    </UForm>
    </UContainer>      
    </UModal>
  </div>
</template>

<script setup>
const isOpen = ref(false)
console.log("MIXER")
const submitCreateMixer = async () => {
    const { data: responseData } = await useFetch('/api/mixers', {
        method: 'put',
        body: { 
          type: 'mixer',
        }
    })
    console.log(responseData.value)
}
</script>