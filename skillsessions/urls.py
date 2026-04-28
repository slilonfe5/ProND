from django.urls import path
from . import views

urlpatterns = [
    path('', views.session_list, name='session_list'),
    path('mine/', views.my_sessions, name='my_sessions'),
    path('create/', views.session_create, name='session_create'),
    path('sharer/<int:user_id>/', views.sharer_session_list, name='sharer_session_list'),
    path('<int:pk>/', views.session_detail, name='session_detail'),
    path('<int:pk>/messages/', views.session_message_create, name='session_message_create'),
    path('<int:pk>/messages/<int:message_id>/edit/', views.session_message_edit, name='session_message_edit'),
    path('<int:pk>/messages/<int:message_id>/delete/', views.session_message_delete, name='session_message_delete'),
    path('<int:pk>/join/', views.session_join, name='session_join'),
    path('<int:pk>/leave/', views.session_leave, name='session_leave'),
    path("<int:pk>/cancel/", views.cancel_session, name="cancel_session"),
]
