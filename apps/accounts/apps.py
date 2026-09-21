from django.apps import AppConfig
from django.conf import settings


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.accounts"
    label = "accounts"

    def ready(self):
        import apps.accounts.signals  # noqa: F401
        self._ensure_site_settings()

    def _ensure_site_settings(self):
        try:
            from django.contrib.sites.models import Site
            from django.db import OperationalError, connection
        except ImportError:
            return

        try:
            tables = connection.introspection.table_names()
        except OperationalError:
            return

        if "django_site" not in tables:
            return

        site_domain = getattr(settings, "SITE_DOMAIN", "127.0.0.1:8001")
        site_name = getattr(settings, "SITE_NAME", "Local Development")

        try:
            site, created = Site.objects.get_or_create(
                id=settings.SITE_ID,
                defaults={"domain": site_domain, "name": site_name},
            )
        except OperationalError:
            return

        if not created:
            changed = False
            if site.domain != site_domain:
                site.domain = site_domain
                changed = True
            if site.name != site_name:
                site.name = site_name
                changed = True
            if changed:
                site.save(update_fields=["domain", "name"])
