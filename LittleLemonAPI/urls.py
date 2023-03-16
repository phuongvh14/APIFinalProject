from django.urls import path
from . import views


urlpatterns = [
    path('groups/manager/users', views.UserGroupViewSet.as_view(
        {'get': 'list', 'post': 'create'})),
    path('groups/manager/users/<str:pk>', views.UserGroupViewSet.as_view(
        {'delete': 'destroy'})),
    path('groups/delivery-crew/users', views.DeliveryCrewManagementViewset.as_view(
        {'get': 'list', 'post': 'create'})),
    path('groups/delivery-crew/users/<str:pk>', views.DeliveryCrewManagementViewset.as_view(
        {'delete': 'destroy'})),
    path('menu-items', views.MenuItemView.as_view()),
    path('menu-items/<int:pk>', views.SingleMenuItemView.as_view()),
    path('cart/menu-items', views.CartView.as_view()),
    path('orders', views.OrderView.as_view()),
    path('orders/<int:pk>', views.SingleOrderView.as_view()),
    path('category', views.CategoriesView.as_view()),
]