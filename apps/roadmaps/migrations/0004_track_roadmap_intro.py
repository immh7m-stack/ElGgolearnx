# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("roadmaps", "0003_alter_playlist_options_playlist_order_num_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="track",
            name="roadmap_intro",
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text="Optional: skills_ar/en, tips_ar/en lists for track intro / notes.",
            ),
        ),
    ]
