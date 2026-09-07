from pathlib import Path
import pypdfium2 as pdfium
import docx
from docx import Document
import openpyxl


# ---------- PDF ----------
def pdf_text(pdf_path: str | Path) -> str:
    """Extracts text from a PDF file.
        Args:
            pdf_path: Path to the PDF file (string or Path object).
        Returns:
            A string with the text extracted from all pages of the PDF
    """
    with pdfium.PdfDocument(pdf_path) as pdf:
        return "\n".join(
            pdf[idx].get_textpage().get_text_range()
            for idx in range(len(pdf))
        )


# ---------- DOCX ----------
def docx_text(docx_path: str | Path) -> str:
    """Extracts text from a DOCX file.
        Args:
            docx_path: Path to the DOCX file (string or Path object).

        Returns:
            A string with the text of all non-empty paragraphs in the document
    """
    return "\n".join(p.text for p in docx.Document(docx_path).paragraphs if p.text.strip())


# ---------- XLSX ----------
def xlsx_text(xlsx_path: str | Path) -> str:
    """Extracts text from an XLSX file as markdown tables (one per sheet).
        Args:
            xlsx_path: Path to the XLSX file (string or Path object).

        Returns:
            A string with the contents of all sheets in the workbook as markdown tables
    """
    workbook = openpyxl.load_workbook(xlsx_path, data_only=True, read_only=True)
    sheets_text = []
    for sheet in workbook.worksheets:
        rows = [
            [("" if cell is None else str(cell)) for cell in row]
            for row in sheet.iter_rows(values_only=True)
            if any(cell is not None for cell in row)
        ]
        if not rows:
            continue
        lines = [f"### {sheet.title}", "| " + " | ".join(rows[0]) + " |"]
        lines.append("| " + " | ".join(["---"] * len(rows[0])) + " |")
        for row in rows[1:]:
            lines.append("| " + " | ".join(row) + " |")
        sheets_text.append("\n".join(lines))
    return "\n\n".join(sheets_text)


# ---------- auto-route ----------
def document_to_txt(file_path: str | Path) -> str:
    """Determines the document type and extracts text based on the file extension.
        Args:
            file_path: Path to the document file (string or Path object).

        Returns:
            The document's text
    """
    try:
        file_path = Path(file_path)
        suffix = file_path.suffix.lower()
        if suffix == ".pdf":
            result_txt = pdf_text(file_path)
            if result_txt == "":
                return "This is a scanned PDF file, tell the user that the text could not be read"
            return result_txt
        elif suffix == ".docx":
            return docx_text(file_path)
        elif suffix == ".xlsx":
            result_txt = xlsx_text(file_path)
            if result_txt == "":
                return "The file is empty, tell the user that the text could not be read"
            return result_txt
        else:
            return "tell the user, Only .pdf, .docx and .xlsx supported"
    except Exception as e:
        return f"An error occurred: {e}"


def text_to_docx(text: str, file_path: str | Path ):
    doc = Document()

    # Add the text to the document
    doc.add_paragraph(text)

    # Save the document
    doc.save(str(file_path))




# ---------- use ----------
# text = document_to_txt("files/ggg.pdf")  # or .docx
# messages = [("human", f"Summarise this:\n\n{text}")]
# print(text)
