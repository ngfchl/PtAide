# Generated by Django 4.2.1 on 2023-06-05 23:48

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('toolbox', '0001_initial'),
    ]

    operations = [
        migrations.DeleteModel(
            name='BaiduOCR',
        ),
        migrations.DeleteModel(
            name='Notify',
        ),
    ]
