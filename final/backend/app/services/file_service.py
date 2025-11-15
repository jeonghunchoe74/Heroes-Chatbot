from __future__ import annotations

import io
import re
import zipfile
from pathlib import Path
from typing import Optional

import pandas as pd


def _clip(text: str, limit: int = 600) -> str:
    normalized = " ".join((text or "").split())
    return (normalized[:limit] + "…") if len(normalized) > limit else normalized


def _pdf_to_text(path: Path) -> str:
    try:
        from pdfminer.high_level import extract_text

        return extract_text(str(path))
    except Exception:
        try:
            import pdfplumber

            with pdfplumber.open(str(path)) as pdf:
                return "\n".join(page.extract_text() or "" for page in pdf.pages)
        except Exception:
            return ""


def _excel_to_text(path: Path) -> str:
    try:
        xl = pd.ExcelFile(path)
        chunks: list[str] = []
        for sheet in xl.sheet_names[:3]:
            df = xl.parse(sheet).head(10)
            chunks.append(f"[{sheet}]\n{df.to_string(index=False)}")
        return "\n\n".join(chunks)
    except Exception:
        try:
            df = pd.read_csv(path).head(20)
            return df.to_string(index=False)
        except Exception:
            return ""


def _hwpx_to_text(path: Path) -> str:
    try:
        with zipfile.ZipFile(path) as z:
            xmls = [name for name in z.namelist() if name.endswith(".xml")]
            buf: list[str] = []
            for name in xmls:
                if "Section" in name or "doc" in name.lower():
                    buf.append(z.read(name).decode("utf-8", errors="ignore"))
            text = re.sub(r"<[^>]+>", " ", " ".join(buf))
            return text
    except Exception:
        return ""


def extract_text_preview(path: Path, mime: Optional[str] = None) -> str:
    ext = path.suffix.lower()
    mime = (mime or "").lower()
    text = ""

    if ext == ".pdf" or mime.startswith("application/pdf"):
        text = _pdf_to_text(path)
    elif ext in {".xls", ".xlsx", ".csv"} or mime in {
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "text/csv",
    }:
        text = _excel_to_text(path)
    elif ext == ".hwpx":
        text = _hwpx_to_text(path)
    elif ext == ".hwp":
        # 구형 HWP는 환경 의존. 필요 시 pyhwp/hwp5txt 설치 후 사용 권장.
        text = ""

    return _clip(text, 600)


def extract_full_text(path: Path, mime: Optional[str] = None) -> str:
    """
    파일에서 전체 텍스트를 추출 (AI 분석용, 안전한 상한 적용)
    """
    ext = path.suffix.lower()
    mime = (mime or "").lower()
    text = ""

    if ext == ".pdf" or mime.startswith("application/pdf"):
        text = _pdf_to_text(path)
    elif ext in {".xls", ".xlsx", ".csv"} or mime in {
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "text/csv",
    }:
        text = _excel_to_text(path)
    elif ext == ".hwpx":
        text = _hwpx_to_text(path)
    elif ext == ".hwp":
        # 구형 HWP는 환경 의존. 필요 시 pyhwp/hwp5txt 설치 후 사용 권장.
        text = ""

    normalized = " ".join((text or "").split())
    max_length = 50000
    if len(normalized) > max_length:
        return normalized[:max_length] + "\n\n[문서가 너무 길어 일부만 추출되었습니다]"
    return normalized