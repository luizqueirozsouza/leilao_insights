# Reconciliacao do estado legado do banco.
#
# O modelo Auction sempre apontou para a tabela `current_imoveis` (db_table),
# mas as migrations 0001/0002 foram aplicadas quando o modelo ainda apontava
# para a tabela padrao `auctions_auction` (vazia, nunca usada). Como
# `current_imoveis` ja existe (criada pelo pipeline via SQL), a migration de
# reconciliacao alinha o ESTADO do Django para `current_imoveis` sem renomear
# tabelas (evita conflito) e remove a tabela fantasma `auctions_auction`.

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('auctions', '0003_assinatura_notificacaoenviada_preferenciaalerta_and_more'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AlterModelTable(
                    name='auction',
                    table='current_imoveis',
                ),
            ],
            database_operations=[
                migrations.RunSQL("DROP TABLE IF EXISTS auctions_auction"),
                migrations.RunSQL(
                    "CREATE INDEX IF NOT EXISTS idx_uf_cidade ON current_imoveis (uf, cidade)"
                ),
                migrations.RunSQL(
                    "CREATE INDEX IF NOT EXISTS idx_uf_cidade_bairro ON current_imoveis (uf, cidade, bairro)"
                ),
                migrations.RunSQL(
                    "CREATE INDEX IF NOT EXISTS idx_uf_modalidade ON current_imoveis (uf, modalidade)"
                ),
                migrations.RunSQL(
                    "CREATE INDEX IF NOT EXISTS idx_cidade_modalidade ON current_imoveis (cidade, modalidade)"
                ),
                migrations.RunSQL(
                    "CREATE INDEX IF NOT EXISTS idx_preco ON current_imoveis (preco)"
                ),
                migrations.RunSQL(
                    "CREATE INDEX IF NOT EXISTS idx_valor_avaliacao ON current_imoveis (valor_avaliacao)"
                ),
                migrations.RunSQL(
                    "CREATE INDEX IF NOT EXISTS idx_tipo_imovel ON current_imoveis (tipo_imovel)"
                ),
            ],
        ),
    ]
