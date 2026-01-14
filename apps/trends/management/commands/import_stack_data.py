import csv
from django.core.management.base import BaseCommand
from apps.trends.models import TechStack

class Command(BaseCommand):
    help = 'Import tech stack data from a CSV file'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='The path to the CSV file to import.')

    def handle(self, *args, **options):
        csv_file_path = options['csv_file']
        with open(csv_file_path, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                tech_stack, created = TechStack.objects.get_or_create(
                    name=row['Name'],
                    defaults={
                        'logo': row['Image'],
                        'docs_url': row['Link']
                    }
                )
                if created:
                    self.stdout.write(self.style.SUCCESS(f'Successfully created TechStack: {tech_stack.name}'))
                else:
                    self.stdout.write(self.style.WARNING(f'TechStack already exists: {tech_stack.name}'))
