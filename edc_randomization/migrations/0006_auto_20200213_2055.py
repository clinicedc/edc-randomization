# Generated by Django 2.2.9 on 2020-02-13 17:55

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("edc_randomization", "0005_auto_20200202_2301"),
    ]

    operations = [
        migrations.AddField(
            model_name="historicalrandomizationlist",
            name="randomizer_name",
            field=models.CharField(default="default", max_length=50),
        ),
        migrations.AddField(
            model_name="randomizationlist",
            name="randomizer_name",
            field=models.CharField(default="default", max_length=50),
        ),
    ]
