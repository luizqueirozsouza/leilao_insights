from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('auctions', '0004_reconcile_current_imoveis'),
    ]

    operations = [
        migrations.AddField(
            model_name='preferenciaalerta',
            name='tipos',
            field=models.JSONField(blank=True, default=list, verbose_name='Tipos de imóvel'),
        ),
    ]
