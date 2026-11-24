"""Futuristic Sound Control Panel & Persistent Preferences for SmartWarehouse AI."""

from __future__ import annotations

import json
import os
from typing import Any, Dict

import streamlit as st
import streamlit.components.v1 as components


_SETTINGS_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "data",
    "sound_settings.json",
)

SOUND_THEMES = {
    "industrial": "INDUSTRIAL FUTURE",
    "alien": "ALIEN TECHNOLOGY",
    "cyberpunk": "CYBERPUNK",
}

VOICE_PROFILES = {
    "british_female": "British Female AI (Warm & Refined)",
    "american_female": "American Female AI (Clear & Polished)",
    "command_ai": "Male AI — COMMAND AI (Deep Industrial)",
    "alien_core": "Male AI — ALIEN CORE (Synthetic Alien)",
    "cyber_robot": "Male AI — CYBER ROBOT (Electronic)",
    "neural_ai": "NEURAL AI (Clean Assistant)",
    "alert_system": "ALERT SYSTEM (Emergency)",
}

EMERGENCY_VOICE_OPTIONS = {
    "match_selected": "Use Selected Voice (Automatic)",
    **VOICE_PROFILES,
}

ROBOT_AUDIO_NAMES = {
    1: ("TITAN-X", "Heavy AMR • Deep Engine & Hydraulics"),
    2: ("ATLAS", "Humanoid • Precision Servos & Footsteps"),
    3: ("VORTEX", "Humanoid • High-Speed Turbine & Scan"),
    4: ("NOVA", "Humanoid • Harmonic Sonar & Inspection"),
    5: ("SPECTRE", "Humanoid • Alien Shimmer & Sensor Pulse"),
}


def default_sound_settings() -> Dict[str, Any]:
    """Return default sound configuration dictionary."""
    return {
        "masterEnabled": True,
        "masterVolume": 0.75,
        "sfxVolume": 0.85,
        "ambientVolume": 0.25,
        "movementEnabled": True,
        "pickupEnabled": True,
        "deliveryEnabled": True,
        "scanningEnabled": True,
        "ambientEnabled": False,
        "theme": "industrial",
        "robotVolumes": {"1": 1.0, "2": 1.0, "3": 1.0, "4": 1.0, "5": 1.0},
        "voiceEnabled": True,
        "voiceVolume": 0.9,
        "voiceProfile": "command_ai",
        "emergencyVoiceProfile": "match_selected",
        "voiceMovement": True,
        "voiceParcels": True,
        "voiceEmergency": True,
        "voiceSystem": True,
    }


