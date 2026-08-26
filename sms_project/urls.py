from django.contrib import admin
from django.urls import path, include

from core.views import ResilientPasswordResetView

urlpatterns = [
    path('admin/', admin.site.urls),
    # Listed before the include so it wins over the stock password-reset view.
    path(
        'accounts/password_reset/',
        ResilientPasswordResetView.as_view(),
        name='password_reset',
    ),
    path('accounts/', include('django.contrib.auth.urls')),
    path('i18n/', include('django.conf.urls.i18n')),
    path('', include('core.urls')),
]
