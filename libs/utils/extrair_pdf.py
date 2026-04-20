"""Script auxiliar para extrair texto do PDF modelo."""
import os
import sys

try:
    import fitz  # PyMuPDF
except ImportError:
    print("ERRO: pymupdf não instalado. Rode: pip install pymupdf")
    sys.exit(1)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PDF_MODELO = os.path.join(BASE_DIR, "Relatorio_Geracao_PCH-PIRA_2026.pdf")
PDF_TESTE = os.path.join(BASE_DIR, "Relatorio_Teste.pdf")

def extrair(pdf_path, nome):
    if not os.path.exists(pdf_path):
        print(f"ARQUIVO NAO ENCONTRADO: {pdf_path}")
        return
    doc = fitz.open(pdf_path)
    print(f"\n{'='*60}")
    print(f" {nome} — {doc.page_count} páginas")
    print(f"{'='*60}")
    for i, page in enumerate(doc):
        print(f"\n--- PAGINA {i+1} (tamanho: {page.rect.width:.0f}x{page.rect.height:.0f}) ---")
        print(page.get_text())
    doc.close()

if __name__ == "__main__":
    extrair(PDF_MODELO, "PDF MODELO")
    extrair(PDF_TESTE, "PDF TESTE")
