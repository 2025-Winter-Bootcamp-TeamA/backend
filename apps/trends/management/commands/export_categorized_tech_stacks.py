import csv
from django.core.management.base import BaseCommand
from apps.trends.models import TechStack, CategoryTech

class Command(BaseCommand):
    help = 'Exports categorized tech stacks to a CSV file.'

    def add_arguments(self, parser):
        parser.add_argument(
            'output_file',
            type=str,
            help='The path to the output CSV file.',
            nargs='?', # Makes it optional
            default='categorized_tech_stacks.csv' # Default value
        )

    def handle(self, *args, **options):
        output_file_path = options['output_file']
        
        self.stdout.write(self.style.SUCCESS(f'Starting export of categorized tech stacks to {output_file_path}...'))

        tech_stacks = TechStack.objects.all().prefetch_related('category_relations__category')

        with open(output_file_path, 'w', newline='', encoding='utf-8') as csvfile:
            csv_writer = csv.writer(csvfile)
            csv_writer.writerow(['Technology', 'Categories']) # Write header

            for tech_stack in tech_stacks:
                categories = [
                    ct.category.name
                    for ct in tech_stack.category_relations.all()
                ]
                # Format: "TechName:[Category1,Category2]"
                output_line = f'{tech_stack.name}:[{",".join(categories)}]'
                csv_writer.writerow([tech_stack.name, f'[{",".join(categories)}]']) # Write as two columns for better CSV parsing
                # For direct output as a single string: csv_writer.writerow([output_line])

        self.stdout.write(self.style.SUCCESS(f'Successfully exported {len(tech_stacks)} tech stacks.'))
