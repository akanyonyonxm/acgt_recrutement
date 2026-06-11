<script setup>
import { RouterLink } from 'vue-router'

const PROFILS = [
  'Ingénieur civil',
  'Ingénieur électromécanicien',
  'Ingénieur en Bâtiment et Travaux Publics (BTP)',
  'Ingénieur géomètre-topographe',
  'Architecte',
  'Urbaniste',
  'Environnementaliste',
]
const CRITERES = [
  "Avoir effectué un stage professionnel à l'ACGT",
  "Être en train d'effectuer son stage à l'ACGT",
  "Avoir exprimé la volonté d'effectuer un stage professionnel au sein de l'ACGT",
  "Avoir exprimé la volonté de travailler à l'ACGT",
]

const DOCUMENTS = [
  { icon: 'mdi-file-certificate-outline', titre: 'Accusé de réception', detail: "De votre lettre de demande de stage, de demande d'emploi, ou de votre lettre de stage.", reclamation: true, postuler: false },
  { icon: 'mdi-file-account-outline', titre: 'CV', detail: 'Curriculum vitae à jour.', reclamation: true, postuler: true },
  { icon: 'mdi-card-account-details-outline', titre: "Pièce d'identité", detail: "Carte d'électeur, passeport ou permis de conduire.", reclamation: true, postuler: true },
  { icon: 'mdi-school-outline', titre: 'Diplôme(s)', detail: 'Un ou plusieurs diplômes (ou équivalent).', reclamation: true, postuler: true },
]

const CALENDRIER = [
  { label: 'Date limite de soumission', date: '14 juin 2026 à 12h00 (TU+1)', fort: true },
  { label: 'Publication de la liste provisoire', date: '18 juin 2026' },
  { label: 'Délai de recours', date: 'Du 18 au 20 juin 2026' },
  { label: 'Liste définitive des retenus', date: '24 juin 2026' },
]

const FAQ = [
  { q: "Je ne trouve pas mon nom dans la liste, que faire ?", r: "Essayez votre nom de famille seul, ou votre postnom, ou votre prénom. Si vous ne vous trouvez toujours pas et que vous avez déposé un dossier ou effectué un stage à l'ACGT, utilisez le bouton « Réclamation » en joignant votre accusé de réception ou votre lettre de stage." },
  { q: "Où trouver mon code ?", r: "Votre code figure sur la liste des éligibles, à gauche de votre nom. En cliquant sur « Postuler » depuis la liste, il est rempli automatiquement." },
  { q: "Comment suivre mon dossier ?", r: "Connectez-vous à votre espace candidat (« Mes dossiers ») et surveillez vos emails : vous êtes notifié(e) à chaque évolution." },
  { q: "Je n'ai pas reçu l'email d'activation, que faire ?", r: "Vérifiez votre dossier « spam » / « courrier indésirable » et que l'adresse email saisie est correcte. Vous pouvez aussi le renvoyer : connectez-vous, un bandeau « Renvoyer l'email d'activation » s'affiche tant que votre adresse n'est pas vérifiée." },
  { q: "Je n'ai pas reçu l'accusé de réception : mon dossier est-il bien enregistré ?", r: "Connectez-vous à « Mes dossiers ». Si votre dossier y figure avec le statut « Déposé », il est bien enregistré (vérifiez aussi le « spam » pour l'accusé). S'il est encore en « Brouillon », c'est qu'il n'a pas été soumis : ouvrez-le, allez jusqu'à la page de confirmation et cliquez sur « Soumettre le dossier »." },
  { q: "Quels formats de fichiers sont acceptés ?", r: "PDF, image (JPG, PNG) ou Word, dans la limite de 5 Mo par fichier." },
]
</script>

