from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('auctions', '0005_preferenciaalerta_tipos'),
    ]

    operations = [
        migrations.RenameField(
            model_name='preferenciaalerta',
            old_name='canal_whatsapp',
            new_name='canal_telegram',
        ),
        migrations.RenameField(
            model_name='preferenciaalerta',
            old_name='contato_whatsapp',
            new_name='contato_telegram',
        ),
        migrations.AlterField(
            model_name='preferenciaalerta',
            name='canal_telegram',
            field=models.BooleanField(default=False, verbose_name='Notificar por Telegram'),
        ),
        migrations.AlterField(
            model_name='preferenciaalerta',
            name='contato_telegram',
            field=models.CharField(
                blank=True,
                default='',
                max_length=100,
                verbose_name='Telegram (chat ID)',
            ),
        ),
    ]
