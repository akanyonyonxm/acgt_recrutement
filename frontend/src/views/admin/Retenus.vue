<script setup>
import { ref, onMounted, computed, watch } from 'vue'
import api from '../../api'
import StatCard from '../../components/StatCard.vue'
import { useAuthStore } from '../../stores/auth'
import logoAcgt from '../../assets/acgt_logo.png'

const auth = useAuthStore()

const appels = ref([])
const appelId = ref(null)
const onglet = ref('provisoire')   // 'provisoire' | 'definitive'
const retenus = ref([])
const total = ref(0)            // vrai nombre de retenus (toutes pages)
const chargement = ref(false)
const q = ref('')
const tri = ref([])
const page = ref(1)
const parPage = ref(25)
const snack = ref({ show: false, color: 'success', text: '' })

const appelCourant = computed(() => appels.value.find((a) => a.id === appelId.value))
const publiee = computed(() => !!appelCourant.value?.liste_retenus_publiee)
const notifier = (text, color = 'success') => (snack.value = { show: true, color, text })

const ENTETES = [
  { title: '#', key: 'rang', sortable: false, width: 64 },
  { title: 'Nom', key: 'nom' },
  { title: 'Postnom', key: 'postnom' },
  { title: 'Prénom', key: 'prenom' },
  { title: 'Poste', key: 'poste_libelle' },
]
// Clé de colonne triée -> champ API (allowlist backend).
const TRI = { nom: 'nom', postnom: 'postnom', prenom: 'prenom', poste_libelle: 'poste__libelle' }

// Clé réactive : recharge la 1ʳᵉ page quand l'appel ou la recherche change.
const cle = computed(() => `${appelId.value || ''}|${q.value}`)

async function rechargerAppels() {
  const { data } = await api.get('/appels/')
  appels.value = data.results
}

async function charger({ page: p = 1, itemsPerPage = 25, sortBy } = {}) {
  if (!appelId.value) { retenus.value = []; total.value = 0; return }
  if (sortBy !== undefined) tri.value = sortBy
  page.value = p
  parPage.value = itemsPerPage > 0 ? itemsPerPage : 25
  chargement.value = true
  try {
    const params = { statut: 'retenu', appel: appelId.value, page: p, page_size: parPage.value }
    if (q.value) params.q = q.value
    const s = tri.value && tri.value[0]
    if (s && TRI[s.key]) params.ordering = (s.order === 'desc' ? '-' : '') + TRI[s.key]
    const { data } = await api.get('/dossiers/', { params })
    retenus.value = data.results
    total.value = data.count
  } finally {
    chargement.value = false
  }
}

let minuteur
function rechercher() { clearTimeout(minuteur); minuteur = setTimeout(() => { q.value = q.value.trim() }, 300) }

async function publier() {
  try {
    const { data } = await api.post(`/appels/${appelId.value}/publier-retenus/`)
    notifier(`Liste publiée — ${data.retenus} retenu(s) désormais visibles publiquement.`)
    await rechargerAppels()
  } catch (e) { notifier(e.response?.data?.detail || 'Publication impossible.', 'error') }
}
async function depublier() {
  try {
    await api.post(`/appels/${appelId.value}/depublier-retenus/`)
    notifier("Liste retirée de l'affichage public.")
    await rechargerAppels()
  } catch (e) { notifier(e.response?.data?.detail || 'Action impossible.', 'error') }
}

// --- Liste DÉFINITIVE (retenus publiés + recours validés, code stable) ---
const definitif = ref({ publiee: false, total: 0, nb_recours: 0, nb_codes: 0, results: [] })
const qDef = ref('')
const chargementDef = ref(false)
const defPubliee = computed(() => !!appelCourant.value?.liste_definitive_publiee)
const ENTETES_DEF = computed(() => {
  const base = [
    { title: 'Code', key: 'code', width: 90 },
    { title: 'Nom', key: 'nom' },
    { title: 'Postnom', key: 'postnom' },
    { title: 'Prénom', key: 'prenom' },
    { title: 'Domaine', key: 'poste_libelle' },
    { title: 'Ville du test', key: 'ville_examen' },
    { title: 'Salle', key: 'salle' },
    { title: 'Origine', key: 'origine', sortable: false },
  ]
  if (auth.estAdmin) base.push({ title: '', key: 'actions', sortable: false, width: 96, align: 'end' })
  return base
})
// Filtre par ville du test (côté client, sur les libellés renvoyés).
const villeFiltre = ref('')
const VILLES_FILTRE = ['Kinshasa', 'Lubumbashi', 'Mbuji-Mayi']
const definitifAffiche = computed(() => {
  const r = definitif.value.results || []
  return villeFiltre.value ? r.filter((x) => x.ville_examen === villeFiltre.value) : r
})

// Affectation automatique des salles (par ville)
const dialogSalles = ref(false)
const salleForm = ref({ ville: 'kinshasa', nombre_salles: 10, par_salle: 50 })
const enSalles = ref(false)
const VILLES_VAL = [
  { value: 'kinshasa', title: 'Kinshasa' },
  { value: 'lubumbashi', title: 'Lubumbashi' },
  { value: 'mbuji_mayi', title: 'Mbuji-Mayi' },
]
const LBL_VILLE = { kinshasa: 'Kinshasa', lubumbashi: 'Lubumbashi', mbuji_mayi: 'Mbuji-Mayi' }
// Nombre de candidats de la ville choisie (depuis la liste définitive chargée).
const nbVilleChoisie = computed(() =>
  (definitif.value.results || []).filter((x) => x.ville_examen === LBL_VILLE[salleForm.value.ville]).length)
