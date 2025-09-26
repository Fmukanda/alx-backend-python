rom django.urls import path
from . import views

urlpatterns = [
    path('chatings/', views.ChatingChat.as_view(), name='listing-list'),
    path('chatings/<int:pk>/', views.ChatingDetail.as_view(), name='listing-detail'),

]
