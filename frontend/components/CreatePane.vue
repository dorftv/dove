<script setup>
const isOpen = ref(false)
</script>

<template>
  <div>
    <UButton label="Create Input" @click="isOpen = true" />

    <UModal v-model="isOpen" :transition="false">
      <div class="p-4">
        <Placeholder class="h-48" />
        <UInput size="md" />
        <UButton label="Create Input" @click="isOpen = true" />

      </div>
    </UModal>
  </div>
</template>