// Export des feuilles de salle en PDF (1 page par salle, en-tête ACGT).
const affNom = (v) => (v || '').normalize('NFKC')
const enPdf = ref(false)
async function exporterSallesPdf() {
  const rows = (definitifAffiche.value || []).filter((r) => r.salle)
  if (!rows.length) { notifier("Aucune salle affectée — utilisez d'abord « Affecter les salles ».", 'error'); return }
  const groupes = {}
  for (const r of rows) {
    const k = `${r.ville_examen}||${r.salle}`
    if (!groupes[k]) groupes[k] = { ville: r.ville_examen, salle: r.salle, items: [] }
    groupes[k].items.push(r)
  }
  const liste = Object.values(groupes)
    .sort((a, b) => a.ville.localeCompare(b.ville) || a.salle.localeCompare(b.salle, 'fr', { numeric: true }))
  liste.forEach((g) => g.items.sort((x, y) => x.code.localeCompare(y.code)))

  enPdf.value = true
  try {
    const { jsPDF } = await import('jspdf')
    const autoTable = (await import('jspdf-autotable')).default
    const logo = await new Promise((res) => {
      const i = new Image(); i.onload = () => res(i); i.onerror = () => res(null); i.src = logoAcgt
    })
    const doc = new jsPDF({ unit: 'mm', format: 'a4' })
    liste.forEach((g, gi) => {
      if (gi > 0) doc.addPage()
      const premier = g.items[0]?.code || ''
      const dernier = g.items[g.items.length - 1]?.code || ''
      autoTable(doc, {
        head: [['Code', 'Nom', 'Postnom', 'Prénom', 'Domaine']],
        body: g.items.map((r) => [r.code, affNom(r.nom).toUpperCase(), affNom(r.postnom).toUpperCase(), affNom(r.prenom).toUpperCase(), r.poste_libelle || '']),
        startY: 40,
        margin: { top: 40, left: 12, right: 12 },
        headStyles: { fillColor: [26, 35, 126], textColor: 255, fontStyle: 'bold' },
        styles: { fontSize: 9, cellPadding: 2, overflow: 'linebreak', textColor: [0, 0, 0] },
        alternateRowStyles: { fillColor: [245, 246, 251] },
        columnStyles: { 0: { fontStyle: 'bold', textColor: [26, 35, 126], cellWidth: 22 } },
        didDrawPage: () => {
          // Logo borné dans une boîte (ratio conservé) ; le texte est placé à
          // DROITE du logo réellement dessiné → pas de superposition.
          let x = 12
          if (logo) {
            const s = Math.min(30 / (logo.naturalWidth || 1), 20 / (logo.naturalHeight || 1))
            const w = (logo.naturalWidth || 1) * s
            const h = (logo.naturalHeight || 1) * s
            // Centré verticalement sur le bloc de texte (≈ y 11 → 33).
            const y = Math.max(8, 22 - h / 2)
            doc.addImage(logo, 'PNG', 12, y, w, h)
            x = 12 + w + 6
          }
          doc.setFont('helvetica', 'bold'); doc.setFontSize(15); doc.setTextColor(26, 35, 126)
          doc.text('LISTE DES CANDIDATS ADMIS AU TEST', x, 16)
          doc.setFontSize(12); doc.setTextColor(55, 55, 55)
          doc.text(`Salle ${g.salle} - ${g.ville}`, x, 23)
          const t = `Codes ${premier} à ${dernier}`
          doc.setFontSize(11)
          const tw = doc.getTextWidth(t) + 8
          doc.setFillColor(198, 40, 40); doc.roundedRect(x, 26, tw, 7.5, 1.5, 1.5, 'F')
          doc.setTextColor(255, 255, 255); doc.text(t, x + 4, 31.2)
          doc.setTextColor(0, 0, 0); doc.setFont('helvetica', 'normal')
        },
        didDrawCell: () => {},
      })
    })
    doc.save(`feuilles_salle_${villeFiltre.value || 'toutes'}.pdf`)
  } catch (e) {
    notifier('Génération du PDF impossible.', 'error')
  } finally { enPdf.value = false }
}

// Affichage de la salle sur la page publique (interrupteur)
const sallePublic = ref(false)
watch(() => appelCourant.value?.afficher_salle_public, (v) => { sallePublic.value = !!v }, { immediate: true })
async function basculerSallePublic(val) {
  try {
    await api.post(`/appels/${appelId.value}/afficher-salle-public/`, { afficher: val })
    notifier(val ? 'Salle désormais visible sur la page publique.' : 'Salle masquée au public.')
    await rechargerAppels()
  } catch (e) {
    notifier(e.response?.data?.detail || 'Action impossible.', 'error')
    sallePublic.value = !val
  }
}
// Inclusion des ajouts supplémentaires dans la liste définitive (interrupteur)
const supplementsVisibles = ref(true)
watch(() => appelCourant.value?.afficher_supplements_definitif,
  (v) => { supplementsVisibles.value = v !== false }, { immediate: true })
async function basculerSupplements(val) {
  try {
    await api.post(`/appels/${appelId.value}/afficher-supplements/`, { afficher: val })
    notifier(val ? 'Ajouts supplémentaires inclus dans la liste définitive.'
                 : 'Ajouts supplémentaires masqués de la liste définitive.')
    await rechargerAppels()
    await chargerDefinitif()
  } catch (e) {
    notifier(e.response?.data?.detail || 'Action impossible.', 'error')
    supplementsVisibles.value = !val
  }
}
async function affecterSalles() {
  enSalles.value = true
  try {
    const { data } = await api.post(`/appels/${appelId.value}/affecter-salles/`, salleForm.value)
    notifier(`Salles affectées (${LBL_VILLE[data.ville]}) : ${data.affectes} personne(s) sur ${data.salles_utilisees} salle(s)`
      + (data.non_affectes ? ` — ⚠ ${data.non_affectes} non affecté(s), capacité insuffisante.` : '.'))
    dialogSalles.value = false
    await chargerDefinitif()
  } catch (e) {
    notifier(e.response?.data?.ville || e.response?.data?.detail || 'Affectation impossible.', 'error')
  } finally { enSalles.value = false }
}
function exporterDefinitive() {
  window.open(`/api/appels/${appelId.value}/liste-definitive-export/`, '_blank')
}

async function chargerDefinitif() {
  if (!appelId.value) { definitif.value = { publiee: false, total: 0, nb_recours: 0, nb_codes: 0, results: [] }; return }
  chargementDef.value = true
  try {
    const params = {}
    if (qDef.value) params.q = qDef.value
    const { data } = await api.get(`/appels/${appelId.value}/liste-definitive/`, { params })
    definitif.value = data
  } finally { chargementDef.value = false }
}
let minuteurDef
function rechercherDef() { clearTimeout(minuteurDef); minuteurDef = setTimeout(chargerDefinitif, 300) }

// --- Ajouts supplémentaires : CRUD (admin) ---
// Personnes décidées hors plateforme, ajoutées à la fin de la liste définitive
// (origine « supplément », code attribué automatiquement à la suite).
const postes = ref([])
const dialogSupp = ref(false)
const suppEdit = ref(false)
const enSupp = ref(false)
const suppVierge = () => ({ id: null, nom: '', postnom: '', prenom: '', poste_libelle: '', ville_examen: 'kinshasa', salle: '' })
const suppForm = ref(suppVierge())

function ouvrirSupplement() {
  suppEdit.value = false
  suppForm.value = suppVierge()
  dialogSupp.value = true
}
function modifierSupplement(row) {
  suppEdit.value = true
  suppForm.value = {
    id: row.id, nom: row.nom, postnom: row.postnom, prenom: row.prenom,
    poste_libelle: row.poste_libelle || '', ville_examen: row.ville_examen_code || 'kinshasa',
    salle: row.salle || '',
  }
  dialogSupp.value = true
}
async function enregistrerSupplement() {
  if (!suppForm.value.nom.trim() || !suppForm.value.prenom.trim()) {
    notifier('Le nom et le prénom sont requis.', 'error'); return
  }
  enSupp.value = true
  try {
    const corps = {
      nom: suppForm.value.nom, postnom: suppForm.value.postnom, prenom: suppForm.value.prenom,
      poste_libelle: suppForm.value.poste_libelle, ville_examen: suppForm.value.ville_examen,
      salle: (suppForm.value.salle || '').trim().toUpperCase(),
    }
    if (suppEdit.value) {
      await api.patch(`/supplements/${suppForm.value.id}/`, corps)
      notifier('Ajout supplémentaire modifié.')
    } else {
      await api.post('/supplements/', { ...corps, appel: appelId.value })
      notifier('Ajout supplémentaire enregistré.')
    }
    dialogSupp.value = false
    await chargerDefinitif()
  } catch (e) {
    const d = e.response?.data
    notifier(d?.detail || d?.nom?.[0] || d?.prenom?.[0] || 'Enregistrement impossible.', 'error')
  } finally { enSupp.value = false }
}
async function supprimerSupplement(row) {
  if (!window.confirm(`Supprimer définitivement l'ajout « ${row.nom} ${row.postnom} ${row.prenom} » (code ${row.code}) ?`)) return
  try {
    await api.delete(`/supplements/${row.id}/`)
    notifier('Ajout supplémentaire supprimé.')
    await chargerDefinitif()
  } catch (e) { notifier(e.response?.data?.detail || 'Suppression impossible.', 'error') }
}

