"""
Views for the carbon emission tracking application.
Dashboard, Activity, and History sections.
"""

import json
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.db.models import Sum, Count, Avg
from django.contrib import messages
from datetime import date, timedelta

from .models import ActivityType, EmissionRecord, EmissionGoal


def dashboard(request):
    """Dashboard view showing summary statistics and recent activity."""
    total_emissions = EmissionRecord.objects.aggregate(
        total=Sum('emission_amount')
    )['total'] or 0.0

    total_records = EmissionRecord.objects.count()

    avg_emission = EmissionRecord.objects.aggregate(
        avg=Avg('emission_amount')
    )['avg'] or 0.0

    top_activities = (
        EmissionRecord.objects
        .values('activity__activity_name')
        .annotate(total=Sum('emission_amount'), count=Count('id'))
        .order_by('-total')[:5]
    )

    recent_records = EmissionRecord.objects.select_related('activity').order_by('-date', '-created_at')[:5]

    # Emissions over the last 7 days for a simple chart
    today = date.today()
    daily_data = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        day_total = EmissionRecord.objects.filter(date=day).aggregate(
            total=Sum('emission_amount')
        )['total'] or 0.0
        daily_data.append({'date': day.strftime('%b %d'), 'total': round(day_total, 2)})

    context = {
        'total_emissions': round(total_emissions, 2),
        'total_records': total_records,
        'avg_emission': round(avg_emission, 2),
        'top_activities': top_activities,
        'recent_records': recent_records,
        'daily_data': daily_data,
        'daily_labels_json': json.dumps([d['date'] for d in daily_data]),
        'daily_totals_json': json.dumps([d['total'] for d in daily_data]),
        'act_labels_json': json.dumps([a['activity__activity_name'] for a in top_activities]),
        'act_totals_json': json.dumps([round(a['total'], 2) for a in top_activities]),
    }
    return render(request, 'emission_app/dashboard.html', context)


def activity(request):
    """Activity view for managing activity types and adding emission records."""
    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'add_record':
            activity_id = request.POST.get('activity_id')
            quantity = request.POST.get('quantity')
            record_date = request.POST.get('date')
            description = request.POST.get('description', '')

            try:
                activity_type = get_object_or_404(ActivityType, pk=activity_id)
                qty = float(quantity)
                if qty <= 0:
                    raise ValueError("Quantity must be positive")
                EmissionRecord.objects.create(
                    activity=activity_type,
                    quantity=qty,
                    date=record_date or date.today(),
                    description=description,
                )
                messages.success(request, 'Emission record added successfully!')
            except (ValueError, TypeError) as e:
                messages.error(request, f'Invalid input: {e}')
            return redirect('activity')

        elif action == 'add_activity':
            name = request.POST.get('activity_name', '').strip()
            factor = request.POST.get('emission_factor')
            unit = request.POST.get('unit', '').strip()
            try:
                if not name or not unit:
                    raise ValueError("Name and unit are required")
                ActivityType.objects.create(
                    activity_name=name,
                    emission_factor=float(factor),
                    unit=unit,
                )
                messages.success(request, f'Activity type "{name}" added successfully!')
            except (ValueError, TypeError) as e:
                messages.error(request, f'Invalid input: {e}')
            return redirect('activity')

    activity_types = ActivityType.objects.annotate(
        record_count=Count('emissionrecord'),
        total_emissions=Sum('emissionrecord__emission_amount'),
    ).order_by('activity_name')

    context = {
        'activity_types': activity_types,
        'today': date.today(),
    }
    return render(request, 'emission_app/activity.html', context)


