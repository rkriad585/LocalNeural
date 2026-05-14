import io
import csv
import json
from pypdf import PdfReader

def extract_text_from_file(file_storage):
    filename = file_storage.filename.lower()
    text_content = ""

    try:
        if filename.endswith('.pdf'):
            try:
                pdf_file = io.BytesIO(file_storage.read())
                reader = PdfReader(pdf_file)
                for page in reader.pages:
                    extracted = page.extract_text()
                    if extracted:
                        text_content += extracted + "\n"

                if not text_content.strip():
                    return ""

            except Exception as e:
                return f"[Error parsing PDF {filename}: {str(e)}]"

        elif filename.endswith('.docx'):
            try:
                from docx import Document
                file_storage.seek(0)
                doc = Document(file_storage)
                for para in doc.paragraphs:
                    text_content += para.text + "\n"
                if not text_content.strip():
                    return ""
            except Exception as e:
                return f"[Error parsing DOCX {filename}: {str(e)}]"

        elif filename.endswith('.csv'):
            try:
                file_storage.seek(0)
                content = file_storage.read().decode('utf-8', errors='replace')
                reader = csv.reader(io.StringIO(content))
                for i, row in enumerate(reader):
                    text_content += " | ".join(row) + "\n"
                if not text_content.strip():
                    return ""
            except Exception as e:
                return f"[Error parsing CSV {filename}: {str(e)}]"

        elif filename.endswith('.json'):
            try:
                file_storage.seek(0)
                content = file_storage.read().decode('utf-8', errors='replace')
                data = json.loads(content)
                text_content = json.dumps(data, indent=2)
                if not text_content.strip():
                    return ""
            except Exception as e:
                return f"[Error parsing JSON {filename}: {str(e)}]"

        else:
            try:
                file_storage.seek(0)
                content = file_storage.read().decode('utf-8', errors='replace')
                text_content = content
            except Exception as e:
                return f"[Error reading text file {filename}: {str(e)}]"

        return text_content

    except Exception as e:
        return f"[System Error processing file: {str(e)}]"


def extract_html_text(html):
    import re
    text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    return '\n'.join(lines[:200])
