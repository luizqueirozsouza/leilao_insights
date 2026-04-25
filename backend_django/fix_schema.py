import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.db import connection

def fix_schema():
    with connection.cursor() as cursor:
        print("Adicionando colunas à tabela current_imoveis...")
        sql = """
        ALTER TABLE current_imoveis ADD COLUMN IF NOT EXISTS cidade VARCHAR(255);
        ALTER TABLE current_imoveis ADD COLUMN IF NOT EXISTS bairro VARCHAR(255);
        ALTER TABLE current_imoveis ADD COLUMN IF NOT EXISTS endereco TEXT;
        ALTER TABLE current_imoveis ADD COLUMN IF NOT EXISTS preco DECIMAL(15,2);
        ALTER TABLE current_imoveis ADD COLUMN IF NOT EXISTS valor_avaliacao DECIMAL(15,2);
        ALTER TABLE current_imoveis ADD COLUMN IF NOT EXISTS desconto DECIMAL(5,2);
        ALTER TABLE current_imoveis ADD COLUMN IF NOT EXISTS descricao TEXT;
        ALTER TABLE current_imoveis ADD COLUMN IF NOT EXISTS modalidade VARCHAR(255);
        ALTER TABLE current_imoveis ADD COLUMN IF NOT EXISTS link TEXT;
        ALTER TABLE current_imoveis ADD COLUMN IF NOT EXISTS fingerprint VARCHAR(32);
        """
        cursor.execute(sql)
        
        print("Adicionando colunas à tabela changes...")
        sql_changes = """
        ALTER TABLE changes ADD COLUMN IF NOT EXISTS auction_id INTEGER;
        """
        cursor.execute(sql_changes)
        
    print("Esquema atualizado com sucesso!")

if __name__ == "__main__":
    fix_schema()