def load_persisted_sound_settings() -> Dict[str, Any]:
    """Load persisted sound settings from disk, falling back to defaults."""
    cfg = default_sound_settings()
    try:
        if os.path.isfile(_SETTINGS_PATH):
            with open(_SETTINGS_PATH, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            if isinstance(loaded, dict):
                rvols = loaded.pop("robotVolumes", None)
                cfg.update(loaded)
                if isinstance(rvols, dict):
                    cfg["robotVolumes"].update({str(k): float(v) for k, v in rvols.items()})
    except Exception:
        pass
    return cfg


def save_persisted_sound_settings(settings: Dict[str, Any]) -> None:
    """Persist sound settings to disk and session_state."""
    st.session_state["sound_settings"] = settings
    try:
        os.makedirs(os.path.dirname(_SETTINGS_PATH), exist_ok=True)
        with open(_SETTINGS_PATH, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2)
    except Exception:
        pass


def get_sound_settings() -> Dict[str, Any]:
    """Retrieve current sound settings from session_state (loading from disk once)."""
    if "sound_settings" not in st.session_state:
        st.session_state["sound_settings"] = load_persisted_sound_settings()
    return st.session_state["sound_settings"]


def _render_preview_audio_snippet(theme: str, master_vol: float) -> None:
    """Play an immediate Web Audio theme preview with a live mini waveform."""
    pitch_mult = {"industrial": 1.0, "alien": 0.86, "cyberpunk": 1.16}.get(theme, 1.0)
    wave = {"industrial": "sawtooth", "alien": "sine", "cyberpunk": "square"}.get(theme, "sawtooth")
    fm_depth = {"industrial": 18, "alien": 65, "cyberpunk": 36}.get(theme, 18)
    components.html(
        f"""
        <div style="display:flex;align-items:center;gap:10px;background:#090e1a;border:1px solid rgba(0,240,255,0.3);border-radius:6px;padding:6px 10px;color:#e2e8f0;font-family:sans-serif;font-size:11px;">
          <span style="color:#00f0ff;font-weight:700;">🔊 Previewing {SOUND_THEMES.get(theme, theme)}</span>
          <canvas id="pv_viz" width="120" height="22" style="background:rgba(0,240,255,0.06);border-radius:4px;"></canvas>
        </div>
        <script>
        (function() {{
          const AudioCtx = window.AudioContext || window.webkitAudioContext;
          if (!AudioCtx) return;
          const ctx = new AudioCtx();
          const analyser = ctx.createAnalyser();
          analyser.fftSize = 32;
          const master = ctx.createGain();
          master.gain.value = {max(0.05, float(master_vol))};
          master.connect(analyser);
          analyser.connect(ctx.destination);

          const f = 320 * {pitch_mult};
          function play(freq, endFreq, dur, delay, type, fm) {{
            const t0 = ctx.currentTime + delay;
            const t1 = t0 + dur;
            const osc = ctx.createOscillator();
            osc.type = type;
            osc.frequency.setValueAtTime(freq, t0);
            if (endFreq) osc.frequency.exponentialRampToValueAtTime(endFreq, t1);
            if (fm > 0) {{
              const mod = ctx.createOscillator();
              const mg = ctx.createGain();
              mod.frequency.setValueAtTime(22, t0);
              mg.gain.setValueAtTime(fm, t0);
              mod.connect(mg); mg.connect(osc.frequency);
              mod.start(t0); mod.stop(t1 + 0.02);
            }}
            const flt = ctx.createBiquadFilter();
            flt.type = 'lowpass'; flt.frequency.value = 3400;
            const env = ctx.createGain();
            env.gain.setValueAtTime(0.001, t0);
            env.gain.linearRampToValueAtTime(0.22, t0 + 0.015);
            env.gain.exponentialRampToValueAtTime(0.001, t1);
            osc.connect(flt); flt.connect(env); env.connect(master);
            osc.start(t0); osc.stop(t1 + 0.02);
          }}
          play(f * 0.5, f * 1.4, 0.28, 0.0, "{wave}", {fm_depth});
          play(f * 1.8, f * 2.6, 0.16, 0.24, "sine", 0);
          play(f * 1.5, null, 0.16, 0.42, "triangle", 0);
          play(f * 2.25, null, 0.28, 0.52, "sine", 0);

          const c = document.getElementById('pv_viz');
          const cctx = c.getContext('2d');
          const bins = new Uint8Array(16);
          let frames = 0;
          function draw() {{
            if (frames++ > 65) {{ try {{ ctx.close(); }} catch(_){{}} return; }}
            analyser.getByteFrequencyData(bins);
            cctx.clearRect(0, 0, c.width, c.height);
            for (let i = 0; i < 12; i++) {{
              const h = Math.max(2, (bins[i] / 255) * 19);
              cctx.fillStyle = i % 2 === 0 ? '#00f0ff' : '#d946ef';
              cctx.fillRect(i * 10, 21 - h, 7, h);
            }}
            requestAnimationFrame(draw);
          }}
          draw();
        }})();
        </script>
        """,
        height=44,
    )


def _render_preview_voice_snippet(profile: str, voice_vol: float, is_emergency: bool = False) -> None:
    """Play an immediate Web Speech + Web Audio comms preview using genuine female/male TTS voices."""
    pitch_map = {"british_female": 1.04, "american_female": 1.02, "command_ai": 0.72, "alien_core": 0.62, "cyber_robot": 0.86, "neural_ai": 1.0, "alert_system": 0.78}
    rate_map = {"british_female": 0.94, "american_female": 0.97, "command_ai": 0.92, "alien_core": 0.84, "cyber_robot": 1.03, "neural_ai": 0.98, "alert_system": 1.04}
    pitch = pitch_map.get(profile, 0.96)
    rate = rate_map.get(profile, 0.95)
    is_female = profile in ("british_female", "american_female", "neural_ai")
    lang_prefix = "en-gb" if profile == "british_female" else ("en-us" if profile == "american_female" else "en")
    label = VOICE_PROFILES.get(profile, profile)
    phrase = (
        "Warning. Emergency stop activated. All affected autonomous units are stopping. Please stand by."
        if is_emergency
        else f"{label.split('(')[0].strip()} online. SmartWarehouse autonomous fleet telemetry nominal."
    )
    components.html(
        f"""
        <div style="display:flex;align-items:center;gap:10px;background:#090e1a;border:1px solid {'rgba(239,68,68,0.45)' if is_emergency else 'rgba(56,189,248,0.35)'};border-radius:6px;padding:6px 10px;color:#e2e8f0;font-family:sans-serif;font-size:11px;">
          <span style="color:{'#ef4444' if is_emergency else '#38bdf8'};font-weight:700;">{'🚨 Emergency Voice Test' if is_emergency else '🗣️ Voice Test'}: {label}</span>
        </div>
        <script>
        (function() {{
          if ('speechSynthesis' in window) {{
            window.speechSynthesis.cancel();
            const u = new SpeechSynthesisUtterance({json.dumps(phrase)});
            const voices = window.speechSynthesis.getVoices() || [];
            const en = voices.filter(v => String(v.lang).toLowerCase().startsWith('en'));
            const pool = en.length ? en : voices;
            const femRx = /libby|sonia|hazel|kate|serena|susan|martha|aria|jenny|zira|samantha|ava|allison|victoria|emma|amy|female|natural/i;
            const maleRx = /david|mark|daniel|george|james|ryan|guy|alex|male/i;
            let chosen = null;
            if ({'true' if is_female else 'false'}) {{
              const lp = pool.filter(v => String(v.lang).toLowerCase().startsWith({json.dumps(lang_prefix)}));
              chosen = lp.find(v => femRx.test(v.name) && !maleRx.test(v.name))
                    || lp.find(v => !maleRx.test(v.name))
                    || pool.find(v => femRx.test(v.name) && !maleRx.test(v.name));
            }} else {{
              chosen = pool.find(v => maleRx.test(v.name));
            }}
            if (chosen) u.voice = chosen;
            u.pitch = {pitch};
            u.rate = {rate};
            u.volume = {max(0.05, min(1.0, float(voice_vol)))};
            window.speechSynthesis.speak(u);
          }}
        }})();
        </script>
        """,
        height=38,
    )


def render_sound_control_panel(key_prefix: str = "snd") -> Dict[str, Any]:
    """Render the premium dark industrial Sound Control Panel and persist changes."""
    cfg = dict(get_sound_settings())
    cfg["robotVolumes"] = dict(cfg.get("robotVolumes", {}))

    active_theme_label = SOUND_THEMES.get(cfg.get("theme", "industrial"), "INDUSTRIAL FUTURE")
    status_color = "#10B981" if cfg.get("masterEnabled", True) else "#EF4444"
    status_text = "ONLINE • ARMED" if cfg.get("masterEnabled", True) else "MUTED"

    st.markdown(
        f"""
        <div style="background: linear-gradient(135deg, rgba(13, 21, 39, 0.94) 0%, rgba(8, 13, 24, 0.96) 100%);
                    border: 1px solid rgba(0, 240, 255, 0.28);
                    border-radius: 10px;
                    padding: 14px 16px;
                    margin-bottom: 12px;
                    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.45), inset 0 1px 0 rgba(255,255,255,0.05);">
            <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;">
                <div>
                    <div style="font-family:'Orbitron','Space Grotesk',sans-serif;font-size:15px;font-weight:700;color:#f8fafc;letter-spacing:0.6px;">
                        🔊 AUTONOMOUS ACOUSTIC TELEMETRY &amp; SOUND ENGINE
                    </div>
                    <div style="font-size:11px;color:#94a3b8;margin-top:2px;">
                        Web Audio procedural synthesis • Event-locked to real robot kinematics &amp; parcel lifecycle
                    </div>
                </div>
                <div style="display:flex;align-items:center;gap:8px;">
                    <span style="background:rgba(217,70,239,0.16);border:1px solid rgba(217,70,239,0.45);color:#e879f9;font-size:10px;font-weight:700;padding:3px 9px;border-radius:4px;">
                        THEME: {active_theme_label}
                    </span>
                    <span style="background:rgba(16,185,129,0.14);border:1px solid {status_color};color:{status_color};font-size:10px;font-weight:700;padding:3px 9px;border-radius:4px;">
                        ● {status_text}
                    </span>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    c_top1, c_top2, c_top3 = st.columns([1.0, 1.4, 0.9])
    with c_top1:
        cfg["masterEnabled"] = st.toggle(
            "Master Sound ON / OFF",
            value=bool(cfg.get("masterEnabled", True)),
            key=f"{key_prefix}_master_on",
        )
    with c_top2:
        theme_keys = list(SOUND_THEMES.keys())
        cur_idx = theme_keys.index(cfg.get("theme", "industrial")) if cfg.get("theme") in theme_keys else 0
        cfg["theme"] = st.selectbox(
            "Sound Theme",
            options=theme_keys,
            index=cur_idx,
            format_func=lambda k: SOUND_THEMES[k],
            key=f"{key_prefix}_theme",
        )
    with c_top3:
        st.write("")
        preview_clicked = st.button(
            "▶ Preview Sound",
            key=f"{key_prefix}_preview_btn",
            use_container_width=True,
        )

    if preview_clicked:
        _render_preview_audio_snippet(cfg["theme"], cfg.get("masterVolume", 0.75))

    c_vol1, c_vol2, c_vol3 = st.columns(3)
    with c_vol1:
        cfg["masterVolume"] = st.slider(
            "Master Volume",
            min_value=0.0,
            max_value=1.0,
            value=float(cfg.get("masterVolume", 0.75)),
            step=0.05,
            key=f"{key_prefix}_master_vol",
        )
    with c_vol2:
        cfg["sfxVolume"] = st.slider(
            "Sound Effects Volume",
            min_value=0.0,
            max_value=1.0,
            value=float(cfg.get("sfxVolume", 0.85)),
            step=0.05,
            key=f"{key_prefix}_sfx_vol",
        )
    with c_vol3:
        cfg["ambientVolume"] = st.slider(
            "Ambient Volume",
            min_value=0.0,
            max_value=1.0,
            value=float(cfg.get("ambientVolume", 0.25)),
            step=0.05,
            key=f"{key_prefix}_amb_vol",
        )

    st.markdown("**Event Channel Toggles**")
    t1, t2, t3, t4, t5 = st.columns(5)
    with t1:
        cfg["movementEnabled"] = st.checkbox("Movement", value=bool(cfg.get("movementEnabled", True)), key=f"{key_prefix}_move")
    with t2:
        cfg["pickupEnabled"] = st.checkbox("Pickup", value=bool(cfg.get("pickupEnabled", True)), key=f"{key_prefix}_pick")
    with t3:
        cfg["deliveryEnabled"] = st.checkbox("Delivery", value=bool(cfg.get("deliveryEnabled", True)), key=f"{key_prefix}_deliv")
    with t4:
        cfg["scanningEnabled"] = st.checkbox("Scanning", value=bool(cfg.get("scanningEnabled", True)), key=f"{key_prefix}_scan")
    with t5:
        cfg["ambientEnabled"] = st.checkbox("Ambient", value=bool(cfg.get("ambientEnabled", False)), key=f"{key_prefix}_amb")

    st.markdown("**Individual Robot Audio Mix**")
    r_cols = st.columns(5)
    for idx, rid in enumerate([1, 2, 3, 4, 5]):
        r_name, r_desc = ROBOT_AUDIO_NAMES[rid]
        with r_cols[idx]:
            cur_rv = float(cfg["robotVolumes"].get(str(rid), 1.0))
            cfg["robotVolumes"][str(rid)] = st.slider(
                f"0{rid} {r_name}",
                min_value=0.0,
                max_value=1.5,
                value=cur_rv,
                step=0.05,
                help=r_desc,
                key=f"{key_prefix}_rvol_{rid}",
            )

    save_persisted_sound_settings(cfg)
    st.divider()
    st.markdown("**🗣️ Futuristic AI Voice Announcements**")
    v_top1, v_top2, v_top3 = st.columns([1.0, 1.2, 1.2])
    with v_top1:
        cfg["voiceEnabled"] = st.toggle(
            "AI Voice ON / OFF",
            value=bool(cfg.get("voiceEnabled", True)),
            key=f"{key_prefix}_voice_on",
        )
        cfg["voiceVolume"] = st.slider(
            "Voice Volume",
            min_value=0.0,
            max_value=1.0,
            value=float(cfg.get("voiceVolume", 0.9)),
            step=0.05,
            key=f"{key_prefix}_voice_vol",
        )
    with v_top2:
        vp_keys = list(VOICE_PROFILES.keys())
        vp_idx = vp_keys.index(cfg.get("voiceProfile", "command_ai")) if cfg.get("voiceProfile") in vp_keys else 0
        cfg["voiceProfile"] = st.selectbox(
            "Normal Voice Profile",
            options=vp_keys,
            index=vp_idx,
            format_func=lambda k: VOICE_PROFILES[k],
            key=f"{key_prefix}_voice_prof",
        )
        if st.button("🗣️ Test Voice", key=f"{key_prefix}_test_voice", use_container_width=True):
            _render_preview_voice_snippet(cfg["voiceProfile"], cfg["voiceVolume"], is_emergency=False)
    with v_top3:
        ep_keys = list(EMERGENCY_VOICE_OPTIONS.keys())
        ep_idx = ep_keys.index(cfg.get("emergencyVoiceProfile", "match_selected")) if cfg.get("emergencyVoiceProfile") in ep_keys else 0
        cfg["emergencyVoiceProfile"] = st.selectbox(
            "Emergency Alert Voice",
            options=ep_keys,
            index=ep_idx,
            format_func=lambda k: EMERGENCY_VOICE_OPTIONS[k],
            key=f"{key_prefix}_emg_prof",
        )
        if st.button("🚨 Test Emergency", key=f"{key_prefix}_test_emg", use_container_width=True):
            emg_prof = cfg["voiceProfile"] if cfg["emergencyVoiceProfile"] == "match_selected" else cfg["emergencyVoiceProfile"]
            _render_preview_voice_snippet(emg_prof, cfg["voiceVolume"], is_emergency=True)

    vc1, vc2, vc3, vc4 = st.columns(4)
    with vc1:
        cfg["voiceMovement"] = st.checkbox("Movement Voice", value=bool(cfg.get("voiceMovement", True)), key=f"{key_prefix}_vmove")
    with vc2:
        cfg["voiceParcels"] = st.checkbox("Parcel Ops Voice", value=bool(cfg.get("voiceParcels", True)), key=f"{key_prefix}_vparc")
    with vc3:
        cfg["voiceEmergency"] = st.checkbox("Emergency Voice", value=bool(cfg.get("voiceEmergency", True)), key=f"{key_prefix}_vemg")
    with vc4:
        cfg["voiceSystem"] = st.checkbox("System & Fleet Voice", value=bool(cfg.get("voiceSystem", True)), key=f"{key_prefix}_vsys")

    save_persisted_sound_settings(cfg)
    return cfg
