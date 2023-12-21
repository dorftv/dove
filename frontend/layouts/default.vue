<script setup>
const isOpen = ref(false)
const resolutions = "test"
const { data: config, pending, error } = await useFetch('/api/config');

if (!pending.value && !error.value && config.value) {
      // Access the mixer_resolutions object
     // const resolutions = config.value.mixer_resolutions;
      console.log("hit")
      console.log(resolutions)

}

</script>

<template>
    <div>
        <header class="shadow-sm bg-white">
            <nav class="flex justify-between">
                <NuxtLink to="/" class="font-bold">DOVE - Online Video Editor</NuxtLink>
                <div class="flex" >
                  <CreateInputPane class="p-2"/>
                  <CreateMixerPane class="p-2"/>
                  <CreateOutputPane class="p-2"/>
                </div>
                <ul class="flex gap-4">
                    <li><NuxtLink to="/">Home</NuxtLink></li>
                    <li><NuxtLink to="/about">About</NuxtLink></li>
                    <li><NuxtLink to="/help">Help</NuxtLink></li>
                    <li><NuxtLink to="/debug">Debug</NuxtLink></li>
                </ul>
                <TogglePreview />
                <a href="https://github.com/dorftv/brave">
                  <Icon name="uil:github" color="black" size="36px" />
                </a>
            </nav>
        </header>

        <div class="grid grid-cols-12 px-4 py-8">
        <slot />
        </div>
    </div>
</template>

<style scoped>
.router-link-exact {
  color: #12b488;
}
.router-link-exact-active {
  color: #12b488;
}
</style>