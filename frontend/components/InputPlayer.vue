<template>
    <div>
      <VideoPlayer :preview_uri="input.uri" />
      Status: {{  input.status }}
    </div>
</template>

<script setup>
  const { input } = defineProps(['input'])
</script>

<style scoped>

</style>