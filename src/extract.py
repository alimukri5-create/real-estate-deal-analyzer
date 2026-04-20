"""PDF text extraction module."""
import re
from pathlib import Path
from typing import Dict, Any, Optional

try:
    import pdfplumber
    HAS_PDFPLUMBER = True
except ImportError:
    HAS_PDFPLUMBER = False

try:
    import PyPDF2
    HAS_PYPDF2 = True
except ImportError:
    HAS_PYPDF2 = False


def extract_text_from_pdf(pdf_path: str | Path) -> str:
    """Extract raw text from a PDF file."""
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    text = ""

    # Prefer pdfplumber for better layout preservation
    if HAS_PDFPLUMBER:
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n\n"
            if text.strip():
                return text.strip()
        except Exception:
            pass  # Fall through to PyPDF2

    if HAS_PYPDF2:
        try:
            with open(pdf_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n\n"
            return text.strip()
        except Exception as e:
            raise RuntimeError(f"Failed to extract PDF text: {e}")

    raise RuntimeError("No PDF extraction library available. Install pdfplumber or PyPDF2.")


def extract_facts(text: str) -> Dict[str, Any]:
    """Extract structured facts from memo text using regex heuristics."""
    facts = {
        "address": None,
        "price": None,
        "bedrooms": None,
        "sqft": None,
        "yield": None,
        "rent": None,
        "tenure": None,
        "council_tax_band": None,
        "epc_rating": None,
        "key_notes": [],
    }

    # Address - look for UK postcode pattern
    postcode_match = re.search(r'([A-Z]{1,2}\d[A-Z\d]?\s?\d[A-Z]{2})', text, re.IGNORECASE)
    if postcode_match:
        # Try to grab some preceding context as the address
        start = max(0, postcode_match.start() - 100)
        facts["address"] = text[start:postcode_match.end()].strip().replace('\n', ' ')

    # Price - look for £XX,XXX or £X,XXX,XXX
    price_matches = re.findall(r'£([\d,]+(?:\.\d{2})?)', text)
    if price_matches:
        # Usually the asking price is one of the larger figures
        prices = [int(p.replace(',', '')) for p in price_matches if p.replace(',', '').isdigit()]
        if prices:
            facts["price"] = max(prices)  # Asking price is usually the highest mentioned

    # Bedrooms
    bed_match = re.search(r'(\d+)\s*(?:bed|bedroom)', text, re.IGNORECASE)
    if bed_match:
        facts["bedrooms"] = int(bed_match.group(1))

    # Square footage
    sqft_match = re.search(r'(\d{2,4})\s*sq\s*ft', text, re.IGNORECASE)
    if not sqft_match:
        sqft_match = re.search(r'(\d{2,4})\s*sqft', text, re.IGNORECASE)
    if sqft_match:
        facts["sqft"] = int(sqft_match.group(1))

    # Yield
    yield_match = re.search(r'(\d{1,2}\.?\d?)\s*%\s*(?:yield|net yield|gross yield)', text, re.IGNORECASE)
    if yield_match:
        facts["yield"] = float(yield_match.group(1))

    # Rent
    rent_match = re.search(r'£([\d,]+)\s*(?:pcm|per month|monthly)', text, re.IGNORECASE)
    if not rent_match:
        rent_match = re.search(r'£([\d,]+)\s*(?:pcw|per week|weekly)', text, re.IGNORECASE)
    if rent_match:
        facts["rent"] = int(rent_match.group(1).replace(',', ''))

    # Tenure
    if re.search(r'freehold', text, re.IGNORECASE):
        facts["tenure"] = "Freehold"
    elif re.search(r'leasehold', text, re.IGNORECASE):
        lease_match = re.search(r'(\d+)\s*years?\s*remaining', text, re.IGNORECASE)
        years = f" ({lease_match.group(1)} years)" if lease_match else ""
        facts["tenure"] = f"Leasehold{years}"

    # EPC
    epc_match = re.search(r'EPC\s*[;:]?\s*([A-G])', text, re.IGNORECASE)
    if epc_match:
        facts["epc_rating"] = epc_match.group(1).upper()

    # Council tax
    ct_match = re.search(r'Council Tax\s*[;:]?\s*Band\s*([A-H])', text, re.IGNORECASE)
    if ct_match:
        facts["council_tax_band"] = ct_match.group(1).upper()

    # Key notes - grab bullet points or numbered lists
    bullet_lines = re.findall(r'[•\-\*]\s*(.+?)(?=\n|$)', text)
    if bullet_lines:
        facts["key_notes"] = [l.strip() for l in bullet_lines[:10] if len(l.strip()) > 10]

    return facts