def history(request):
    """History view showing all emission records with filtering options."""
    records = EmissionRecord.objects.select_related('activity').order_by('-date', '-created_at')

    # Filter by activity type
    activity_filter = request.GET.get('activity')
    if activity_filter:
        records = records.filter(activity__id=activity_filter)

    # Filter by date range
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    if start_date:
        records = records.filter(date__gte=start_date)
    if end_date:
        records = records.filter(date__lte=end_date)

    total_filtered = records.aggregate(total=Sum('emission_amount'))['total'] or 0.0

    activity_types = ActivityType.objects.order_by('activity_name')

    # Aggregate daily totals for the chart (from filtered queryset)
    daily_agg = (
        records
        .values('date')
        .annotate(total=Sum('emission_amount'))
        .order_by('date')
    )
    chart_dates = [str(row['date']) for row in daily_agg]
    chart_totals = [round(row['total'], 2) for row in daily_agg]

    # Emissions by activity for the filtered period
    by_activity = (
        records
        .values('activity__activity_name')
        .annotate(total=Sum('emission_amount'))
        .order_by('-total')
    )
    act_labels = [row['activity__activity_name'] for row in by_activity]
    act_totals = [round(row['total'], 2) for row in by_activity]

    context = {
        'records': records,
        'total_filtered': round(total_filtered, 2),
        'activity_types': activity_types,
        'activity_filter': activity_filter,
        'start_date': start_date,
        'end_date': end_date,
        'chart_dates': chart_dates,
        'chart_totals': chart_totals,
        'act_labels': act_labels,
        'act_totals': act_totals,
        'chart_dates_json': json.dumps(chart_dates),
        'chart_totals_json': json.dumps(chart_totals),
        'act_labels_json': json.dumps(act_labels),
        'act_totals_json': json.dumps(act_totals),
    }
    return render(request, 'emission_app/history.html', context)


def delete_record(request, record_id):
    """Delete an emission record."""
    if request.method == 'POST':
        record = get_object_or_404(EmissionRecord, pk=record_id)
        record.delete()
        messages.success(request, 'Record deleted successfully.')
    return redirect('history')


def goals(request):
    """Goals view for setting and tracking emission reduction targets."""
    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'add_goal':
            title = request.POST.get('title', '').strip()
            target = request.POST.get('target_emission')
            period = request.POST.get('period', 'monthly')
            start_date = request.POST.get('start_date')
            end_date = request.POST.get('end_date') or None
            notes = request.POST.get('notes', '').strip()

            try:
                if not title:
                    raise ValueError("Title is required")
                EmissionGoal.objects.create(
                    title=title,
                    target_emission=float(target),
                    period=period,
                    start_date=start_date or date.today(),
                    end_date=end_date,
                    notes=notes,
                )
                messages.success(request, f'Goal "{title}" added successfully!')
            except (ValueError, TypeError) as e:
                messages.error(request, f'Invalid input: {e}')
            return redirect('goals')

        elif action == 'delete_goal':
            goal_id = request.POST.get('goal_id')
            goal = get_object_or_404(EmissionGoal, pk=goal_id)
            goal.delete()
            messages.success(request, 'Goal deleted successfully.')
            return redirect('goals')

    all_goals = EmissionGoal.objects.all()

    # Calculate actual emissions for each goal's current period window
    today = date.today()
    goals_with_progress = []
    for goal in all_goals:
        # Determine the measurement window for this period
        if goal.period == 'daily':
            window_start = today
            window_end = today
        elif goal.period == 'weekly':
            # weekday() returns 0 for Monday … 6 for Sunday, so subtract to get Monday
            window_start = today - timedelta(days=today.weekday())
            window_end = window_start + timedelta(days=6)
        else:  # monthly
            window_start = today.replace(day=1)
            # last day of current month
            if today.month == 12:
                window_end = today.replace(month=12, day=31)
            else:
                window_end = today.replace(month=today.month + 1, day=1) - timedelta(days=1)

        actual = EmissionRecord.objects.filter(
            date__gte=window_start,
            date__lte=window_end,
        ).aggregate(total=Sum('emission_amount'))['total'] or 0.0
        actual = round(actual, 2)

        # Cap at 200 % to avoid extreme bar distortion when actuals far exceed target
        pct = min(round((actual / goal.target_emission) * 100, 1), 200) if goal.target_emission else 0
        goals_with_progress.append({
            'goal': goal,
            'actual': actual,
            'pct': pct,
            'over_target': actual > goal.target_emission,
        })

    # Bar chart data: target vs actual per goal
    goal_labels = [g['goal'].title for g in goals_with_progress]
    goal_targets = [g['goal'].target_emission for g in goals_with_progress]
    goal_actuals = [g['actual'] for g in goals_with_progress]

    context = {
        'goals_with_progress': goals_with_progress,
        'today': today,
        'period_choices': EmissionGoal.PERIOD_CHOICES,
        'goal_labels_json': json.dumps(goal_labels),
        'goal_targets_json': json.dumps(goal_targets),
        'goal_actuals_json': json.dumps(goal_actuals),
    }
    return render(request, 'emission_app/goals.html', context)