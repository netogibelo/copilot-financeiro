"""
Serviço de importação de extratos:
- OFX: ofxparse
- XLSX: pandas/openpyxl
- PDF: PyMuPDF
- Imagem: Tesseract OCR + OpenCV
"""

import re
import io
import os
from datetime import datetime, date
from typing import List, Dict, Optional, Tuple
from pathlib import Path

from loguru import logger


# =====================================================
# OFX PARSER
# =====================================================

def parse_ofx(content: bytes) -> List[Dict]:
    """Parse OFX/OFC bank statement using regex (no external dependency)."""
    try:
        # Try multiple encodings (OFX BR files are often in cp1252 or latin-1)
        text = None
        for encoding in ("utf-8", "cp1252", "latin-1", "iso-8859-1"):
            try:
                text = content.decode(encoding)
                break
            except (UnicodeDecodeError, LookupError):
                continue
        if text is None:
            text = content.decode("utf-8", errors="replace")

        # Extract each transaction block
        # OFX format: <STMTTRN> ... </STMTTRN> (or without closing tags in legacy)
        transactions = []
        # Match from <STMTTRN> to the next <STMTTRN> or </BANKTRANLIST>
        txn_blocks = re.findall(
            r"<STMTTRN>(.*?)(?=<STMTTRN>|</BANKTRANLIST>|</STMTRS>|</CREDITCARDMSGSRSV1>|$)",
            text,
            re.DOTALL | re.IGNORECASE,
        )

        for block in txn_blocks:
            # Extract fields using regex (works for both closed and unclosed tags)
            def get_tag(tag):
                m = re.search(rf"<{tag}>([^<\r\n]+)", block, re.IGNORECASE)
                return m.group(1).strip() if m else None

            dt_posted = get_tag("DTPOSTED")
            trn_amount = get_tag("TRNAMT")
            memo = get_tag("MEMO") or ""
            payee = get_tag("NAME") or ""
            fitid = get_tag("FITID") or ""
            trn_type = get_tag("TRNTYPE") or ""

            if not dt_posted or not trn_amount:
                continue

            # Parse date: OFX dates are usually YYYYMMDD or YYYYMMDDHHMMSS
            date_str = dt_posted[:8]  # Take first 8 chars (YYYYMMDD)
            try:
                t_date = datetime.strptime(date_str, "%Y%m%d").date()
            except ValueError:
                continue

            # Parse amount
            try:
                amount = float(trn_amount.replace(",", "."))
            except ValueError:
                continue

            # Build description (prefer memo, fallback to payee or trntype)
            description = (memo or payee or trn_type or "Sem descrição").strip()
            if not description:
                description = "Importado"

            transactions.append({
                "date": t_date,
                "description": description[:500],
                "amount": abs(amount),
                "type": "receita" if amount > 0 else "despesa",
                "original_description": fitid or description,
            })

        return transactions
    except Exception as e:
        logger.error(f"OFX parse error: {e}")
        return []


# =====================================================
# XLSX PARSER
# =====================================================

def parse_xlsx(content: bytes) -> List[Dict]:
    """Parse Excel bank statement."""
    try:
        import pandas as pd
        df = pd.read_excel(io.BytesIO(content), header=None)

        transactions = []
        date_col = amount_col = desc_col = None

        # Auto-detect columns
        for col in df.columns:
            sample = df[col].dropna().head(20)
            for val in sample:
                val_str = str(val)
                # Date detection
                if date_col is None and re.match(r"\d{2}/\d{2}/\d{4}|\d{4}-\d{2}-\d{2}", val_str):
                    date_col = col
                    break
                # Amount detection
                if amount_col is None and re.match(r"-?\d+[\.,]\d{2}", val_str.replace("R$", "").strip()):
                    amount_col = col
                    break

        if date_col is None or amount_col is None:
            # Try with header row
            df = pd.read_excel(io.BytesIO(content))
            for col in df.columns:
                col_lower = str(col).lower()
                if date_col is None and any(k in col_lower for k in ["data", "date", "dt"]):
                    date_col = col
                if desc_col is None and any(k in col_lower for k in ["descricao", "descrição", "historico", "memo", "pagamento"]):
                    desc_col = col
                if amount_col is None and any(k in col_lower for k in ["valor", "amount", "credito", "debito", "lancamento"]):
                    amount_col = col

        for _, row in df.iterrows():
            try:
                raw_date = row.get(date_col) if date_col else None
                raw_amount = row.get(amount_col) if amount_col else None
                raw_desc = row.get(desc_col) if desc_col else "Importado"

                if raw_date is None or raw_amount is None:
                    continue

                # Parse date
                t_date = None
                if isinstance(raw_date, datetime):
                    t_date = raw_date.date()
                elif isinstance(raw_date, str):
                    for fmt in ["%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"]:
                        try:
                            t_date = datetime.strptime(raw_date.strip(), fmt).date()
                            break
                        except:
                            pass

                if t_date is None:
                    continue

                # Parse amount
                amount_str = str(raw_amount).replace("R$", "").replace(".", "").replace(",", ".").strip()
                try:
                    amount = float(amount_str)
                except:
                    continue

                transactions.append({
                    "date": t_date,
                    "description": str(raw_desc).strip()[:500],
                    "amount": abs(amount),
                    "type": "receita" if amount > 0 else "despesa",
                    "original_description": str(raw_desc).strip(),
                })
            except Exception:
                continue

        return transactions
    except Exception as e:
        logger.error(f"XLSX parse error: {e}")
        return []


