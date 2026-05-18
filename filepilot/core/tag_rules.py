"""Tag automation rules — auto-apply tags to files based on conditions."""

from datetime import datetime
from pathlib import Path

from filepilot.core.config import load, save
from filepilot.core.tag_manager import TagManager

DEFAULT_RULES: list[dict] = []


def get_rules() -> list[dict]:
    settings = load()
    return list(settings.get("tag_automation_rules", []))


def save_rules(rules: list[dict]):
    settings = load()
    settings["tag_automation_rules"] = rules
    save(settings)


def add_rule(name: str, conditions: dict, tags: list[str]) -> dict:
    rule = {
        "name": name,
        "conditions": conditions,
        "tags": tags,
    }
    rules = get_rules()
    rules.append(rule)
    save_rules(rules)
    return rule


def update_rule(index: int, name: str, conditions: dict, tags: list[str]) -> dict | None:
    rules = get_rules()
    if index < 0 or index >= len(rules):
        return None
    rules[index] = {"name": name, "conditions": conditions, "tags": tags}
    save_rules(rules)
    return rules[index]


def delete_rule(index: int) -> bool:
    rules = get_rules()
    if index < 0 or index >= len(rules):
        return False
    rules.pop(index)
    save_rules(rules)
    return True


def rule_matches(file_path: Path, conditions: dict) -> bool:
    """Check if a file matches all conditions in a rule."""
    ext = file_path.suffix.lower()

    # Extension filter (OR logic)
    exts = conditions.get("extensions", [])
    if exts and ext not in [e.lower() if e.startswith(".") else f".{e.lower()}" for e in exts]:
        return False

    # Category filter
    cats = conditions.get("categories", [])
    if cats:
        from filepilot.utils.file_utils import get_category_name

        if get_category_name(ext) not in cats:
            return False

    # Size filters
    min_size = conditions.get("min_size_mb", 0)
    max_size = conditions.get("max_size_mb", 0)
    if min_size > 0 or max_size > 0:
        if not file_path.exists():
            return False
        size_mb = file_path.stat().st_size / (1024 * 1024)
        if min_size > 0 and size_mb < min_size:
            return False
        if max_size > 0 and size_mb > max_size:
            return False

    # Age filter (days since modified)
    max_age = conditions.get("max_age_days", 0)
    if max_age > 0:
        if not file_path.exists():
            return False
        age_days = (datetime.now() - datetime.fromtimestamp(file_path.stat().st_mtime)).days
        if age_days > max_age:
            return False

    return True


def apply_rules_to_files(file_paths: list[Path]) -> int:
    """Apply all matching rules to a list of files. Returns count of tagged files."""
    tm = TagManager()
    rules = get_rules()
    tagged_count = 0
    for fp in file_paths:
        if not fp.exists():
            continue
        for rule in rules:
            if rule_matches(fp, rule.get("conditions", {})):
                for tag in rule.get("tags", []):
                    tm.add_tag(fp, tag)
                tagged_count += 1
                break  # Only apply first matching rule per file
    return tagged_count


def apply_rules_to_directory(dir_path: Path, tm: TagManager | None = None) -> int:
    """Apply rules to all files in a directory recursively."""
    if tm is None:
        tm = TagManager()
    rules = get_rules()
    if not rules:
        return 0
    tagged_count = 0
    for fp in dir_path.rglob("*"):
        if fp.is_file():
            for rule in rules:
                if rule_matches(fp, rule.get("conditions", {})):
                    for tag in rule.get("tags", []):
                        tm.add_tag(fp, tag)
                    tagged_count += 1
                    break
    return tagged_count
