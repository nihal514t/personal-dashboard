import json
from datetime import date, timedelta
from calendar import month_abbr
from decimal import Decimal
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Sum
from .models import SocialAccount, Content, Habit, HabitLog, Goal, Notification, FinancialAccount, Transaction


def is_admin(user):
    return user.is_staff or user.is_superuser


def safe_date_str(d):
    """Return ISO date string regardless of whether d is a date object or string."""
    if d is None:
        return ''
    if hasattr(d, 'isoformat'):
        return d.isoformat()
    s = str(d)
    return s[:10] if len(s) >= 10 else s


# ── AUTH ─────────────────────────────────────────────────────────

def login_view(request):
    if request.user.is_authenticated:
        return redirect('overview')
    error = None
    if request.method == 'POST':
        user = authenticate(request,
                            username=request.POST.get('username','').strip(),
                            password=request.POST.get('password',''))
        if user:
            login(request, user)
            nxt = request.GET.get('next','')
            return redirect(nxt if nxt else 'overview')
        error = 'Invalid username or password.'
    return render(request, 'dashboard/login.html', {'error': error})


def logout_view(request):
    logout(request)
    return redirect('login')


# ── PAGES ─────────────────────────────────────────────────────────

@login_required(login_url='/login/')
def overview(request):
    today = date.today()

    # Habits scoped to current user
    my_habits   = Habit.objects.filter(is_active=True, owner=request.user)
    total_h     = my_habits.count()
    best_streak = max([h.streak() for h in my_habits], default=0)
    done_today  = HabitLog.objects.filter(date=today, completed=True, habit__in=my_habits).count()
    consistency = round((done_today / total_h) * 100) if total_h else 0

    today_habits = []
    for h in my_habits:
        log, _ = HabitLog.objects.get_or_create(habit=h, date=today)
        today_habits.append({'habit': h, 'log': log})

    weekly_data = []
    for i in range(6, -1, -1):
        d    = today - timedelta(days=i)
        done = HabitLog.objects.filter(date=d, completed=True, habit__in=my_habits).count()
        rate = round((done / total_h) * 100) if total_h else 0
        weekly_data.append({'date': d.strftime('%a'), 'rate': rate})

    # Goals — everyone can see all
    goals = Goal.objects.select_related('created_by').all()[:6]

    # Finance
    total_income  = Transaction.objects.filter(type='income').aggregate(s=Sum('amount'))['s'] or 0
    total_expense = Transaction.objects.filter(type='expense').aggregate(s=Sum('amount'))['s'] or 0

    # Recent POSTED content only
    if is_admin(request.user):
        recent_content = Content.objects.filter(status='posted').select_related('account','created_by').order_by('-updated_at')[:5]
        recent_tx      = Transaction.objects.select_related('account').order_by('-date','-created_at')[:5]
    else:
        recent_content = Content.objects.filter(status='posted', created_by=request.user).select_related('account').order_by('-updated_at')[:5]
        recent_tx      = []

    # Unread notifications for admin
    notif_count = Notification.objects.filter(read=False).count() if is_admin(request.user) else 0

    return render(request, 'dashboard/overview.html', {
        'total_posted'      : Content.objects.filter(status='posted').count(),
        'best_streak'       : best_streak,
        'consistency'       : consistency,
        'net_balance'       : float(total_income - total_expense),
        'total_income'      : float(total_income),
        'total_expense'     : float(total_expense),
        'recent_content'    : recent_content,
        'recent_transactions': recent_tx,
        'today_habits'      : today_habits,
        'goals'             : goals,
        'weekly_data'       : json.dumps(weekly_data),
        'notif_count'       : notif_count,
        'active_page'       : 'overview',
        'is_admin'          : is_admin(request.user),
    })


