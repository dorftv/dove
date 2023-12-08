<script setup>
const isOpen = ref(false)

//const setModalTrue= () => this.isOpen = true;        

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
    <UModal v-model="isOpen" :transition="false" >
        <CreateInputUri :isOpen="isOpen" @close="(closing) => isOpen = closing" />

    </UModal>
  </div>
</template>