from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('auctions', '0006_preferenciaalerta_telegram'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='preferenciaalerta',
            name='canal_telegram',
        ),
        migrations.RemoveField(
            model_name='preferenciaalerta',
            name='contato_telegram',
        ),
    ]