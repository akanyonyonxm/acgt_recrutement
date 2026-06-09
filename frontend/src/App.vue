<script setup>
import { navEnCours } from './router'
</script>

<template>
  <v-app>
    <v-progress-linear
      v-if="navEnCours"
      indeterminate
      color="accent"
      height="3"
      class="barre-nav"
    />
    <router-view />
  </v-app>
</template>

<style scoped>
.barre-nav {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 3000;
}
</style>
