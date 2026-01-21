"""
Django management command to apply categorization from tech_stacks_merged_final.csv using TECH_TO_CATEGORIES mapping.
"""
import csv
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.trends.models import TechStack, Category, CategoryTech
from apps.trends.management.commands.categorize_stacks import TECH_TO_CATEGORIES

class Command(BaseCommand):
    help = 'Applies categories to TechStacks from tech_stacks_merged_final.csv using TECH_TO_CATEGORIES mapping.'

    def add_arguments(self, parser):
        parser.add_argument(
            'source_csv',
            type=str,
            nargs='?',
            default='tech_stacks_merged_final.csv'
        )

    @transaction.atomic
    def handle(self, *args, **options):
        source_csv_path = options['source_csv']
        self.stdout.write(self.style.SUCCESS(f'--- Applying categories from {source_csv_path} ---'))

        # Step 1: Clear all existing category relationships for a clean slate
        self.stdout.write('Clearing all existing tech-category relationships...')
        deleted_count, _ = CategoryTech.objects.all().delete()
        self.stdout.write(f'  - Deleted {deleted_count} old relationships.')

        # Step 2: Read the CSV and get tech stack names
        try:
            tech_names_from_csv = []
            with open(source_csv_path, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    tech_name = row.get('name', '').strip()
                    if tech_name:
                        tech_names_from_csv.append(tech_name)

            self.stdout.write(f'Found {len(tech_names_from_csv)} technologies in the CSV.')
            
            # Step 3: Get all tech stacks and categories from DB for efficiency
            all_tech_stacks = {ts.name: ts for ts in TechStack.objects.all()}
            all_categories = {cat.name: cat for cat in Category.objects.all()}

            # Step 4: Collect all categories that will be used
            all_used_categories = set()
            for tech_name in tech_names_from_csv:
                if tech_name in TECH_TO_CATEGORIES:
                    all_used_categories.update(TECH_TO_CATEGORIES[tech_name])

            # Step 5: Create categories that don't exist in the DB
            for cat_name in all_used_categories:
                if cat_name not in all_categories:
                    new_cat = Category.objects.create(name=cat_name)
                    all_categories[cat_name] = new_cat
                    self.stdout.write(self.style.SUCCESS(f'  - Created new category: "{cat_name}"'))
            
            # Step 6: Create the relationships
            relations_created = 0
            tech_with_categories = 0
            tech_without_categories = 0
            
            for tech_name in tech_names_from_csv:
                if tech_name in all_tech_stacks:
                    tech_stack = all_tech_stacks[tech_name]
                    
                    # Look up categories from TECH_TO_CATEGORIES
                    if tech_name in TECH_TO_CATEGORIES:
                        cat_names = TECH_TO_CATEGORIES[tech_name]
                        tech_with_categories += 1
                        for cat_name in cat_names:
                            if cat_name in all_categories:
                                CategoryTech.objects.create(
                                    tech_stack=tech_stack,
                                    category=all_categories[cat_name]
                                )
                                relations_created += 1
                    else:
                        tech_without_categories += 1
                        self.stdout.write(self.style.WARNING(f'  - TechStack "{tech_name}" not found in TECH_TO_CATEGORIES. Skipping.'))
                else:
                    self.stdout.write(self.style.WARNING(f'  - TechStack "{tech_name}" from CSV not found in database. Skipping.'))

            self.stdout.write(self.style.SUCCESS(
                f'Sync complete. Created {relations_created} new category relationships.\n'
                f'  - Tech stacks with categories: {tech_with_categories}\n'
                f'  - Tech stacks without categories (not in TECH_TO_CATEGORIES): {tech_without_categories}'
            ))

        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f'Source CSV file not found: {source_csv_path}.'))
            raise