<template>
  <div>
    <!-- HERO -->
    <section class="hero">
      <div class="hero-inner">
        <div class="hero-pastille">Guide d'utilisation</div>
        <h1 class="hero-titre">Comment postuler ?</h1>
        <p class="hero-sous">
          Suivez ces étapes simples pour déposer votre candidature en ligne.
          <strong>Seuls les candidats figurant sur la liste publiée</strong> peuvent soumettre leur dossier,
          <mark>au plus tard le 14 juin 2026 à 12h00 (TU+1)</mark>.
        </p>
      </div>
    </section>

    <div class="wrap">
      <!-- QUI PEUT POSTULER -->
      <h2 class="section-titre" style="margin-top:0">Qui peut postuler ?</h2>
      <p class="elig-intro">
        Dans le cadre du renforcement de ses capacités techniques, l'ACGT recrute des
        professionnels qualifiés. Le recrutement concerne les profils et critères ci-dessous.
      </p>
      <div class="elig-grid">
        <div class="elig-carte">
          <div class="elig-tete"><v-icon color="#1a237e" class="mr-2">mdi-briefcase-outline</v-icon>Profils recherchés</div>
          <ul class="elig-liste">
            <li v-for="p in PROFILS" :key="p">{{ p }}</li>
          </ul>
        </div>
        <div class="elig-carte">
          <div class="elig-tete"><v-icon color="#1a237e" class="mr-2">mdi-check-decagram-outline</v-icon>Critères d'éligibilité</div>
          <p class="elig-periode">
            Avoir déposé un dossier <strong>du 1ᵉʳ octobre 2024 au 5 juin 2026</strong>
            (pour un stage ou une demande d'emploi) et répondre à l'un des critères :
          </p>
          <ul class="elig-liste">
            <li v-for="c in CRITERES" :key="c">{{ c }}</li>
          </ul>
        </div>
      </div>
      <div class="elig-regle">
        <v-icon color="#fff" class="mr-2">mdi-information</v-icon>
        <span>
          Seuls les candidats ayant <strong>l'un de ces profils</strong> <strong>et figurant sur la liste
          des éligibles</strong> sont autorisés à postuler. Si vous n'êtes <strong>pas sur la liste</strong>
          mais que vous avez déposé un dossier ou effectué un stage à l'ACGT, et que vous disposez de
          l'<strong>accusé de réception</strong> ou de la <strong>lettre de stage</strong>,
          faites une <RouterLink :to="{ name: 'reclamation' }" class="elig-lien">réclamation</RouterLink>.
        </span>
      </div>
      <br/>

      <!-- ÉTAPE 1 -->
      <div class="etape">
        <div class="num">1</div>
        <div class="etape-corps">
          <h2>Recherchez votre nom dans la liste des éligibles</h2>
          <p>Rendez-vous sur <strong>Candidats éligibles</strong> et tapez votre nom dans la barre de recherche.
             Astuce : essayez votre <strong>nom de famille seul</strong>, ou votre <strong>postnom</strong>, ou votre <strong>prénom</strong>.</p>
          <div class="mock">
            <span class="mock-loupe">🔍</span>
            <span class="mock-ph">Rechercher votre nom…</span>
          </div>
          <RouterLink :to="{ name: 'eligibles' }" class="lien-action"> Ouvrir la liste des éligibles →</RouterLink>
        </div>
      </div>

      <!-- BIFURCATION -->
      <div class="bifurcation">
        <v-icon size="22" class="mr-2" color="#1a237e">mdi-source-branch</v-icon>
        Deux cas possibles selon que vous trouvez votre nom ou non :
      </div>

      <div class="branches">
        <!-- BRANCHE A : trouvé -->
        <div class="branche branche-ok">
          <div class="branche-tete">
            <v-icon color="#2E7D32">mdi-check-circle</v-icon>
            <span>Je trouve mon nom</span>
          </div>
          <ol class="sous-etapes">
            <li><strong>Notez votre code</strong> (à gauche de votre nom).</li>
            <li>Cliquez sur le bouton <span class="btn-jaune">Postuler</span> sur votre ligne.</li>
            <li><strong>Connectez-vous</strong>, ou <strong>créez un compte</strong> avec une <strong>adresse email valide</strong> et un mot de passe.
              <span class="note-mail">À la création, un email d'activation y est envoyé : ouvrez-le et cliquez sur le lien pour activer votre compte (vérifiez aussi le dossier « spam »).</span></li>
            <li>Renseignez les informations demandées : <strong>nom, postnom, prénom</strong>, email de contact, code, appel et poste visé.</li>
            <li>Joignez les <strong>3 documents obligatoires</strong> : <strong>CV, pièce d'identité et diplôme(s)</strong>.</li>
            <li>Allez jusqu'à la <strong>page de confirmation</strong> et cliquez sur <strong>« Soumettre le dossier »</strong>.</li>
            <li>Vous recevez alors un <strong>accusé de réception</strong> par email.</li>
          </ol>
          <p class="alerte-soumission">
            ⚠️ Tant que vous n'êtes pas arrivé(e) à la <strong>page de confirmation</strong> et que vous n'avez
            <strong>pas reçu l'email d'accusé de réception</strong>, votre dossier n'est <strong>pas soumis</strong>.
            <br />✅ Pour vérifier : dans <strong>« Mes dossiers »</strong>, votre dossier doit afficher le statut
            <strong>« Déposé »</strong> (et non <strong>« Brouillon »</strong>).
          </p>
        </div>

        <!-- BRANCHE B : pas trouvé -->
        <div class="branche branche-warn">
          <div class="branche-tete">
            <v-icon color="#EF6C00">mdi-alert-circle</v-icon>
            <span>Je ne trouve pas mon nom</span>
          </div>
          <p class="branche-intro">
            Si vous avez déposé un dossier ou effectué un stage à l'ACGT, et disposez de
            l'<strong>accusé de réception</strong> ou de la <strong>lettre de stage</strong>,
            faites une <strong>réclamation</strong> :
          </p>
          <ol class="sous-etapes">
            <li>Cliquez sur le bouton <span class="btn-jaune">Réclamation</span> (en haut du site).</li>
            <li>Joignez l'<strong>accusé de réception</strong> (demande de stage / d'emploi) ou votre <strong>lettre de stage</strong> <span class="oblig">(OBLIGATOIRE)</span>.</li>
            <li>Joignez aussi votre <strong>CV</strong>, votre <strong>pièce d'identité</strong> et vos <strong>diplômes</strong>.</li>
            <li><strong>Soumettez.</strong> L'ACGT examine votre réclamation.</li>
            <li>Si elle est <strong>validée</strong>, vous êtes ajouté(e) aux personnes retenues.</li>
          </ol>
          <RouterLink :to="{ name: 'reclamation' }" class="lien-action">Faire une réclamation →</RouterLink>
        </div>
      </div>

      <!-- ÉTAPE 3 -->
      <div class="etape">
        <div class="num">3</div>
        <div class="etape-corps">
          <h2>Suivez l'évolution de votre dossier</h2>
          <p>Connectez-vous à votre <strong>espace candidat</strong> (« Mes dossiers ») et surveillez vos emails :
             vous êtes notifié(e) à chaque étape (réception, examen, décision).</p>
        </div>
      </div>

      <!-- ÉTAPE 4 -->
      <div class="etape">
        <div class="num">4</div>
        <div class="etape-corps">
          <h2>Consultez les résultats</h2>
          <p>La liste des <strong>personnes retenues</strong> est publiée en ligne aux dates indiquées ci-dessous.</p>
          <RouterLink :to="{ name: 'retenus-public' }" class="lien-action">Voir les candidats retenus →</RouterLink>
        </div>
      </div>

      <!-- DOCUMENTS REQUIS -->
      <h2 class="section-titre">Documents à préparer</h2>
      <div class="docs-grid">
        <div v-for="d in DOCUMENTS" :key="d.titre" class="doc-carte">
          <v-icon size="30" color="#1a237e" class="mb-2">{{ d.icon }}</v-icon>
          <div class="doc-titre">{{ d.titre }}</div>
          <div class="doc-detail">{{ d.detail }}</div>
          <div class="doc-tags">
            <span v-if="d.postuler" class="tag tag-bleu">Postuler</span>
            <span v-if="d.reclamation" class="tag tag-jaune">Réclamation</span>
          </div>
        </div>
      </div>
      <p class="note-format">Formats acceptés : PDF, image (JPG/PNG) ou Word — 5 Mo max par fichier.</p>

      <!-- CALENDRIER -->
      <h2 class="section-titre">Calendrier du processus</h2>
      <div class="cal-grid">
        <div v-for="(e, i) in CALENDRIER" :key="i" class="cal-item" :class="{ fort: e.fort }">
          <div class="cal-label">{{ e.label }}</div>
          <div class="cal-date">{{ e.date }}</div>
        </div>
      </div>

      <!-- FAQ -->
      <h2 class="section-titre">Questions fréquentes</h2>
      <v-expansion-panels variant="accordion" class="faq">
        <v-expansion-panel v-for="(f, i) in FAQ" :key="i" :title="f.q" :text="f.r" />
      </v-expansion-panels>

      <!-- CTA final -->
      <div class="cta-final">
        <h2>Prêt(e) à postuler ?</h2>
        <div class="cta-btns">
          <RouterLink :to="{ name: 'eligibles' }" class="btn-plein">Vérifier mon éligibilité</RouterLink>
          <RouterLink :to="{ name: 'reclamation' }" class="btn-contour">Faire une réclamation</RouterLink>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.hero { background: linear-gradient(135deg, #1a237e 0%, #0d1b2a 100%); padding: 48px 24px 56px; }
.hero-inner { max-width: 760px; margin: 0 auto; text-align: center; }
.hero-pastille { display: inline-block; background: rgba(253,216,53,0.18); color: #FDD835; font-weight: 700; padding: 4px 14px; border-radius: 9999px; font-size: 0.8rem; margin-bottom: 12px; }
.hero-titre { color: #fff; font-size: clamp(2rem, 5vw, 3rem); font-weight: 800; letter-spacing: -0.5px; }
.hero-sous { color: #fff; opacity: 0.92; font-size: 1.02rem; line-height: 1.6; margin: 14px auto 0; }
.hero-sous mark { background: #E53935; color: #fff; padding: 1px 8px; border-radius: 6px; font-weight: 800; }

.wrap { max-width: 900px; margin: 0 auto; padding: 40px 24px 56px; }

.elig-intro { color: #525f71; line-height: 1.6; margin: 0 0 18px; }
.elig-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 18px; }
@media (max-width: 760px) { .elig-grid { grid-template-columns: 1fr; } }
.elig-carte { border: 1px solid #e2e6ea; border-radius: 16px; padding: 18px 20px; background: #fff; }
.elig-tete { display: flex; align-items: center; font-weight: 800; color: #1a237e; margin-bottom: 10px; }
.elig-periode { color: #525f71; font-size: 0.92rem; line-height: 1.55; margin: 0 0 8px; }
.elig-liste { margin: 0; padding-left: 20px; }
.elig-liste li { color: #2b2f36; line-height: 1.7; margin-bottom: 2px; }
.elig-regle { display: flex; align-items: flex-start; background: linear-gradient(135deg, #1a237e, #0d1b2a); color: #fff; border-radius: 14px; padding: 16px 18px; margin-top: 18px; line-height: 1.6; }
.elig-lien { color: #FDD835; font-weight: 800; text-decoration: underline; }

.etape { display: flex; gap: 18px; margin-bottom: 28px; }
.num { flex-shrink: 0; width: 44px; height: 44px; border-radius: 50%; background: #1a237e; color: #fff; font-weight: 800; font-size: 1.2rem; display: flex; align-items: center; justify-content: center; }
.etape-corps h2 { color: #1a237e; font-size: 1.25rem; margin: 4px 0 6px; }
.etape-corps p { color: #525f71; line-height: 1.6; margin: 0 0 10px; }
.lien-action { color: #1a237e; font-weight: 700; text-decoration: none; }
.lien-action:hover { text-decoration: underline; }

.mock { display: inline-flex; align-items: center; gap: 10px; border: 1px solid #c6c5d4; border-radius: 12px; padding: 12px 16px; color: #767683; background: #fff; margin: 4px 0 12px; min-width: 280px; }

.bifurcation { display: flex; align-items: center; background: #eef1f8; border-radius: 12px; padding: 14px 18px; font-weight: 600; color: #1a237e; margin: 8px 0 20px; }

.branches { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 32px; }
@media (max-width: 760px) { .branches { grid-template-columns: 1fr; } }
.branche { border: 1px solid #e2e6ea; border-radius: 16px; padding: 20px; background: #fff; }
.branche-ok { border-top: 4px solid #2E7D32; }
.branche-warn { border-top: 4px solid #EF6C00; }
.branche-tete { display: flex; align-items: center; gap: 8px; font-weight: 800; font-size: 1.05rem; color: #1b1b21; margin-bottom: 10px; }
.branche-intro { color: #525f71; line-height: 1.5; margin: 0 0 8px; }
.sous-etapes { margin: 0; padding-left: 20px; }
.sous-etapes li { color: #2b2f36; line-height: 1.7; margin-bottom: 4px; }
.note-mail { display: block; margin-top: 2px; font-size: 0.82rem; color: #0d47a1; background: #e7f3fb; border-left: 3px solid #0288D1; border-radius: 0 6px 6px 0; padding: 6px 10px; }
.alerte-soumission { margin-top: 12px; font-size: 0.85rem; color: #b71c1c; background: #fdecea; border-left: 3px solid #D32F2F; border-radius: 0 8px 8px 0; padding: 10px 12px; line-height: 1.5; }
.btn-jaune { background: #FDD835; color: #1a237e; padding: 1px 10px; border-radius: 9999px; font-weight: 800; font-size: 0.85rem; }
.oblig { color: #D32F2F; font-weight: 800; }

.section-titre { color: #1a237e; font-size: 1.4rem; font-weight: 700; margin: 36px 0 16px; border-bottom: 2px solid #FDD835; padding-bottom: 6px; }

.docs-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; }
@media (max-width: 760px) { .docs-grid { grid-template-columns: 1fr 1fr; } }
.doc-carte { border: 1px solid #e2e6ea; border-radius: 14px; padding: 16px; text-align: center; background: #fff; }
.doc-titre { font-weight: 700; color: #1b1b21; }
.doc-detail { font-size: 0.8rem; color: #767683; margin-top: 4px; min-height: 48px; }
.doc-tags { margin-top: 8px; display: flex; gap: 6px; justify-content: center; flex-wrap: wrap; }
.tag { font-size: 0.68rem; font-weight: 700; padding: 2px 8px; border-radius: 9999px; }
.tag-bleu { background: #e8eaf6; color: #1a237e; }
.tag-jaune { background: #fff7d6; color: #8a6d00; }
.note-format { text-align: center; color: #767683; font-size: 0.85rem; margin-top: 12px; }

.cal-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; }
@media (max-width: 760px) { .cal-grid { grid-template-columns: 1fr 1fr; } }
.cal-item { border: 1px solid #e2e6ea; border-top: 4px solid #1a237e; border-radius: 14px; padding: 16px; text-align: center; background: #fff; }
.cal-item.fort { border-top-color: #D32F2F; background: #fff7f7; }
.cal-label { font-size: 0.82rem; color: #525f71; min-height: 34px; }
.cal-date { font-size: 0.98rem; font-weight: 800; color: #1b1b21; margin-top: 6px; }
.cal-item.fort .cal-date { color: #D32F2F; }

.faq { margin-top: 8px; }

.cta-final { text-align: center; margin-top: 44px; background: #eef1f8; border-radius: 18px; padding: 32px 24px; }
.cta-final h2 { color: #1a237e; margin: 0 0 16px; }
.cta-btns { display: flex; gap: 14px; justify-content: center; flex-wrap: wrap; }
.btn-plein { background: #1a237e; color: #fff; padding: 12px 26px; border-radius: 12px; font-weight: 700; text-decoration: none; }
.btn-plein:hover { background: #283593; }
.btn-contour { border: 2px solid #1a237e; color: #1a237e; padding: 10px 26px; border-radius: 12px; font-weight: 700; text-decoration: none; }
.btn-contour:hover { background: rgba(26,35,126,0.05); }
</style>
