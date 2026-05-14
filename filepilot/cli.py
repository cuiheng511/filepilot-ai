#!/usr/bin/env python3
"""FilePilot AI — CLI Entry Point

Usage:
    python -m filepilot.cli scan /path/to/dir
    python -m filepilot.cli search /path/to/dir "keyword"
    python -m filepilot.cli duplicates /path/to/dir
    python -m filepilot.cli organize /path/to/dir /target/dir --rule category
    python -m filepilot.cli export /path/to/dir --format csv --output results.csv
    python -m filepilot.cli disk-usage /path/to/dir
"""

import argparse
import csv
import json
import sys
from pathlib import Path


def cmd_scan(args):
    """Scan directory"""
    from filepilot.core.file_scanner import FileScanner

    scanner = FileScanner()
    files = scanner.scan(
        args.path,
        recursive=not args.no_recursive,
        progress_callback=lambda i, p: print(f"\r  Scanning... {i} files", end="", file=sys.stderr),
    )
    print(
        f"\r  Scan complete: {len(files)} files, {scanner.stats['total_size_str']}", file=sys.stderr
    )

    for f in files:
        print(
            json.dumps(
                {
                    "path": str(f.path),
                    "name": f.name,
                    "extension": f.extension,
                    "size": f.size_bytes,
                    "size_str": f.size_str,
                    "category": f.category.label,
                    "modified": f.modified_time.isoformat(),
                },
                ensure_ascii=False,
            )
        )


def cmd_search(args):
    """Search files"""
    from filepilot.core.indexer import FileIndexer

    indexer = FileIndexer(index_dir=str(Path.home() / ".filepilot" / "index"))
    results = indexer.search(args.query, limit=args.limit)
    if not results:
        print("No matching results found", file=sys.stderr)
        return
    for r in results:
        print(json.dumps(r, ensure_ascii=False, default=str))


def cmd_duplicates(args):
    """Find duplicate files"""
    from filepilot.core.duplicate_finder import DuplicateFinder
    from filepilot.core.file_scanner import FileScanner

    scanner = FileScanner()
    files = scanner.scan(args.path)
    print(f"Scan complete: {len(files)} files", file=sys.stderr)

    finder = DuplicateFinder()
    groups = finder.find_duplicates(files)
    stats = finder.get_duplicate_stats(groups)
    print(
        f"Found {stats['groups']} groups of duplicates, wasted {stats['wasted_space_str']}",
        file=sys.stderr,
    )

    for group in groups:
        paths = [str(f.path) for f in group]
        print(json.dumps({"hash": group[0].hash_sha256 or "", "files": paths}, ensure_ascii=False))


def cmd_organize(args):
    """Organize files"""
    from filepilot.core.file_organizer import CategoryRule, DateRule, FileOrganizer, SizeRule
    from filepilot.core.file_scanner import FileScanner

    scanner = FileScanner()
    files = scanner.scan(args.path)

    rule_map = {"category": CategoryRule, "date": DateRule, "size": SizeRule}
    rules = [rule_map[r]() for r in args.rules if r in rule_map]
    if not rules:
        rules = [CategoryRule()]

    organizer = FileOrganizer()
    operations = organizer.organize(
        files,
        target_root=args.target,
        rules=rules,
        dry_run=args.dry_run,
        rename=bool(args.rename),
        rename_pattern=args.rename,
    )
    for op in operations:
        print(json.dumps(op, ensure_ascii=False))


def cmd_export(args):
    """Export scan results"""
    from filepilot.core.file_scanner import FileScanner

    scanner = FileScanner()
    files = scanner.scan(args.path)
    print(f"Scan complete: {len(files)} files", file=sys.stderr)

    rows = []
    for f in files:
        rows.append(
            {
                "path": str(f.path),
                "name": f.name,
                "extension": f.extension,
                "size_bytes": f.size_bytes,
                "size_str": f.size_str,
                "category": f.category.label,
                "modified": f.modified_time.isoformat(),
                "created": f.created_time.isoformat(),
            }
        )

    if args.format == "csv":
        if args.output:
            with open(args.output, "w", newline="", encoding="utf-8-sig") as out:
                writer = csv.DictWriter(out, fieldnames=rows[0].keys() if rows else [])
                writer.writeheader()
                writer.writerows(rows)
            print(f"Exported {len(rows)} records to {args.output}", file=sys.stderr)
        else:
            writer = csv.DictWriter(sys.stdout, fieldnames=rows[0].keys() if rows else [])
            writer.writeheader()
            writer.writerows(rows)
    else:
        output = json.dumps(rows, ensure_ascii=False, indent=2)
        if args.output:
            Path(args.output).write_text(output, encoding="utf-8")
            print(f"Exported {len(rows)} records to {args.output}", file=sys.stderr)
        else:
            print(output)


def cmd_disk_usage(args):
    """Disk usage analysis"""
    root = Path(args.path)
    if not root.exists():
        print(f"Path does not exist: {root}", file=sys.stderr)
        return

    dirs = {}
    files_total = 0
    for f in root.rglob("*"):
        if f.is_file():
            size = f.stat().st_size
            files_total += size
            parent = str(f.parent.relative_to(root))
            dirs[parent] = dirs.get(parent, 0) + size

    # Sort by size
    sorted_dirs = sorted(dirs.items(), key=lambda x: x[1], reverse=True)

    print(
        json.dumps(
            {
                "total_size": files_total,
                "total_dirs": len(sorted_dirs),
                "top_dirs": [
                    {"path": d, "size": s, "size_str": _fmt(s)} for d, s in sorted_dirs[:20]
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


def _fmt(size):
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} PB"


def main():
    parser = argparse.ArgumentParser(description="FilePilot AI CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    # scan
    p_scan = sub.add_parser("scan", help="Scan a directory")
    p_scan.add_argument("path", help="Directory path")
    p_scan.add_argument("--no-recursive", action="store_true")

    # search
    p_search = sub.add_parser("search", help="Search files")
    p_search.add_argument("path", help="Directory path")
    p_search.add_argument("query", help="Search keywords")
    p_search.add_argument("--limit", type=int, default=50)

    # duplicates
    p_dup = sub.add_parser("duplicates", help="Find duplicate files")
    p_dup.add_argument("path", help="Directory path")

    # organize
    p_org = sub.add_parser("organize", help="Organize files")
    p_org.add_argument("path", help="Source directory")
    p_org.add_argument("target", help="Target directory")
    p_org.add_argument("--rules", nargs="+", default=["category"])
    p_org.add_argument("--dry-run", action="store_true")
    p_org.add_argument("--rename", help="Rename template")

    # export
    p_exp = sub.add_parser("export", help="Export scan results")
    p_exp.add_argument("path", help="Directory path")
    p_exp.add_argument("--format", choices=["csv", "json"], default="json")
    p_exp.add_argument("--output", "-o", help="Output file path")

    # disk-usage
    p_du = sub.add_parser("disk-usage", help="Disk usage analysis")
    p_du.add_argument("path", help="Directory path")

    args = parser.parse_args()
    cmd_map = {
        "scan": cmd_scan,
        "search": cmd_search,
        "duplicates": cmd_duplicates,
        "organize": cmd_organize,
        "export": cmd_export,
        "disk-usage": cmd_disk_usage,
    }
    cmd_map[args.command](args)


if __name__ == "__main__":
    main()
