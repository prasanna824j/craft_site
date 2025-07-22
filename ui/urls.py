from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('add_category/', views.ProductAdd.as_view(), name='add_category'),
    path('order-management/', views.OrderManagement.as_view(), name='order_management'),
    path('update_order_status/', views.update_order_status, name='update_order_status'),
    path("account/", views.account.as_view(), name="account"),
    path("cart/", views.cart.as_view(), name="cart"),
    path("", views.index.as_view(), name="index"),
    path("index/", views.index.as_view(), name="index"),
    path("watchlist/", views.watchlist.as_view(), name="watchlist"),
    path("product_add/", views.ProductAdd.as_view(), name="product_add"),
    path("signup/", views.Signup.as_view(), name="signup"),
    path("login/", views.Login.as_view(), name="login"),
    path("logout/", views.Logout.as_view(), name="logout"),
    path("orders/", views.Order.as_view(), name="orders"),
    path("edit_product/<int:pk>/", views.EditProduct.as_view(), name="edit_product"),
    path('add_category/', views.add_category, name='add_category'),
    path('wishlist/add/<int:product_id>/', views.add_to_wishlist, name='add_to_wishlist'),
    path('wishlist/remove/<int:product_id>/', views.remove_from_wishlist, name='remove_from_wishlist'),
    path('add_to_cart/', views.add_to_cart, name='add_to_cart'),
    path('update_cart/', views.update_cart, name='update_cart'),
    path('remove_cart_item/', views.remove_cart_item, name='remove_cart_item'),
    path('account_update/', views.UpdateAccount, name='account_update'),
    path('update_address/', views.update_address, name='update_address'),
    path("password_reset/", views.PasswordReset.as_view(), name="password_reset"),
    path('razorpay-payment/', views.RazorpayPaymentView.as_view(), name='razorpay_payment'),
    path('razorpay-callback/', views.razorpay_callback, name='razorpay_callback'),
    path('categories/', views.categories, name='categories'),
]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)