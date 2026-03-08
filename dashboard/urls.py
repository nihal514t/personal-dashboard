from django.urls import path
from . import views

urlpatterns = [
    path('login/',        views.login_view,   name='login'),
    path('logout/',       views.logout_view,  name='logout'),
    path('',              views.overview,     name='overview'),
    path('content/',      views.content_manager, name='content'),
    path('habits/',       views.habits,       name='habits'),
    path('goals/',        views.goals_view,   name='goals'),
    path('finance/',      views.finance,      name='finance'),
    path('admin-panel/',  views.admin_panel,  name='admin_panel'),

    # Accounts (admin only)
    path('api/accounts/add/',              views.api_add_account,        name='api_add_account'),
    path('api/accounts/<int:pk>/delete/',  views.api_delete_account,     name='api_delete_account'),
    path('api/accounts/assign/',           views.api_assign_account,     name='api_assign_account'),

    # Content
    path('api/content/add/',               views.api_add_content,        name='api_add_content'),
    path('api/content/<int:pk>/',          views.api_content_detail,     name='api_content_detail'),
    path('api/content/<int:pk>/approval/', views.api_content_approval,   name='api_content_approval'),
    path('api/content/order/',             views.api_update_content_order, name='api_update_content_order'),

    # Notifications
    path('api/notifications/',             views.api_notifications,           name='api_notifications'),
    path('api/notifications/read/',        views.api_mark_notifications_read, name='api_mark_notifications_read'),

    # Habits (per-user)
    path('api/habits/toggle/',             views.api_toggle_habit,  name='api_toggle_habit'),
    path('api/habits/add/',                views.api_add_habit,     name='api_add_habit'),
    path('api/habits/<int:pk>/update/',    views.api_update_habit,  name='api_update_habit'),
    path('api/habits/<int:pk>/delete/',    views.api_delete_habit,  name='api_delete_habit'),
    path('api/habits/all/',                views.api_all_habits,    name='api_all_habits'),

    # Goals (admin CRUD, all view)
    path('api/goals/add/',                 views.api_add_goal,    name='api_add_goal'),
    path('api/goals/<int:pk>/update/',     views.api_update_goal, name='api_update_goal'),
    path('api/goals/<int:pk>/delete/',     views.api_delete_goal, name='api_delete_goal'),

    # Finance (admin only)
    path('api/finance/add/',               views.api_add_transaction,  name='api_add_transaction'),
    path('api/finance/<int:pk>/delete/',   views.api_delete_transaction, name='api_delete_transaction'),
    path('api/finance/accounts/add/',      views.api_add_fin_account,  name='api_add_fin_account'),
    path('api/finance/accounts/<int:pk>/delete/', views.api_delete_fin_account, name='api_delete_fin_account'),
]
