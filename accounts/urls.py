from django.urls import path
from .views import login_page, about_page, profile_view, profile_edit, profile_detail, profile_search, inbox, send_message

urlpatterns = [
    path('', login_page, name='login'),
    path('about/', about_page, name='about'),
    path('profile/', profile_view, name='profile_view'),
    path('profile/edit/', profile_edit, name='profile_edit'),
    path('profile/<int:user_id>/', profile_detail, name='profile_detail'),
    path('search/', profile_search, name='profile_search'),
    path('inbox/', inbox, name='inbox'),
    path('messages/send/<int:receiver_id>/', send_message, name='send_message'),
    path('messages/chat/<int:receiver_id>/', send_message, name='chat_detail')
]