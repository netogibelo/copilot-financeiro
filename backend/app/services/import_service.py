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
    """Parse Excel/CSV bank statement (robust: multi-sheet, header detection, multiple bank formats)."""
    try:
        import pandas as pd

        # Try reading all sheets (for XLSX); CSV reads as single DF
        try:
            all_sheets = pd.read_excel(io.BytesIO(content), header=None, sheet_name=None)
        except Exception:
            # Fallback: maybe CSV
            all_sheets = {"Sheet1": pd.read_csv(io.BytesIO(content), header=None, sep=None, engine="python", encoding_errors="replace")}

        all_transactions = []

        for sheet_name, df_raw in all_sheets.items():
            transactions = _extract_from_dataframe(df_raw)
            all_transactions.extend(transactions)

        return all_transactions
    except Exception as e:
        logger.error(f"XLSX parse error: {e}")
        return []


def _extract_from_dataframe(df_raw) -> List[Dict]:
    """Extract transactions from a single DataFrame by auto-detecting header row and columns."""
    import pandas as pd

    if df_raw.empty:
        return []

    # Step 1: find the header row (row containing typical header keywords)
    header_row_idx = _find_header_row(df_raw)
    logger.info(f"XLSX parse: header_row_idx={header_row_idx}, shape={df_raw.shape}")

    if header_row_idx is None:
        # No clear header — try treating each row as data and detect columns by content
        return _extract_by_content(df_raw)

    # Use that row as header
    headers = [str(v).strip().lower() if pd.notna(v) else f"col{i}" for i, v in enumerate(df_raw.iloc[header_row_idx])]
    df = df_raw.iloc[header_row_idx + 1:].copy()
    df.columns = headers
    df = df.reset_index(drop=True)

    # Step 2: identify columns semantically
    date_col = _match_col(headers, ["data", "date", "dt ", "dt.", "dtposted", "data lancamento", "data lançamento", "data movimento"])
    desc_col = _match_col(headers, ["descri", "histor", "memo", "pagamento", "estabelecimento", "detalhe", "lancamento", "lançamento", "operaç", "operacao"])
    amount_col = _match_col(headers, ["valor", "amount", "montante", "quantia"])
    credit_col = _match_col(headers, ["credito", "crédito", "entrada", "receita"])
    debit_col = _match_col(headers, ["debito", "débito", "saida", "saída", "despesa"])
    type_col = _match_col(headers, ["tipo", "type", "natureza", "operação"])

    logger.info(f"XLSX parse: headers={headers}, date_col={date_col}, desc_col={desc_col}, amount_col={amount_col}, credit_col={credit_col}, debit_col={debit_col}")

    if date_col is None:
        return _extract_by_content(df_raw)
        
    transactions = []
    for _, row in df.iterrows():
        try:
            raw_date = row.get(date_col)
            if raw_date is None or (hasattr(pd, "isna") and pd.isna(raw_date)):
                continue

            t_date = _parse_date(raw_date)
            if t_date is None:
                continue

            # Amount: single column or credit/debit split
            amount = None
            if amount_col:
                amount = _parse_amount(row.get(amount_col))
            elif credit_col or debit_col:
                credit = _parse_amount(row.get(credit_col)) if credit_col else 0
                debit = _parse_amount(row.get(debit_col)) if debit_col else 0
                credit = credit if credit else 0
                debit = debit if debit else 0
                if credit and credit != 0:
                    amount = abs(credit)
                elif debit and debit != 0:
                    amount = -abs(debit)

            if amount is None or amount == 0:
                continue

            # Type: use explicit column if available, otherwise sign
            if type_col:
                type_val = str(row.get(type_col) or "").lower()
                if any(k in type_val for k in ["cred", "receita", "entrada"]):
                    tx_type = "receita"
                elif any(k in type_val for k in ["deb", "despesa", "saida", "saída"]):
                    tx_type = "despesa"
                else:
                    tx_type = "receita" if amount > 0 else "despesa"
            else:
                tx_type = "receita" if amount > 0 else "despesa"

            desc = str(row.get(desc_col) or "").strip() if desc_col else ""
            if not desc:
                desc = "Importado"

            transactions.append({
                "date": t_date,
                "description": desc[:500],
                "amount": abs(amount),
                "type": tx_type,
                "original_description": desc,
            })
        except Exception:
            continue

    return transactions


def _find_header_row(df_raw) -> Optional[int]:
    """Find the first row that looks like a header (contains typical bank statement keywords)."""
    import pandas as pd

    keywords = ["data", "date", "valor", "amount", "descri", "histor", "credito", "debito", "lancamento", "lançamento"]
    max_rows_to_check = min(20, len(df_raw))

    for i in range(max_rows_to_check):
        row = df_raw.iloc[i]
        row_str = " ".join(str(v).lower() for v in row if pd.notna(v))
        matches = sum(1 for kw in keywords if kw in row_str)
        if matches >= 2:  # At least 2 header keywords in same row
            return i
    return None


