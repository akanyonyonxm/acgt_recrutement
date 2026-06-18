from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    AppelCandidatureViewSet,
    CritereValidationViewSet,
    DossierViewSet,
    EligibiliteViewSet,
    PosteViewSet,
    RapportsView,
    ReclamationViewSet,
    RetenusViewSet,
    TypePieceViewSet,
)

router = DefaultRouter()
router.register('types-piece', TypePieceViewSet, basename='type-piece')
router.register('postes', PosteViewSet, basename='poste')
router.register('eligibilite', EligibiliteViewSet, basename='eligibilite')
router.register('retenus', RetenusViewSet, basename='retenu')
router.register('appels', AppelCandidatureViewSet, basename='appel')
router.register('dossiers', DossierViewSet, basename='dossier')
router.register('reclamations', ReclamationViewSet, basename='reclamation')
router.register('criteres', CritereValidationViewSet, basename='critere')

urlpatterns = router.urls + [
    path('rapports/', RapportsView.as_view(), name='rapports'),
]