async function publierDefinitive() {
  try {
    const { data } = await api.post(`/appels/${appelId.value}/publier-liste-definitive/`)
    notifier(`Liste définitive publiée — ${data.total} personne(s), ${data.nouveaux_codes} nouveau(x) code(s).`)
    await Promise.all([rechargerAppels(), chargerDefinitif()])
  } catch (e) { notifier(e.response?.data?.detail || 'Publication impossible.', 'error') }
}
async function depublierDefinitive() {
  try {
    await api.post(`/appels/${appelId.value}/depublier-liste-definitive/`)
    notifier("Liste définitive retirée de l'affichage public.")
    await Promise.all([rechargerAppels(), chargerDefinitif()])
  } catch (e) { notifier(e.response?.data?.detail || 'Action impossible.', 'error') }
}

// --- Demandes de ville d'examen (validées par un agent) ---
const demandes = ref([])
const chargementDem = ref(false)
const ENTETES_DEM = [
  { title: 'Code', key: 'code', width: 90 },
  { title: 'Candidat', key: 'nom' },
  { title: 'Né(e) le', key: 'date_naissance', sortable: false },
  { title: 'Ville actuelle', key: 'ville_actuelle', sortable: false },
  { title: 'Ville demandée', key: 'ville_demandee', sortable: false },
  { title: 'Demandé le', key: 'demande_le', sortable: false },
  { title: '', key: 'actions', sortable: false, align: 'end' },
]
const demandeStatut = ref('en_attente')
const demandesCounts = ref({ en_attente: 0, validees: 0, rejetees: 0 })
async function chargerDemandes() {
  if (!appelId.value) { demandes.value = []; demandesCounts.value = { en_attente: 0, validees: 0, rejetees: 0 }; return }
  chargementDem.value = true
  try {
    const { data } = await api.get(`/appels/${appelId.value}/demandes-ville/`, { params: { statut: demandeStatut.value } })
    demandes.value = data.results
    demandesCounts.value = { en_attente: data.en_attente, validees: data.validees, rejetees: data.rejetees }
  } finally { chargementDem.value = false }
}
// Examen d'une demande : voir les pièces + la date de naissance avant de trancher.
const demandeDetail = ref(null)
const dialogDemande = ref(false)
function ouvrirDemande(item) { demandeDetail.value = item; dialogDemande.value = true }

// --- Visionneuse de document (image : rotation/zoom ; PDF : iframe) ---
const EXT_IMAGE = ['jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp']
const apercu = ref({ show: false, url: '', urlDl: '', titre: '', estImage: false })
const rotation = ref(0)
const zoom = ref(1)
function voirDocument(doc) {
  const nom = (doc.nom_original || doc.url || '').toLowerCase()
  const ext = nom.split('.').pop().split('?')[0]
  rotation.value = 0; zoom.value = 1
  apercu.value = {
    show: true,
    url: `${doc.url}${doc.url.includes('?') ? '&' : '?'}inline=1`,
    urlDl: doc.url,
    titre: doc.libelle || doc.nom_original || 'Document',
    estImage: EXT_IMAGE.includes(ext),
  }
}
const pivoter = (sens) => { rotation.value = (rotation.value + sens * 90 + 360) % 360 }
const zoomer = (pas) => { zoom.value = Math.min(4, Math.max(0.25, +(zoom.value + pas).toFixed(2))) }
const reinitVue = () => { rotation.value = 0; zoom.value = 1 }
const styleImage = computed(() => ({ transform: `rotate(${rotation.value}deg) scale(${zoom.value})` }))
async function traiterDemande(id, action) {
  try {
    await api.post(`/appels/${appelId.value}/traiter-demande-ville/`, { id, action })
    notifier(action === 'valider' ? 'Demande validée — ville officielle mise à jour.' : 'Demande rejetée.')
    dialogDemande.value = false
    await Promise.all([chargerDemandes(), chargerDefinitif()])
  } catch (e) { notifier(e.response?.data?.detail || 'Action impossible.', 'error') }
}
const dateFr = (d) => (d ? new Date(d).toLocaleDateString('fr-FR') : '—')

// --- Aperçu des e-mails de résultat (admin) : admis (liste définitive) +
//     non retenus (dernier traitement), 1 par personne. Aucun envoi ici. ---
const resultats = ref({ admis: 0, non_retenus: 0, total: 0, sans_email: 0, results: [] })
const chargementRes = ref(false)
const ENTETES_RES = [
  { title: 'Résultat', key: 'type' },
  { title: 'Code', key: 'code', sortable: false },
  { title: 'Nom', key: 'nom' },
  { title: 'Postnom', key: 'postnom', sortable: false },
  { title: 'Prénom', key: 'prenom', sortable: false },
  { title: 'E-mail', key: 'email', sortable: false },
  { title: 'Dernier traitement', key: 'dernier_traitement', sortable: false },
  { title: 'Ville / Motif', key: 'detail', sortable: false },
]
async function chargerResultats() {
  if (!appelId.value || !auth.estAdmin) return
  chargementRes.value = true
  try {
    const { data } = await api.get(`/appels/${appelId.value}/resultats-apercu/`)
    resultats.value = data
  } finally { chargementRes.value = false }
}
function exporterResultats() {
  window.open(`/api/appels/${appelId.value}/resultats-export/`, '_blank')
}
const LBL_TRAIT = { dossier: 'Dossier', reclamation: 'Réclamation', recours: 'Recours', '': 'Liste définitive' }

// --- Envoi des e-mails de résultat (test / préparer / envoyer + progression) ---
const etatEnvoi = ref({ total: 0, envoyes: 0, echecs: 0, restants: 0, termine: false })
const enTest = ref(false)
const enPrep = ref(false)
const envoiEnCours = ref(false)
const dialogEnvoi = ref(false)
const pctEnvoi = computed(() => etatEnvoi.value.total
  ? Math.round((etatEnvoi.value.envoyes + etatEnvoi.value.echecs) / etatEnvoi.value.total * 100) : 0)

