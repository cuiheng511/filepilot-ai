"""Regression tests for recently added UI translation keys."""

from filepilot.i18n import _translations


def test_recent_auto_start_translations_are_not_shifted_between_languages():
    expected = {
        "zh": "🖥️ 开机自启",
        "en": "🖥️ Launch at Startup",
        "ja": "🖥️ ログイン時に起動",
        "ko": "🖥️ 시작 시 실행",
        "fr": "🖥️ Lancer au démarrage",
        "de": "🖥️ Beim Start öffnen",
        "es": "🖥️ Iniciar al arrancar",
        "pt": "🖥️ Iniciar com o sistema",
        "ru": "🖥️ Запускать при входе",
        "vi": "🖥️ Khởi chạy cùng hệ thống",
        "th": "🖥️ เปิดเมื่อเริ่มระบบ",
        "ar": "🖥️ التشغيل عند بدء النظام",
        "it": "🖥️ Avvia all'accesso",
        "id": "🖥️ Jalankan saat startup",
        "tr": "🖥️ Başlangıçta çalıştır",
        "pl": "🖥️ Uruchom przy starcie",
        "nl": "🖥️ Starten bij inloggen",
        "uk": "🖥️ Запускати під час входу",
    }

    for lang, auto_start in expected.items():
        assert _translations[lang]["auto_start"] == auto_start


def test_recent_tray_keys_exist_for_all_supported_languages():
    keys = {
        "close_to_tray",
        "minimize_to_tray",
        "tray_pause",
        "tray_tooltip",
        "tray_watching_paused",
        "tray_watching_resumed",
        "menu_recent_files",
        "search_semantic",
        "search_semantic_tip",
    }

    for lang, entries in _translations.items():
        missing = keys - entries.keys()
        assert not missing, f"{lang} missing: {sorted(missing)}"
