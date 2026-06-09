<script setup>
defineProps({
  icon: { type: String, default: 'mdi-folder' },
  value: { type: [Number, String], default: 0 },
  label: { type: String, default: '' },
  color: { type: String, default: '#1a237e' },
  active: Boolean,
  clickable: Boolean,
})
defineEmits(['click'])
</script>

<template>
  <v-card flat border class="stat pa-4" :class="{ active, clickable }"
          :style="{ borderColor: active ? color : '' }"
          @click="clickable && $emit('click')">
    <span class="bande" :style="{ background: color }"></span>
    <div class="d-flex align-center">
      <v-avatar :color="color" size="44" rounded="lg" variant="tonal" class="mr-3">
        <v-icon :color="color" size="24">{{ icon }}</v-icon>
      </v-avatar>
      <div>
        <div class="val">{{ value }}</div>
        <div class="lbl">{{ label }}</div>
      </div>
    </div>
  </v-card>
</template>

<style scoped>
.stat { position: relative; overflow: hidden; height: 100%; transition: box-shadow 0.2s, transform 0.2s, border-color 0.2s; }
.stat .val { font-size: 1.7rem; font-weight: 800; line-height: 1; color: #1f2933; }
.stat .lbl { font-size: 0.8rem; color: #767683; margin-top: 4px; }
.stat .bande { position: absolute; left: 0; top: 0; bottom: 0; width: 4px; }
.clickable { cursor: pointer; }
.clickable:hover { box-shadow: 0 8px 22px rgba(26,35,126,0.10); transform: translateY(-2px); }
.active { box-shadow: 0 6px 18px rgba(26,35,126,0.12); }
</style>
