import os
import django
import re
import sys
from pathlib import Path

# Setup Django
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend_django.core.settings')
django.setup()

from backend_django.auctions.models import Auction

def clean_money(val):
    if not val: return 0
    # Remove R$, espaços e converte formato BR (1.234,56) para US (1234.56)
    s = str(val).replace("R$", "").replace(" ", "").strip()
    if not s: return 0
    
    # Se tem ponto e vírgula (ex: 1.234,56)
    if "." in s and "," in s:
        s = s.replace(".", "").replace(",", ".")
    # Se tem apenas vírgula como decimal (ex: 1234,56)
    elif "," in s:
        s = s.replace(",", ".")
        
    try:
        return float(re.sub(r"[^\d.]", "", s))
    except:
        return 0

def populate():
    auctions = Auction.objects.all()
    total = auctions.count()
    print(f"Recalculando e populando {total} leilões...")
    
    batch_size = 1000
    updates = []
    
    for i, a in enumerate(auctions):
        payload = a.payload_json
        if not payload: continue
        
        a.cidade = payload.get("Cidade")
        a.bairro = payload.get("Bairro")
        a.endereco = payload.get("Endereço")
        a.preco = clean_money(payload.get("Preço"))
        a.valor_avaliacao = clean_money(payload.get("Valor de avaliação"))
        
        # Cálculo manual do desconto para precisão
        if a.valor_avaliacao and a.valor_avaliacao > 0 and a.preco:
            a.desconto = ((a.valor_avaliacao - a.preco) / a.valor_avaliacao) * 100
        else:
            # Fallback para o valor do CSV se não der pra calcular
            a.desconto = clean_money(payload.get("Desconto"))
            
        a.descricao = payload.get("Descrição")
        a.modalidade = payload.get("Modalidade de venda")
        a.link = payload.get("Link de acesso")
        
        updates.append(a)
        
        if len(updates) >= batch_size:
            Auction.objects.bulk_update(updates, ['cidade', 'bairro', 'endereco', 'preco', 'valor_avaliacao', 'desconto', 'descricao', 'modalidade', 'link'])
            print(f"Processado: {i+1} / {total}")
            updates = []
            
    if updates:
        Auction.objects.bulk_update(updates, ['cidade', 'bairro', 'endereco', 'preco', 'valor_avaliacao', 'desconto', 'descricao', 'modalidade', 'link'])
        print(f"Processado: {total} / {total}")
    
    print("Dados populados e descontos recalculados com sucesso!")

if __name__ == "__main__":
    populate()
