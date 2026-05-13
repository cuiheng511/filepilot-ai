"""Check Python syntax of all new panel and core files."""
import ast
import os

files = [
    'filepilot-ai/filepilot/ui/summary_panel.py',
    'filepilot-ai/filepilot/ui/index_panel.py',
    'filepilot-ai/filepilot/ui/organize_panel.py',
    'filepilot-ai/filepilot/ui/duplicates_panel.py',
    'filepilot-ai/filepilot/ui/main_window.py',
    'filepilot-ai/filepilot/ui/file_browser.py',
    'filepilot-ai/filepilot/ui/search_panel.py',
    'filepilot-ai/filepilot/ui/settings_dialog.py',
    'filepilot-ai/filepilot/core/indexer.py',
    'filepilot-ai/filepilot/core/file_scanner.py',
    'filepilot-ai/filepilot/core/file_organizer.py',
    'filepilot-ai/filepilot/core/duplicate_finder.py',
    'filepilot-ai/filepilot/ai/summarizer.py',
    'filepilot-ai/filepilot/app.py',
    'filepilot-ai/filepilot/main.py',
]

errors = []
for f in files:
    if not os.path.exists(f):
        print(f'❌ {f} - FILE NOT FOUND')
        errors.append(f)
        continue
    try:
        with open(f, encoding='utf-8') as fh:
            ast.parse(fh.read())
        print(f'✅ {f}')
    except SyntaxError as e:
        print(f'❌ {f} - line {e.lineno}: {e.msg}')
        errors.append(f)

print(f'\n结果: {len(files) - len(errors)}/{len(files)} 通过')
if errors:
    print(f'失败: {len(errors)} 个文件')
else:
    print('全部通过! 🎉')
