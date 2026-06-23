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
const MSG_DEFINITIF_DEFAUT = "La liste définitive des candidats retenus sera publiée le jeudi 24 juin 2026. "
  + "Les candidats résidant en dehors de Kinshasa pourront préciser la ville dans laquelle ils souhaitent passer l'examen."
const messageActif = computed(() => modeDefinitif.value
  ? (_msg('message_retenus_definitif') || MSG_DEFINITIF_DEFAUT)
  : _msg('message_retenus'))
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
  const w = window.open('', '_blank', 'width=760,height=540')
  if (!w) return
  w.document.write(`<!doctype html><html lang="fr"><head><meta charset="utf-8">
    <title>Badge ${e.code} — ${nom}</title>
    <style>
      *{box-sizing:border-box} body{font-family:Arial,Helvetica,sans-serif;margin:0;padding:24px;color:#1b1b21}
      .badge{max-width:620px;margin:0 auto;border:2px solid #1a237e;border-radius:16px;overflow:hidden}
      .tete{background:#1a237e;color:#fff;padding:16px 22px;display:flex;justify-content:space-between;align-items:center}
      .tete .org{font-size:1.3rem;font-weight:800;letter-spacing:.5px}
      .tete .sous{font-size:.78rem;opacity:.9}
      .corps{padding:22px}
      .code{font-size:2.6rem;font-weight:800;color:#1a237e;letter-spacing:2px}
      .code-lbl{font-size:.7rem;text-transform:uppercase;letter-spacing:.08em;color:#6b7280}
      .ligne{margin-top:14px} .k{font-size:.72rem;text-transform:uppercase;letter-spacing:.05em;color:#6b7280}
      .v{font-size:1.15rem;font-weight:700;text-transform:uppercase}
      .vd{font-size:1rem;color:#374151}
      .sign{margin-top:30px;display:flex;justify-content:space-between;gap:24px}
      .sign div{flex:1;border-top:1px solid #9ca3af;padding-top:6px;font-size:.75rem;color:#6b7280;text-align:center}
      .note{margin-top:18px;font-size:.72rem;color:#6b7280;border-top:1px dashed #d1d5db;padding-top:10px}
      @media print{body{padding:0}}
    </style></head><body>
    <div class="badge">
      <div class="tete"><div><div class="org">ACGT</div><div class="sous">Agence Congolaise des Grands Travaux</div></div>
        <div style="text-align:right"><div class="sous">Badge d'accès au test</div></div></div>
      <div class="corps">
        <div class="code-lbl">Code candidat</div><div class="code">${e.code}</div>
        <div class="ligne"><div class="k">Nom complet</div><div class="v">${nom}</div></div>
        <div class="ligne"><div class="k">Domaine</div><div class="vd">${e.poste_libelle || '—'}</div></div>
        <div class="sign"><div>Signature du candidat</div><div>Visa ACGT</div></div>
        <div class="note">À imprimer, signer et présenter le jour du test avec une pièce d'identité.</div>
      </div>
    </div>
    <script>window.onload=function(){window.print()}<\/script>
    </body></html>`)
  w.document.close()
}

onMounted(async () => {
  const { data } = await api.get('/appels/')
  // Appels visibles publiquement : liste provisoire OU définitive publiée.
  appels.value = data.results.filter((a) => a.liste_retenus_publiee || a.liste_definitive_publiee)
  charger()
})
</script>

<template>
  <div>
    <!-- HERO -->
    <section class="hero">
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
        <h1 class="hero-titre">Candidats retenus</h1>
        <p v-if="modeDefinitif" class="hero-sous">
          <strong>Liste définitive</strong> des candidats retenus.
          Chaque candidat dispose d'un <mark class="surbrillance-claire">code unique</mark> ;
          imprimez votre <strong>badge d'accès</strong> et présentez-le, signé, le jour du test.
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
      <div v-if="messageActif" class="communique">
        <div class="comm-entete">
          <span class="comm-icone">📢</span>
          <span>Communiqué</span>
        </div>
        <p class="comm-texte">{{ messageActif }}</p>
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
                <th class="num">#</th><th>NOM</th><th>POSTNOM</th><th>PRÉNOM</th><th>DOMAINE</th>
                <th v-if="modeDefinitif" class="badge-col">BADGE</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(e, i) in items" :key="e.id" :class="{ zebra: i % 2 }">
                <td v-if="modeDefinitif" class="code-cell">{{ e.code }}</td>
                <td class="num">{{ debut + i }}</td>
                <td class="nom-cell">{{ aff(e.nom) }}</td>
                <td class="nom-cell">{{ aff(e.postnom) }}</td>
                <td class="nom-cell">{{ aff(e.prenom) }}</td>
                <td class="muted">{{ e.poste_libelle || '—' }}</td>
                <td v-if="modeDefinitif" class="badge-col">
                  <button class="btn-badge" @click="imprimerBadge(e)">🖨️ Badge</button>
                </td>
              </tr>
              <tr v-if="!loading && !items.length">
                <td :colspan="modeDefinitif ? 7 : 5" class="vide">Aucune liste de retenus publiée pour le moment.</td>
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
  </div>
</template>

<style scoped>
.hero { background: linear-gradient(135deg, #1a237e 0%, #0d1b2a 100%); position: relative; overflow: hidden; padding: 56px 24px 64px; }
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
.comm-texte { white-space: pre-line; color: #1f2933; line-height: 1.6; margin: 0; }
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
.btn-badge { background: #1a237e; color: #fff; border: none; border-radius: 9999px; padding: 7px 14px;
  font-size: 0.82rem; font-weight: 700; cursor: pointer; white-space: nowrap; transition: background 0.15s; }
.btn-badge:hover { background: #283593; }
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
