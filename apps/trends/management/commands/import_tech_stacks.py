"""
Django management command to import/sync TechStack objects from a canonical CSV file.
"""
import csv
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.trends.models import TechStack

class Command(BaseCommand):
    help = 'Imports/Syncs TechStack objects from tech_stacks_source.csv.'

    def add_arguments(self, parser):
        parser.add_argument(
            'source_csv',
            type=str,
            nargs='?',
            default='tech_stacks_source.csv'
        )

    @transaction.atomic
    def handle(self, *args, **options):
        source_csv_path = options['source_csv']
        self.stdout.write(self.style.SUCCESS(f'--- Syncing TechStacks from {source_csv_path} ---'))

        try:
            with open(source_csv_path, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                created_count = 0
                updated_count = 0
                for row in reader:
                    stack_name = row.get('Name', '').strip()
                    if not stack_name:
                        continue

                    obj, created = TechStack.objects.get_or_create(
                        name=stack_name,
                        defaults={
                            'logo': row.get('Image', ''),
                            'docs_url': row.get('Link', 'replace_here')
                        }
                    )
                    
                    if created:
                        created_count += 1
                    else:
                        # Optionally update existing entries if needed
                        if (obj.logo != row.get('Image', '') or 
                            obj.docs_url != row.get('Link', 'replace_here')):
                            obj.logo = row.get('Image', '')
                            obj.docs_url = row.get('Link', 'replace_here')
                            obj.save()
                            updated_count += 1

            self.stdout.write(self.style.SUCCESS(f'Sync complete. Created: {created_count}, Updated: {updated_count}.'))

        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f'Source CSV file not found: {source_csv_path}.'))
            raise
