"""EQ state, plus loading/saving it and presets as JSON."""
import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path

CONFIG_DIR = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "tofu-eq"
STATE_FILE = CONFIG_DIR / "state.json"
PRESET_DIR = CONFIG_DIR / "presets"


@dataclass
class Band:
    type: str = "peak"
    freq: float = 1000.0
    gain: float = 0.0
    q: float = 1.0
    enabled: bool = True


@dataclass
class EqState:
    preamp: float = 0.0
    bypass: bool = False
    bands: list = field(default_factory=list)

    def to_dict(self):
        return {"preamp": self.preamp, "bypass": self.bypass, "bands": [asdict(b) for b in self.bands]}

    @classmethod
    def from_dict(cls, d):
        bands = [Band(**{k: v for k, v in b.items() if k in Band.__dataclass_fields__}) for b in d.get("bands", [])]
        return cls(preamp=float(d.get("preamp", 0.0)), bypass=bool(d.get("bypass", False)), bands=bands)


def default_state():
    freqs = [32, 64, 125, 250, 500, 1000, 2000, 4000, 8000, 16000]
    bands = [Band("peak", f, 0.0, 1.41) for f in freqs]
    bands[0].type, bands[0].q = "lowshelf", 0.71
    bands[-1].type, bands[-1].q = "highshelf", 0.71
    return EqState(bands=bands)


def _write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    tmp.replace(path)


def load_state():
    try:
        return EqState.from_dict(json.loads(STATE_FILE.read_text()))
    except (OSError, ValueError, TypeError):
        return default_state()


def save_state(state):
    _write_json(STATE_FILE, state.to_dict())


def list_presets():
    return sorted(p.stem for p in PRESET_DIR.glob("*.json"))


def save_preset(name, state):
    d = state.to_dict()
    d.pop("bypass")
    _write_json(PRESET_DIR / f"{name}.json", d)


def load_preset(name):
    return EqState.from_dict(json.loads((PRESET_DIR / f"{name}.json").read_text()))


def delete_preset(name):
    (PRESET_DIR / f"{name}.json").unlink(missing_ok=True)
