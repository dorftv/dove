<script setup>
const isOpen = ref(false)
</script>

<template>
  <div>
    <UButton class="ma-0 pa-0"
  icon="i-heroicons-pencil-square"
  size="sm"
  color="primary"
  variant="solid"
  label="Add Output"
  :trailing="false"
  @click="isOpen = true"
/>
    <UModal v-model="isOpen" :transition="false">
      <div class="p-4">
        <Placeholder class="h-48" />
        <UInput size="md" />
        <UButton label="Create Output" @click="isOpen = false" />
        <UButton color="red" label="Cancel" @click="isOpen = false" />
      </div>
    </UModal>
  </div>
</template>