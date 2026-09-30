"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
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
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.conf.urls.i18n import i18n_patterns
from rest_framework.routers import DefaultRouter
from store.api import AdminOrderViewSet, LocalAssistantView, ProductViewSet, StoreContentView, api_root


api_router = DefaultRouter()
api_router.register('products', ProductViewSet, basename='api-product')
api_router.register('orders', AdminOrderViewSet, basename='api-order')


urlpatterns = [
    path('i18n/', include('django.conf.urls.i18n')),
    path('api/', api_root, name='api-root'),
    path('api/site-content/', StoreContentView.as_view(), name='api-store-content'),
    path('api/assistant/', LocalAssistantView.as_view(), name='api-assistant'),
    path('api/', include(api_router.urls)),
    path('api-auth/', include('rest_framework.urls')),
]

urlpatterns += i18n_patterns(
    path('admin/', admin.site.urls),
    path('', include('store.urls')),
    path('accounts/', include('accounts.urls')),
)

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT
    )
