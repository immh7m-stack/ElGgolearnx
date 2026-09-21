from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Fill missing CuratedBook thumbnails using Open Library covers"

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=None, help="Max number of books to process")
        parser.add_argument("--dry-run", action="store_true", help="Don't save changes; just show what would be updated")

    def handle(self, *args, **options):
        from apps.library.services import books as book_services

        limit = options.get("limit")
        dry_run = options.get("dry_run")
        updated = book_services.fill_curated_book_thumbnails(limit=limit, dry_run=dry_run)
        self.stdout.write(self.style.SUCCESS(f"Updated {updated} CuratedBook thumbnails"))
