# Generated by Django 5.2 on 2025-07-03 14:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0006_alter_variationcategory_options'),
    ]

    operations = [
        migrations.AlterField(
            model_name='variationcategory',
            name='name',
            field=models.CharField(max_length=100, unique=True, verbose_name='Variation Category Name'),
        ),
    ]
