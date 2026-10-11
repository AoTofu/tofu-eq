import re
import string
import unittest
from pathlib import Path

from tofu_eq import dsp, i18n

SRC = Path(__file__).resolve().parent.parent / "tofu_eq"


def used_messages():
    msgs = set(dsp.LABELS.values())
    for path in SRC.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        msgs |= set(re.findall(r'\btr\(\s*"((?:[^"\\]|\\.)*)"', text))
        msgs |= set(re.findall(r"\btr\(\s*'((?:[^'\\]|\\.)*)'", text))
    return {m.replace("\\'", "'") for m in msgs}


def fields(s):
    return {f for _, f, _, _ in string.Formatter().parse(s) if f}


class TestTranslations(unittest.TestCase):
    def test_every_ui_string_is_translated(self):
        used = used_messages()
        self.assertGreater(len(used), 30)
        for lang, table in i18n._TABLES.items():
            with self.subTest(lang=lang):
                self.assertEqual(sorted(used - table.keys()), [], f"missing in {lang}")
                self.assertEqual(sorted(table.keys() - used), [], f"unused keys in {lang}")

    def test_placeholders_match(self):
        for lang, table in i18n._TABLES.items():
            for msg, text in table.items():
                with self.subTest(lang=lang, msg=msg):
                    self.assertEqual(fields(msg), fields(text))

    def test_resolve(self):
        self.assertEqual(i18n.resolve("ja"), "ja")
        self.assertEqual(i18n.resolve("zh_CN"), "zh_CN")
        self.assertIn(i18n.resolve("xx"), i18n.LANGUAGES)

    def test_tr_formats(self):
        i18n.set_language("ja")
        try:
            self.assertEqual(i18n.tr("⚠ +{db} dB may clip", db="1.5"), "⚠ +1.5 dB クリップの恐れ")
        finally:
            i18n.set_language("en")
        self.assertEqual(i18n.tr("Name:"), "Name:")


if __name__ == "__main__":
    unittest.main()