@login_required(login_url='/login/')
def content_manager(request):
    if is_admin(request.user):
        accounts = SocialAccount.objects.filter(is_active=True).select_related('owner')
    else:
        accounts = SocialAccount.objects.filter(is_active=True, owner=request.user)

    account_id, selected_account = request.GET.get('account','').strip(), None
    if account_id:
        try:
            selected_account = SocialAccount.objects.get(pk=int(account_id))
        except (SocialAccount.DoesNotExist, ValueError):
            account_id = ''

    if account_id and selected_account:
        qs = Content.objects.filter(account=selected_account)
        if not is_admin(request.user):
            qs = qs.filter(created_by=request.user)
    else:
        qs = Content.objects.all() if is_admin(request.user) else Content.objects.filter(created_by=request.user)

    def serialize(queryset):
        rows = list(queryset.values(
            'id','title','description','status','approval_status',
            'account__username','account__platform','account__id','created_by__username'
        ))
        for r in rows:
            for k, v in r.items():
                if hasattr(v,'isoformat'): r[k] = v.isoformat()
        return rows

    return render(request, 'dashboard/content.html', {
        'accounts'          : accounts,
        'selected_account'  : selected_account,
        'selected_account_id': account_id,
        'ideas'             : json.dumps(serialize(qs.filter(status='idea'))),
        'editing'           : json.dumps(serialize(qs.filter(status='editing'))),
        'posted'            : json.dumps(serialize(qs.filter(status='posted'))),
        'columns'           : [('💡 Ideas','idea'),('✂️ Editing','editing'),('✅ Posted','posted')],
        'active_page'       : 'content',
        'is_admin'          : is_admin(request.user),
    })


@login_required(login_url='/login/')
def habits(request):
    today = date.today()
    my_habits  = Habit.objects.filter(is_active=True, owner=request.user)
    today_data = []
    for h in my_habits:
        log, _ = HabitLog.objects.get_or_create(habit=h, date=today)
        today_data.append({
            'id': h.id,'name': h.name,'description': h.description,'color': h.color,
            'streak': h.streak(),'rate': h.completion_rate(),
            'log_id': log.id,'completed': log.completed,
        })
    return render(request, 'dashboard/habits.html', {
        'today'         : today.isoformat(),
        'today_display' : today.strftime('%A, %B %d'),
        'today_data'    : json.dumps(today_data),
        'color_choices' : [('#FF9500','Orange'),('#FF3B30','Red'),('#34C759','Green'),
                           ('#007AFF','Blue'),('#AF52DE','Purple'),('#FF2D55','Pink')],
        'active_page'   : 'habits',
        'is_admin'      : is_admin(request.user),
    })


@login_required(login_url='/login/')
def goals_view(request):
    all_goals = Goal.objects.select_related('created_by').all()
    return render(request, 'dashboard/goals.html', {
        'goals'      : all_goals,
        'active_page': 'goals',
        'is_admin'   : is_admin(request.user),
    })


