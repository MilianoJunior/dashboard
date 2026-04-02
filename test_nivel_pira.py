# -------------------------------------------------------------------
# SCRIPT DE DIAGNÓSTICO — Consulta nível PCH-PIRA via API
# Uso: python test_nivel_pira.py
# -------------------------------------------------------------------
import json
from urllib import request, error
from datetime import datetime, timedelta

URL_API = "https://engesepapi-production.up.railway.app"
TOKEN = "12345678"

agora = datetime.now()
payload = {
    "usina": "PCH-PIRA",
    "grupo": "hidraulica",
    "data_inicio": (agora - timedelta(days=1)).strftime("%d/%m/%Y %H:%M"),
    "data_fim": agora.strftime("%d/%m/%Y %H:%M"),
    "token": TOKEN,
}

print(f"Payload: {json.dumps(payload, indent=2)}")
print()

req = request.Request(
    f"{URL_API}/grupo-usina",
    data=json.dumps(payload).encode("utf-8"),
    headers={"Content-Type": "application/json"},
    method="POST",
)

try:
    with request.urlopen(req) as resp:
        raw = resp.read().decode("utf-8")
        data = json.loads(raw)
        
        print(f"Chaves da resposta: {list(data.keys())}")
        print(f"Tipo de 'dados': {type(data.get('dados'))}")
        print(f"Tipo de 'resultado': {type(data.get('resultado'))}")
        print()
        
        # Mostrar primeiros 3 registros completos
        for key in ("dados", "resultado"):
            items = data.get(key)
            if isinstance(items, list) and items:
                print(f"--- {key} ({len(items)} registros) ---")
                for i, item in enumerate(items[:3]):
                    print(f"  [{i}] {json.dumps(item, ensure_ascii=False)}")
                print()
            elif items is not None:
                print(f"--- {key} (tipo: {type(items).__name__}) ---")
                print(f"  {str(items)[:500]}")
                print()
                
        # Se nenhum dos dois existir, printar resposta bruta
        if not data.get("dados") and not data.get("resultado"):
            print("Resposta bruta (truncada):")
            print(raw[:1000])

except error.HTTPError as e:
    print(f"HTTP {e.code}: {e.read().decode()}")
except Exception as e:
    print(f"Erro: {e}")
