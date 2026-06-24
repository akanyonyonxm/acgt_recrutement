<script setup>
import { ref, computed, onMounted } from 'vue'
import api from '../../api'

const appels = ref([])
const appelId = ref('')

const appelCourant = computed(() => appels.value.find((x) => x.id === appelId.value))

// Mode DÉFINITIF : si l'appel sélectionné (ou, en « Tous », au moins un appel) a
// publié sa liste définitive → on affiche la définitive (codes) à la place de la
// provisoire (« la définitive remplace la provisoire »).
const modeDefinitif = computed(() => appelId.value
  ? !!appelCourant.value?.liste_definitive_publiee
  : appels.value.some((a) => a.liste_definitive_publiee))

// Communiqué : message définitif si on est en mode définitif, sinon le message
// de la liste provisoire. Celui de l'appel sélectionné, sinon le premier qui en a un.
function _msg(champ) {
  if (appelId.value) return (appelCourant.value?.[champ] || '').trim()
  return (appels.value.find((x) => (x[champ] || '').trim())?.[champ] || '').trim()
}
const MSG_DEFINITIF_DEFAUT = "Le test de sélection pour le recrutement est prévu le **dimanche 28 juin 2026 à 07h00 (TU+1)** "
  + "à **Kinshasa**, à **l'Institut de la Gombe** (en diagonal du Palais de Justice). Toutefois, les candidats "
  + "souhaitant passer le test dans un autre site en dehors de Kinshasa sont invités **à sélectionner** "
  + "**Lubumbashi** ou **Mbuji-Mayi** sur le portail au plus tard le **jeudi 25 juin 2026 à 12h00 (TU+1)**."
const messageActif = computed(() => modeDefinitif.value
  ? (_msg('message_retenus_definitif') || MSG_DEFINITIF_DEFAUT)
  : _msg('message_retenus'))

// Instructions du test (bouton « Instructions ») : texte réglable en console, sinon défaut officiel.
const INSTRUCTIONS_DEFAUT = "Les candidats retenus sont priés de respecter les instructions ci-après :\n\n"
  + "1. L'accès aux sites est conditionné par la présentation :\n"
  + "   • d'une **pièce d'identité valide** ;\n"
  + "   • du **badge d'accès** généré en ligne sur https://recrutement.acgt.cd/retenus et **à imprimer**.\n"
  + "2. **Aucun retard ne sera toléré.**\n"
  + "3. Le port du téléphone ou de tout objet connecté est **strictement interdit**.\n"
  + "4. En dehors des fournitures de bureau disponibles au lieu du test, aucun autre objet ne sera autorisé (papier, stylo, crayon, etc.).\n"
  + "5. L'examen est individuel : **aucune collaboration ne sera tolérée**.\n"
  + "6. Le port d'une tenue décente est de rigueur.\n"
  + "7. Le non-respect du local d'affectation **vaut disqualification**.\n\n"
  + "**Note :** Les lieux précis du test à Lubumbashi et Mbuji-Mayi seront communiqués le **vendredi 26 juin 2026** sur le portail de recrutement ACGT."
const instructionsActif = computed(() => _msg('instructions_examen') || INSTRUCTIONS_DEFAUT)
const showInstructions = ref(false)

// Message d'état vide, contextuel : recherche sans résultat vs aucune liste publiée.
const messageVide = computed(() => {
  if (q.value.trim()) {
    return `Aucune personne trouvée pour « ${q.value.trim()} » dans la liste ${modeDefinitif.value ? 'définitive' : 'des retenus'}. Vérifiez l'orthographe.`
  }
  return modeDefinitif.value
    ? 'Aucun candidat dans la liste définitive pour le moment.'
    : 'Aucune liste de retenus publiée pour le moment.'
})

// Mise en forme légère et sûre : on échappe le HTML, puis on autorise le gras
// (**texte**) et une surbrillance (==texte==). Fonctionne pour le texte par
// défaut comme pour celui saisi dans la console (réglable sans toucher au code).
function enrichir(txt) {
  const html = (txt || '')
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/==(.+?)==/g, '<mark class="surb-comm">$1</mark>')
    .replace(/\n/g, '<br>')
  return html
}
const items = ref([])
const total = ref(0)
const loading = ref(false)
const q = ref('')
const page = ref(1)
const PAR_PAGE = 10