def _match_col(headers: List[str], patterns: List[str]) -> Optional[str]:
    """Find best column header matching any pattern. Prefers exact/prefix match over substring."""
    # Priority 1: exact match (case-insensitive, after strip)
    for pat in patterns:
        for h in headers:
            if h == pat:
                return h
    # Priority 2: starts with pattern
    for pat in patterns:
        for h in headers:
            if h.startswith(pat):
                return h
    # Priority 3: pattern is a whole word in the header (not part of another word)
    for pat in patterns:
        for h in headers:
            # Split by common separators and check word match
            words = re.split(r"[\s\(\)/\-_.]+", h)
            if pat in words:
                return h
    # Priority 4: substring (last resort)
    for pat in patterns:
        for h in headers:
            if pat in h:
                return h
    return None


def _parse_date(raw):
    """Parse a date value from various formats."""
    import pandas as pd

    if raw is None or (hasattr(pd, "isna") and pd.isna(raw)):
        return None
    if isinstance(raw, datetime):
        return raw.date()
    if hasattr(raw, "date") and callable(raw.date):
        try:
            return raw.date()
        except Exception:
            pass
    s = str(raw).strip()
    if not s or s.lower() in ("nan", "nat", "none"):
        return None
    # Try ISO first (common in OFX export)
    for fmt in ["%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%d.%m.%Y", "%Y/%m/%d", "%d/%m/%y"]:
        try:
            return datetime.strptime(s[:10], fmt).date()
        except ValueError:
            continue
    return None


def _parse_amount(raw):
    """Parse a monetary amount from various formats (BR/US)."""
    import pandas as pd

    if raw is None or (hasattr(pd, "isna") and pd.isna(raw)):
        return None
    if isinstance(raw, (int, float)):
        return float(raw)
    s = str(raw).strip()
    if not s or s.lower() in ("nan", "none", "-"):
        return None
    # Clean: remove R$, spaces, dots as thousand sep; keep comma as decimal
    s = s.replace("R$", "").replace(" ", "").strip()
    # If has both . and , use , as decimal
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        s = s.replace(",", ".")
    # Handle parenthesis as negative
    if s.startswith("(") and s.endswith(")"):
        s = "-" + s[1:-1]
    try:
        return float(s)
    except ValueError:
        return None


def _extract_by_content(df_raw) -> List[Dict]:
    """Fallback: scan each row and try to extract [date + amount + desc] pattern."""
    import pandas as pd

    transactions = []
    for _, row in df_raw.iterrows():
        values = [str(v).strip() for v in row if pd.notna(v)]
        if not values:
            continue

        row_date = None
        row_amount = None
        row_desc_parts = []

        for val in values:
            if row_date is None:
                d = _parse_date(val)
                if d is not None:
                    row_date = d
                    continue
            if row_amount is None:
                a = _parse_amount(val)
                if a is not None and a != 0 and not (val.replace(".", "").replace(",", "").replace("-", "").isdigit() and len(val) < 5):
                    # Avoid matching codes/ids that look like small numbers
                    row_amount = a
                    continue
            row_desc_parts.append(val)

        if row_date is None or row_amount is None:
            continue

        desc = " ".join(row_desc_parts).strip() or "Importado"
        transactions.append({
            "date": row_date,
            "description": desc[:500],
            "amount": abs(row_amount),
            "type": "receita" if row_amount > 0 else "despesa",
            "original_description": desc,
        })

    return transactions


# =====================================================
# PDF PARSER
# =====================================================

def parse_pdf(content: bytes) -> List[Dict]:
    """Parse PDF bank statement using PyMuPDF. Tries multiple strategies."""
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(stream=content, filetype="pdf")

        # Strategy 1: Extract as blocks (preserves layout - better for tabular statements)
        block_transactions = []
        full_text = ""
        for page in doc:
            full_text += page.get_text() + "\n"
            # Get blocks: each block is a paragraph/cell in the layout
            blocks = page.get_text("blocks")
            for block in blocks:
                # block = (x0, y0, x1, y1, text, block_no, block_type)
                block_text = block[4] if len(block) > 4 else ""
                parsed = _extract_from_block(block_text)
                if parsed:
                    block_transactions.append(parsed)

        if block_transactions:
            logger.info(f"PDF parse: extracted {len(block_transactions)} transactions via blocks strategy")
            return block_transactions

        # Strategy 2: Multi-line extraction (date on one line, amount on nearby line)
        multiline_transactions = _extract_multiline_transactions(full_text)
        if multiline_transactions:
            logger.info(f"PDF parse: extracted {len(multiline_transactions)} transactions via multiline strategy")
            return multiline_transactions

        # Strategy 3: Original single-line extraction (for PDFs with tabular text)
        single_line = _extract_transactions_from_text(full_text)
        logger.info(f"PDF parse: extracted {len(single_line)} transactions via single-line strategy")
        return single_line

    except Exception as e:
        logger.error(f"PDF parse error: {e}")
        return []


