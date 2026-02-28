"""
Tests for the emission_app views - Dashboard, Activity, and History sections.
"""

from django.test import TestCase, Client
from django.urls import reverse
from datetime import date, timedelta

from .models import ActivityType, EmissionRecord


class EmissionAppSetup(TestCase):
    def setUp(self):
        self.client = Client()
        self.car = ActivityType.objects.create(
            activity_name='Car Travel',
            emission_factor=0.21,
            unit='km'
        )
        self.elec = ActivityType.objects.create(
            activity_name='Electricity Usage',
            emission_factor=0.475,
            unit='kWh'
        )
        self.record1 = EmissionRecord.objects.create(
            activity=self.car,
            quantity=100.0,
            date=date.today(),
            description='Test drive'
        )
        self.record2 = EmissionRecord.objects.create(
            activity=self.elec,
            quantity=200.0,
            date=date.today() - timedelta(days=3),
            description='Monthly electricity'
        )


class DashboardViewTest(EmissionAppSetup):
    def test_dashboard_loads(self):
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'emission_app/dashboard.html')

    def test_dashboard_shows_stats(self):
        response = self.client.get(reverse('dashboard'))
        self.assertIn('total_emissions', response.context)
        self.assertIn('total_records', response.context)
        self.assertIn('avg_emission', response.context)
        self.assertEqual(response.context['total_records'], 2)

    def test_dashboard_shows_recent_records(self):
        response = self.client.get(reverse('dashboard'))
        self.assertIn('recent_records', response.context)
        self.assertGreater(len(response.context['recent_records']), 0)

    def test_dashboard_shows_daily_data(self):
        response = self.client.get(reverse('dashboard'))
        self.assertIn('daily_data', response.context)
        self.assertEqual(len(response.context['daily_data']), 7)


class ActivityViewTest(EmissionAppSetup):
    def test_activity_loads(self):
        response = self.client.get(reverse('activity'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'emission_app/activity.html')

    def test_activity_shows_activity_types(self):
        response = self.client.get(reverse('activity'))
        self.assertIn('activity_types', response.context)
        self.assertEqual(response.context['activity_types'].count(), 2)

    def test_add_emission_record(self):
        initial_count = EmissionRecord.objects.count()
        response = self.client.post(reverse('activity'), {
            'action': 'add_record',
            'activity_id': self.car.id,
            'quantity': '50.0',
            'date': str(date.today()),
            'description': 'Test record',
        })
        self.assertRedirects(response, reverse('activity'))
        self.assertEqual(EmissionRecord.objects.count(), initial_count + 1)

    def test_add_activity_type(self):
        initial_count = ActivityType.objects.count()
        response = self.client.post(reverse('activity'), {
            'action': 'add_activity',
            'activity_name': 'Bus Travel',
            'emission_factor': '0.089',
            'unit': 'km',
        })
        self.assertRedirects(response, reverse('activity'))
        self.assertEqual(ActivityType.objects.count(), initial_count + 1)

    def test_add_record_invalid_quantity(self):
        response = self.client.post(reverse('activity'), {
            'action': 'add_record',
            'activity_id': self.car.id,
            'quantity': 'not-a-number',
            'date': str(date.today()),
        })
        self.assertRedirects(response, reverse('activity'))


class HistoryViewTest(EmissionAppSetup):
    def test_history_loads(self):
        response = self.client.get(reverse('history'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'emission_app/history.html')

    def test_history_shows_all_records(self):
        response = self.client.get(reverse('history'))
        self.assertIn('records', response.context)
        self.assertEqual(len(response.context['records']), 2)

    def test_history_shows_total(self):
        response = self.client.get(reverse('history'))
        self.assertIn('total_filtered', response.context)
        expected_total = round(
            self.record1.emission_amount + self.record2.emission_amount, 2
        )
        self.assertAlmostEqual(
            float(response.context['total_filtered']), expected_total, places=1
        )

    def test_history_filter_by_activity(self):
        response = self.client.get(
            reverse('history'), {'activity': str(self.car.id)}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['records']), 1)
        self.assertEqual(
            response.context['records'][0].activity.activity_name, 'Car Travel'
        )

    def test_history_filter_by_date_range(self):
        today = date.today()
        response = self.client.get(reverse('history'), {
            'start_date': str(today),
            'end_date': str(today),
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['records']), 1)

    def test_history_shows_activity_types_for_filter(self):
        response = self.client.get(reverse('history'))
        self.assertIn('activity_types', response.context)
        self.assertEqual(response.context['activity_types'].count(), 2)

    def test_delete_record(self):
        initial_count = EmissionRecord.objects.count()
        response = self.client.post(
            reverse('delete_record', args=[self.record1.id])
        )
        self.assertRedirects(response, reverse('history'))
        self.assertEqual(EmissionRecord.objects.count(), initial_count - 1)

    def test_history_empty_when_no_records_match_filter(self):
        future_date = str(date.today() + timedelta(days=365))
        response = self.client.get(reverse('history'), {
            'start_date': future_date,
            'end_date': future_date,
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['records']), 0)