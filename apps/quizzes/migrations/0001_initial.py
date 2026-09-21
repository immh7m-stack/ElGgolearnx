# Generated for quizzes app

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='VideoQuizCatalog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('video_id', models.CharField(db_index=True, max_length=50, unique=True)),
                ('title', models.CharField(blank=True, max_length=255, null=True)),
                ('is_generated', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'Video Quiz Catalog',
                'verbose_name_plural': 'Video Quiz Catalogs',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='Question',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('question_type', models.CharField(choices=[('MICRO', 'Micro Question (5-10 min mark)'), ('FINAL', 'Comprehensive Question (Self-Test)')], max_length=10)),
                ('timestamp_start', models.PositiveIntegerField(default=0, help_text='بداية الجزئية بالثواني')),
                ('timestamp_end', models.PositiveIntegerField(default=0, help_text='نهاية الجزئية بالثواني')),
                ('text', models.TextField(help_text='نص السؤال بالعربي مع المصطلحات التقنية بالإنجليزي')),
                ('options', models.JSONField(help_text="قائمة الاختيارات ['A', 'B', 'C', 'D']")),
                ('correct_answer', models.CharField(max_length=255)),
                ('explanation', models.TextField(help_text='الشرح لتعزيز التعلم النشط')),
                ('catalog', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='questions', to='quizzes.videoquizcatalog')),
            ],
            options={
                'verbose_name': 'Question',
                'verbose_name_plural': 'Questions',
                'ordering': ['timestamp_start', 'id'],
            },
        ),
        migrations.CreateModel(
            name='QuizAttempt',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('score', models.FloatField(default=0.0)),
                ('user_answers', models.JSONField(default=dict)),
                ('completed_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                ('video_catalog', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='attempts', to='quizzes.videoquizcatalog')),
            ],
            options={
                'verbose_name': 'Quiz Attempt',
                'verbose_name_plural': 'Quiz Attempts',
                'ordering': ['-completed_at'],
            },
        ),
    ]
