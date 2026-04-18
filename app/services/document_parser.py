"""Document parser service for multiple file formats"""
import io
import gc
import logging
from typing import Dict, Any, List
from pathlib import Path
import json
from app.config import settings

logger = logging.getLogger(__name__)

# PDF parsing
try:
    from PyPDF2 import PdfReader
except ImportError:
    PdfReader = None

# Word document parsing
try:
    from docx import Document as DocxDocument
except ImportError:
    DocxDocument = None

# Excel parsing
try:
    import pandas as pd
except ImportError:
    pd = None

# HTML parsing
try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

# Markdown parsing
try:
    import markdown
except ImportError:
    markdown = None


class DocumentParser:
    """Parse various document formats to extract text content"""
    
    @staticmethod
    def parse_pdf(file_content: bytes) -> str:
        """Extract text from PDF with STRICT memory limits"""
        if PdfReader is None:
            raise ImportError("PyPDF2 not installed. Install with: pip install pypdf2")
        
        # ULTRA-STRICT file size limit for mid-spec laptops
        max_size_mb = min(settings.max_parse_size_mb, 5)  # Max 5MB
        if len(file_content) > max_size_mb * 1024 * 1024:
            raise ValueError(f"PDF file too large. Max size: {max_size_mb}MB")
        
        pdf_file = io.BytesIO(file_content)
        reader = PdfReader(pdf_file)
        
        # ULTRA-STRICT page limit for low-spec laptops
        max_pages = 20  # Very low limit
        num_pages = min(len(reader.pages), max_pages)
        
        if len(reader.pages) > max_pages:
            logger.warning(f"PDF has {len(reader.pages)} pages, limiting to {max_pages}")
        
        text_content = []
        for i in range(num_pages):
            try:
                page_text = reader.pages[i].extract_text()
                if page_text:
                    # Strict limit on text per page
                    if len(page_text) > 5000:  # Reduced from 10000
                        page_text = page_text[:5000]
                    text_content.append(page_text)
            except Exception as e:
                logger.warning(f"Failed to extract page {i}: {e}")
                continue
            
            # Clear memory every 5 pages (more frequent)
            if i % 5 == 0:
                gc.collect()
        
        result = "\n\n".join(text_content)
        
        # Clean up
        del pdf_file, reader, text_content
        gc.collect()
        
        return result
    
    @staticmethod
    def parse_docx(file_content: bytes) -> str:
        """Extract text from Word document with STRICT memory limits"""
        if DocxDocument is None:
            raise ImportError("python-docx not installed. Install with: pip install python-docx")
        
        # ULTRA-STRICT file size limit
        max_size_mb = min(settings.max_parse_size_mb, 3)  # Max 3MB
        if len(file_content) > max_size_mb * 1024 * 1024:
            raise ValueError(f"DOCX file too large. Max size: {max_size_mb}MB")
        
        doc_file = io.BytesIO(file_content)
        doc = DocxDocument(doc_file)
        
        text_content = []
        max_paragraphs = 200  # Very strict limit
        
        for i, paragraph in enumerate(doc.paragraphs):
            if i >= max_paragraphs:
                logger.warning(f"Limiting to {max_paragraphs} paragraphs")
                break
            if paragraph.text.strip():
                text_content.append(paragraph.text)
        
        result = "\n\n".join(text_content)
        
        # Clean up
        del doc_file, doc, text_content
        gc.collect()
        
        return result
    
    @staticmethod
    def parse_txt(file_content: bytes, encoding: str = "utf-8") -> str:
        """Extract text from plain text file with size limit"""
        # Enforce size limit even for text files
        max_size_mb = min(settings.max_parse_size_mb, 20)
        if len(file_content) > max_size_mb * 1024 * 1024:
            raise ValueError(f"Text file too large. Max size: {max_size_mb}MB")
        
        return file_content.decode(encoding)
    
    @staticmethod
    def parse_csv(file_content: bytes, encoding: str = "utf-8", max_rows: int = None) -> str:
        """CSV SAFE PARSING - Direct text processing without pandas memory overhead"""
        
        import csv as csv_module
        
        # File size check BEFORE any processing
        file_size_kb = len(file_content) / 1024
        logger.info(f"CSV file size: {file_size_kb:.1f}KB")
        
        if file_size_kb > 500:
            raise ValueError(f"CSV file too large ({file_size_kb:.1f}KB). Max: 500KB.")
        
        # Memory check
        import psutil
        mem_before = psutil.virtual_memory().percent
        logger.info(f"CSV parsing started - Memory: {mem_before:.1f}%")
        
        if mem_before > 40:
            raise MemoryError(f"Memory too high ({mem_before}%) - refusing to parse CSV")
        
        if max_rows is None:
            max_rows = settings.max_csv_rows
        
        max_rows = min(max_rows, 20)  # Only 20 rows max
        
        # Use Python's csv module - much lighter than pandas
        csv_text = file_content.decode(encoding)
        csv_reader = csv_module.DictReader(io.StringIO(csv_text))
        
        rows = []
        for i, row in enumerate(csv_reader):
            if i >= max_rows:
                break
            rows.append(row)
        
        # Format as readable text
        if not rows:
            return "Empty CSV file"
        
        headers = list(rows[0].keys())
        text_content = [f"CSV Data with {len(rows)} rows"]
        text_content.append(f"Columns: {', '.join(headers)}")
        text_content.append("")
        
        for i, row in enumerate(rows):
            row_text = f"Row {i+1}: " + " | ".join([f"{k}={v}" for k, v in row.items()])
            text_content.append(row_text)
        
        result = "\n".join(text_content)
        
        # Cleanup
        del csv_text, rows, file_content
        gc.collect()
        
        mem_after = psutil.virtual_memory().percent
        logger.info(f"CSV parsing complete - Memory: {mem_after:.1f}% (delta: +{mem_after-mem_before:.1f}%)")
        
        return result
    
    @staticmethod
    def parse_excel(file_content: bytes, max_rows: int = None) -> str:
        """Excel SAFE PARSING - Read only first sheet with strict limits"""
        if pd is None:
            raise ImportError("pandas not installed. Install with: pip install pandas openpyxl")
        
        # File size check
        file_size_kb = len(file_content) / 1024
        logger.info(f"Excel file size: {file_size_kb:.1f}KB")
        
        if file_size_kb > 500:
            raise ValueError(f"Excel file too large ({file_size_kb:.1f}KB). Max: 500KB.")
        
        # Memory check
        import psutil
        mem_before = psutil.virtual_memory().percent
        logger.info(f"Excel parsing started - Memory: {mem_before:.1f}%")
        
        if mem_before > 40:
            raise MemoryError(f"Memory too high ({mem_before}%) - refusing to parse Excel")
        
        if max_rows is None:
            max_rows = settings.max_csv_rows
        
        max_rows = min(max_rows, 20)  # Only 20 rows
        
        excel_file = io.BytesIO(file_content)
        
        # Read ONLY first sheet with row limit - avoid iterrows() memory issue
        df = pd.read_excel(excel_file, sheet_name=0, nrows=max_rows, engine='openpyxl')
        
        text_content = []
        text_content.append("Excel Data (First Sheet)")
        text_content.append("Columns: " + ", ".join(df.columns.astype(str)))
        text_content.append(f"Rows: {len(df)}")
        text_content.append("")
        
        # Use iloc instead of iterrows() - much safer
        for idx in range(len(df)):
            row_dict = df.iloc[idx].to_dict()
            row_text = f"Row {idx+1}: " + " | ".join([f"{k}={v}" for k, v in row_dict.items()])
            text_content.append(row_text)
        
        result = "\n".join(text_content)
        
        # Cleanup
        del excel_file, df, text_content, file_content
        gc.collect()
        
        mem_after = psutil.virtual_memory().percent
        logger.info(f"Excel parsing complete - Memory: {mem_after:.1f}% (delta: +{mem_after-mem_before:.1f}%)")
        
        return result
    
    @staticmethod
    def parse_json(file_content: bytes, encoding: str = "utf-8") -> str:
        """Extract text from JSON file"""
        json_data = json.loads(file_content.decode(encoding))
        
        # Convert JSON to readable text format
        return json.dumps(json_data, indent=2)
    
    @staticmethod
    def parse_markdown(file_content: bytes, encoding: str = "utf-8") -> str:
        """Extract text from Markdown file"""
        if markdown is None:
            # If markdown package not available, return raw markdown
            return file_content.decode(encoding)
        
        md_text = file_content.decode(encoding)
        
        # Convert markdown to HTML first
        html = markdown.markdown(md_text)
        
        # Extract plain text from HTML
        if BeautifulSoup:
            soup = BeautifulSoup(html, 'html.parser')
            return soup.get_text()
        
        return md_text
    
    @staticmethod
    def parse_html(file_content: bytes, encoding: str = "utf-8") -> str:
        """Extract text from HTML file"""
        if BeautifulSoup is None:
            raise ImportError("beautifulsoup4 not installed. Install with: pip install beautifulsoup4 lxml")
        
        html_text = file_content.decode(encoding)
        soup = BeautifulSoup(html_text, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
        
        # Get text
        text = soup.get_text()
        
        # Clean up whitespace
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = '\n'.join(chunk for chunk in chunks if chunk)
        
        return text
    
    @classmethod
    def parse_file(cls, file_content: bytes, file_extension: str) -> str:
        """Parse file based on extension"""
        file_extension = file_extension.lower().lstrip('.')
        
        parsers = {
            'pdf': cls.parse_pdf,
            'docx': cls.parse_docx,
            'doc': cls.parse_docx,
            'txt': cls.parse_txt,
            'csv': cls.parse_csv,
            'xlsx': cls.parse_excel,
            'xls': cls.parse_excel,
            'json': cls.parse_json,
            'md': cls.parse_markdown,
            'markdown': cls.parse_markdown,
            'html': cls.parse_html,
            'htm': cls.parse_html,
        }
        
        parser = parsers.get(file_extension)
        
        if parser is None:
            raise ValueError(f"Unsupported file extension: {file_extension}")
        
        return parser(file_content)
    
    @classmethod
    def parse_file_from_path(cls, file_path: str, file_extension: str, max_size_mb: int = None) -> str:
        """Parse file from path with memory limits"""
        if max_size_mb is None:
            max_size_mb = settings.max_parse_size_mb
        
        file_extension = file_extension.lower().lstrip('.')
        
        # For text files, read in chunks
        if file_extension in ['txt', 'md', 'markdown', 'html', 'htm']:
            chunks = []
            max_bytes = max_size_mb * 1024 * 1024
            bytes_read = 0
            
            with open(file_path, 'rb') as f:
                while chunk := f.read(1024 * 1024):  # 1MB chunks
                    bytes_read += len(chunk)
                    if bytes_read > max_bytes:
                        raise ValueError(f"File exceeds {max_size_mb}MB limit")
                    chunks.append(chunk)
            
            file_content = b''.join(chunks)
            return cls.parse_file(file_content, file_extension)
        
        # For binary formats, check size first then read
        import os
        file_size = os.path.getsize(file_path)
        max_bytes = max_size_mb * 1024 * 1024
        
        if file_size > max_bytes:
            raise ValueError(f"File size {file_size / (1024*1024):.1f}MB exceeds {max_size_mb}MB limit")
        
        with open(file_path, 'rb') as f:
            file_content = f.read()
        
        return cls.parse_file(file_content, file_extension)
    
    @staticmethod
    def extract_structured_data(file_content: bytes, file_extension: str) -> List[Dict[str, Any]]:
        """Extract structured data from CSV/Excel/JSON files"""
        file_extension = file_extension.lower().lstrip('.')
        
        if file_extension == 'json':
            json_data = json.loads(file_content.decode('utf-8'))
            if isinstance(json_data, list):
                return json_data
            elif isinstance(json_data, dict):
                return [json_data]
            else:
                return [{"data": json_data}]
        
        elif file_extension == 'csv':
            if pd is None:
                raise ImportError("pandas not installed")
            
            csv_file = io.BytesIO(file_content)
            df = pd.read_csv(csv_file)
            return df.to_dict('records')
        
        elif file_extension in ['xlsx', 'xls']:
            if pd is None:
                raise ImportError("pandas not installed")
            
            excel_file = io.BytesIO(file_content)
            excel_data = pd.read_excel(excel_file, sheet_name=None)
            
            all_records = []
            for sheet_name, df in excel_data.items():
                records = df.to_dict('records')
                for record in records:
                    record['_sheet'] = sheet_name
                all_records.extend(records)
            
            return all_records
        
        else:
            raise ValueError(f"Cannot extract structured data from {file_extension} files")
