from PyPDF2 import PdfReader

def extract_text_from_pdf(file_obj) -> str:
    """Extract text from a PDF binary file-like object."""
    try:
        reader = PdfReader(file_obj)
        text = []
        for page in reader.pages:
            content = page.extract_text()
            if content:
                text.append(content)
        return "\n".join(text).strip()
    except Exception as e:
        raise ValueError(f"PDF extraction failed: {str(e)}")
