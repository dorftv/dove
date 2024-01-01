<script setup>
const isOpen = ref(false)

// TODO receive a list of avaliable inputs from api
const items = [{
  key: 'uri',
  label: 'Uri Input',
  description: 'Add uri input.'
}, {
  key: 'testsrc',
  label: 'Test Source',
  description: 'Add Test Source.',
}, {
  key: 'test',
  label: 'Test Theme',
  description: 'Add Test Source.'  
}]

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
  @click="isOpen = true"
/>
    <UModal v-model="isOpen" :transition="false">
  <UTabs :items="items"  orientation="vertical">
    <template #item="{ item }">
        <CreateInputUri v-if="item.key === 'uri'" :isOpen="isOpen" @close="(closing) => isOpen = closing" /> 
          <!--
                  <CreateInputUri :isOpen="isOpen" @close="(closing) => isOpen = closing" /> 
--> 
        <CreateInputTestsrc  v-if="item.key === 'testsrc'" :isOpen="isOpen" @close="(closing) => isOpen = closing" /> 
        <CreateInputTest v-if="item.key === 'test'" :isOpen="isOpen" @close="(closing) => isOpen = closing" />
      <CreateInputCommon />
    </template>
  </UTabs>      



    </UModal>
  </div>
</template>