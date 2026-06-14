<script setup>
import { ref, computed, onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import api from '../../api'
import { useAppelsStore } from '../../stores/appels'

const appels = useAppelsStore()

const items = ref([])
const total = ref(0)
const loading = ref(false)
const q = ref('')
const page = ref(1)
const PAR_PAGE = 10

// État des candidatures : ouvertes seulement si au moins un appel est publié.
// Tant que ce n'est pas connu (null), on n'affiche ni la liste ni le message
// de clôture (évite le clignotement).
const candidaturesOuvertes = computed(() => (appels.charge ? appels.ouvertes : null))
const dernierAppel = computed(() => appels.dernierAppel)

async function charger() {
  loading.value = true
  try {
    const { data } = await api.get('/eligibilite/', { params: { q: q.value, page: page.value } })
    items.value = data.results
    total.value = data.count
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  await appels.charger()
  // La liste des éligibles n'est consultable que pendant les candidatures.
  if (appels.ouvertes) charger()
})

let minuteur
function rechercher() {
  clearTimeout(minuteur)
  minuteur = setTimeout(() => { page.value = 1; charger() }, 350)
}

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

// Calendrier du processus (campagne en cours).
const CALENDRIER = [
  { label: 'Date limite de soumission', date: '14 juin 2026 à 12h00 (TU+1)', icon: 'mdi-clock-alert-outline', fort: true },
  { label: 'Publication de la liste provisoire', date: '18 juin 2026', icon: 'mdi-format-list-checks' },
  { label: 'Délai de recours', date: 'Du 18 au 20 juin 2026', icon: 'mdi-gavel' },
  { label: 'Liste définitive des retenus (concours d\'embauche)', date: '24 juin 2026', icon: 'mdi-trophy-outline' },
]
</script>

<template>
  <div>
    <!-- HERO centré -->
    <section class="hero">
      <!-- Motif : lignes courbes en fond -->
      <svg class="hero-courbes" viewBox="0 0 1440 420" preserveAspectRatio="none" aria-hidden="true">
        <defs>
          <linearGradient id="lg" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0" stop-color="#ffffff" stop-opacity="0.16" />
            <stop offset="1" stop-color="#FDD835" stop-opacity="0.14" />
          </linearGradient>
        </defs>
        <g fill="none" stroke="url(#lg)" stroke-width="1">
          <path d="M-50,410 C360,430 720,360 1080,395 C1300,415 1420,365 1500,395" />
          <path d="M-50,392 C360,414 720,344 1080,380 C1300,402 1420,350 1500,380" />
          <path d="M-50,374 C360,398 720,330 1080,366 C1300,388 1420,336 1500,366" />
          <path d="M-50,356 C360,382 720,316 1080,352 C1300,374 1420,322 1500,352" />
        </g>
        <circle cx="180" cy="400" r="80" fill="#FDD835" opacity="0.04" />
      </svg>
      <div class="hero-inner">
        <h1 class="hero-titre">Candidats éligibles</h1>
        <!-- Candidatures ouvertes : consigne de dépôt -->
        <p v-if="candidaturesOuvertes" class="hero-sous">
          Consultez la liste officielle des personnes autorisées à postuler
          <mark class="surbrillance-profils">(Ingénieur civil, Ingénieur électromécanicien, Ingénieur BTP,
          Ingénieur géomètre-topographe, Architecte, Urbaniste, Environnementaliste)</mark>.
          <strong>Seuls les candidats dont les noms apparaissent sur la liste publiée sont autorisés à soumettre leur dossier
          <mark class="surbrillance">au plus tard le 14 juin 2026 à 12h00 (TU+1)</mark>.</strong>
        </p>
        <!-- Candidatures clôturées : on affiche le dernier appel + son état -->
        <p v-else-if="candidaturesOuvertes === false" class="hero-sous">
          <template v-if="dernierAppel">
            Dernier appel à candidature :
            <mark class="surbrillance-profils">{{ dernierAppel.titre }}</mark>.
          </template>
          <strong>La période de dépôt des candidatures est
          <mark class="surbrillance">clôturée</mark>.</strong>
          La liste des éligibles n'est plus consultable. Consultez les candidats retenus
          dès la publication des résultats.
        </p>
        <div class="hero-actions">
          <RouterLink v-if="candidaturesOuvertes" :to="{ name: 'mes-dossiers' }" class="hero-cta">
            POSTULER EN LIGNE <span class="fleche">→</span>
          </RouterLink>
          <div v-else-if="candidaturesOuvertes === false" class="hero-cloture">
            <span class="hero-cloture-ic">🔒</span> Les candidatures sont clôturées
          </div>
          <RouterLink v-if="candidaturesOuvertes" :to="{ name: 'guide' }" class="hero-guide">
            <span class="hero-guide-ic">📖</span> Besoin d'aide ? Voir le guide « Comment postuler ? »
          </RouterLink>
        </div>
      </div>
    </section>

    <div class="wrap">
      <!-- Candidatures ouvertes : liste consultable + recherche. À la clôture,
           rien ici : le hero porte déjà le message (la liste disparaît). -->
      <template v-if="candidaturesOuvertes">
      <!-- Carte recherche flottante -->
      <div class="recherche">
        <div class="rech-input">
          <span class="loupe">🔍</span>
          <input v-model="q" @input="rechercher" type="text" placeholder="Rechercher votre nom…" />
        </div>
        <span class="pastille"><strong>{{ total }}</strong> personnes éligibles</span>
      </div>

      <!-- Tableau -->
      <h2 class="liste-titre">Liste des candidats éligibles</h2>
      <div class="tableau-carte">
        <div class="tableau-scroll">
          <table class="tableau">
            <thead>
              <tr>
                <th>CODE</th><th>NOM</th><th>POSTNOM</th><th>PRÉNOM</th><th class="ar"></th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(e, i) in items" :key="e.id" :class="{ zebra: i % 2 }">
                <td class="code">{{ e.code || '—' }}</td>
                <td class="nom">{{ e.nom }}</td>
                <td class="muted">{{ e.postnom }}</td>
                <td class="muted">{{ e.prenom }}</td>
                <td class="ar">
                  <RouterLink :to="{ name: 'postuler', query: { code: e.code, nom: e.nom, postnom: e.postnom, prenom: e.prenom } }"
                              class="btn-postuler">Postuler</RouterLink>
                </td>
              </tr>
              <tr v-if="!loading && !items.length">
                <td colspan="5" class="vide">
                  Aucune personne ne correspond à cette recherche.
                  <strong class="vide-aide">
                    Essayez votre nom de famille seul, ou votre postnom, ou votre prénom. <br/>
                    Si vous ne vous trouvez toujours pas et que vous avez déposé un dossier ou vous avez effectué un stage à l'ACGT, vous pouvez faire une réclamation en joignant
                    votre accusé de réception ou la lettre de stage.
                  </strong>
                  <RouterLink :to="{ name: 'reclamation' }" class="vide-btn">Faire une réclamation</RouterLink>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <!-- Pagination -->
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

      <!-- Calendrier du processus -->
      <section class="calendrier">
        <h2 class="cal-titre">Calendrier du processus</h2>
        <div class="cal-grid">
          <div v-for="(e, i) in CALENDRIER" :key="i" class="cal-item" :class="{ fort: e.fort }">
            <v-icon :icon="e.icon" size="26" class="cal-ic" />
            <div class="cal-label">{{ e.label }}</div>
            <div class="cal-date">{{ e.date }}</div>
          </div>
        </div>
      </section>
      </template>

    </div>
  </div>
</template>

<style scoped>
/* Bandeau de clôture (hero) */
.hero-cloture { display: inline-flex; align-items: center; gap: 10px; padding: 12px 26px;
  border-radius: 9999px; background: rgba(229,57,53,0.18); border: 1px solid rgba(255,255,255,0.35);
  color: #fff; font-size: 1rem; font-weight: 800; letter-spacing: 0.02em; }
.hero-cloture-ic { font-size: 1.1rem; }

/* HERO centré */
.hero { background: linear-gradient(135deg, #1a237e 0%, #0d1b2a 100%); position: relative; overflow: hidden; padding: 56px 24px 64px; }
.hero-courbes { position: absolute; inset: 0; width: 100%; height: 100%; z-index: 0; }
.hero-inner { position: relative; z-index: 1; max-width: 760px; margin: 0 auto; text-align: center; }
.hero-titre { color: #fff; font-size: clamp(2.2rem, 5vw, 3.4rem); font-weight: 800; letter-spacing: -0.5px; line-height: 1.05; }
.hero-sous { color: #fff; opacity: 0.9; font-size: 1.05rem; line-height: 1.6; max-width: 660px; margin: 16px auto 24px; }
.surbrillance { background: #E53935; color: #fff; padding: 1px 8px; border-radius: 6px; font-weight: 800; box-decoration-break: clone; -webkit-box-decoration-break: clone; }
.surbrillance-profils { background: #fff; color: #1a237e; padding: 1px 7px; border-radius: 6px; font-weight: 700; box-decoration-break: clone; -webkit-box-decoration-break: clone; }
.hero-actions { display: flex; flex-direction: column; align-items: center; gap: 14px; }
.hero-guide { display: inline-flex; align-items: center; gap: 8px; padding: 9px 20px;
  border-radius: 9999px; background: rgba(255,255,255,0.10); border: 1px solid rgba(255,255,255,0.30);
  color: #fff; font-size: 0.9rem; font-weight: 600; text-decoration: none; transition: background 0.2s, border-color 0.2s; }
.hero-guide:hover { background: rgba(253,216,53,0.18); border-color: #FDD835; }
.hero-guide-ic { font-size: 1.05rem; }
.hero-cta { display: inline-flex; align-items: center; gap: 8px; background: #FDD835; color: #1a237e;
  padding: 15px 34px; border-radius: 12px; font-weight: 700; text-decoration: none; transition: all 0.2s; }
.hero-cta:hover { box-shadow: 0 10px 24px rgba(0,0,0,0.25); transform: translateY(-1px); }
.fleche { font-size: 1.1rem; }

/* WRAP */
.wrap { max-width: 1200px; margin: 0 auto; padding: 0 24px 48px; }

/* Recherche flottante */
.recherche { background: #fff; border: 2px solid #29b6f6; border-radius: 18px; box-shadow: 0 12px 30px rgba(41,182,246,0.15);
  margin-top: -40px; position: relative; z-index: 10; padding: 22px; display: flex; gap: 16px; align-items: center; justify-content: space-between; flex-wrap: wrap; }
.rech-input { position: relative; flex: 1; min-width: 240px; }
.rech-input .loupe { position: absolute; left: 14px; top: 50%; transform: translateY(-50%); opacity: 0.5; }
.rech-input input { width: 100%; padding: 12px 16px 12px 42px; border: 1px solid #c6c5d4; border-radius: 12px; outline: none; font-size: 0.95rem; transition: border-color 0.2s; }
.rech-input input:focus { border-color: #1a237e; box-shadow: 0 0 0 1px #1a237e; }
.pastille { background: #d3e1f6; color: #566475; padding: 8px 18px; border-radius: 9999px; font-size: 0.9rem; }

/* Tableau */
.liste-titre { color: #1a237e; font-size: 1.4rem; font-weight: 700; margin: 28px 0 12px; }
.tableau-carte { background: #fff; border: 2px solid #29b6f6; border-radius: 18px; overflow: hidden; margin-top: 24px; box-shadow: 0 6px 20px rgba(41,182,246,0.12); }
.tableau-scroll { overflow-x: auto; }
.tableau { width: 100%; border-collapse: collapse; }
.tableau th { background: #eae7ef; text-align: left; padding: 16px 24px; font-size: 0.9rem; font-weight: 700; color: #1a237e; }
.tableau td { padding: 16px 24px; border-top: 1px solid #e4e1ea; font-size: 0.95rem; }
.tableau tbody tr { transition: background 0.15s; }
.tableau tbody tr:hover { background: #f5f2fb; }
.tableau tr.zebra { background: #fcfbff; }
.num { width: 64px; color: #767683; font-weight: 600; }
.code { font-weight: 700; color: #1a237e; white-space: nowrap; }
.nom { font-weight: 600; color: #1b1b21; }
.muted { color: #525f71; }
.ar { text-align: right; }
.btn-postuler { display: inline-flex; align-items: center; background: #FDD835; color: #1a237e; padding: 7px 18px; border-radius: 9999px; font-size: 0.8rem; font-weight: 700; text-decoration: none; transition: background 0.15s, box-shadow 0.15s; }
.btn-postuler:hover { background: #fbc02d; box-shadow: 0 4px 12px rgba(253,216,53,0.5); }
.vide { text-align: center; color: #767683; padding: 32px; }
.vide-aide { display: block; max-width: 920px; margin: 8px auto 0; color: #1a237e; font-weight: 700; }
.vide-btn { display: inline-block; margin-top: 16px; background: #1a237e; color: #fff; padding: 11px 24px; border-radius: 12px; font-weight: 700; text-decoration: none; transition: box-shadow 0.2s, background 0.2s; }
.vide-btn:hover { background: #283593; box-shadow: 0 8px 20px rgba(26,35,126,0.3); }

/* Pagination */
.pagination { display: flex; align-items: center; justify-content: space-between; padding: 16px 24px; background: #f5f2fb; border-top: 1px solid #e4e1ea; flex-wrap: wrap; gap: 12px; }
.affichage { font-size: 0.85rem; color: #525f71; }
.pages { display: flex; align-items: center; gap: 8px; }
.rond { width: 40px; height: 40px; border-radius: 9999px; border: 1px solid #c6c5d4; background: #fff; cursor: pointer; font-size: 0.9rem; color: #1b1b21; transition: background 0.15s; }
.rond:hover:not(:disabled):not(.courant) { background: #eae7ef; }
.rond.courant { background: #1a237e; color: #fff; border-color: #1a237e; font-weight: 700; }
.rond.ellipse { border: none; background: none; cursor: default; }
.rond:disabled { opacity: 0.3; cursor: not-allowed; }

/* Calendrier du processus */
.calendrier { padding: 48px 0 8px; }
.cal-titre { text-align: center; color: #1a237e; font-size: 1.5rem; font-weight: 700; margin-bottom: 24px; }
.cal-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; }
@media (max-width: 900px) { .cal-grid { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 540px) { .cal-grid { grid-template-columns: 1fr; } }
.cal-item { background: #fff; border: 1px solid #e2e6ea; border-top: 4px solid #1a237e; border-radius: 14px; padding: 20px 18px; text-align: center; transition: box-shadow 0.2s, transform 0.2s; }
.cal-item:hover { box-shadow: 0 8px 22px rgba(26,35,126,0.10); transform: translateY(-2px); }
.cal-item.fort { border-top-color: #D32F2F; background: #fff7f7; }
.cal-ic { color: #1a237e; margin-bottom: 8px; }
.cal-item.fort .cal-ic { color: #D32F2F; }
.cal-label { font-size: 0.82rem; color: #525f71; line-height: 1.3; min-height: 34px; }
.cal-date { font-size: 1rem; font-weight: 800; color: #1b1b21; margin-top: 8px; }
.cal-item.fort .cal-date { color: #D32F2F; }
</style>