@login_required(login_url='/login/')
def finance(request):
    if not is_admin(request.user):
        return redirect('overview')

    transactions = Transaction.objects.select_related('account','from_account','to_account').all()
    fin_accounts = FinancialAccount.objects.all()
    total_income  = transactions.filter(type='income').aggregate(s=Sum('amount'))['s'] or 0
    total_expense = transactions.filter(type='expense').aggregate(s=Sum('amount'))['s'] or 0

    tx_data = []
    for t in transactions:
        tx_data.append({
            'id': t.id,'type': t.type,
            'date': safe_date_str(t.date),
            'amount': float(t.amount),'category': t.category,'notes': t.notes,
            'account'     : t.account.name      if t.account      else '',
            'from_account': t.from_account.name if t.from_account else '',
            'to_account'  : t.to_account.name   if t.to_account   else '',
        })

    # Monthly chart
    today = date.today()
    monthly = []
    for i in range(5, -1, -1):
        offset = today.month - i
        y = today.year - 1 if offset <= 0 else today.year
        m = 12 + offset     if offset <= 0 else offset
        inc = float(transactions.filter(type='income', date__year=y, date__month=m).aggregate(s=Sum('amount'))['s'] or 0)
        exp = float(transactions.filter(type='expense',date__year=y, date__month=m).aggregate(s=Sum('amount'))['s'] or 0)
        monthly.append({'month': month_abbr[m],'income': inc,'expense': exp})

    cat_data = []
    for cat, label in Transaction.CATEGORY_CHOICES:
        amt = float(transactions.filter(type='expense',category=cat).aggregate(s=Sum('amount'))['s'] or 0)
        if amt > 0:
            cat_data.append({'cat': label,'amount': amt})
    cat_data.sort(key=lambda x: -x['amount'])

    # Compute live balance for each account
    acc_data = []
    for acc in fin_accounts:
        inc = float(acc.transactions.filter(type='income').aggregate(s=Sum('amount'))['s'] or 0)
        exp = float(acc.transactions.filter(type='expense').aggregate(s=Sum('amount'))['s'] or 0)
        tr_in  = float(acc.transfers_in.aggregate(s=Sum('amount'))['s'] or 0)
        tr_out = float(acc.transfers_out.aggregate(s=Sum('amount'))['s'] or 0)
        live_balance = inc - exp + tr_in - tr_out
        acc_data.append({'id': acc.id,'name': acc.name,'balance': round(live_balance, 2)})

    return render(request, 'dashboard/finance.html', {
        'transactions' : json.dumps(tx_data),
        'fin_accounts' : fin_accounts,
        'acc_data'     : json.dumps(acc_data),
        'acc_data_list': acc_data,
        'total_income' : float(total_income),
        'total_expense': float(total_expense),
        'net_balance'  : float(total_income - total_expense),
        'monthly_data' : json.dumps(monthly),
        'cat_data'     : json.dumps(cat_data),
        'active_page'  : 'finance',
        'is_admin'     : True,
    })


@login_required(login_url='/login/')
def admin_panel(request):
    if not is_admin(request.user):
        return redirect('overview')
    users    = User.objects.filter(is_staff=False,is_superuser=False).prefetch_related('social_accounts','content')
    content  = Content.objects.select_related('account','created_by').order_by('-created_at')
    accounts = SocialAccount.objects.filter(is_active=True).select_related('owner')
    notifs   = Notification.objects.select_related('created_by','content').filter(read=False)[:20]
    return render(request, 'dashboard/admin_panel.html', {
        'users': users,'content': content,'accounts': accounts,'notifs': notifs,
        'active_page':'admin','is_admin': True,
    })


# ── API ───────────────────────────────────────────────────────────

@csrf_exempt
@login_required(login_url='/login/')
def api_add_account(request):
    """Admin-only: create and assign account to a user."""
    if not is_admin(request.user):
        return JsonResponse({'error':'Forbidden — only admin can add accounts'}, status=403)
    if request.method != 'POST':
        return JsonResponse({'error':'Method not allowed'}, status=405)
    data = json.loads(request.body)
    uid  = data.get('user_id')
    owner = User.objects.filter(pk=uid).first() if uid else None
    acc = SocialAccount.objects.create(platform=data['platform'], username=data['username'], owner=owner)
    return JsonResponse({
        'id': acc.id,'platform': acc.platform,
        'display': acc.get_platform_display(),'username': acc.username,
        'owner': owner.username if owner else '',
    })


@csrf_exempt
@login_required(login_url='/login/')
def api_delete_account(request, pk):
    if not is_admin(request.user):
        return JsonResponse({'error':'Forbidden'}, status=403)
    if request.method != 'DELETE':
        return JsonResponse({'error':'Method not allowed'}, status=405)
    acc = get_object_or_404(SocialAccount, pk=pk)
    acc.is_active = False; acc.save()
    return JsonResponse({'success': True})


@csrf_exempt
@login_required(login_url='/login/')
def api_assign_account(request):
    if not is_admin(request.user):
        return JsonResponse({'error':'Forbidden'}, status=403)
    if request.method != 'POST':
        return JsonResponse({'error':'Method not allowed'}, status=405)
    data = json.loads(request.body)
    acc  = get_object_or_404(SocialAccount, pk=data['account_id'])
    user = User.objects.filter(pk=data['user_id']).first() if data.get('user_id') else None
    acc.owner = user; acc.save()
    return JsonResponse({'success': True,'owner': user.username if user else ''})