async function chargerEtatEnvoi() {
  if (!appelId.value || !auth.estAdmin) return
  try { etatEnvoi.value = (await api.get(`/appels/${appelId.value}/resultats-etat/`)).data } catch { /* */ }
}
async function testerEnvoi() {
  enTest.value = true
  try {
    const { data } = await api.post(`/appels/${appelId.value}/resultats-test/`)
    notifier(data.detail || 'Exemples envoyés.')
  } catch (e) { notifier(e.response?.data?.detail || 'Échec du test.', 'error') } finally { enTest.value = false }
}
async function preparerEnvoi() {
  enPrep.value = true
  try {
    const { data } = await api.post(`/appels/${appelId.value}/resultats-preparer/`)
    etatEnvoi.value = data
    notifier(`${data.prepares} e-mail(s) préparé(s) · ${data.deja_en_file} déjà en file · ${data.sans_email} sans e-mail.`)
  } catch (e) { notifier(e.response?.data?.detail || 'Préparation impossible.', 'error') } finally { enPrep.value = false }
}
async function envoyerTout() {
  dialogEnvoi.value = false
  envoiEnCours.value = true
  try {
    let termine = false
    while (!termine) {
      const { data } = await api.post(`/appels/${appelId.value}/resultats-envoyer-lot/`, { limite: 30 })
      etatEnvoi.value = data
      termine = data.termine
    }
    notifier(`Envoi terminé : ${etatEnvoi.value.envoyes} envoyé(s), ${etatEnvoi.value.echecs} échec(s).`)
  } catch (e) {
    notifier(e.response?.data?.detail || 'Envoi interrompu — relancez pour reprendre.', 'error')
  } finally { envoiEnCours.value = false }
}

// Recharge la définitive, les demandes et l'aperçu des résultats au changement d'appel.
watch(appelId, () => { chargerDefinitif(); chargerDemandes(); chargerResultats(); chargerEtatEnvoi() })

onMounted(async () => {
  await rechargerAppels()
  if (auth.estAdmin) {
    try {
      const { data } = await api.get('/postes/', { params: { page_size: 200 } })
      postes.value = (data.results || data).map((p) => p.libelle)
    } catch { /* non bloquant */ }
  }
})
</script>

