from django.urls import path
from . import views

urlpatterns = [
    path('', views.splash, name='splash'),
    path('auth', views.auth_view, name='auth'),
    path('home', views.home, name='home'),
    path('chat/<int:user_id>', views.chat_window, name='chat_window'),
    path('profile', views.profile_view, name='profile'),
    path('discover', views.discover_view, name='discover'),
    path('notifications', views.notifications_view, name='notifications'),
    path('add_friend_page', views.add_friend_page, name='add_friend_page'),
    path('logout', views.logout_view, name='logout'),
    path('friend/profile/<int:user_id>', views.friend_profile, name='friend_profile'),
    
    # APIs
    path('api/register', views.register_api, name='register_api'),
    path('api/login', views.login_api, name='login_api'),
    path('api/user_search', views.user_search_api, name='user_search'),
    path('api/friend_request/send', views.send_request_api, name='send_request'),
    path('api/friend_request/update', views.update_request_api, name='update_request'),
    path('api/upload_post', views.upload_post_api, name='upload_post'),
    path('api/update_profile', views.update_profile_api, name='update_profile'),
    path('api/messages/<int:user_id>', views.get_messages_api, name='get_messages'),
    path('api/send_message', views.send_message_api, name='send_message'),
    path('api/toggle_block', views.toggle_block_api, name='toggle_block'),
    path('api/delete_chat', views.delete_chat_api, name='delete_chat'),
    path('settings', views.settings_view, name='settings'),
    path('api/update_settings', views.update_settings_api, name='update_settings'),
    path('api/like_post', views.like_post_api, name='like_post'),
    path('api/delete_post', views.delete_post_api, name='delete_post'),
    
    # Comment & Share
    path('post/<int:post_id>/share/', views.share_page, name='share_page'),
    path('post/<int:post_id>/comments/', views.comment_page, name='comment_page'),
    path('api/get_friends_for_share/', views.get_friends_for_share_api, name='get_friends_for_share'),
    path('api/comment_post', views.comment_post_api, name='comment_post'),
    path('api/share_post', views.share_post_api, name='share_post'),
    path('api/delete_comment', views.delete_comment_api, name='delete_comment'),
]