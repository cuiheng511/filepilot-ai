"""Example plugin for FilePilot AI's plugin system.

This file demonstrates how to write a custom extractor plugin.
Place this file (or your own plugin) in ~/.filepilot/plugins/
and it will be automatically discovered on next launch.

To test without restarting: go to Plugins panel → Reload.

See docs/PLUGIN_SDK.md for full documentation.
"""

from pathlib import Path

from filepilot.core.plugin_system import BaseFileExtractor


class CSVAnalyzerExtractor(BaseFileExtractor):
    """Extracts structured data from CSV files using the built-in csv module."""

    display_name = "CSV Analyzer"
    description = "Reads and analyzes CSV files — extracts headers, row count, and sample data"
    version = "1.0.0"
    extensions = [".csv"]

    def supports(self, extension: str) -> bool:
        return extension.lower() in self.extensions

    def extract_text(self, file_path: Path) -> str | None:
        if not file_path.exists():
            return None
        try:
            import csv

            with open(file_path, newline="", encoding="utf-8", errors="replace") as f:
                reader = csv.reader(f)
                rows = list(reader)

            if not rows:
                return "[Empty CSV file]"

            headers = rows[0]
            text_parts = [
                f"CSV File: {file_path.name}",
                f"Rows: {len(rows) - 1} (excluding header)",
                f"Columns: {len(headers)}",
                f"Headers: {', '.join(headers)}",
            ]

            # Include first 5 data rows as sample
            sample_count = min(5, len(rows) - 1)
            if sample_count > 0:
                text_parts.append(f"\nSample data ({sample_count} rows):")
                for row in rows[1 : 1 + sample_count]:
                    text_parts.append("  " + " | ".join(row))

            return "\n".join(text_parts)
        except Exception as e:
            return f"[Error reading CSV: {e}]"

    def extract_metadata(self, file_path: Path) -> dict:
        """Extract metadata from CSV file."""
        try:
            import csv

            with open(file_path, newline="", encoding="utf-8", errors="replace") as f:
                reader = csv.reader(f)
                rows = list(reader)
            return {
                "row_count": len(rows) - 1 if rows else 0,
                "column_count": len(rows[0]) if rows else 0,
                "headers": rows[0] if rows else [],
            }
        except Exception:
            return {}


class LogFileExtractor(BaseFileExtractor):
    """Extracts and parses common log file formats."""

    display_name = "Log File Parser"
    description = "Parses .log files, extracts timestamps, log levels, and error summaries"
    version = "1.0.0"
    extensions = [".log", ".txt"]

    def supports(self, extension: str) -> bool:
        return extension.lower() in self.extensions

    def extract_text(self, file_path: Path) -> str | None:
        if not file_path.exists():
            return None
        try:
            text = file_path.read_text(encoding="utf-8", errors="replace")
            lines = text.splitlines()
            total = len(lines)

            # Count log levels
            levels = {"ERROR": 0, "WARN": 0, "INFO": 0, "DEBUG": 0, "TRACE": 0}
            errors: list[str] = []
            for line in lines:
                for level in levels:
                    if f"[{level}]" in line or f" {level} " in line:
                        levels[level] += 1
                        if level == "ERROR" and len(errors) < 10:
                            errors.append(line.strip())
                        break

            result = [
                f"Log File: {file_path.name}",
                f"Total Lines: {total}",
                "Log Levels:",
            ]
            for level, count in levels.items():
                if count > 0:
                    result.append(f"  {level}: {count}")

            if errors:
                result.append(f"\nRecent Errors (first {len(errors)}):")
                for err in errors:
                    result.append(f"  ❌ {err[:200]}")

            # Include last 20 lines for context
            context_start = max(0, total - 20)
            result.append(f"\nLast {total - context_start} lines:")
            result.extend(lines[context_start:])

            return "\n".join(result)
        except Exception as e:
            return f"[Error reading log: {e}]"
