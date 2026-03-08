from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class SocialAccount(models.Model):
    PLATFORM_CHOICES = [
        ('instagram','Instagram'),('youtube','YouTube'),('tiktok','TikTok'),
        ('twitter','Twitter/X'),('linkedin','LinkedIn'),('other','Other'),
    ]
    platform   = models.CharField(max_length=20, choices=PLATFORM_CHOICES)
    username   = models.CharField(max_length=100)
    owner      = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='social_accounts')
    is_active  = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self): return f"{self.get_platform_display()} - {self.username}"
    def total_posts(self): return self.content_set.filter(status='posted').count()
    def consistency_score(self):
        total = self.content_set.count()
        posted = self.content_set.filter(status='posted').count()
        return round((posted / total) * 100) if total else 0


class Content(models.Model):
    STATUS_CHOICES   = [('idea','Idea'),('editing','Editing'),('posted','Posted')]
    APPROVAL_CHOICES = [('pending','Pending'),('approved','Approved'),('rejected','Rejected')]
    title           = models.CharField(max_length=200)
    description     = models.TextField(blank=True)
    status          = models.CharField(max_length=10, choices=STATUS_CHOICES, default='idea')
    approval_status = models.CharField(max_length=10, choices=APPROVAL_CHOICES, default='pending')
    account         = models.ForeignKey(SocialAccount, on_delete=models.SET_NULL, null=True, blank=True)
    created_by      = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='content')
    order           = models.IntegerField(default=0)
    posted_at       = models.DateField(null=True, blank=True)
    created_at      = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)
    def __str__(self): return self.title
    class Meta: ordering = ['order','-created_at']


class Notification(models.Model):
    """Admin notifications — e.g. content marked as posted."""
    TYPE_CHOICES = [('posted','Content Posted'),('info','Info')]
    message    = models.CharField(max_length=300)
    type       = models.CharField(max_length=20, choices=TYPE_CHOICES, default='info')
    content    = models.ForeignKey(Content, on_delete=models.CASCADE, null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    read       = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta: ordering = ['-created_at']


class Habit(models.Model):
    COLOR_CHOICES = [
        ('#FF9500','Orange'),('#FF3B30','Red'),('#34C759','Green'),
        ('#007AFF','Blue'),('#AF52DE','Purple'),('#FF2D55','Pink'),
    ]
    name        = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    color       = models.CharField(max_length=10, default='#FF9500', choices=COLOR_CHOICES)
    owner       = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='habits')
    is_active   = models.BooleanField(default=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    def __str__(self): return self.name

    def streak(self):
        from datetime import date, timedelta
        today = date.today(); streak = 0; current = today
        while True:
            if self.logs.filter(date=current, completed=True).exists():
                streak += 1; current -= timedelta(days=1)
            else: break
        return streak

    def completion_rate(self, days=30):
        from datetime import date, timedelta
        today = date.today(); start = today - timedelta(days=days)
        total = (today - start).days + 1
        done  = self.logs.filter(date__gte=start, date__lte=today, completed=True).count()
        return round((done / total) * 100) if total else 0


class HabitLog(models.Model):
    habit     = models.ForeignKey(Habit, on_delete=models.CASCADE, related_name='logs')
    date      = models.DateField()
    completed = models.BooleanField(default=False)
    class Meta: unique_together = ['habit','date']; ordering = ['-date']


class Goal(models.Model):
    STATUS_CHOICES = [('active','Active'),('completed','Completed'),('paused','Paused')]
    title       = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    status      = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')
    target_date = models.DateField(null=True, blank=True)
    progress    = models.IntegerField(default=0)   # 0–100
    created_by  = models.ForeignKey(User, on_delete=models.CASCADE, related_name='goals_created')
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)
    def __str__(self): return self.title
    class Meta: ordering = ['-created_at']


class FinancialAccount(models.Model):
    name       = models.CharField(max_length=100)
    balance    = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self): return self.name


class Transaction(models.Model):
    TYPE_CHOICES = [('income','Income'),('expense','Expense'),('transfer','Transfer')]
    CATEGORY_CHOICES = [
        ('salary','Salary'),('freelance','Freelance'),('investment','Investment'),
        ('food','Food & Dining'),('transport','Transport'),('utilities','Utilities'),
        ('entertainment','Entertainment'),('shopping','Shopping'),('health','Health'),
        ('education','Education'),('rent','Rent'),('other','Other'),
    ]
    type         = models.CharField(max_length=10, choices=TYPE_CHOICES)
    date         = models.DateField(default=timezone.now)
    amount       = models.DecimalField(max_digits=15, decimal_places=2)
    category     = models.CharField(max_length=50, blank=True)
    account      = models.ForeignKey(FinancialAccount, on_delete=models.SET_NULL, null=True, blank=True, related_name='transactions')
    from_account = models.ForeignKey(FinancialAccount, on_delete=models.SET_NULL, null=True, blank=True, related_name='transfers_out')
    to_account   = models.ForeignKey(FinancialAccount, on_delete=models.SET_NULL, null=True, blank=True, related_name='transfers_in')
    notes        = models.TextField(blank=True)
    created_at   = models.DateTimeField(auto_now_add=True)
    class Meta: ordering = ['-date','-created_at']
