# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("library", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="userplaylist",
            name="is_saved_explicit",
            field=models.BooleanField(
                default=True,
                help_text="True if user clicked Save; False if row was created from opening a playlist only.",
            ),
        ),
        migrations.AddField(
            model_name="userplaylist",
            name="last_opened_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="userplaylist",
            name="playlist_id",
            field=models.CharField(blank=True, db_index=True, max_length=50),
        ),
        migrations.AlterModelOptions(
            name="userplaylist",
            options={"ordering": ["-last_opened_at", "-created_at"]},
        ),
    ]
