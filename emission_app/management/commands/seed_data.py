"""
Django management command to populate the database with sample data.
Usage: python manage.py seed_data
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from datetime import date, timedelta
from emission_app.models import ActivityType, EmissionRecord


class Command(BaseCommand):
    help = 'Seed database with sample activity types, emission records, and a demo user'

    def handle(self, *args, **options):
        # --- 1. Create demo superuser (login: demo / password: demo1234) ---
        if not User.objects.filter(username='demo').exists():
            User.objects.create_superuser(
                username='demo',
                email='demo@example.com',
                password='demo1234',
            )
            self.stdout.write(self.style.SUCCESS('✓ Created demo superuser (demo / demo1234)'))
        else:
            self.stdout.write('  Demo user already exists, skipping.')

        # --- 2. Create activity types (same as my-app's CLI version) ---
        activity_types = [
            ("Car Travel", 0.21, "km"),
            ("Bus Travel", 0.089, "km"),
            ("Train Travel", 0.041, "km"),
            ("Air Travel", 0.255, "km"),
            ("Electricity Usage", 0.475, "kWh"),
            ("Natural Gas", 2.0, "m³"),
            ("Coal Burning", 2.86, "kg"),
            ("Waste Production", 0.5, "kg"),
            ("Water Usage", 0.344, "m³"),
            ("Paper Usage", 1.32, "kg"),
        ]

        created_activities = {}
        for name, factor, unit in activity_types:
            obj, created = ActivityType.objects.get_or_create(
                activity_name=name,
                defaults={'emission_factor': factor, 'unit': unit},
            )
            created_activities[name] = obj
            status = 'Created' if created else 'Exists'
            self.stdout.write(f'  {status}: {name} ({factor} kg CO2/{unit})')

        self.stdout.write(self.style.SUCCESS(f'✓ {len(activity_types)} activity types ready'))

        # --- 3. Create sample emission records ---
        if EmissionRecord.objects.exists():
            self.stdout.write('  Emission records already exist, skipping sample data.')
            return

        today = date.today()
        sample_records = [
            ("Car Travel", 25.5, 0, "Daily commute to office"),
            ("Electricity Usage", 150.0, 0, "Home electricity usage"),
            ("Bus Travel", 12.0, 1, "Bus commute to downtown"),
            ("Car Travel", 45.0, 1, "Weekend road trip"),
            ("Air Travel", 350.0, 2, "Business flight to conference"),
            ("Electricity Usage", 200.0, 2, "Apartment electricity"),
            ("Train Travel", 30.0, 3, "Train commute"),
            ("Natural Gas", 15.5, 3, "Heating - natural gas"),
            ("Waste Production", 5.0, 4, "Household waste"),
            ("Paper Usage", 2.5, 5, "Office paper usage"),
            ("Water Usage", 8.0, 5, "Household water usage"),
            ("Car Travel", 60.0, 6, "Long drive to countryside"),
        ]

        count = 0
        for activity_name, quantity, days_ago, description in sample_records:
            activity = created_activities.get(activity_name)
            if activity:
                EmissionRecord.objects.create(
                    activity=activity,
                    quantity=quantity,
                    date=today - timedelta(days=days_ago),
                    description=description,
                )
                count += 1

        self.stdout.write(self.style.SUCCESS(f'✓ {count} sample emission records created'))
        self.stdout.write(self.style.SUCCESS('\n🎉 Database seeded successfully!'))
        self.stdout.write(self.style.SUCCESS('   Demo login → username: demo | password: demo1234'))