async function charger() {
  loading.value = true
  try {
    const params = { q: q.value, page: page.value }
    if (appelId.value) params.appel = appelId.value
    const url = modeDefinitif.value ? '/retenus-definitifs/' : '/retenus/'
    const { data } = await api.get(url, { params })
    items.value = data.results
    total.value = data.count
  } finally {
    loading.value = false
  }
}

let minuteur
function rechercher() {
  clearTimeout(minuteur)
  minuteur = setTimeout(() => { page.value = 1; charger() }, 350)
}
function changerAppel() { page.value = 1; charger() }

// Normalise les caractères Unicode « stylisés » (lettres mathématiques, pleine
// largeur, ligatures…) en lettres normales pour un affichage homogène.
// Ex. « 𝐅𝐥𝐨𝐫𝐲 » → « Flory ». N'altère pas les accents.
const aff = (v) => (v || '').normalize('NFKC')

const nbPages = computed(() => Math.max(1, Math.ceil(total.value / PAR_PAGE)))
const debut = computed(() => (total.value === 0 ? 0 : (page.value - 1) * PAR_PAGE + 1))
const fin = computed(() => Math.min(page.value * PAR_PAGE, total.value))
const pages = computed(() => {
  const n = nbPages.value, c = page.value, out = []
  out.push(1)
  if (c > 3) out.push('…')
  for (let p = c - 1; p <= c + 1; p++) if (p > 1 && p < n) out.push(p)
  if (c < n - 2) out.push('…')
  if (n > 1) out.push(n)
  return out
})
function aller(p) {
  if (p === '…' || p < 1 || p > nbPages.value || p === page.value) return
  page.value = p
  charger()
}

// Impression d'un badge d'accès au test (code + nom complet + domaine + zone à
// signer), à présenter le jour de l'examen. Ouvre une fenêtre prête à imprimer.
function imprimerBadge(e) {
  const nom = `${aff(e.nom)} ${aff(e.postnom)} ${aff(e.prenom)}`.replace(/\s+/g, ' ').trim()
  const w = window.open('', '_blank', 'width=940,height=760')
  if (!w) return
  w.document.write(`<!doctype html><html lang="fr"><head><meta charset="utf-8">
    <title>Badge ${e.code} — ${nom}</title>
    <style>
      *{box-sizing:border-box} body{font-family:Arial,Helvetica,sans-serif;margin:0;padding:32px;color:#1b1b21}
      .badge{max-width:820px;margin:0 auto;border:3px solid #1a237e;border-radius:20px;overflow:hidden}
      .tete{background:#1a237e;color:#fff;padding:24px 32px;display:flex;justify-content:space-between;align-items:center}
      .tete .org{font-size:2rem;font-weight:800;letter-spacing:.5px}
      .tete .sous{font-size:1rem;opacity:.92}
      .corps{padding:34px 36px 30px}
      .code{font-size:4.4rem;font-weight:800;color:#1a237e;letter-spacing:4px;line-height:1}
      .code-lbl{font-size:.95rem;text-transform:uppercase;letter-spacing:.08em;color:#6b7280}
      .ligne{margin-top:24px} .k{font-size:.95rem;text-transform:uppercase;letter-spacing:.05em;color:#6b7280}
      .v{font-size:2.1rem;font-weight:800;text-transform:uppercase;margin-top:2px}
      .vd{font-size:1.6rem;color:#374151;margin-top:2px}
      .sign{margin-top:56px}
      .sign div{width:60%;border-top:1px solid #9ca3af;padding-top:8px;font-size:1rem;color:#6b7280;text-align:center}
      .note{margin-top:28px;font-size:.92rem;color:#6b7280;border-top:1px dashed #d1d5db;padding-top:14px}
      .toolbar{max-width:820px;margin:0 auto 16px;display:flex;gap:10px;justify-content:flex-end}
      .toolbar button{border:none;border-radius:9999px;padding:9px 18px;font-size:.9rem;font-weight:700;cursor:pointer}
      .b-print{background:#1a237e;color:#fff} .b-pdf{background:#2E7D32;color:#fff} .b-close{background:#e5e7eb;color:#374151}
      @page{size:A4;margin:14mm}
      @media print{body{padding:0} .toolbar{display:none} .badge{max-width:100%;border-width:2px}}
    </style></head><body>
    <div class="toolbar">
      <button class="b-print" onclick="window.print()">🖨️ Imprimer</button>
      <button class="b-pdf" onclick="window.print()" title="Choisissez « Enregistrer au format PDF » comme destination">⬇ Télécharger PDF</button>
      <button class="b-close" onclick="window.close()">Fermer</button>
    </div>
    <div class="badge">
      <div class="tete"><div><div class="org">ACGT</div><div class="sous">Agence Congolaise des Grands Travaux</div></div>
        <div style="text-align:right"><div class="sous">Badge d'accès au test</div></div></div>
      <div class="corps">
        <div class="code-lbl">Code candidat</div><div class="code">${e.code}</div>
        <div class="ligne"><div class="k">Nom complet</div><div class="v">${nom}</div></div>
        <div class="ligne"><div class="k">Domaine</div><div class="vd">${e.poste_libelle || '—'}</div></div>
        <div class="sign"><div>Signature du candidat</div></div>
        <div class="note">À imprimer, signer et présenter le jour du test avec une pièce d'identité.</div>
      </div>
    </div>
    </body></html>`)
  w.document.close()
}

