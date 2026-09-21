from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("library", "0005_book"),
    ]

    operations = [
        migrations.AddField(
            model_name="book",
            name="is_cached",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="book",
            name="cached_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="book",
            name="last_accessed",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="book",
            name="cache_size",
            field=models.PositiveBigIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="book",
            name="cache_expires_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
