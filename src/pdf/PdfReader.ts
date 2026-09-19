import * as pdfjsLib from "pdfjs-dist/legacy/build/pdf.mjs";

export class PdfReader {
    private document: pdfjsLib.PDFDocumentProxy;

    private constructor(document: pdfjsLib.PDFDocumentProxy) {
        this.document = document;
    }

    static async open(filePath: string): Promise<PdfReader> {
        const loadingTask = pdfjsLib.getDocument({
            url: filePath
        });

        const document = await loadingTask.promise;

        return new PdfReader(document);
    }

    get pageCount(): number {
        return this.document.numPages;
    }

    async extractText(pageNumber: number): Promise<string> {
        const page = await this.document.getPage(pageNumber);
        const content = await page.getTextContent();

        const textItems = content.items
            .filter((item) => "str" in item)
            .map((item) => item.str);

        return textItems.join(" ");
    }
}