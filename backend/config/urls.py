"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    # Admin technique Django sur une URL discrète (non devinable), distincte de
    # l'espace de traitement métier (front Vue). Doit être proxifiée par Nginx.
    path('console-3xfk2a/', admin.site.urls),
    path('api/auth/', include('comptes.urls')),
    path('api/', include('candidatures.urls')),
    # Auth navigateur de l'API DRF (login/logout) — pratique en développement.
    path('api-auth/', include('rest_framework.urls')),
]
