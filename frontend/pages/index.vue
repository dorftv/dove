<template>
  <div class="grid col-span-8">
    <div class="grid grid-cols-3 px-4 py-8">
      <div v-for="mixer in mixers" :key="mixer.uid">
        <MixerPlayerMain :mixer="mixer" :inputs="inputs"/>
      </div>    
    </div>
  </div> 
  <div class="grid col-span-3"> 
    Main Outputs
    <!--  <MainOutputPlayer preview_uri="http://localhost:88/preview/playlist.m3u8" />-->
  </div>
  <div class="grid col-span-1">
    <div v-for="output in outputs" :key="output.uid">
      <OutputMain :output="output"/>
    </div>
  </div>  
  <div v-for="input in inputs" :key="input.uid" class="grid col-span-2 px-4 py-8">
    <InputPlayerMain :input="input" :mixers="mixers"/>
  </div>
</template>

<script setup>
import { useEntities } from '@/composables/entities';

const { inputs, mixers, outputs } = useEntities();
</script>

<style scoped>
</style>