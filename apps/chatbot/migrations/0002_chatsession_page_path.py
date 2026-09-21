# Generated manually for chat page context

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("chatbot", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="chatsession",
            name="page_path",
            field=models.CharField(blank=True, default="", max_length=512),
        ),
    ]