@csrf_exempt
@login_required(login_url='/login/')
def api_add_content(request):
    if request.method != 'POST':
        return JsonResponse({'error':'Method not allowed'}, status=405)
    data    = json.loads(request.body)
    account = SocialAccount.objects.filter(pk=data['account_id']).first() if data.get('account_id') else None
    old_status = None
    c = Content.objects.create(
        title=data['title'], description=data.get('description',''),
        status=data.get('status','idea'), account=account, created_by=request.user,
    )
    # Notification if posted
    if c.status == 'posted':
        Notification.objects.create(
            message=f"{request.user.username} posted: {c.title}",
            type='posted', content=c, created_by=request.user,
        )
    return JsonResponse({
        'id': c.id,'title': c.title,'description': c.description,
        'status': c.status,'approval_status': c.approval_status,
        'account__username': account.username if account else '',
        'account__platform': account.platform if account else '',
        'account__id'      : account.id       if account else None,
        'created_by__username': request.user.username,
    })


@csrf_exempt
@login_required(login_url='/login/')
def api_content_detail(request, pk):
    c = get_object_or_404(Content, pk=pk)
    if not is_admin(request.user) and c.created_by != request.user:
        return JsonResponse({'error':'Forbidden'}, status=403)
    if request.method == 'DELETE':
        c.delete()
        return JsonResponse({'success': True})
    if request.method == 'POST':
        data       = json.loads(request.body)
        old_status = c.status
        for field in ('status','title','description'):
            if field in data: setattr(c, field, data[field])
        c.save()
        # Notification when moved to posted
        if old_status != 'posted' and c.status == 'posted':
            Notification.objects.create(
                message=f"{request.user.username} posted: {c.title}",
                type='posted', content=c, created_by=request.user,
            )
        return JsonResponse({'id': c.id,'status': c.status})
    return JsonResponse({'error':'Method not allowed'}, status=405)


@csrf_exempt
@login_required(login_url='/login/')
def api_content_approval(request, pk):
    if not is_admin(request.user):
        return JsonResponse({'error':'Forbidden'}, status=403)
    if request.method != 'POST':
        return JsonResponse({'error':'Method not allowed'}, status=405)
    c = get_object_or_404(Content, pk=pk)
    data = json.loads(request.body)
    c.approval_status = data.get('approval_status', c.approval_status)
    c.save()
    return JsonResponse({'id': c.id,'approval_status': c.approval_status})


@csrf_exempt
@login_required(login_url='/login/')
def api_update_content_order(request):
    if request.method != 'POST':
        return JsonResponse({'error':'Method not allowed'}, status=405)
    data = json.loads(request.body)
    for item in data.get('items',[]):
        old = Content.objects.filter(pk=item['id']).first()
        if old:
            old_status = old.status
            Content.objects.filter(pk=item['id']).update(status=item['status'], order=item['order'])
            # Notification on drag to posted
            if old_status != 'posted' and item['status'] == 'posted':
                c = Content.objects.get(pk=item['id'])
                Notification.objects.create(
                    message=f"{request.user.username} moved {c.title} to Posted",
                    type='posted', content=c, created_by=request.user,
                )
    return JsonResponse({'success': True})


# ── NOTIFICATIONS API ─────────────────────────────────────────────

@login_required(login_url='/login/')
def api_notifications(request):
    """Poll for unread notifications (admin only)."""
    if not is_admin(request.user):
        return JsonResponse({'count': 0,'items': []})
    notifs = Notification.objects.filter(read=False).select_related('created_by')[:10]
    items = [{
        'id': n.id,'message': n.message,'type': n.type,
        'time': n.created_at.strftime('%H:%M'),
    } for n in notifs]
    return JsonResponse({'count': notifs.count(),'items': items})


@csrf_exempt
@login_required(login_url='/login/')
def api_mark_notifications_read(request):
    if not is_admin(request.user):
        return JsonResponse({'error':'Forbidden'}, status=403)
    if request.method != 'POST':
        return JsonResponse({'error':'Method not allowed'}, status=405)
    Notification.objects.filter(read=False).update(read=True)
    return JsonResponse({'success': True})


# ── HABITS API ────────────────────────────────────────────────────

