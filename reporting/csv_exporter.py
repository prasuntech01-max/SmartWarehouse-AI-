"""CSV Export utility with formula-injection neutralization and Windows Excel compatibility."""

import io
import pandas as pd
from typing import Any, List, Dict


def sanitize_for_csv(value: Any) -> Any:
    """Neutralize formula injection by prefixing risky initial characters with a single quote."""
    if isinstance(value, str):
        if value and value[0] in ('=', '+', '-', '@', '\t', '\r'):
            return "'" + value
    return value


def sanitize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Sanitize all string columns in a DataFrame against CSV formula injection."""
    cleaned = df.copy()
    for col in cleaned.columns:
        cleaned[col] = cleaned[col].map(sanitize_for_csv)
    return cleaned


def export_dataframe_to_csv(df: pd.DataFrame) -> bytes:
    """Export DataFrame to UTF-8-SIG encoded CSV bytes with formula-injection neutralization."""
    cleaned = sanitize_dataframe(df)
    buffer = io.StringIO()
    cleaned.to_csv(buffer, index=False)
    # Encode with utf-8-sig for Windows Excel BOM compatibility
    return buffer.getvalue().encode("utf-8-sig")
