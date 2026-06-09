<script setup>
defineProps({
  icon: { type: String, default: 'mdi-folder' },
  value: { type: [Number, String], default: 0 },
  label: { type: String, default: '' },         // libellé du haut (catégorie)
  description: { type: String, default: '' },    // sous-libellé du bas (facultatif)
  unit: { type: String, default: '' },           // ex. « jours »
  color: { type: String, default: '#1a237e' },
  active: Boolean,
  clickable: Boolean,
})
defineEmits(['click'])
</script>

<template>
  <div class="stat" :class="{ active, clickable }" :style="{ '--c': color }"
       @click="clickable && $emit('click')">
    <div class="top">
      <div class="lbl">{{ label }}</div>
      <v-icon v-if="!description" class="watermark" size="44">{{ icon }}</v-icon>
    </div>
    <div class="val">{{ value }}<span v-if="unit" class="unit">{{ unit }}</span></div>
    <div v-if="description" class="foot">
      <v-icon size="18" color="white">{{ icon }}</v-icon>
      <span>{{ description }}</span>
    </div>
    <span class="deco"></span>
  </div>
</template>

<style scoped>
.stat {
  position: relative; overflow: hidden;
  display: flex; flex-direction: column;
  min-height: 130px;
  padding: 16px 18px;
  border-radius: 16px;
  color: #fff;
  background: linear-gradient(135deg, var(--c) 0%, color-mix(in srgb, var(--c) 66%, #000) 100%);
  box-shadow: 0 8px 20px rgba(0, 0, 0, 0.10);
  transition: transform 0.2s, box-shadow 0.2s;
}
.top { display: flex; align-items: flex-start; justify-content: space-between; gap: 8px; }
.lbl { font-size: 0.72rem; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase; opacity: 0.92; }
.watermark { opacity: 0.28; }
.val { font-size: 2.4rem; font-weight: 800; line-height: 1.1; margin-top: 2px; }
.val .unit { font-size: 1rem; font-weight: 600; opacity: 0.85; margin-left: 6px; }
.foot { margin-top: auto; padding-top: 8px; display: flex; align-items: center; gap: 6px; font-size: 0.8rem; opacity: 0.95; }
/* Cercle décoratif translucide en coin. */
.deco {
  position: absolute; right: -28px; top: -28px; width: 116px; height: 116px;
  background: rgba(255, 255, 255, 0.10); border-radius: 50%;
}
.clickable { cursor: pointer; }
.clickable:hover { transform: translateY(-3px); box-shadow: 0 14px 30px rgba(0, 0, 0, 0.18); }
.active { outline: 3px solid rgba(255, 255, 255, 0.7); outline-offset: -3px; }
</style>
