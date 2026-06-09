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
  <div class="stat" :class="{ active, clickable }" :style="{ '--c': color }"
       @click="clickable && $emit('click')">
    <div class="stat-head">
      <div class="ic"><v-icon :color="color" size="24">{{ icon }}</v-icon></div>
      <div class="val">{{ value }}</div>
    </div>
    <div class="lbl">{{ label }}</div>
  </div>
</template>

<style scoped>
.stat {
  position: relative;
  background: #fff;
  border: 1px solid #e6e8ef;
  border-radius: 16px;
  padding: 16px 18px;
  height: 100%;
  overflow: hidden;
  transition: transform 0.2s, box-shadow 0.2s, border-color 0.2s;
}
/* Liseré d'accent en haut de la carte. */
.stat::before {
  content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px;
  background: var(--c); opacity: 0.9;
}
.stat-head { display: flex; align-items: center; gap: 12px; }
.ic {
  width: 44px; height: 44px; border-radius: 12px; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
  background: color-mix(in srgb, var(--c) 13%, #ffffff);
}
.val { font-size: 1.9rem; font-weight: 800; line-height: 1; color: #1f2933; }
.lbl {
  margin-top: 10px; font-size: 0.78rem; font-weight: 700; color: #6b7785;
  text-transform: uppercase; letter-spacing: 0.03em; line-height: 1.25;
}
.clickable { cursor: pointer; }
.clickable:hover {
  transform: translateY(-3px);
  box-shadow: 0 12px 26px rgba(26, 35, 126, 0.12);
  border-color: color-mix(in srgb, var(--c) 45%, #e6e8ef);
}
.active {
  border-color: var(--c);
  box-shadow: 0 8px 22px rgba(26, 35, 126, 0.14);
  background: color-mix(in srgb, var(--c) 5%, #ffffff);
}
.active .lbl { color: var(--c); }
</style>
