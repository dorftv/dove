<script setup>
const isOpen = ref(false)
// TODO receive a list of avaliable inputs from api
const items = [{
  key: 'uri',
  label: 'Uri Input',
  description: 'Add uri input.'
}, {
  key: 'ytdlp',
  label: 'YtDlp Input',
  description: 'Add yt_dlp input.'
}, {
  key: 'wpe',
  label: 'Html Source',
  description: 'Add Html Source.',
}, {
  key: 'testsrc',
  label: 'Test Source Input',
  description: 'Add testsrc input.'
}]

const handleClose = (closing) => {
  isOpen.value = closing
}

const formData = reactive({});

function handleUpdateFormData(updatedFormData) {
  Object.assign(formData, updatedFormData);
}


const submitCreate = async () => {
    const { data: responseData } = await $fetch('/api/inputs', {
        method: 'put',
        body: formData
    })
    
    handleClose()
    //test.value.reset()
    console.log(responseData.value)
}

// Define a function to open the modal and reset form data
const openModal = () => {
  isOpen.value = true
  inputForm.clear()
  state.clear()
}

</script>



<template>
  <div>
    <UButton class="ma-0 pa-0"
  icon="i-heroicons-pencil-square"
  size="sm"
  color="primary"
  variant="solid"
  label="Add Input"
  :trailing="false"
  @click="openModal"

/>
    <UModal v-model="isOpen" :transition="false">
  <UTabs :items="items"  orientation="vertical">
    <template #item="{ item }">
      <div class="p-4">

      <UForm refs="inputForm" :validate="validate" :state="state" class="space-y-4" @submit="submitCreate">

        <CreateInputUri v-if="item.key === 'uri'" @update:formData="handleUpdateFormData"/> 
        <CreateInputYtDlp v-if="item.key === 'ytdlp'" @update:formData="handleUpdateFormData"/> 
        <CreateInputWpe v-if="item.key === 'wpe'" @update:formData="handleUpdateFormData"/> 
        <CreateInputTestsrc  v-if="item.key === 'testsrc'"   @update:formData="handleUpdateFormData"/> 

                <!--

        <CreateInputTest v-if="item.key === 'test'"  :formData="formData" @update:formData="updateFormData"/>
          -->
        <CreateInputCommon @update:formData="handleUpdateFormData"/>

      <UButton type="submit" label="Create Input"  />
      <UButton color="red" label="Cancel" @click="handleClose()" />        
    </UForm>
</div>
    </template> 
  </UTabs>      



    </UModal>
  </div>
</template>