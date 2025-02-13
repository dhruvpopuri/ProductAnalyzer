# Generated by Django 4.2.19 on 2025-02-13 07:19

from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='ProductTrend',
            fields=[
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('trend_date', models.DateField(auto_now_add=True)),
                ('trend_analysis', models.JSONField()),
            ],
            options={
                'get_latest_by': 'created_at',
            },
        ),
        migrations.CreateModel(
            name='Product',
            fields=[
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=255)),
                ('price', models.DecimalField(decimal_places=2, max_digits=10)),
                ('rating', models.DecimalField(decimal_places=2, max_digits=3, null=True)),
                ('description', models.TextField()),
                ('url', models.URLField()),
                ('ai_summary', models.TextField(blank=True, null=True)),
            ],
            options={
                'indexes': [models.Index(fields=['name'], name='analyzer_pr_name_b0f7f0_idx'), models.Index(fields=['price'], name='analyzer_pr_price_a6f80c_idx'), models.Index(fields=['rating'], name='analyzer_pr_rating_698b27_idx')],
            },
        ),
    ]
