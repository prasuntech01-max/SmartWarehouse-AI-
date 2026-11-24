"""Unit tests for the SmartWarehouse AI Sound Control Panel & Bridge integration."""

import json
import os
import tempfile

from simulation.engine import WarehouseSimulator
from visualization.threejs_bridge import build_simulation_state, to_json, validate_payload
import ui.sound_panel as sp


def test_sound_settings_defaults():
    cfg = sp.default_sound_settings()
    assert cfg["masterEnabled"] is True
    assert cfg["theme"] == "industrial"
    assert 0.0 <= cfg["masterVolume"] <= 1.0
    assert set(cfg["robotVolumes"].keys()) == {"1", "2", "3", "4", "5"}
    assert set(sp.SOUND_THEMES.keys()) == {"industrial", "alien", "cyberpunk"}
    assert set(sp.VOICE_PROFILES.keys()) == {
        "british_female", "american_female",
        "command_ai", "alien_core", "cyber_robot", "neural_ai", "alert_system",
    }
    assert cfg["voiceEnabled"] is True
    assert cfg["voiceProfile"] == "command_ai"
    assert cfg["emergencyVoiceProfile"] == "match_selected"


def test_sound_settings_persistence_roundtrip(monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = os.path.join(tmpdir, "sound_settings.json")
        monkeypatch.setattr(sp, "_SETTINGS_PATH", tmp_path)

        cfg = sp.default_sound_settings()
        cfg["theme"] = "cyberpunk"
        cfg["masterVolume"] = 0.45
        cfg["ambientEnabled"] = True
        cfg["robotVolumes"]["1"] = 1.25

        os.makedirs(os.path.dirname(tmp_path), exist_ok=True)
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(cfg, f)

        loaded = sp.load_persisted_sound_settings()
        assert loaded["theme"] == "cyberpunk"
        assert loaded["masterVolume"] == 0.45
        assert loaded["ambientEnabled"] is True
        assert loaded["robotVolumes"]["1"] == 1.25


def test_bridge_sound_settings_integration():
    sim = WarehouseSimulator(num_robots=5, width=15, height=15)
    cfg = sp.default_sound_settings()
    cfg["theme"] = "alien"

    state = build_simulation_state(sim, sound_settings=cfg)
    assert state["sound_settings"]["theme"] == "alien"
    assert validate_payload(state) == []

    raw = to_json(state)
    assert len(raw.encode("utf-8")) / 1024.0 < 30.0