<template>
  <div>
    <div class="d-flex align-center mb-5">
      <v-icon color="primary" size="30" class="mr-3">mdi-trophy-outline</v-icon>
      <h1 class="text-h5 font-weight-bold text-primary">Publication des retenus</h1>
    </div>

    <v-card flat border class="pa-4 mb-5">
      <v-select
        v-model="appelId"
        :items="appels.map((a) => ({ value: a.id, title: a.titre + (a.liste_retenus_publiee ? ' — publié' : '') }))"
        label="Appel à candidature" hide-details style="max-width: 460px" />
    </v-card>

    <template v-if="appelId">
      <!-- Stats : état global des deux listes -->
      <v-row dense class="mb-5">
        <v-col cols="6" md="3">
          <StatCard icon="mdi-account-check" :value="total" label="Retenus (provisoire)"
                    description="Présélectionnés" color="#2E7D32" />
        </v-col>
        <v-col cols="6" md="3">
          <StatCard :icon="publiee ? 'mdi-earth' : 'mdi-earth-off'" :value="publiee ? 'Oui' : 'Non'"
                    label="Liste provisoire" :description="publiee ? 'Publiée' : 'Non publiée'"
                    :color="publiee ? '#0288D1' : '#607D8B'" />
        </v-col>
        <v-col cols="6" md="3">
          <StatCard icon="mdi-seal-variant" :value="definitif.total" label="Liste définitive"
                    :description="definitif.nb_recours ? `dont ${definitif.nb_recours} via recours` : 'Retenus + recours'"
                    color="#5E35B1" />
        </v-col>
        <v-col cols="6" md="3">
          <StatCard :icon="defPubliee ? 'mdi-earth' : 'mdi-earth-off'" :value="defPubliee ? 'Oui' : 'Non'"
                    label="Définitive publiée" :description="defPubliee ? 'Visible publiquement' : 'Non publiée'"
                    :color="defPubliee ? '#5E35B1' : '#607D8B'" />
        </v-col>
      </v-row>

      <!-- Onglets -->
      <v-card flat border rounded="lg" class="mb-4 onglets-barre">
        <v-tabs v-model="onglet" color="primary" align-tabs="start" height="56" slider-color="primary">
          <v-tab value="provisoire" prepend-icon="mdi-format-list-bulleted-square" class="text-none font-weight-bold">
            Liste provisoire
            <v-chip size="x-small" class="ml-2" variant="flat" color="primary">{{ total }}</v-chip>
          </v-tab>
          <v-tab value="definitive" prepend-icon="mdi-seal-variant" class="text-none font-weight-bold">
            Liste définitive
            <v-chip size="x-small" class="ml-2" variant="flat" color="#5E35B1">{{ definitif.total }}</v-chip>
          </v-tab>
          <v-tab value="demandes" prepend-icon="mdi-map-marker-radius-outline" class="text-none font-weight-bold">
            Demandes de ville
            <v-chip v-if="demandesCounts.en_attente" size="x-small" class="ml-2" variant="flat" color="#EF6C00">{{ demandesCounts.en_attente }}</v-chip>
          </v-tab>
          <v-tab v-if="auth.estAdmin" value="resultats" prepend-icon="mdi-email-multiple-outline" class="text-none font-weight-bold">
            Résultats e-mail
          </v-tab>
        </v-tabs>
      </v-card>

      <v-window v-model="onglet">
      <!-- ===== Onglet : LISTE PROVISOIRE ===== -->
      <v-window-item value="provisoire">
      <v-card flat border>
        <v-card-title class="d-flex align-center flex-wrap ga-3 py-4">
          <span class="text-subtitle-1 font-weight-bold">Personnes retenues</span>
          <v-chip color="primary" variant="tonal" size="small">{{ total }}</v-chip>
          <v-spacer />
          <v-text-field v-model="q" @update:modelValue="rechercher" placeholder="Rechercher un nom…"
                        prepend-inner-icon="mdi-magnify" variant="outlined" density="compact" hide-details
                        clearable style="max-width: 260px" @click:clear="q = ''" />
          <v-chip v-if="publiee" color="success" variant="flat" prepend-icon="mdi-earth">Liste publiée</v-chip>
          <template v-if="auth.estAdmin">
            <v-btn v-if="!publiee" color="primary" variant="flat"
                   prepend-icon="mdi-publish" :disabled="!total" @click="publier">Publier la liste</v-btn>
            <v-btn v-else color="grey" variant="outlined" prepend-icon="mdi-publish-off" @click="depublier">Dépublier</v-btn>
          </template>
        </v-card-title>
        <v-divider />
        <v-data-table-server
          :headers="ENTETES" :items="retenus" :items-length="total" :loading="chargement"
          :search="cle" :sort-by="tri" :items-per-page="25"
          :items-per-page-options="[{ value: 25, title: '25' }, { value: 50, title: '50' }, { value: 100, title: '100' }]"
          @update:options="charger" class="tableau-admin"
          no-data-text="Aucune personne retenue pour cet appel." loading-text="Chargement…">
          <template #item.rang="{ index }">
            <span class="text-medium-emphasis">{{ (page - 1) * parPage + index + 1 }}</span>
          </template>
          <template #item.nom="{ item }"><span class="font-weight-bold">{{ item.nom }}</span></template>
          <template #item.poste_libelle="{ item }">
            <span class="text-medium-emphasis">{{ item.poste_libelle || '—' }}</span>
          </template>
        </v-data-table-server>
        <v-card-text class="text-caption text-medium-emphasis">
          Publier rend cette liste consultable publiquement (NOM · POSTNOM · PRÉNOM).
          Les candidats retenus ont déjà été notifiés individuellement.
        </v-card-text>
      </v-card>
      </v-window-item>

      <!-- ===== Onglet : LISTE DÉFINITIVE (retenus publiés + recours validés) ===== -->
      <v-window-item value="definitive">
      <v-card flat border>
        <!-- Ligne 1 : titre + état de publication -->
        <div class="d-flex align-center flex-wrap ga-3 px-4 pt-4 pb-2">
          <v-icon color="#5E35B1">mdi-seal-variant</v-icon>
          <span class="text-subtitle-1 font-weight-bold">Liste définitive</span>
          <v-chip color="#5E35B1" variant="tonal" size="small">{{ definitif.total }}</v-chip>
          <v-chip v-if="definitif.nb_recours" color="#00838F" variant="tonal" size="small"
                  prepend-icon="mdi-gavel">{{ definitif.nb_recours }} via recours</v-chip>
          <v-spacer />
          <v-chip v-if="defPubliee" color="#5E35B1" variant="flat" prepend-icon="mdi-earth">Publiée</v-chip>
          <template v-if="auth.estAdmin || auth.peutSuperviser">
            <v-btn v-if="!defPubliee" color="#5E35B1" variant="flat" prepend-icon="mdi-publish"
                   :disabled="!definitif.total" @click="publierDefinitive">
              {{ definitif.nb_codes ? 'Republier' : 'Publier' }} la définitive
            </v-btn>
            <v-btn v-else color="grey" variant="outlined" prepend-icon="mdi-publish-off"
                   @click="depublierDefinitive">Dépublier</v-btn>
          </template>
        </div>
        <v-divider />
        <!-- Ligne 2 : filtres + outils (salles, exports) -->
        <div class="d-flex align-center flex-wrap ga-3 px-4 py-3">
          <v-select v-model="villeFiltre" :items="VILLES_FILTRE" label="Ville du test" clearable
                    hide-details density="compact" variant="outlined" style="max-width: 200px"
                    prepend-inner-icon="mdi-map-marker-outline" />
          <v-text-field v-model="qDef" @update:modelValue="rechercherDef" placeholder="Rechercher un nom…"
                        prepend-inner-icon="mdi-magnify" variant="outlined" density="compact" hide-details
                        clearable style="max-width: 240px" @click:clear="qDef = ''; chargerDefinitif()" />
          <v-spacer />
          <v-switch v-if="auth.peutSuperviser" v-model="supplementsVisibles" @update:modelValue="basculerSupplements"
                    color="amber-darken-2" hide-details density="compact" inset
                    label="Suppléments visibles" class="flex-grow-0 mr-1" />
          <v-switch v-if="auth.peutSuperviser" v-model="sallePublic" @update:modelValue="basculerSallePublic"
                    color="#00838F" hide-details density="compact" inset
                    label="Salle visible au public" class="flex-grow-0 mr-1" />
          <v-btn v-if="auth.estAdmin" color="amber-darken-3" variant="tonal" prepend-icon="mdi-account-plus-outline"
                 :disabled="!appelId" @click="ouvrirSupplement">Ajouter un supplément</v-btn>
          <v-btn v-if="auth.peutSuperviser" color="#00838F" variant="tonal" prepend-icon="mdi-door-open"
                 :disabled="!definitif.total" @click="dialogSalles = true">Affecter les salles</v-btn>
          <v-btn color="#5E35B1" variant="tonal" prepend-icon="mdi-file-pdf-box" :loading="enPdf"
                 :disabled="!definitif.total" @click="exporterSallesPdf">Feuilles de salle (PDF)</v-btn>
          <v-btn color="#1D6F42" variant="tonal" prepend-icon="mdi-microsoft-excel"
                 :disabled="!definitif.total" @click="exporterDefinitive">Exporter Excel</v-btn>
        </div>
        <v-divider />
        <v-alert v-if="defPubliee" type="success" variant="tonal" density="compact" class="ma-3" icon="mdi-information-outline">
          La liste définitive est publiée : elle <strong>remplace la liste provisoire</strong> sur la page publique des retenus.
        </v-alert>
        <v-data-table
          :headers="ENTETES_DEF" :items="definitifAffiche" :loading="chargementDef"
          :items-per-page="25" :items-per-page-options="[{ value: 25, title: '25' }, { value: 50, title: '50' }, { value: 100, title: '100' }]"
          class="tableau-admin" no-data-text="Aucune personne (retenus publiés + recours validés)." loading-text="Chargement…">
          <template #item.code="{ item }">
            <span class="font-weight-bold" :class="item.code ? 'text-primary' : 'text-medium-emphasis'">
              {{ item.code || '—' }}
            </span>
          </template>
          <template #item.nom="{ item }"><span class="font-weight-bold">{{ item.nom }}</span></template>
          <template #item.poste_libelle="{ item }"><span class="text-medium-emphasis">{{ item.poste_libelle || '—' }}</span></template>
          <template #item.ville_examen="{ item }">
            <v-chip size="x-small" label variant="tonal"
                    :color="item.ville_examen === 'Kinshasa' ? 'grey' : '#EF6C00'">{{ item.ville_examen }}</v-chip>
          </template>
          <template #item.salle="{ item }">
            <v-chip v-if="item.salle" size="x-small" label color="#00838F" variant="flat">{{ item.salle }}</v-chip>
            <span v-else class="text-medium-emphasis">—</span>
          </template>
          <template #item.origine="{ item }">
            <v-chip v-if="item.origine === 'recours'" size="x-small" label color="#00838F" variant="tonal">Recours</v-chip>
            <v-chip v-else-if="item.origine === 'supplement'" size="x-small" label color="amber-darken-2" variant="tonal">Supplément</v-chip>
            <v-chip v-else size="x-small" label color="grey" variant="tonal">Liste</v-chip>
          </template>
          <template #item.actions="{ item }">
            <template v-if="item.origine === 'supplement' && item.id">
              <v-btn icon="mdi-pencil" size="x-small" variant="text" color="primary" @click="modifierSupplement(item)" />
              <v-btn icon="mdi-delete-outline" size="x-small" variant="text" color="error" @click="supprimerSupplement(item)" />
            </template>
          </template>
        </v-data-table>
        <v-card-text class="text-caption text-medium-emphasis">
          La définitive combine les retenus publiés et les recours validés (dédupliqués). À la publication,
          chaque personne reçoit un <strong>code stable</strong> (0001…) conservé même si on republie après ajout.
          Le message public spécifique se règle dans la console (champ « message public (liste définitive) »).
        </v-card-text>
      </v-card>
      </v-window-item>

      <!-- ===== Onglet : DEMANDES DE VILLE (à valider par un agent) ===== -->
      <v-window-item value="demandes">
      <v-card flat border>
        <v-card-title class="d-flex align-center flex-wrap ga-3 py-4">
          <v-icon color="#EF6C00">mdi-map-marker-radius-outline</v-icon>
          <span class="text-subtitle-1 font-weight-bold">Demandes de ville d'examen</span>
          <v-spacer />
          <v-btn-toggle v-model="demandeStatut" mandatory density="compact" variant="outlined"
                        divided @update:modelValue="chargerDemandes">
            <v-btn value="en_attente" size="small">En attente ({{ demandesCounts.en_attente }})</v-btn>
            <v-btn value="validee" size="small">Validées ({{ demandesCounts.validees }})</v-btn>
            <v-btn value="rejetee" size="small">Rejetées ({{ demandesCounts.rejetees }})</v-btn>
          </v-btn-toggle>
        </v-card-title>
        <v-divider />
        <v-alert type="info" variant="tonal" density="compact" class="ma-3" icon="mdi-shield-check-outline">
          Les candidats hors Kinshasa <strong>demandent</strong> leur ville sur le portail ; la ville officielle
          ne change qu'après <strong>validation</strong> (vérifiez la date de naissance avec leur pièce d'identité).
        </v-alert>
        <v-data-table
          :headers="ENTETES_DEM" :items="demandes" :loading="chargementDem"
          :items-per-page="25" :items-per-page-options="[{ value: 25, title: '25' }, { value: 50, title: '50' }, { value: 100, title: '100' }]"
          class="tableau-admin" no-data-text="Aucune demande dans cette catégorie." loading-text="Chargement…">
          <template #item.code="{ item }"><span class="font-weight-bold text-primary">{{ item.code }}</span></template>
          <template #item.nom="{ item }">
            <span class="font-weight-bold">{{ item.nom }}</span> {{ item.postnom }} {{ item.prenom }}
          </template>
          <template #item.date_naissance="{ item }">{{ dateFr(item.date_naissance) }}</template>
          <template #item.ville_actuelle="{ item }"><span class="text-medium-emphasis">{{ item.ville_actuelle }}</span></template>
          <template #item.ville_demandee="{ item }">
            <v-chip color="#EF6C00" size="small" variant="tonal" label>{{ item.ville_demandee_libelle }}</v-chip>
          </template>
          <template #item.demande_le="{ item }">{{ dateFr(item.demande_le) }}</template>
          <template #item.actions="{ item }">
            <v-btn v-if="auth.peutTraiter" color="primary" variant="text" size="small"
                   append-icon="mdi-arrow-right" @click="ouvrirDemande(item)">Examiner</v-btn>
          </template>
        </v-data-table>
      </v-card>
      </v-window-item>

      <!-- ===== Onglet : RÉSULTATS E-MAIL (aperçu, admin) ===== -->
      <v-window-item v-if="auth.estAdmin" value="resultats">
      <v-row dense class="mb-4">
        <v-col cols="6" md="3"><StatCard icon="mdi-email-check-outline" :value="resultats.admis" label="Admis" description="Liste définitive" color="#2E7D32" /></v-col>
        <v-col cols="6" md="3"><StatCard icon="mdi-email-remove-outline" :value="resultats.non_retenus" label="Non retenus" description="Dernier traitement" color="#C62828" /></v-col>
        <v-col cols="6" md="3"><StatCard icon="mdi-email-multiple-outline" :value="resultats.total" label="E-mails (total)" description="1 par personne" color="#1a237e" /></v-col>
        <v-col cols="6" md="3"><StatCard icon="mdi-email-alert-outline" :value="resultats.sans_email" label="Sans e-mail" description="À vérifier" color="#EF6C00" /></v-col>
      </v-row>
      <!-- Bloc d'envoi : test -> préparer -> envoyer (progression) -->
      <v-card flat border class="mb-4 pa-4">
        <div class="d-flex align-center flex-wrap ga-3">
          <v-icon color="#1a237e">mdi-send-outline</v-icon>
          <span class="text-subtitle-1 font-weight-bold">Envoi des e-mails de résultat</span>
          <v-spacer />
          <v-btn variant="outlined" color="primary" prepend-icon="mdi-email-fast-outline"
                 :loading="enTest" @click="testerEnvoi">Test (m'envoyer un exemple)</v-btn>
          <v-btn variant="tonal" color="primary" prepend-icon="mdi-playlist-check"
                 :loading="enPrep" :disabled="!resultats.total" @click="preparerEnvoi">Préparer l'envoi</v-btn>
          <v-btn color="error" variant="flat" prepend-icon="mdi-send"
                 :loading="envoiEnCours" :disabled="!etatEnvoi.restants" @click="dialogEnvoi = true">
            Envoyer à tous ({{ etatEnvoi.restants }})
          </v-btn>
        </div>
        <div v-if="etatEnvoi.total" class="mt-4">
          <v-progress-linear :model-value="pctEnvoi" color="#2E7D32" height="20" rounded>
            <span class="text-caption font-weight-bold">{{ pctEnvoi }}%</span>
          </v-progress-linear>
          <div class="d-flex flex-wrap ga-4 mt-2 text-body-2">
            <span><strong>{{ etatEnvoi.envoyes }}</strong> envoyé(s)</span>
            <span class="text-error"><strong>{{ etatEnvoi.echecs }}</strong> échec(s)</span>
            <span class="text-medium-emphasis"><strong>{{ etatEnvoi.restants }}</strong> restant(s)</span>
            <span class="text-medium-emphasis">sur {{ etatEnvoi.total }}</span>
            <span v-if="envoiEnCours" class="text-primary">Envoi en cours…</span>
            <span v-else-if="etatEnvoi.termine && etatEnvoi.total" class="text-success font-weight-bold">✓ Terminé</span>
          </div>
        </div>
        <div class="text-caption text-medium-emphasis mt-3">
          1. <strong>Test</strong> (vérifie le rendu sur ton adresse) → 2. <strong>Préparer</strong> (met en file, sans envoi)
          → 3. <strong>Envoyer à tous</strong> (envoi réel, progressif, reprise possible). 1 e-mail par personne, déjà envoyés ignorés.
        </div>
      </v-card>

      <v-card flat border>
        <v-card-title class="d-flex align-center flex-wrap ga-3 py-4">
          <v-icon color="primary">mdi-email-multiple-outline</v-icon>
          <span class="text-subtitle-1 font-weight-bold">Aperçu des e-mails de résultat</span>
          <v-spacer />
          <v-btn color="#1D6F42" variant="tonal" prepend-icon="mdi-microsoft-excel"
                 :disabled="!resultats.total" @click="exporterResultats">Exporter Excel</v-btn>
        </v-card-title>
        <v-divider />
        <v-alert type="warning" variant="tonal" density="compact" class="ma-3" icon="mdi-information-outline">
          <strong>Aperçu uniquement — aucun e-mail n'est envoyé.</strong> 1 e-mail par personne :
          <strong>admis</strong> (liste définitive) ou <strong>non retenu</strong> (selon le dernier traitement :
          recours → réclamation → dossier). Vérifie les chiffres et exporte avant d'activer l'envoi.
        </v-alert>
        <v-data-table
          :headers="ENTETES_RES" :items="resultats.results" :loading="chargementRes"
          :items-per-page="25" :items-per-page-options="[{ value: 25, title: '25' }, { value: 50, title: '50' }, { value: 100, title: '100' }]"
          class="tableau-admin" no-data-text="Aucun e-mail à envoyer (publie d'abord la liste définitive)." loading-text="Chargement…">
          <template #item.type="{ item }">
            <v-chip size="small" label variant="flat" :color="item.type === 'admis' ? 'success' : 'error'">
              {{ item.type === 'admis' ? 'Admis' : 'Non retenu' }}
            </v-chip>
          </template>
          <template #item.code="{ item }"><span class="font-weight-bold text-primary">{{ item.code || '—' }}</span></template>
          <template #item.nom="{ item }"><span class="font-weight-bold">{{ item.nom }}</span></template>
          <template #item.email="{ item }">
            <span :class="{ 'text-error font-weight-bold': !item.email }">{{ item.email || '⚠ aucun' }}</span>
          </template>
          <template #item.dernier_traitement="{ item }">
            <span class="text-medium-emphasis">{{ LBL_TRAIT[item.dernier_traitement] ?? 'Liste définitive' }}</span>
          </template>
          <template #item.detail="{ item }">
            <span class="text-medium-emphasis">{{ item.type === 'admis' ? item.ville : (item.motif || '—') }}</span>
          </template>
        </v-data-table>
        <v-card-text class="text-caption text-medium-emphasis">
          Prochaine étape (après ta validation) : test d'envoi sur ton adresse, puis envoi en masse
          (file lissée) avec confirmation. Rien n'est envoyé tant que ce n'est pas activé.
        </v-card-text>
      </v-card>
      </v-window-item>
      </v-window>
    </template>

    <v-card v-else flat border class="pa-10 text-center">
      <v-icon size="48" color="grey-lighten-1" class="mb-2">mdi-trophy-outline</v-icon>
      <p class="text-body-2 text-medium-emphasis mb-0">Sélectionnez un appel à candidature pour gérer sa liste de retenus.</p>
    </v-card>

    <!-- Affectation automatique des salles -->
    <!-- Ajout / modification d'un supplément (admin) -->
    <v-dialog v-model="dialogSupp" max-width="580">
      <v-card rounded="lg">
        <v-card-title class="d-flex align-center ga-2 pa-4">
          <v-icon color="amber-darken-3">mdi-account-plus-outline</v-icon>
          <span class="text-h6">{{ suppEdit ? 'Modifier' : 'Ajouter' }} un supplément</span>
        </v-card-title>
        <v-divider />
        <v-card-text class="pa-4">
          <p class="text-body-2 text-medium-emphasis mb-3">
            Personne admise décidée hors plateforme. Elle est ajoutée
            <strong>à la fin</strong> de la liste définitive ; le <strong>code</strong> est attribué
            automatiquement à la suite.
          </p>
          <v-row dense>
            <v-col cols="12" sm="4"><v-text-field v-model="suppForm.nom" label="Nom *" density="compact" variant="outlined" hide-details /></v-col>
            <v-col cols="12" sm="4"><v-text-field v-model="suppForm.postnom" label="Postnom" density="compact" variant="outlined" hide-details /></v-col>
            <v-col cols="12" sm="4"><v-text-field v-model="suppForm.prenom" label="Prénom *" density="compact" variant="outlined" hide-details /></v-col>
          </v-row>
          <v-combobox v-model="suppForm.poste_libelle" :items="postes" label="Domaine"
                      density="compact" variant="outlined" hide-details class="mt-3" />
          <v-row dense class="mt-1">
            <v-col cols="12" sm="8">
              <v-select v-model="suppForm.ville_examen" :items="VILLES_VAL" label="Ville du test"
                        density="compact" variant="outlined" hide-details />
            </v-col>
            <v-col cols="12" sm="4">
              <v-text-field v-model="suppForm.salle" label="Salle" placeholder="ex. A"
                            density="compact" variant="outlined" hide-details
                            hint="Lettre de la salle (facultatif)" />
            </v-col>
          </v-row>
          <p class="text-caption text-medium-emphasis mt-2">
            Saisissez la <strong>salle manuellement</strong> (ex. la dernière salle de la ville) pour
            ne pas relancer « Affecter les salles », qui réécrirait toute la ville.
          </p>
        </v-card-text>
        <v-divider />
        <v-card-actions class="pa-3">
          <v-spacer />
          <v-btn variant="text" @click="dialogSupp = false">Annuler</v-btn>
          <v-btn color="amber-darken-3" variant="flat" prepend-icon="mdi-content-save"
                 :loading="enSupp" @click="enregistrerSupplement">Enregistrer</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-dialog v-model="dialogSalles" max-width="480">
      <v-card rounded="lg">
        <v-card-title class="d-flex align-center ga-2 pa-4">
          <v-icon color="#00838F">mdi-door-open</v-icon>
          <span class="text-h6">Affecter les salles</span>
        </v-card-title>
        <v-divider />
        <v-card-text class="pa-4">
          <p class="text-body-2 text-medium-emphasis mb-4">
            Les candidats de la ville choisie (triés par <strong>code</strong>) sont répartis par
            paquets dans des salles <strong>A, B, C…</strong> Ré-exécutable à tout moment : les codes
            étant stables, chacun retrouve la même salle.
          </p>
          <v-select v-model="salleForm.ville" :items="VILLES_VAL" label="Ville du test"
                    variant="outlined" density="comfortable" class="mb-3" hide-details />
          <div class="text-caption text-medium-emphasis mb-3">
            <strong>{{ nbVilleChoisie }}</strong> candidat(s) à {{ LBL_VILLE[salleForm.ville] }} sur la liste définitive.
          </div>
          <v-row dense>
            <v-col cols="6">
              <v-text-field v-model.number="salleForm.nombre_salles" type="number" min="1"
                            label="Nombre de salles" variant="outlined" density="comfortable" hide-details />
            </v-col>
            <v-col cols="6">
              <v-text-field v-model.number="salleForm.par_salle" type="number" min="1"
                            label="Personnes / salle" variant="outlined" density="comfortable" hide-details />
            </v-col>
          </v-row>
          <v-alert v-if="nbVilleChoisie > salleForm.nombre_salles * salleForm.par_salle"
                   type="warning" variant="tonal" density="compact" class="mt-3">
            Capacité ({{ salleForm.nombre_salles * salleForm.par_salle }}) inférieure au nombre de candidats
            ({{ nbVilleChoisie }}) : les derniers ne seront pas affectés.
          </v-alert>
        </v-card-text>
        <v-divider />
        <v-card-actions class="pa-3">
          <v-btn variant="text" @click="dialogSalles = false">Annuler</v-btn>
          <v-spacer />
          <v-btn color="#00838F" variant="flat" prepend-icon="mdi-door-open" :loading="enSalles"
                 :disabled="!salleForm.nombre_salles || !salleForm.par_salle" @click="affecterSalles">
            Affecter
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Examen d'une demande de ville -->
    <v-dialog v-model="dialogDemande" max-width="560">
      <v-card v-if="demandeDetail" rounded="lg">
        <v-card-title class="d-flex align-center ga-2 pa-4">
          <v-icon color="#EF6C00">mdi-map-marker-radius-outline</v-icon>
          <span class="text-h6">{{ demandeDetail.code }} — {{ demandeDetail.nom }} {{ demandeDetail.postnom }} {{ demandeDetail.prenom }}</span>
        </v-card-title>
        <v-divider />
        <v-card-text class="pa-4">
          <div class="d-flex flex-wrap ga-4 mb-3 text-body-2">
            <span><span class="text-medium-emphasis">Ville actuelle :</span> <strong>{{ demandeDetail.ville_actuelle }}</strong></span>
            <span><span class="text-medium-emphasis">Ville demandée :</span>
              <v-chip color="#EF6C00" size="small" variant="tonal" label>{{ demandeDetail.ville_demandee_libelle }}</v-chip>
            </span>
          </div>
          <v-alert type="info" variant="tonal" density="compact" class="mb-3" icon="mdi-card-account-details-outline">
            Date de naissance déclarée : <strong>{{ dateFr(demandeDetail.date_naissance) }}</strong>.
            Vérifiez-la avec la <strong>pièce d'identité</strong> ci-dessous.
          </v-alert>
          <div class="text-caption font-weight-bold text-primary mb-2">Documents transmis</div>
          <div v-if="demandeDetail.documents && demandeDetail.documents.length" class="d-flex flex-wrap ga-2">
            <v-btn v-for="(d, i) in demandeDetail.documents" :key="i" variant="outlined" size="small"
                   color="primary" prepend-icon="mdi-file-eye-outline"
                   @click="voirDocument(d)">{{ d.libelle }}</v-btn>
          </div>
          <div v-else class="text-body-2 text-medium-emphasis">Aucun document transmis pour ce candidat.</div>
          <v-alert v-if="demandeDetail.statut !== 'en_attente'" class="mt-3" density="compact" variant="tonal"
                   :type="demandeDetail.statut === 'validee' ? 'success' : 'error'">
            Demande déjà <strong>{{ demandeDetail.statut === 'validee' ? 'validée' : 'rejetée' }}</strong>{{ demandeDetail.traite_par ? ` par ${demandeDetail.traite_par}` : '' }}.
          </v-alert>
        </v-card-text>
        <v-divider />
        <v-card-actions class="pa-3">
          <v-btn variant="text" @click="dialogDemande = false">Fermer</v-btn>
          <v-spacer />
          <template v-if="demandeDetail.statut === 'en_attente' && auth.peutTraiter">
            <v-btn color="grey" variant="outlined" prepend-icon="mdi-close-circle-outline"
                   @click="traiterDemande(demandeDetail.id, 'rejeter')">Rejeter</v-btn>
            <v-btn color="success" variant="flat" prepend-icon="mdi-check-circle-outline"
                   @click="traiterDemande(demandeDetail.id, 'valider')">Valider la ville</v-btn>
          </template>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Visionneuse de document (image : rotation/zoom ; PDF : iframe) -->
    <v-dialog v-model="apercu.show" max-width="1000" scrollable>
      <v-card rounded="lg">
        <v-card-title class="d-flex align-center ga-1 pa-2 pl-3">
          <v-icon color="primary" class="mr-1">mdi-file-eye-outline</v-icon>
          <span class="text-subtitle-1 text-truncate" style="max-width: 220px">{{ apercu.titre }}</span>
          <v-spacer />
          <template v-if="apercu.estImage">
            <v-btn icon="mdi-rotate-left" variant="text" size="small" title="Pivoter à gauche" @click="pivoter(-1)" />
            <v-btn icon="mdi-rotate-right" variant="text" size="small" title="Pivoter à droite" @click="pivoter(1)" />
            <v-btn icon="mdi-magnify-minus-outline" variant="text" size="small" title="Dézoomer" @click="zoomer(-0.25)" />
            <span class="text-caption" style="min-width: 38px; text-align:center">{{ Math.round(zoom * 100) }}%</span>
            <v-btn icon="mdi-magnify-plus-outline" variant="text" size="small" title="Zoomer" @click="zoomer(0.25)" />
            <v-btn icon="mdi-backup-restore" variant="text" size="small" title="Réinitialiser" @click="reinitVue" />
            <v-divider vertical class="mx-1" />
          </template>
          <v-btn icon="mdi-download" variant="text" size="small" title="Télécharger" :href="apercu.urlDl" />
          <v-btn icon="mdi-open-in-new" variant="text" size="small" title="Ouvrir dans un onglet" :href="apercu.url" target="_blank" />
          <v-btn icon="mdi-close" variant="text" size="small" @click="apercu.show = false" />
        </v-card-title>
        <v-divider />
        <v-card-text class="pa-0">
          <div v-if="apercu.estImage" class="apercu-img-zone">
            <img :src="apercu.url" :style="styleImage" class="apercu-img" alt="aperçu" />
          </div>
          <iframe v-else-if="apercu.url" :src="apercu.url" title="Aperçu" class="apercu-frame" />
        </v-card-text>
      </v-card>
    </v-dialog>

    <!-- Confirmation envoi en masse -->
    <v-dialog v-model="dialogEnvoi" max-width="480">
      <v-card rounded="lg">
        <v-card-title class="d-flex align-center ga-2 pa-4">
          <v-icon color="error">mdi-email-alert-outline</v-icon>
          <span class="text-h6">Envoyer les e-mails ?</span>
        </v-card-title>
        <v-divider />
        <v-card-text class="pa-4">
          Vous allez envoyer <strong>{{ etatEnvoi.restants }}</strong> e-mail(s) de résultat
          (admis / non retenu) aux candidats. <strong>Cette action est irréversible.</strong>
          Assurez-vous d'avoir fait un <strong>test</strong> au préalable.
        </v-card-text>
        <v-divider />
        <v-card-actions class="pa-3">
          <v-spacer />
          <v-btn variant="text" @click="dialogEnvoi = false">Annuler</v-btn>
          <v-btn color="error" variant="flat" prepend-icon="mdi-send" @click="envoyerTout">
            Oui, envoyer à tous
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-snackbar v-model="snack.show" :color="snack.color" timeout="3000">{{ snack.text }}</v-snackbar>
  </div>
</template>

<style scoped>
.tableau-admin :deep(thead th) { background: #f4f5f9; font-weight: 700 !important; color: #1a237e !important; text-transform: uppercase; font-size: 0.75rem; letter-spacing: 0.03em; }
.onglets-barre { overflow: hidden; }
.onglets-barre :deep(.v-tab) { letter-spacing: 0.01em; }
.onglets-barre :deep(.v-tab--selected) { background: #f5f6fb; }
.apercu-frame { width: 100%; height: 72vh; border: 0; }
.apercu-img-zone { height: 72vh; display: flex; align-items: center; justify-content: center; overflow: auto; background: #2b2b33; padding: 12px; }
.apercu-img { max-width: 100%; max-height: 100%; object-fit: contain; transition: transform 0.2s ease; box-shadow: 0 4px 24px rgba(0,0,0,0.35); background: #fff; }
</style>
