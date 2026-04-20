"""Converte páginas do PDF modelo em imagens PNG para análise."""
import os
import sys

try:
    import fitz
except ImportError:
    print("ERRO: pip install pymupdf")
    sys.exit(1)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PDF_MODELO = os.path.join(BASE_DIR, "Relatorio_Geracao_PCH-PIRA_2026.pdf")
PDF_TESTE = os.path.join(BASE_DIR, "Relatorio_Teste.pdf")
OUT_DIR = os.path.join(BASE_DIR, "pdf_pages")
os.makedirs(OUT_DIR, exist_ok=True)

def pdf_to_images(pdf_path, prefix):
    if not os.path.exists(pdf_path):
        print(f"NAO ENCONTRADO: {pdf_path}")
        return
    doc = fitz.open(pdf_path)
    print(f"{prefix}: {doc.page_count} páginas")
    for i, page in enumerate(doc):
        pix = page.get_pixmap(dpi=150)
        img_path = os.path.join(OUT_DIR, f"{prefix}_p{i+1}.png")
        pix.save(img_path)
        print(f"  Salvo: {img_path}")
    
    # Extrair texto também
    txt_path = os.path.join(OUT_DIR, f"{prefix}_texto.txt")
    with open(txt_path, "w") as f:
        for i, page in enumerate(doc):
            f.write(f"=== PAGINA {i+1} ===\n")
            f.write(page.get_text())
            f.write("\n\n")
    print(f"  Texto: {txt_path}")
    doc.close()

if __name__ == "__main__":
    pdf_to_images(PDF_MODELO, "modelo")
    pdf_to_images(PDF_TESTE, "teste")
    print("\nPronto! Imagens salvas em:", OUT_DIR)
