"""Check syntax of all Python files in the project"""

import ast
import sys
from pathlib import Path


def check_syntax(filepath: Path) -> tuple[bool, str | None]:
    """Check Python file syntax. Returns (is_valid, error_message)."""
    try:
        source = filepath.read_text(encoding="utf-8")
        ast.parse(source)
        return True, None
    except SyntaxError as e:
        return False, f"Syntax error in {filepath.name}: line {e.lineno}: {e.msg}"
    except UnicodeDecodeError as e:
        return False, f"Encoding error in {filepath.name}: {e}"
    except Exception as e:
        return False, f"Error reading {filepath.name}: {e}"


def main():
    """Run syntax check on entire project"""
    project_root = Path(__file__).resolve().parent
    errors = []

    for py_file in sorted(project_root.rglob("*.py")):
        # Skip files in .git or __pycache__ directories
        if any(part.startswith(".") for part in py_file.parts):
            if part.name == ".git" or part.name == "__pycache__":
                continue
        valid, error = check_syntax(py_file)
        if not valid:
            errors.append(error)
            print(f"❌ {error}", file=sys.stderr)
        else:
            print(f"✅ {py_file.relative_to(project_root)}")

    if errors:
        print(f"\n❌ Found {len(errors)} syntax error(s)", file=sys.stderr)
        sys.exit(1)
    else:
        print(f"\n✅ All files passed syntax check")


if __name__ == "__main__":
    main()
