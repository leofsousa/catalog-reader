from pathlib import Path
import pymupdf


PDF_DIR = Path("test-data/catalogs")


def diagnose_pdf(pdf_path: Path) -> None:
    print("=" * 70)
    print(f"PDF: {pdf_path.name}")

    document = pymupdf.open(pdf_path)

    print(f"Páginas: {len(document)}")

    for page_number, page in enumerate(document, start=1):
        text = page.get_text("text").strip()
        char_count = len(text)

        print(f"\nPágina {page_number}: {char_count} caracteres")

        if text:
            sample = " ".join(text.split())[:200]
            print(f"  Amostra: {sample}")
        else:
            print("  Sem texto nativo")

    document.close()


def main() -> None:
    pdf_files = sorted(PDF_DIR.glob("*.pdf"))

    if not pdf_files:
        print(f"Nenhum PDF encontrado em: {PDF_DIR}")
        return

    print(f"Encontrados {len(pdf_files)} PDF(s).")

    for pdf_path in pdf_files:
        diagnose_pdf(pdf_path)


if __name__ == "__main__":
    main()