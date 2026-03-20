"""
URL configuration for AppPresenze project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
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

# AppPresenze/urls.py
# AppPresenze/urls.py
from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView

urlpatterns = [
    path('admin/', admin.site.urls),

    # Login/Logout standard di Django
    path('accounts/', include('django.contrib.auth.urls')),

    # Profile e change password personalizzati
    path('accounts/profile/', include(('presenze.urls_profile', 'profile'), namespace='profile')),

    # Tutte le API e funzionalità dell'app Presenze
    path('presenze/', include(('presenze.urls', 'presenze'), namespace='presenze')),

    # Home del sito
    path('', TemplateView.as_view(template_name='site_home.html'), name='home'),
]