// `pret` : on ne rend la page qu'une fois les appels chargés, pour connaître
// d'emblée le mode (provisoire / définitive) et éviter le flash de transition
// du titre et de la couleur du hero.
const pret = ref(false)
onMounted(async () => {
  try {
    const { data } = await api.get('/appels/')
    // Appels visibles publiquement : liste provisoire OU définitive publiée.
    appels.value = data.results.filter((a) => a.liste_retenus_publiee || a.liste_definitive_publiee)
  } finally {
    pret.value = true
  }
  charger()
})
</script>

<template>
  <div>
    <!-- Attente du chargement des appels : évite le flash de bascule du hero -->
    <div v-if="!pret" class="chargement-page">
      <div class="spinner" />
    </div>

    <template v-else>
    <!-- HERO -->
    <section class="hero" :class="{ 'hero--def': modeDefinitif }">
      <svg class="hero-courbes" viewBox="0 0 1440 420" preserveAspectRatio="none" aria-hidden="true">
        <defs>
          <linearGradient id="lgr" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0" stop-color="#ffffff" stop-opacity="0.16" />
            <stop offset="1" stop-color="#FDD835" stop-opacity="0.14" />
          </linearGradient>
        </defs>
        <g fill="none" stroke="url(#lgr)" stroke-width="1">
          <path d="M-50,410 C360,430 720,360 1080,395 C1300,415 1420,365 1500,395" />
          <path d="M-50,392 C360,414 720,344 1080,380 C1300,402 1420,350 1500,380" />
          <path d="M-50,374 C360,398 720,330 1080,366 C1300,388 1420,336 1500,366" />
        </g>
        <circle cx="180" cy="400" r="80" fill="#FDD835" opacity="0.04" />
      </svg>
      <div class="hero-inner">
        <h1 class="hero-titre">{{ modeDefinitif ? 'Candidats admis au test' : 'Candidats retenus' }}</h1>
        <p v-if="modeDefinitif" class="hero-sous">
          <strong>Liste définitive</strong> des candidats retenus.
          Chaque candidat dispose d'un <mark class="surbrillance-claire">code unique</mark> ;
          imprimez votre <strong>badge d'accès</strong> et présentez-le, signé, le jour du test,
          accompagné de votre <strong>carte d'identité valide</strong>.
          Prière de lire les <a class="lien-instructions" @click="showInstructions = true">instructions</a>.
        </p>
        <p v-else class="hero-sous">
          Liste provisoire des candidats présélectionnés.
          Les candidats dont le nom n'apparaît pas et qui estiment remplir les critères requis
          (<i>âge maximum de 40 ans, niveau minimum requis de BAC&nbsp;+5, soumission des dossiers dans la période requise, domaines de métier publiés</i>)
          peuvent <strong>introduire leur recours <mark class="surbrillance">au plus tard le samedi 20 juin 2026 à 23h00</mark></strong>.
        </p>
      </div>
    </section>

    <div class="wrap">
      <!-- Communiqué officiel (éditable dans la console : champ « message public ») -->
      <div v-if="messageActif" class="communique" :class="{ 'communique--def': modeDefinitif }">
        <div class="comm-entete">
          <span class="comm-icone">📢</span>
          <span>Communiqué</span>
        </div>
        <p class="comm-texte" v-html="enrichir(messageActif)"></p>
      </div>

      <!-- Actions (liste définitive) : juste sous le message -->
      <div v-if="modeDefinitif" class="actions-def">
        <button class="btn-act btn-act-clair" @click="showInstructions = true">📋 Instructions du test</button>
        <RouterLink :to="{ name: 'ville-examen' }" class="btn-act btn-act-vert">📍 Préciser ma ville d'examen</RouterLink>
      </div>

      <!-- Recherche flottante -->
      <div class="recherche" :class="{ 'rech-mt': messageActif }">
        <div class="rech-input">
          <span class="loupe">🔍</span>
          <input v-model="q" @input="rechercher" type="text" placeholder="Rechercher un nom…" />
        </div>
        <select class="rech-select" v-model="appelId" @change="changerAppel">
          <option value="">Tous les appels</option>
          <option v-for="a in appels" :key="a.id" :value="a.id">{{ a.titre }}</option>
        </select>
        <span class="pastille"><strong>{{ total }}</strong> retenu(s)</span>
      </div>

      <!-- Tableau -->
      <div class="tableau-carte">
        <div class="tableau-scroll">
          <table class="tableau">
            <thead>
              <tr>
                <th v-if="modeDefinitif" class="num">CODE</th>
                <th v-else class="num">#</th>
                <th>NOM</th><th>POSTNOM</th><th>PRÉNOM</th><th>DOMAINE</th>
                <th v-if="modeDefinitif" class="badge-col">BADGE</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(e, i) in items" :key="e.id" :class="{ zebra: i % 2 }">
                <td v-if="modeDefinitif" class="code-cell" data-label="Code">{{ e.code }}</td>
                <td v-else class="num" data-label="N°">{{ debut + i }}</td>
                <td class="nom-cell" data-label="Nom">{{ aff(e.nom) }}</td>
                <td class="nom-cell" data-label="Postnom">{{ aff(e.postnom) }}</td>
                <td class="nom-cell" data-label="Prénom">{{ aff(e.prenom) }}</td>
                <td class="muted" data-label="Domaine">{{ e.poste_libelle || '—' }}</td>
                <td v-if="modeDefinitif" class="badge-col" data-label="">
                  <button class="btn-badge" @click="imprimerBadge(e)">Badge</button>
                </td>
              </tr>
              <tr v-if="!loading && !items.length">
                <td :colspan="modeDefinitif ? 6 : 5" class="vide">{{ messageVide }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div class="pagination">
          <span class="affichage">Affichage {{ debut }} à {{ fin }} sur {{ total }}</span>
          <div class="pages">
            <button class="rond" :disabled="page <= 1" @click="aller(page - 1)">‹</button>
            <button v-for="(p, idx) in pages" :key="idx" class="rond"
                    :class="{ courant: p === page, ellipse: p === '…' }"
                    :disabled="p === '…'" @click="aller(p)">{{ p }}</button>
            <button class="rond" :disabled="page >= nbPages" @click="aller(page + 1)">›</button>
          </div>
        </div>
      </div>
    </div>
    </template>

    <!-- Modal Instructions -->
    <div v-if="showInstructions" class="modal-fond" @click.self="showInstructions = false">
      <div class="modal-carte">
        <div class="modal-tete">
          <span>📋 Instructions du test</span>
          <button class="modal-x" @click="showInstructions = false">✕</button>
        </div>
        <p class="modal-texte" v-html="enrichir(instructionsActif)"></p>
        <div class="modal-pied">
          <button class="btn-act btn-act-vert" @click="showInstructions = false">J'ai compris</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.chargement-page { min-height: 60vh; display: flex; align-items: center; justify-content: center; }
.spinner { width: 42px; height: 42px; border: 4px solid #e0e3ee; border-top-color: #1a237e; border-radius: 50%; animation: tourner 0.8s linear infinite; }
@keyframes tourner { to { transform: rotate(360deg); } }
.hero { background: linear-gradient(135deg, #1a237e 0%, #0d1b2a 100%); position: relative; overflow: hidden; padding: 56px 24px 64px; }
.hero--def { background: linear-gradient(135deg, #1b5e20 0%, #0b3d1a 100%); }
.hero--def .hero-sous strong { color: #FDD835; }
.lien-instructions { color: #FDD835; font-weight: 800; text-decoration: underline; cursor: pointer; }
.lien-instructions:hover { color: #fff; }

/* Actions liste définitive */
.actions-def { display: flex; gap: 14px; flex-wrap: wrap; justify-content: center; margin-top: 28px; }
.btn-act { display: inline-flex; align-items: center; gap: 6px; padding: 13px 26px; border-radius: 9999px;
  font-weight: 700; font-size: 0.95rem; text-decoration: none; border: none; cursor: pointer; transition: all 0.2s; }
.btn-act-vert { background: #2E7D32; color: #fff; }
.btn-act-vert:hover { background: #1b5e20; box-shadow: 0 6px 16px rgba(46,125,50,0.4); }
.btn-act-clair { background: #fff; color: #1b5e20; border: 1.5px solid #2E7D32; }
.btn-act-clair:hover { background: #e9f6ec; }

/* Modal instructions */
.modal-fond { position: fixed; inset: 0; background: rgba(15,27,42,0.55); display: flex; align-items: center;
  justify-content: center; z-index: 100; padding: 20px; }
.modal-carte { background: #fff; border-radius: 18px; max-width: 560px; width: 100%; box-shadow: 0 20px 60px rgba(0,0,0,0.3); overflow: hidden; }
.modal-tete { display: flex; align-items: center; justify-content: space-between; background: #2E7D32; color: #fff; padding: 16px 22px; font-weight: 800; }
.modal-x { background: none; border: none; color: #fff; font-size: 1.2rem; cursor: pointer; }
.modal-texte { padding: 22px; color: #1f2933; line-height: 1.7; margin: 0; max-height: 70vh; overflow-y: auto; }
.modal-texte :deep(strong) { color: #14361b; font-weight: 800; }
.modal-pied { padding: 0 22px 22px; text-align: right; }
.hero-courbes { position: absolute; inset: 0; width: 100%; height: 100%; z-index: 0; }
.hero-inner { position: relative; z-index: 1; max-width: 760px; margin: 0 auto; text-align: center; }
.hero-titre { color: #fff; font-size: clamp(2.2rem, 5vw, 3.4rem); font-weight: 800; letter-spacing: -0.5px; line-height: 1.05; }
.hero-sous { color: #fff; opacity: 0.9; font-size: 1.05rem; line-height: 1.7; max-width: 780px; margin: 16px auto 0; }
.surbrillance { background: #E53935; color: #fff; padding: 1px 8px; border-radius: 6px; font-weight: 800; box-decoration-break: clone; -webkit-box-decoration-break: clone; }
.surbrillance-claire { background: #fff; color: #1a237e; padding: 1px 7px; border-radius: 6px; font-weight: 700; box-decoration-break: clone; -webkit-box-decoration-break: clone; }

.wrap { max-width: 1200px; margin: 0 auto; padding: 0 24px 48px; }

.communique { background: #fff; border: 1px solid #c6c5d4; border-left: 6px solid #1a237e; border-radius: 16px;
  padding: 18px 22px; margin-top: -40px; position: relative; z-index: 10; box-shadow: 0 12px 30px rgba(26,35,126,0.12); }
.comm-entete { display: flex; align-items: center; gap: 8px; font-weight: 800; color: #1a237e;
  text-transform: uppercase; letter-spacing: 0.04em; font-size: 0.85rem; margin-bottom: 8px; }
.comm-icone { font-size: 1.1rem; }
.comm-texte { color: #1f2933; line-height: 1.7; margin: 0; font-size: 1.02rem; }
.comm-texte :deep(strong) { color: #14361b; font-weight: 800; }
.surb-comm { background: transparent; color: #1b5e20; font-weight: 800; }
.communique--def { border-left-color: #2E7D32; box-shadow: 0 12px 30px rgba(27,94,32,0.14); }
.communique--def .comm-entete { color: #1b5e20; }
.rech-mt { margin-top: 24px !important; }

.recherche { background: #fff; border: 2px solid #29b6f6; border-radius: 18px; box-shadow: 0 12px 30px rgba(41,182,246,0.15);
  margin-top: -40px; position: relative; z-index: 10; padding: 22px; display: flex; gap: 16px; align-items: center; flex-wrap: wrap; }
.rech-input { position: relative; flex: 1; min-width: 220px; }
.rech-input .loupe { position: absolute; left: 14px; top: 50%; transform: translateY(-50%); opacity: 0.5; }
.rech-input input { width: 100%; padding: 12px 16px 12px 42px; border: 1px solid #c6c5d4; border-radius: 12px; outline: none; font-size: 0.95rem; transition: border-color 0.2s; }
.rech-input input:focus { border-color: #1a237e; box-shadow: 0 0 0 1px #1a237e; }
.rech-select { padding: 12px 16px; border: 1px solid #c6c5d4; border-radius: 12px; outline: none; font-size: 0.95rem; background: #fff; min-width: 220px; cursor: pointer; }
.rech-select:focus { border-color: #1a237e; }
.pastille { background: #e7f5ef; color: #166534; padding: 8px 18px; border-radius: 9999px; font-size: 0.9rem; }

.tableau-carte { background: #fff; border: 2px solid #29b6f6; border-radius: 18px; overflow: hidden; margin-top: 24px; box-shadow: 0 6px 20px rgba(41,182,246,0.12); }
.tableau-scroll { overflow-x: auto; }
.tableau { width: 100%; border-collapse: collapse; }
.tableau th { background: #eae7ef; text-align: left; padding: 16px 24px; font-size: 0.9rem; font-weight: 700; color: #1a237e; }
.tableau td { padding: 16px 24px; border-top: 1px solid #e4e1ea; font-size: 0.95rem; }
.tableau tbody tr:hover { background: #f5f2fb; }
.tableau tr.zebra { background: #fcfbff; }
.num { width: 64px; color: #767683; font-weight: 600; }
.nom-cell { font-weight: 600; color: #1b1b21; text-transform: uppercase; }
.code-cell { font-weight: 800; color: #1a237e; letter-spacing: 1px; white-space: nowrap; }
.badge-col { width: 120px; text-align: center; }
.btn-badge { background: #FDD835; color: #1a237e; border: none; border-radius: 9999px; padding: 7px 20px;
  font-size: 0.82rem; font-weight: 800; cursor: pointer; white-space: nowrap; transition: background 0.15s; }
.btn-badge:hover { background: #fbc02d; }

/* Mobile : le tableau devient des cartes empilées (le bouton Badge reste visible
   sans scroll horizontal). */
@media (max-width: 700px) {
  .tableau-scroll { overflow-x: visible; }
  .tableau thead { display: none; }
  .tableau tbody { display: block; }
  .tableau tr { display: block; border: 1px solid #dbe0ee; border-radius: 14px;
    margin: 0 0 14px; padding: 14px 16px; background: #fff !important; box-shadow: 0 2px 10px rgba(26,35,126,0.06); }
  .tableau td { display: block; border: none; padding: 0; }
  .tableau td.num { display: none; }
  .tableau td.code-cell { font-size: 1.4rem; margin-bottom: 4px; }
  .tableau td.code-cell::before { content: 'Code '; font-size: 0.82rem; color: #6b7280; font-weight: 600; letter-spacing: 0; }
  .tableau td.nom-cell { display: inline; font-size: 1.05rem; }
  .tableau td.nom-cell + .nom-cell { margin-left: 4px; }
  .tableau td.muted { margin-top: 8px; color: #525f71; }
  .tableau td.muted::before { content: 'Domaine : '; font-size: 0.78rem; color: #6b7280; }
  .tableau td.badge-col { margin-top: 14px; }
  .btn-badge { width: 100%; padding: 12px; font-size: 0.95rem; }
}
.muted { color: #525f71; }
.vide { text-align: center; color: #767683; padding: 32px; }

.pagination { display: flex; align-items: center; justify-content: space-between; padding: 16px 24px; background: #f5f2fb; border-top: 1px solid #e4e1ea; flex-wrap: wrap; gap: 12px; }
.affichage { font-size: 0.85rem; color: #525f71; }
.pages { display: flex; align-items: center; gap: 8px; }
.rond { width: 40px; height: 40px; border-radius: 9999px; border: 1px solid #c6c5d4; background: #fff; cursor: pointer; font-size: 0.9rem; color: #1b1b21; transition: background 0.15s; }
.rond:hover:not(:disabled):not(.courant) { background: #eae7ef; }
.rond.courant { background: #1a237e; color: #fff; border-color: #1a237e; font-weight: 700; }
.rond.ellipse { border: none; background: none; cursor: default; }
.rond:disabled { opacity: 0.3; cursor: not-allowed; }
</style>
