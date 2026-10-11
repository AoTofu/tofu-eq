"""Tiny dictionary-based i18n. English strings are the message ids.

Language is chosen from (highest priority first): the TOFU_EQ_LANG environment
variable, the in-app setting, then the system locale.
"""
import os

from PySide6.QtCore import QLocale

LANGUAGES = {"en": "English", "ja": "日本語", "zh_CN": "简体中文"}

_TABLES = {
    "ja": {
        # top bar
        "Presets": "プリセット",
        "Save…": "保存…",
        "Delete": "削除",
        "Flat": "フラット",
        "Reset all band gains and the preamp to 0 dB": "全バンドのゲインを 0 dB にする",
        "Preamp": "プリアンプ",
        "Auto": "自動",
        "Set the preamp to offset the EQ's maximum boost so the output can't clip":
            "クリップしないよう、EQ の最大ブースト分だけプリアンプを下げる",
        "⚠ +{db} dB may clip": "⚠ +{db} dB クリップの恐れ",
        "Spectrum": "スペクトラム",
        "Show the post-EQ spectrum behind the curve (captured only while this window is visible)":
            "EQ 後の音のスペクトラムを背景に表示（ウィンドウ表示中のみ取り込み）",
        "Requires numpy (install the python3-numpy package)": "numpy が必要です（python3-numpy パッケージを入れてください）",
        "Bypass": "バイパス",
        "Temporarily disable the EQ (Ctrl+B)": "EQ を一時的に無効化（Ctrl+B）",
        "Language": "言語",
        "System default": "自動（システム）",
        # graph
        "Drag: frequency/gain    Wheel: Q    Double-click: add band    Right-click: type/delete":
            "ドラッグ: 周波数/ゲイン　ホイール: Q　ダブルクリック: バンド追加　右クリック: 種類/削除",
        "Disable": "無効にする",
        "Enable": "有効にする",
        # band list
        "On": "有効",
        "Type": "種類",
        "Frequency": "周波数",
        "Gain": "ゲイン",
        "Remove this band": "このバンドを削除",
        "+ Add band": "＋ バンドを追加",
        # filter types
        "Peak": "ピーク",
        "Low shelf": "ローシェルフ",
        "High shelf": "ハイシェルフ",
        "Low-pass": "ローパス",
        "High-pass": "ハイパス",
        "Band-pass": "バンドパス",
        "Notch": "ノッチ",
        "All-pass": "オールパス",
        # presets
        "Failed to load preset: {err}": "読み込みに失敗しました: {err}",
        "Save preset": "プリセットを保存",
        "Name:": "名前:",
        "Delete preset “{name}”?": "プリセット「{name}」を削除しますか？",
        # status
        "EQ running": "EQ 動作中",
        "EQ stopped": "EQ 停止中",
        "The EQ stays on after you close this window": "GUI を閉じても EQ は有効のままです",
        "Failed to start the EQ service: {err}": "サービスの起動に失敗しました: {err}",
    },
    "zh_CN": {
        "Presets": "预设",
        "Save…": "保存…",
        "Delete": "删除",
        "Flat": "归零",
        "Reset all band gains and the preamp to 0 dB": "将所有频段增益和前置增益重置为 0 dB",
        "Preamp": "前置增益",
        "Auto": "自动",
        "Set the preamp to offset the EQ's maximum boost so the output can't clip":
            "按 EQ 的最大提升量设置前置增益，防止输出削波",
        "⚠ +{db} dB may clip": "⚠ +{db} dB 可能削波",
        "Spectrum": "频谱",
        "Show the post-EQ spectrum behind the curve (captured only while this window is visible)":
            "在曲线背景中显示 EQ 处理后的频谱（仅在窗口可见时采集）",
        "Requires numpy (install the python3-numpy package)": "需要 numpy（请安装 python3-numpy 软件包）",
        "Bypass": "旁通",
        "Temporarily disable the EQ (Ctrl+B)": "暂时停用 EQ（Ctrl+B）",
        "Language": "语言",
        "System default": "跟随系统",
        "Drag: frequency/gain    Wheel: Q    Double-click: add band    Right-click: type/delete":
            "拖动：频率/增益　滚轮：Q 值　双击：添加频段　右键：类型/删除",
        "Disable": "停用",
        "Enable": "启用",
        "On": "启用",
        "Type": "类型",
        "Frequency": "频率",
        "Gain": "增益",
        "Remove this band": "删除此频段",
        "+ Add band": "＋ 添加频段",
        "Peak": "峰值",
        "Low shelf": "低架",
        "High shelf": "高架",
        "Low-pass": "低通",
        "High-pass": "高通",
        "Band-pass": "带通",
        "Notch": "陷波",
        "All-pass": "全通",
        "Failed to load preset: {err}": "无法加载预设：{err}",
        "Save preset": "保存预设",
        "Name:": "名称：",
        "Delete preset “{name}”?": "确定要删除预设“{name}”吗？",
        "EQ running": "EQ 运行中",
        "EQ stopped": "EQ 已停止",
        "The EQ stays on after you close this window": "关闭窗口后 EQ 仍会保持生效",
        "Failed to start the EQ service: {err}": "无法启动 EQ 服务：{err}",
    },
}

_current = "en"


def system_language():
    name = QLocale.system().name()  # e.g. "ja_JP", "zh_CN", "zh_TW", "en_US"
    if name.startswith("ja"):
        return "ja"
    if name.startswith("zh"):
        return "zh_CN"
    return "en"


def resolve(setting):
    """Pick the effective language from the env override, the saved setting and the locale."""
    for code in (os.environ.get("TOFU_EQ_LANG"), setting):
        if code in LANGUAGES:
            return code
    return system_language()


def set_language(code):
    global _current
    _current = code if code in LANGUAGES else "en"


def current():
    return _current


def tr(msg, **kw):
    text = _TABLES.get(_current, {}).get(msg, msg)
    return text.format(**kw) if kw else text