@csrf_exempt
@login_required(login_url='/login/')
def api_toggle_habit(request):
    if request.method != 'POST':
        return JsonResponse({'error':'Method not allowed'}, status=405)
    data = json.loads(request.body)
    log  = get_object_or_404(HabitLog, pk=data['log_id'])
    log.completed = not log.completed; log.save()
    return JsonResponse({'completed': log.completed,'streak': log.habit.streak()})


@csrf_exempt
@login_required(login_url='/login/')
def api_add_habit(request):
    if request.method != 'POST':
        return JsonResponse({'error':'Method not allowed'}, status=405)
    data  = json.loads(request.body)
    habit = Habit.objects.create(
        name=data['name'], description=data.get('description',''),
        color=data.get('color','#FF9500'), owner=request.user,
    )
    log, _ = HabitLog.objects.get_or_create(habit=habit, date=date.today())
    return JsonResponse({
        'id': habit.id,'name': habit.name,'description': habit.description,
        'color': habit.color,'streak': 0,'rate': 0,
        'log_id': log.id,'completed': log.completed,
    })


@csrf_exempt
@login_required(login_url='/login/')
def api_update_habit(request, pk):
    if request.method != 'POST':
        return JsonResponse({'error':'Method not allowed'}, status=405)
    habit = get_object_or_404(Habit, pk=pk, owner=request.user)
    data  = json.loads(request.body)
    habit.name = data.get('name', habit.name)
    habit.description = data.get('description', habit.description)
    habit.color = data.get('color', habit.color)
    habit.save()
    return JsonResponse({'id': habit.id,'name': habit.name,'color': habit.color})


@csrf_exempt
@login_required(login_url='/login/')
def api_delete_habit(request, pk):
    if request.method != 'DELETE':
        return JsonResponse({'error':'Method not allowed'}, status=405)
    habit = get_object_or_404(Habit, pk=pk, owner=request.user)
    habit.is_active = False; habit.save()
    return JsonResponse({'success': True})


@csrf_exempt
@login_required(login_url='/login/')
def api_all_habits(request):
    habits = Habit.objects.filter(is_active=True, owner=request.user)
    today  = date.today()
    start  = today - timedelta(days=29)
    result = []
    for h in habits:
        logs = list(h.logs.filter(date__gte=start).values('date','completed'))
        for l in logs: l['date'] = l['date'].isoformat()
        result.append({'id': h.id,'name': h.name,'color': h.color,'logs': logs})
    return JsonResponse({'habits': result})


# ── GOALS API ─────────────────────────────────────────────────────

@csrf_exempt
@login_required(login_url='/login/')
def api_add_goal(request):
    if not is_admin(request.user):
        return JsonResponse({'error':'Forbidden'}, status=403)
    if request.method != 'POST':
        return JsonResponse({'error':'Method not allowed'}, status=405)
    data = json.loads(request.body)
    g = Goal.objects.create(
        title=data['title'], description=data.get('description',''),
        status=data.get('status','active'),
        target_date=data.get('target_date') or None,
        progress=int(data.get('progress',0)),
        created_by=request.user,
    )
    return JsonResponse({
        'id': g.id,'title': g.title,'description': g.description,
        'status': g.status,'progress': g.progress,
        'target_date': safe_date_str(g.target_date),
        'created_by': g.created_by.username,
    })


@csrf_exempt
@login_required(login_url='/login/')
def api_update_goal(request, pk):
    if not is_admin(request.user):
        return JsonResponse({'error':'Forbidden'}, status=403)
    if request.method != 'POST':
        return JsonResponse({'error':'Method not allowed'}, status=405)
    g    = get_object_or_404(Goal, pk=pk)
    data = json.loads(request.body)
    for field in ('title','description','status','progress'):
        if field in data: setattr(g, field, data[field])
    if 'target_date' in data:
        g.target_date = data['target_date'] or None
    g.save()
    return JsonResponse({'id': g.id,'status': g.status,'progress': g.progress})


