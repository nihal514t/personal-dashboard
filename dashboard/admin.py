from django.contrib import admin
from .models import SocialAccount, Content, Habit, HabitLog, FinancialAccount, Transaction

@admin.register(SocialAccount)
class SocialAccountAdmin(admin.ModelAdmin):
    list_display = ['username','platform','owner','is_active']
    list_filter  = ['platform','is_active']

@admin.register(Content)
class ContentAdmin(admin.ModelAdmin):
    list_display = ['title','status','approval_status','created_by','account']
    list_filter  = ['status','approval_status']
    list_editable = ['approval_status']

@admin.register(Habit)
class HabitAdmin(admin.ModelAdmin):
    list_display = ['name','color','is_active']

@admin.register(HabitLog)
class HabitLogAdmin(admin.ModelAdmin):
    list_display = ['habit','date','completed']
    list_filter  = ['completed']

@admin.register(FinancialAccount)
class FinancialAccountAdmin(admin.ModelAdmin):
    list_display = ['name','balance']

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ['type','amount','date','category','account']
    list_filter  = ['type','category']
