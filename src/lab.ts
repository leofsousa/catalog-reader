import { PdfReader } from "./pdf/PdfReader.js";

async function main() {
    const reader = await PdfReader.open("test-data/catalogo.pdf");

    console.log(`Número de páginas: ${reader.pageCount}`);

    for (const pageNumber of [1, 2, 3, 10, 20]) {
        const text = await reader.extractText(pageNumber);

        console.log(`\n--- Página ${pageNumber} ---`);
        console.log(`Caracteres encontrados: ${text.length}`);
        console.log(text.slice(0, 500));
    }
}

main().catch((error) => {
    console.error("Erro:", error);
    process.exit(1);
});