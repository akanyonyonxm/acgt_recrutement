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
      <v-icon v-if="!description" class="watermark" :style="{ color: active ? '#fff' : color }" size="44">{{ icon }}</v-icon>
    </div>
    <div class="val">{{ value }}<span v-if="unit" class="unit">{{ unit }}</span></div>
    <div v-if="description" class="foot">
      <v-icon size="18" :style="{ color: active ? '#fff' : color }">{{ icon }}</v-icon>
      <span>{{ description }}</span>
    </div>
    <span class="deco"></span>
  </div>
</template>

<style scoped>
/* État de repos : doux. Fond teinté très clair, texte sombre, accent discret. */
.stat {
  position: relative; overflow: hidden;
  display: flex; flex-direction: column;
  min-height: 130px;
  padding: 16px 18px;
  border-radius: 16px;
  color: #1f2933;
  background: color-mix(in srgb, var(--c) 7%, #fff);
  border: 1px solid color-mix(in srgb, var(--c) 22%, #fff);
  transition: transform 0.2s, box-shadow 0.2s, background 0.2s, border-color 0.2s;
}
.top { display: flex; align-items: flex-start; justify-content: space-between; gap: 8px; }
.lbl { font-size: 0.72rem; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase;
  color: color-mix(in srgb, var(--c) 55%, #333); }
.watermark { opacity: 0.35; }
.val { font-size: 2.4rem; font-weight: 800; line-height: 1.1; margin-top: 2px; color: #1f2933; }
.val .unit { font-size: 1rem; font-weight: 600; opacity: 0.7; margin-left: 6px; }
.foot { margin-top: auto; padding-top: 8px; display: flex; align-items: center; gap: 6px;
  font-size: 0.8rem; color: #6b7785; }
/* Cercle décoratif translucide en coin (discret au repos). */
.deco {
  position: absolute; right: -28px; top: -28px; width: 116px; height: 116px;
  background: color-mix(in srgb, var(--c) 12%, transparent); border-radius: 50%;
}
.clickable { cursor: pointer; }
.clickable:hover { transform: translateY(-3px); box-shadow: 0 10px 22px rgba(0, 0, 0, 0.10);
  border-color: color-mix(in srgb, var(--c) 45%, #fff); }

/* État sélectionné : fort. Dégradé plein de la couleur, texte blanc. */
.stat.active {
  color: #fff;
  background: linear-gradient(135deg, var(--c) 0%, color-mix(in srgb, var(--c) 70%, #000) 100%);
  border-color: transparent;
  box-shadow: 0 12px 28px color-mix(in srgb, var(--c) 42%, transparent);
}
.stat.active .lbl { color: rgba(255, 255, 255, 0.92); }
.stat.active .val { color: #fff; }
.stat.active .foot { color: rgba(255, 255, 255, 0.95); }
.stat.active .watermark { opacity: 0.3; }
.stat.active .deco { background: rgba(255, 255, 255, 0.12); }
</style>
