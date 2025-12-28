import io
from pypdf import PdfReader

def extract_text_from_file(file_storage):
    """
    Robust text extractor for Uploaded Knowledge Base.
    Function: extract_text_from_file
    """
    filename = file_storage.filename.lower()
    text_content = ""

    try:
        # 1. PDF Handling
        if filename.endswith('.pdf'):
            try:
                # Wrap stream for pypdf
                pdf_file = io.BytesIO(file_storage.read())
                reader = PdfReader(pdf_file)
                for page in reader.pages:
                    extracted = page.extract_text()
                    if extracted:
                        text_content += extracted + "\n"
                
                # If PDF text layer is empty (scanned image), warn user (OCR is too heavy for this scope)
                if not text_content.strip():
                    return f"[Warning: PDF {filename} appears to be empty or scanned images. No text text found.]"
                    
            except Exception as e:
                return f"[Error parsing PDF {filename}: {str(e)}]"

        # 2. Text/Code Handling (.py, .js, .md, .txt, .json, .html, .css, etc.)
        else:
            try:
                # content = file_storage.read().decode('utf-8') # Stream might be consumed by PDF check if logic flows wrong
                # Reset stream pointer just in case
                file_storage.seek(0)
                content = file_storage.read().decode('utf-8', errors='replace')
                text_content = content
            except Exception as e:
                return f"[Error reading text file {filename}: {str(e)}]"

        return text_content

    except Exception as e:
        return f"[System Error processing file: {str(e)}]"
