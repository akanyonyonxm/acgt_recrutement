<script setup>
import { couleurStatut } from '../statuts'
defineProps({ statut: String, libelle: String })
</script>

<template>
  <v-chip :color="couleurStatut(statut)" variant="flat" size="small" label>
    {{ libelle || statut }}
  </v-chip>
</template>
