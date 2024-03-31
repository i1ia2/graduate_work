
from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularSwaggerView, SpectacularAPIView

from backend import views

from django_rest_passwordreset.views import reset_password_request_token, reset_password_confirm

from backend.views import (ShopView, OrderView, BasketView, ContactView, RegisterAccount, PartnerUpdate,
                           PartnerState, PartnerOrders, LoginAccount, CategoryView, ConfirmAccount, AccountDetails,
                           ProductInfoView, shops_all, product_html,check_user_restricted, upload_image)

def trigger_error(request):
    division_by_zero = 1 / 0


urlpatterns = [
    path('', views.index, name='index'),
    path('admin/', admin.site.urls, name='admin'),
    path('baton/', include('baton.urls')),
    path('product/info', ProductInfoView.as_view(), name='product'),
    path('product', product_html, name='product_html'),
    path('partner/update', PartnerUpdate.as_view(), name='partner-update'),
    path('partner/state', PartnerState.as_view(), name='partner-state'),
    path('partner/orders', PartnerOrders.as_view(), name='partner-orders'),
    path('user/register', RegisterAccount.as_view(), name='register_users'),
    path('user/register/confirm', ConfirmAccount.as_view(), name='user-register-confirm'),
    path('user/details', AccountDetails.as_view(), name='user-details'),
    path('user/contact', ContactView.as_view(), name='user-contact'),
    path('user/login', LoginAccount.as_view(), name='user-login'),
    path('user/password_reset', reset_password_request_token, name='password-reset'),
    path('user/password_reset/confirm', reset_password_confirm, name='password-reset-confirm'),
    path('categories', CategoryView.as_view(), name='categories'),
    path('shops', ShopView.as_view(), name='shops'),
    path('shops/all', shops_all, name='shops_all'),
    path('basket', BasketView.as_view(), name='basket'),
    path('order', OrderView.as_view(), name='order'),
    path('shops/all/<int:shop_id>', ShopView.as_view(), name='shop_products'),
    path('user/examination', check_user_restricted.as_view(), name='user-examination'),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/swagger/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger'),
    path('social-auth/', include('social_django.urls', namespace='social')),
    path('sentry-debug/', trigger_error),
    path('upload/', upload_image, name='upload_image'),
]

