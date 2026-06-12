from django.urls import path

from . import views

urlpatterns = [
    path('csrf/', views.CsrfView.as_view(), name='csrf'),
    path('inscription/', views.InscriptionView.as_view(), name='inscription'),
    path('verifier-email/', views.VerifierEmailView.as_view(), name='verifier-email'),
    path('renvoyer-verification/', views.RenvoyerVerificationView.as_view(),
         name='renvoyer-verification'),
    path('connexion/', views.ConnexionView.as_view(), name='connexion'),
    path('deconnexion/', views.DeconnexionView.as_view(), name='deconnexion'),
    path('moi/', views.MoiView.as_view(), name='moi'),
    path('evaluateurs/', views.ListeEvaluateursView.as_view(), name='evaluateurs'),
    path('utilisateurs/', views.GestionUtilisateursView.as_view(), name='utilisateurs'),
    path('utilisateurs/<int:pk>/', views.GestionUtilisateurDetailView.as_view(),
         name='utilisateur-detail'),
    path('mot-de-passe/demande/', views.DemandeResetView.as_view(),
         name='mot-de-passe-demande'),
    path('mot-de-passe/reinitialiser/', views.ReinitialiserView.as_view(),
         name='mot-de-passe-reinitialiser'),
]
