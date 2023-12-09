<script setup>
const isOpen = ref(false)
</script>

<template>
    <div>
        <header class="shadow-sm bg-white">
            <nav class="container mx-auto flex justify-between">
                <NuxtLink to="/" class="font-bold">DOVE - Online Video Editor</NuxtLink>
                <div class="flex" >
                  <CreateInputPane />
                  <CreateMixerPane />
                  <CreateOutputPane />
                </div>
                <ul class="flex gap-4">
                    <li><NuxtLink to="/">Home</NuxtLink></li>
                    <li><NuxtLink to="/about">About</NuxtLink></li>
                    <li><NuxtLink to="/help">Help</NuxtLink></li>
                </ul>
                <TogglePreview />
                <a href="https://github.com/dorftv/brave">
                  <Icon name="uil:github" color="black" size="36px" />
                </a>
            </nav>
        </header>

        <div class="container mx-auto">
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