def _extract_from_block(block_text: str) -> Optional[Dict]:
    """Extract a single transaction from a text block (cell/paragraph)."""
    if not block_text or len(block_text.strip()) < 5:
        return None

    lines = [ln.strip() for ln in block_text.split("\n") if ln.strip()]
    if not lines:
        return None

    # Find date
    t_date = None
    date_line_idx = None
    for i, ln in enumerate(lines):
        m = re.search(r"(\d{2}[/\-.]\d{2}[/\-.]\d{2,4})", ln)
        if m:
            d = _parse_date(m.group(1))
            if d:
                t_date = d
                date_line_idx = i
                break

    if t_date is None:
        return None

    # Find amount (look for R$ or BR-formatted number)
    amount = None
    amount_line_idx = None
    for i, ln in enumerate(lines):
        m = re.search(r"(-?\s*R?\$?\s*\d{1,3}(?:[.\s]\d{3})*,\d{2})", ln)
        if m:
            a = _parse_amount(m.group(1))
            if a is not None and a != 0:
                amount = a
                amount_line_idx = i
                break

    if amount is None:
        return None

    # Description: all other lines concatenated
    desc_parts = []
    for i, ln in enumerate(lines):
        if i == date_line_idx or i == amount_line_idx:
            continue
        # Remove any date/amount remnants
        clean = re.sub(r"\d{2}[/\-.]\d{2}[/\-.]\d{2,4}", "", ln)
        clean = re.sub(r"-?\s*R?\$?\s*\d{1,3}(?:[.\s]\d{3})*,\d{2}", "", clean)
        clean = clean.strip()
        if clean and len(clean) > 2:
            desc_parts.append(clean)

    desc = " ".join(desc_parts).strip()[:500] or "Importado"

    return {
        "date": t_date,
        "description": desc,
        "amount": abs(amount),
        "type": "receita" if amount > 0 else "despesa",
        "original_description": desc,
    }


def _extract_multiline_transactions(text: str) -> List[Dict]:
    """
    Extract transactions where date and amount are on different lines but near each other.
    Uses a sliding window: for each date found, looks for amount in the next N lines.
    """
    transactions = []
    lines = [ln.strip() for ln in text.split("\n")]
    date_pattern = re.compile(r"(\d{2}[/\-.]\d{2}[/\-.]\d{2,4})")
    amount_pattern = re.compile(r"(-?\s*R?\$?\s*\d{1,3}(?:[.\s]\d{3})*,\d{2})")

    WINDOW = 6  # Look up to 6 lines after the date

    i = 0
    while i < len(lines):
        line = lines[i]
        date_match = date_pattern.search(line)

        if not date_match:
            i += 1
            continue

        t_date = _parse_date(date_match.group(1))
        if t_date is None:
            i += 1
            continue

        # Look for amount in this line or the next WINDOW lines
        amount = None
        amount_line_offset = None
        desc_lines = []

        # Start from the current line (remove date from line to capture description)
        current_clean = date_pattern.sub("", line).strip()

        # Check amount in current line first
        am = amount_pattern.search(current_clean)
        if am:
            a = _parse_amount(am.group(1))
            if a is not None and a != 0:
                amount = a
                # Extract description from same line
                current_clean = amount_pattern.sub("", current_clean).strip()
                if current_clean:
                    desc_lines.append(current_clean)

        # If no amount yet, scan next lines
        if amount is None:
            if current_clean and len(current_clean) > 2:
                desc_lines.append(current_clean)

            for j in range(1, min(WINDOW + 1, len(lines) - i)):
                next_line = lines[i + j]
                if not next_line:
                    continue

                # If we find a new date, stop — this is the next transaction
                if date_pattern.search(next_line) and not amount:
                    break

                am = amount_pattern.search(next_line)
                if am:
                    a = _parse_amount(am.group(1))
                    if a is not None and a != 0:
                        amount = a
                        amount_line_offset = j
                        # Capture the non-amount part as description
                        cleaned = amount_pattern.sub("", next_line).strip()
                        if cleaned and len(cleaned) > 2:
                            desc_lines.append(cleaned)
                        break
                else:
                    # No amount, add as description
                    if len(next_line) > 2:
                        desc_lines.append(next_line)

        if amount is None:
            i += 1
            continue

        desc = " ".join(desc_lines).strip()[:500] or "Importado"
        transactions.append({
            "date": t_date,
            "description": desc,
            "amount": abs(amount),
            "type": "receita" if amount > 0 else "despesa",
            "original_description": desc,
        })

        # Skip past this transaction
        i += (amount_line_offset + 1) if amount_line_offset else 1

    return transactions


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
