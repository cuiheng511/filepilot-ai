"""XLSX 内容提取器"""

from pathlib import Path


class XlsxExtractor:
    """Excel 文档内容提取"""

    SUPPORTED_EXTENSIONS = {".xlsx", ".xls"}

    def extract_text(self, file_path: str | Path) -> str:
        """提取 XLSX 中的文本内容（所有 sheet）"""
        try:
            from openpyxl import load_workbook
        except ImportError:
            return self._fallback_extract(file_path)

        try:
            wb = load_workbook(str(file_path), read_only=True, data_only=True)
            parts = []
            for sheet_name in wb.sheetnames:
                ws = wb[sheet_name]
                parts.append(f"=== {sheet_name} ===")
                for row in ws.iter_rows(values_only=True):
                    cells = [str(c) for c in row if c is not None]
                    if cells:
                        parts.append(" | ".join(cells))
            wb.close()
            return "\n".join(parts)
        except Exception:
            return self._fallback_extract(file_path)

    def _fallback_extract(self, file_path: str | Path) -> str:
        """无 openpyxl 时的降级方案：用 csv 读取"""
        try:
            import csv
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                reader = csv.reader(f)
                return "\n".join(" | ".join(row) for row in reader if any(cell.strip() for cell in row))
        except Exception:
            return ""

    def extract_metadata(self, file_path: str | Path) -> dict:
        """提取 XLSX 元数据"""
        try:
            from openpyxl import load_workbook
        except ImportError:
            return {}

        try:
            wb = load_workbook(str(file_path), read_only=True)
            meta = {
                "sheets": wb.sheetnames,
                "sheet_count": len(wb.sheetnames),
            }
            if wb.properties:
                meta["title"] = wb.properties.title or ""
                meta["author"] = wb.properties.creator or ""
            wb.close()
            return meta
        except Exception:
            return {}
