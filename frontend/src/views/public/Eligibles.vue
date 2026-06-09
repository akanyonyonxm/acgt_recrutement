<script setup>
import { ref, computed } from 'vue'
import { RouterLink } from 'vue-router'
import api from '../../api'

const items = ref([])
const total = ref(0)
const loading = ref(false)
const q = ref('')
const page = ref(1)
const PAR_PAGE = 10

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
charger()

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
        <p class="hero-sous">
          Consultez la liste officielle des personnes autorisées à postuler pour les
          grands chantiers de l'infrastructure nationale. Votre avenir commence ici.
        </p>
        <RouterLink :to="{ name: 'mes-dossiers' }" class="hero-cta">
          POSTULER EN LIGNE <span class="fleche">→</span>
        </RouterLink>
      </div>
    </section>

    <div class="wrap">
      <!-- Carte recherche flottante -->
      <div class="recherche">
        <div class="rech-input">
          <span class="loupe">🔍</span>
          <input v-model="q" @input="rechercher" type="text" placeholder="Rechercher votre nom…" />
        </div>
        <span class="pastille"><strong>{{ total }}</strong> personnes éligibles</span>
      </div>

      <!-- Tableau -->
      <div class="tableau-carte">
        <div class="tableau-scroll">
          <table class="tableau">
            <thead>
              <tr>
                <th class="num">#</th><th>NOM</th><th>POST-NOM</th><th>PRÉNOM</th><th>STATUT</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(e, i) in items" :key="e.id" :class="{ zebra: i % 2 }">
                <td class="num">{{ debut + i }}</td>
                <td class="nom">{{ e.nom }}</td>
                <td class="muted">{{ e.postnom }}</td>
                <td class="muted">{{ e.prenom }}</td>
                <td><span class="chip-elig">Éligible</span></td>
              </tr>
              <tr v-if="!loading && !items.length">
                <td colspan="5" class="vide">Aucune personne ne correspond à cette recherche.</td>
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

    </div>
  </div>
</template>

<style scoped>
/* HERO centré */
.hero { background: linear-gradient(135deg, #1a237e 0%, #0d1b2a 100%); position: relative; overflow: hidden; padding: 56px 24px 64px; }
.hero-courbes { position: absolute; inset: 0; width: 100%; height: 100%; z-index: 0; }
.hero-inner { position: relative; z-index: 1; max-width: 760px; margin: 0 auto; text-align: center; }
.hero-titre { color: #fff; font-size: clamp(2.2rem, 5vw, 3.4rem); font-weight: 800; letter-spacing: -0.5px; line-height: 1.05; }
.hero-sous { color: #fff; opacity: 0.9; font-size: 1.05rem; line-height: 1.6; max-width: 560px; margin: 16px auto 24px; }
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
.tableau-carte { background: #fff; border: 2px solid #29b6f6; border-radius: 18px; overflow: hidden; margin-top: 24px; box-shadow: 0 6px 20px rgba(41,182,246,0.12); }
.tableau-scroll { overflow-x: auto; }
.tableau { width: 100%; border-collapse: collapse; }
.tableau th { background: #eae7ef; text-align: left; padding: 16px 24px; font-size: 0.9rem; font-weight: 700; color: #1a237e; }
.tableau td { padding: 16px 24px; border-top: 1px solid #e4e1ea; font-size: 0.95rem; }
.tableau tbody tr { transition: background 0.15s; }
.tableau tbody tr:hover { background: #f5f2fb; }
.tableau tr.zebra { background: #fcfbff; }
.num { width: 64px; color: #767683; font-weight: 600; }
.nom { font-weight: 600; color: #1b1b21; }
.muted { color: #525f71; }
.chip-elig { background: #dcfce7; color: #166534; padding: 4px 12px; border-radius: 9999px; font-size: 0.72rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.04em; }
.vide { text-align: center; color: #767683; padding: 32px; }

/* Pagination */
.pagination { display: flex; align-items: center; justify-content: space-between; padding: 16px 24px; background: #f5f2fb; border-top: 1px solid #e4e1ea; flex-wrap: wrap; gap: 12px; }
.affichage { font-size: 0.85rem; color: #525f71; }
.pages { display: flex; align-items: center; gap: 8px; }
.rond { width: 40px; height: 40px; border-radius: 9999px; border: 1px solid #c6c5d4; background: #fff; cursor: pointer; font-size: 0.9rem; color: #1b1b21; transition: background 0.15s; }
.rond:hover:not(:disabled):not(.courant) { background: #eae7ef; }
.rond.courant { background: #1a237e; color: #fff; border-color: #1a237e; font-weight: 700; }
.rond.ellipse { border: none; background: none; cursor: default; }
.rond:disabled { opacity: 0.3; cursor: not-allowed; }
</style>