# =====================================================
# PDF PARSER
# =====================================================

def parse_pdf(content: bytes) -> List[Dict]:
    """Parse PDF bank statement using PyMuPDF."""
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(stream=content, filetype="pdf")
        full_text = ""
        for page in doc:
            full_text += page.get_text()

        return _extract_transactions_from_text(full_text)
    except Exception as e:
        logger.error(f"PDF parse error: {e}")
        return []


# =====================================================
# IMAGE OCR PARSER
# =====================================================

def parse_image(content: bytes) -> List[Dict]:
    """Parse bank statement image using Tesseract OCR."""
    try:
        import cv2
        import numpy as np
        import pytesseract
        from PIL import Image

        # Load image
        nparr = np.frombuffer(content, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if img is None:
            # Try with PIL
            img_pil = Image.open(io.BytesIO(content))
            img = cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)

        # Preprocessing for better OCR
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        # Denoise
        denoised = cv2.fastNlMeansDenoising(gray, h=10)
        # Adaptive threshold
        thresh = cv2.adaptiveThreshold(
            denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
        )
        # Upscale if small
        h, w = thresh.shape
        if w < 1000:
            thresh = cv2.resize(thresh, (w * 2, h * 2), interpolation=cv2.INTER_CUBIC)

        # OCR
        text = pytesseract.image_to_string(
            thresh,
            lang="por",
            config="--psm 6 --oem 3",
        )

        return _extract_transactions_from_text(text)
    except Exception as e:
        logger.error(f"Image OCR parse error: {e}")
        return []


# =====================================================
# TEXT EXTRACTOR (shared)
# =====================================================

def _extract_transactions_from_text(text: str) -> List[Dict]:
    """Extrai transações de texto bruto (PDF/OCR)."""
    transactions = []
    lines = text.split("\n")

    date_pattern = r"(\d{2}[/\-]\d{2}[/\-]\d{2,4})"
    amount_pattern = r"([-+]?\s*\d{1,3}(?:[.\s]\d{3})*[,]\d{2}|\d+[,]\d{2})"

    for line in lines:
        line = line.strip()
        if not line or len(line) < 10:
            continue

        date_match = re.search(date_pattern, line)
        amount_match = re.search(amount_pattern, line)

        if not date_match or not amount_match:
            continue

        # Parse date
        date_str = date_match.group(1)
        t_date = None
        for fmt in ["%d/%m/%Y", "%d/%m/%y", "%d-%m-%Y", "%d-%m-%y"]:
            try:
                t_date = datetime.strptime(date_str, fmt).date()
                break
            except:
                pass

        if not t_date:
            continue

        # Parse amount
        amount_str = amount_match.group(1)
        amount_str = amount_str.replace(" ", "").replace(".", "").replace(",", ".")
        try:
            amount = float(amount_str)
        except:
            continue

        # Extract description (text between date and amount)
        desc = line
        desc = re.sub(date_pattern, "", desc)
        desc = re.sub(amount_pattern, "", desc)
        desc = re.sub(r"\s+", " ", desc).strip()
        desc = desc[:200] if desc else "Importado"

        if not desc:
            continue

        transactions.append({
            "date": t_date,
            "description": desc,
            "amount": abs(amount),
            "type": "receita" if amount > 0 else "despesa",
            "original_description": line[:300],
        })

    return transactions


# =====================================================
# MAIN ENTRY POINT
# =====================================================

def parse_file(content: bytes, filename: str) -> Tuple[List[Dict], str]:
    """
    Parse arquivo de extrato de qualquer formato suportado.
    Retorna: (transações, tipo_arquivo)
    """
    ext = Path(filename).suffix.lower()

    if ext == ".ofx" or ext == ".ofc":
        return parse_ofx(content), "ofx"
    elif ext in (".xlsx", ".xls", ".csv"):
        return parse_xlsx(content), "xlsx"
    elif ext == ".pdf":
        return parse_pdf(content), "pdf"
    elif ext in (".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff"):
        return parse_image(content), "image"
    else:
        # Try to detect by content
        if content[:4] == b"OFXH" or b"<OFX>" in content[:200]:
            return parse_ofx(content), "ofx"
        elif content[:4] == b"PK\x03\x04":  # ZIP = XLSX
            return parse_xlsx(content), "xlsx"
        elif content[:4] == b"%PDF":
            return parse_pdf(content), "pdf"
        else:
            # Try as image
            return parse_image(content), "image"
