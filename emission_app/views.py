"""
Views for the carbon emission tracking application.
Dashboard, Activity, and History sections.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.db.models import Sum, Count, Avg
from django.contrib import messages
from datetime import date, timedelta

from .models import ActivityType, EmissionRecord


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

    context = {
        'records': records,
        'total_filtered': round(total_filtered, 2),
        'activity_types': activity_types,
        'activity_filter': activity_filter,
        'start_date': start_date,
        'end_date': end_date,
    }
    return render(request, 'emission_app/history.html', context)


def delete_record(request, record_id):
    """Delete an emission record."""
    if request.method == 'POST':
        record = get_object_or_404(EmissionRecord, pk=record_id)
        record.delete()
        messages.success(request, 'Record deleted successfully.')
    return redirect('history')