"""
Django management command to apply categorization from a canonical CSV file.
"""
import csv
import re
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.trends.models import TechStack, Category, CategoryTech

class Command(BaseCommand):
    help = 'Applies categories to TechStacks from categorized_tech_stacks_final.csv.'

    def add_arguments(self, parser):
        parser.add_argument(
            'source_csv',
            type=str,
            nargs='?',
            default='categorized_tech_stacks_final.csv'
        )

    @transaction.atomic
    def handle(self, *args, **options):
        source_csv_path = options['source_csv']
        self.stdout.write(self.style.SUCCESS(f'--- Applying categories from {source_csv_path} ---'))

        # Step 1: Clear all existing category relationships for a clean slate
        self.stdout.write('Clearing all existing tech-category relationships...')
        deleted_count, _ = CategoryTech.objects.all().delete()
        self.stdout.write(f'  - Deleted {deleted_count} old relationships.')

        # Step 2: Read the CSV and apply new categories
        try:
            with open(source_csv_path, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                tech_category_map = {}
                for row in reader:
                    tech_name = row.get('Technology')
                    # Categories are in a string like '[Category1,Category2]'
                    cat_string = row.get('Categories', '[]')
                    # Use regex to extract category names
                    cat_names = re.findall(r'[\w\s&-]+', cat_string)
                    if tech_name:
                        tech_category_map[tech_name] = [name.strip() for name in cat_names]

            self.stdout.write(f'Found {len(tech_category_map)} technologies in the CSV to categorize.')
            
            # Get all tech stacks and categories from DB for efficiency
            all_tech_stacks = {ts.name: ts for ts in TechStack.objects.all()}
            all_categories = {cat.name: cat for cat in Category.objects.all()}

            # Create categories that exist in the CSV but not in the DB
            all_csv_cats = set(cat for cats in tech_category_map.values() for cat in cats)
            for cat_name in all_csv_cats:
                if cat_name not in all_categories:
                    new_cat = Category.objects.create(name=cat_name)
                    all_categories[cat_name] = new_cat
                    self.stdout.write(self.style.SUCCESS(f'  - Created new category: "{cat_name}"'))
            
            # Create the relationships
            relations_created = 0
            for tech_name, cat_names in tech_category_map.items():
                if tech_name in all_tech_stacks:
                    tech_stack = all_tech_stacks[tech_name]
                    for cat_name in cat_names:
                        if cat_name in all_categories:
                            CategoryTech.objects.create(
                                tech_stack=tech_stack,
                                category=all_categories[cat_name]
                            )
                            relations_created += 1
                else:
                    self.stdout.write(self.style.WARNING(f'  - TechStack "{tech_name}" from CSV not found in database. Skipping.'))

            self.stdout.write(self.style.SUCCESS(f'Sync complete. Created {relations_created} new category relationships.'))

        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f'Source CSV file not found: {source_csv_path}.'))
            raise
