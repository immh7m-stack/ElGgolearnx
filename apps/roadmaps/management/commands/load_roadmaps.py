from django.core.management.base import BaseCommand

from apps.roadmaps.loaders import load_all_roadmaps


class Command(BaseCommand):
    help = "Load roadmap JSON files from data/roadmaps/ into the database"

    def handle(self, *args, **options):
        fields = load_all_roadmaps()
        self.stdout.write(self.style.SUCCESS(f"Loaded {len(fields)} field(s): {', '.join(f.slug for f in fields)}"))