@csrf_exempt
@login_required(login_url='/login/')
def api_delete_goal(request, pk):
    if not is_admin(request.user):
        return JsonResponse({'error':'Forbidden'}, status=403)
    if request.method != 'DELETE':
        return JsonResponse({'error':'Method not allowed'}, status=405)
    get_object_or_404(Goal, pk=pk).delete()
    return JsonResponse({'success': True})


# ── FINANCE API ───────────────────────────────────────────────────

@csrf_exempt
@login_required(login_url='/login/')
def api_add_transaction(request):
    if not is_admin(request.user):
        return JsonResponse({'error':'Forbidden'}, status=403)
    if request.method != 'POST':
        return JsonResponse({'error':'Method not allowed'}, status=405)
    data     = json.loads(request.body)
    account  = FinancialAccount.objects.filter(pk=data.get('account_id')).first() if data.get('account_id') else None
    from_acc = FinancialAccount.objects.filter(pk=data.get('from_id')).first()    if data.get('from_id')    else None
    to_acc   = FinancialAccount.objects.filter(pk=data.get('to_id')).first()      if data.get('to_id')      else None
    amount   = Decimal(str(data['amount']))
    tx_date  = data['date']   # keep as string for storage; Django coerces on save

    tx = Transaction.objects.create(
        type=data['type'], date=tx_date, amount=amount,
        category=data.get('category',''),
        account=account, from_account=from_acc, to_account=to_acc,
        notes=data.get('notes',''),
    )

    # Update account balances
    if data['type'] == 'income' and account:
        account.balance += amount; account.save()
    elif data['type'] == 'expense' and account:
        account.balance -= amount; account.save()
    elif data['type'] == 'transfer':
        if from_acc: from_acc.balance -= amount; from_acc.save()
        if to_acc:   to_acc.balance   += amount; to_acc.save()

    # Return updated balances too
    updated_balances = {}
    for acc in [account, from_acc, to_acc]:
        if acc:
            acc.refresh_from_db()
            updated_balances[acc.id] = float(acc.balance)

    return JsonResponse({
        'id': tx.id,'type': tx.type,
        'date': safe_date_str(tx.date),
        'amount': float(tx.amount),'category': tx.category,'notes': tx.notes,
        'account'     : account.name      if account      else '',
        'from_account': from_acc.name     if from_acc     else '',
        'to_account'  : to_acc.name       if to_acc       else '',
        'updated_balances': updated_balances,
    })


@csrf_exempt
@login_required(login_url='/login/')
def api_delete_transaction(request, pk):
    if not is_admin(request.user):
        return JsonResponse({'error':'Forbidden'}, status=403)
    if request.method != 'DELETE':
        return JsonResponse({'error':'Method not allowed'}, status=405)
    tx = get_object_or_404(Transaction, pk=pk)
    amount = tx.amount
    # Reverse balance effect
    if tx.type == 'income' and tx.account:
        tx.account.balance -= amount; tx.account.save()
    elif tx.type == 'expense' and tx.account:
        tx.account.balance += amount; tx.account.save()
    elif tx.type == 'transfer':
        if tx.from_account: tx.from_account.balance += amount; tx.from_account.save()
        if tx.to_account:   tx.to_account.balance   -= amount; tx.to_account.save()
    tx.delete()
    return JsonResponse({'success': True})


@csrf_exempt
@login_required(login_url='/login/')
def api_add_fin_account(request):
    if not is_admin(request.user):
        return JsonResponse({'error':'Forbidden'}, status=403)
    if request.method != 'POST':
        return JsonResponse({'error':'Method not allowed'}, status=405)
    data = json.loads(request.body)
    acc  = FinancialAccount.objects.create(name=data['name'])
    return JsonResponse({'id': acc.id,'name': acc.name,'balance': 0.0})


@csrf_exempt
@login_required(login_url='/login/')
def api_delete_fin_account(request, pk):
    if not is_admin(request.user):
        return JsonResponse({'error':'Forbidden'}, status=403)
    if request.method != 'DELETE':
        return JsonResponse({'error':'Method not allowed'}, status=405)
    get_object_or_404(FinancialAccount, pk=pk).delete()
    return JsonResponse({'success': True})
