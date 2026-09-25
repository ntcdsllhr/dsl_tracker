"""
URL configuration for dsltracker project.

/admin/         Django admin (quick backend data browsing/edits)
/api/           REST API (see customers/urls.py)
/api/auth/token/  DRF token-auth login (technician app exchanges username/password for a token)
/               The built Svelte SPA (frontend/dist), served by Django in production
"""
from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView
from rest_framework.authtoken.views import obtain_auth_token

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("customers.urls")),
    path("api/auth/token/", obtain_auth_token, name="api-token-auth"),
]

# Serve the built Svelte SPA for every other route (client-side routing).
# In local dev you'll normally run `npm run dev` (Vite) separately instead —
# this only matters once `frontend/dist` has been built and copied in.
if (settings.BASE_DIR / "frontend_dist" / "index.html").exists():
    urlpatterns += [
        path("", TemplateView.as_view(template_name="index.html")),
    ]
