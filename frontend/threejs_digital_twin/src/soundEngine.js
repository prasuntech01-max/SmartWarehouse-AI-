/**
 * SmartWarehouse AI — Futuristic Procedural Web Audio Sound Engine
 * ══════════════════════════════════════════════════════════════════
 * Zero external audio files, zero memory leaks, low CPU footprint.
 * Generates multi-layered sci-fi, industrial, alien, and cyberpunk audio
 * with individual sound identities for all 5 autonomous robots:
 *   1: TITAN-X  (Heavy AMR — deep mechanical engine & hydraulics)
 *   2: ATLAS    (Humanoid — precision servo motors & footsteps)
 *   3: VORTEX   (Humanoid — fast electronic turbine & high-speed scan)
 *   4: NOVA     (Humanoid — intelligent harmonic sonar & inspection pulses)
 *   5: SPECTRE  (Humanoid — alien-like mechanical shimmer & sensor pulses)
 */

export const SOUND_THEMES = {
  industrial: {
    id: 'industrial',
    label: 'INDUSTRIAL FUTURE',
    subtitle: 'Mechanical servos, hydraulics & precision relays',
    pitchMult: 1.0,
    fmDepth: 18,
    filterQ: 3.5,
    reverbMix: 0.16,
    wavePrimary: 'sawtooth',
    waveSecondary: 'triangle',
  },
  alien: {
    id: 'alien',
    label: 'ALIEN TECHNOLOGY',
    subtitle: 'Deep FM resonance, crystalline pulses & warp hum',
    pitchMult: 0.86,
    fmDepth: 65,
    filterQ: 7.0,
    reverbMix: 0.34,
    wavePrimary: 'sine',
    waveSecondary: 'triangle',
  },
  cyberpunk: {
    id: 'cyberpunk',
    label: 'CYBERPUNK',
    subtitle: 'Energetic digital synths, sub-pulses & bright chirps',
    pitchMult: 1.16,
    fmDepth: 36,
    filterQ: 5.5,
    reverbMix: 0.24,
    wavePrimary: 'square',
    waveSecondary: 'sawtooth',
  },
};

export const ROBOT_AUDIO_PROFILES = {
  1: { name: 'TITAN-X', baseFreq: 64, harmonic: 1.5, stepDur: 0.14, style: 'heavy_amr' },
  2: { name: 'ATLAS', baseFreq: 210, harmonic: 1.48, stepDur: 0.09, style: 'servo_humanoid' },
  3: { name: 'VORTEX', baseFreq: 390, harmonic: 1.75, stepDur: 0.07, style: 'fast_sorter' },
  4: { name: 'NOVA', baseFreq: 520, harmonic: 1.5, stepDur: 0.08, style: 'inspector_sonar' },
  5: { name: 'SPECTRE', baseFreq: 165, harmonic: 1.618, stepDur: 0.11, style: 'alien_stealth' },
};

export const DEFAULT_SOUND_SETTINGS = {
  masterEnabled: true,
  masterVolume: 0.75,
  sfxVolume: 0.85,
  ambientVolume: 0.25,
  movementEnabled: true,
  pickupEnabled: true,
  deliveryEnabled: true,
  scanningEnabled: true,
  ambientEnabled: false,
  theme: 'industrial',
  robotVolumes: { 1: 1.0, 2: 1.0, 3: 1.0, 4: 1.0, 5: 1.0 },
};

const STORAGE_KEY = 'sw_sound_settings_v1';

class SoundEngine {
  constructor() {
    this.ctx = null;
    this.masterGain = null;
    this.sfxGain = null;
    this.ambientGain = null;
    this.reverbSend = null;
    this.compressor = null;
    this.analyser = null;
    this.noiseBuffer = null;

    this.unlocked = false;
    this.supported = typeof window !== 'undefined' && !!(window.AudioContext || window.webkitAudioContext);
    this.settings = this._loadSettings();

    this.ambientNodes = null;
    this.cooldowns = new Map();
    this.lastActivityAt = 0;
  }

  _loadSettings() {
    const base = JSON.parse(JSON.stringify(DEFAULT_SOUND_SETTINGS));
    try {
      const raw = window.localStorage?.getItem(STORAGE_KEY);
      if (raw) {
        const parsed = JSON.parse(raw);
        Object.assign(base, parsed);
        if (parsed.robotVolumes) {
          base.robotVolumes = Object.assign({}, DEFAULT_SOUND_SETTINGS.robotVolumes, parsed.robotVolumes);
        }
      }
    } catch (_) {
      // Ignore storage errors in restricted iframes
    }
    return base;
  }

  _saveSettings() {
    try {
      window.localStorage?.setItem(STORAGE_KEY, JSON.stringify(this.settings));
    } catch (_) {
      // Ignore storage errors
    }
  }

  _ensureContext() {
    if (!this.supported) return false;
    if (!this.ctx) {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      this.ctx = new AudioCtx();

      this.compressor = this.ctx.createDynamicsCompressor();
      this.compressor.threshold.value = -14;
      this.compressor.knee.value = 18;
      this.compressor.ratio.value = 6;
      this.compressor.attack.value = 0.005;
      this.compressor.release.value = 0.15;

      this.masterGain = this.ctx.createGain();
      this.sfxGain = this.ctx.createGain();
      this.ambientGain = this.ctx.createGain();
      this.analyser = this.ctx.createAnalyser();
      this.analyser.fftSize = 64;
      this.analyser.smoothingTimeConstant = 0.78;

      // Subtle procedural delay-feedback space reverb (no external IR needed)
      this.reverbSend = this.ctx.createGain();
      const delayL = this.ctx.createDelay(0.5);
      const delayR = this.ctx.createDelay(0.5);
      delayL.delayTime.value = 0.095;
      delayR.delayTime.value = 0.145;
      const fbL = this.ctx.createGain();
      const fbR = this.ctx.createGain();
      fbL.gain.value = 0.28;
      fbR.gain.value = 0.24;
      const revFilter = this.ctx.createBiquadFilter();
      revFilter.type = 'lowpass';
      revFilter.frequency.value = 2600;

      this.reverbSend.connect(delayL);
      this.reverbSend.connect(delayR);
      delayL.connect(fbL);
      fbL.connect(delayR);
      delayR.connect(fbR);
      fbR.connect(delayL);
      delayL.connect(revFilter);
      delayR.connect(revFilter);
      revFilter.connect(this.masterGain);

      this.sfxGain.connect(this.masterGain);
      this.sfxGain.connect(this.reverbSend);
      this.ambientGain.connect(this.masterGain);

      this.masterGain.connect(this.compressor);
      this.compressor.connect(this.analyser);
      this.analyser.connect(this.ctx.destination);

      this.noiseBuffer = this._createNoiseBuffer(1.5);
      this._applyGains();
    }
    return true;
  }

  _createNoiseBuffer(seconds) {
    const sampleRate = this.ctx.sampleRate;
    const len = Math.floor(sampleRate * seconds);
    const buf = this.ctx.createBuffer(1, len, sampleRate);
    const data = buf.getChannelData(0);
    for (let i = 0; i < len; i++) {
      data[i] = Math.random() * 2 - 1;
    }
    return buf;
  }

  async unlockAudio() {
    if (!this._ensureContext()) return false;
    try {
      if (this.ctx.state === 'suspended') {
        await this.ctx.resume();
      }
      this.unlocked = this.ctx.state === 'running';
      this._applyGains();
      if (this.unlocked && this.settings.masterEnabled && this.settings.ambientEnabled) {
        this.startAmbient();
      }
      return this.unlocked;
    } catch (_) {
      return false;
    }
  }

  getStatus() {
    return {
      supported: this.supported,
      unlocked: this.unlocked && this.ctx?.state === 'running',
      ctxState: this.ctx ? this.ctx.state : 'uninitialized',
      theme: this.settings.theme,
      masterEnabled: this.settings.masterEnabled,
      ambientEnabled: this.settings.ambientEnabled,
      activeRecently: (performance.now() - this.lastActivityAt) < 800,
    };
  }

  updateSettings(partial) {
    if (!partial || typeof partial !== 'object') return;
    if (partial.robotVolumes) {
      this.settings.robotVolumes = Object.assign({}, this.settings.robotVolumes, partial.robotVolumes);
    }
    const rest = { ...partial };
    delete rest.robotVolumes;
    Object.assign(this.settings, rest);
    this._saveSettings();
    this._applyGains();

    if (this.unlocked) {
      if (this.settings.masterEnabled && this.settings.ambientEnabled) {
        this.startAmbient();
      } else {
        this.stopAmbient();
      }
    }
  }

  _applyGains() {
    if (!this.ctx) return;
    const now = this.ctx.currentTime;
    const master = this.settings.masterEnabled ? this.settings.masterVolume : 0.0;
    const theme = SOUND_THEMES[this.settings.theme] || SOUND_THEMES.industrial;

    this.masterGain.gain.setTargetAtTime(master, now, 0.02);
    this.sfxGain.gain.setTargetAtTime(this.settings.sfxVolume, now, 0.02);
    this.ambientGain.gain.setTargetAtTime(
      this.settings.ambientEnabled ? this.settings.ambientVolume * 0.45 : 0.0,
      now,
      0.08
    );
    this.reverbSend.gain.setTargetAtTime(theme.reverbMix, now, 0.04);
  }

  _canPlay(key, cooldownMs = 110) {
    if (!this.supported || !this.settings.masterEnabled) return false;
    if (!this.ctx || this.ctx.state !== 'running') return false;
    const now = performance.now();
    const prev = this.cooldowns.get(key) || 0;
    if (now - prev < cooldownMs) return false;
    this.cooldowns.set(key, now);
    this.lastActivityAt = now;
    return true;
  }

  _robotVol(robotId) {
    const v = this.settings.robotVolumes?.[Number(robotId)];
    return v !== undefined ? Math.max(0, Math.min(1.5, Number(v))) : 1.0;
  }

  _theme() {
    return SOUND_THEMES[this.settings.theme] || SOUND_THEMES.industrial;
  }

  _profile(robotId) {
    return ROBOT_AUDIO_PROFILES[Number(robotId)] || ROBOT_AUDIO_PROFILES[2];
  }

  /** Helper: play a shaped tone with optional FM & filter sweep and clean auto-disconnect */
  _tone({
    freq = 440,
    endFreq = null,
    dur = 0.2,
    delay = 0,
    gain = 0.2,
    type = 'sine',
    filterType = 'lowpass',
    filterFreq = 3200,
    filterQ = 2.0,
    fmFreq = 0,
    fmDepth = 0,
    attack = 0.01,
    dest = null,
  }) {
    if (!this.ctx) return;
    const t0 = this.ctx.currentTime + delay;
    const t1 = t0 + Math.max(0.02, dur);

    const osc = this.ctx.createOscillator();
    osc.type = type;
    osc.frequency.setValueAtTime(Math.max(20, freq), t0);
    if (endFreq !== null && endFreq > 0) {
      osc.frequency.exponentialRampToValueAtTime(Math.max(20, endFreq), t1);
    }

    let modOsc = null;
    let modGain = null;
    if (fmFreq > 0 && fmDepth > 0) {
      modOsc = this.ctx.createOscillator();
      modOsc.type = 'sine';
      modOsc.frequency.setValueAtTime(fmFreq, t0);
      modGain = this.ctx.createGain();
      modGain.gain.setValueAtTime(fmDepth, t0);
      modOsc.connect(modGain);
      modGain.connect(osc.frequency);
    }

    const filter = this.ctx.createBiquadFilter();
    filter.type = filterType;
    filter.frequency.setValueAtTime(filterFreq, t0);
    filter.Q.setValueAtTime(filterQ, t0);

    const env = this.ctx.createGain();
    env.gain.setValueAtTime(0.0001, t0);
    env.gain.linearRampToValueAtTime(Math.max(0.0002, gain), t0 + Math.min(attack, dur * 0.4));
    env.gain.exponentialRampToValueAtTime(0.0001, t1);

    osc.connect(filter);
    filter.connect(env);
    env.connect(dest || this.sfxGain);

    osc.start(t0);
    osc.stop(t1 + 0.02);
    if (modOsc) {
      modOsc.start(t0);
      modOsc.stop(t1 + 0.02);
    }

    osc.onended = () => {
      try {
        osc.disconnect();
        filter.disconnect();
        env.disconnect();
        if (modOsc) modOsc.disconnect();
        if (modGain) modGain.disconnect();
      } catch (_) {}
    };
  }

  /** Helper: play filtered noise burst (hydraulics, pneumatic release, mechanical latch) */
  _noise({ dur = 0.12, delay = 0, gain = 0.1, filterType = 'bandpass', freq = 1400, endFreq = null, q = 2.5 }) {
    if (!this.ctx || !this.noiseBuffer) return;
    const t0 = this.ctx.currentTime + delay;
    const t1 = t0 + Math.max(0.02, dur);

    const src = this.ctx.createBufferSource();
    src.buffer = this.noiseBuffer;

    const filter = this.ctx.createBiquadFilter();
    filter.type = filterType;
    filter.frequency.setValueAtTime(freq, t0);
    if (endFreq !== null) {
      filter.frequency.exponentialRampToValueAtTime(Math.max(40, endFreq), t1);
    }
    filter.Q.setValueAtTime(q, t0);

    const env = this.ctx.createGain();
    env.gain.setValueAtTime(0.0001, t0);
    env.gain.linearRampToValueAtTime(Math.max(0.0002, gain), t0 + 0.01);
    env.gain.exponentialRampToValueAtTime(0.0001, t1);

    src.connect(filter);
    filter.connect(env);
    env.connect(this.sfxGain);

    src.start(t0);
    src.stop(t1 + 0.02);
    src.onended = () => {
      try {
        src.disconnect();
        filter.disconnect();
        env.disconnect();
      } catch (_) {}
    };
  }

  // ═══════════════════════════════════════════════════════════════
  //  A & B. ROBOT IDENTITIES & MOVEMENT SOUNDS
  // ═══════════════════════════════════════════════════════════════

  playRobotMoveStart(robotId) {
    if (!this.settings.movementEnabled) return;
    if (!this._canPlay(`move_start_${robotId}`, 260)) return;
    const rv = this._robotVol(robotId);
    if (rv <= 0.01) return;

    const th = this._theme();
    const pr = this._profile(robotId);
    const f = pr.baseFreq * th.pitchMult;

    if (pr.style === 'heavy_amr') {
      // TITAN-X: deep turbine spool-up + pneumatic brake release
      this._tone({ freq: f * 0.8, endFreq: f * 1.45, dur: 0.28, gain: 0.22 * rv, type: th.wavePrimary, filterFreq: 420, fmFreq: 16, fmDepth: th.fmDepth * 0.6 });
      this._noise({ dur: 0.14, delay: 0.02, gain: 0.09 * rv, filterType: 'bandpass', freq: 1800, endFreq: 650, q: 2.0 });
    } else if (pr.style === 'servo_humanoid') {
      // ATLAS: dual precision servo engagement
      this._tone({ freq: f, endFreq: f * 1.35, dur: 0.16, gain: 0.14 * rv, type: th.waveSecondary, filterFreq: 1800, fmFreq: 28, fmDepth: th.fmDepth * 0.4 });
      this._tone({ freq: f * 2, endFreq: f * 2.2, dur: 0.1, delay: 0.04, gain: 0.07 * rv, type: 'sine', filterFreq: 2800 });
    } else if (pr.style === 'fast_sorter') {
      // VORTEX: rapid electric acceleration chirp
      this._tone({ freq: f * 0.9, endFreq: f * 1.9, dur: 0.15, gain: 0.13 * rv, type: th.wavePrimary, filterFreq: 2600, fmFreq: 45, fmDepth: th.fmDepth });
    } else if (pr.style === 'inspector_sonar') {
      // NOVA: intelligent activation ping + soft drive
      this._tone({ freq: f, endFreq: f * 1.25, dur: 0.14, gain: 0.11 * rv, type: 'sine', filterFreq: 3200 });
      this._tone({ freq: f * 1.5, dur: 0.12, delay: 0.06, gain: 0.09 * rv, type: 'triangle', filterFreq: 3600 });
    } else {
      // SPECTRE: alien stealth phase swell
      this._tone({ freq: f, endFreq: f * 1.18, dur: 0.24, gain: 0.13 * rv, type: 'sine', filterFreq: 1600, fmFreq: 11, fmDepth: th.fmDepth * 1.1 });
      this._tone({ freq: f * 1.618, endFreq: f * 1.8, dur: 0.2, delay: 0.03, gain: 0.07 * rv, type: 'triangle', filterFreq: 2200 });
    }
  }

  playRobotStep(robotId, carrying = false) {
    if (!this.settings.movementEnabled) return;
    if (!this._canPlay(`step_${robotId}`, 220)) return;
    const rv = this._robotVol(robotId);
    if (rv <= 0.01) return;

    const th = this._theme();
    const pr = this._profile(robotId);
    const loadPitch = carrying ? 0.9 : 1.0;
    const jitter = 0.96 + Math.random() * 0.08;
    const f = pr.baseFreq * th.pitchMult * loadPitch * jitter;

    if (pr.style === 'heavy_amr') {
      // Subtle low mechanical roll + tread pulse
      this._tone({ freq: f * 0.9, endFreq: f * 0.72, dur: 0.12, gain: 0.13 * rv, type: 'triangle', filterFreq: 280 });
      this._noise({ dur: 0.06, gain: 0.04 * rv, filterType: 'lowpass', freq: 520 });
    } else if (pr.style === 'servo_humanoid') {
      // Crisp humanoid servo + magnetic footstep
      this._tone({ freq: f * 0.7, endFreq: f * 0.45, dur: 0.07, gain: 0.09 * rv, type: 'triangle', filterFreq: 900 });
      this._tone({ freq: f * 1.4, endFreq: f * 1.6, dur: 0.06, gain: 0.05 * rv, type: 'sine', filterFreq: 2100 });
    } else if (pr.style === 'fast_sorter') {
      // Agile zip pulse
      this._tone({ freq: f, endFreq: f * 1.18, dur: 0.07, gain: 0.07 * rv, type: th.waveSecondary, filterFreq: 2200 });
    } else if (pr.style === 'inspector_sonar') {
      // Light precision glide
      this._tone({ freq: f * 0.8, endFreq: f * 0.92, dur: 0.07, gain: 0.06 * rv, type: 'sine', filterFreq: 2400 });
    } else {
      // SPECTRE: soft alien pulse
      this._tone({ freq: f, endFreq: f * 0.95, dur: 0.09, gain: 0.07 * rv, type: 'sine', filterFreq: 1400, fmFreq: 9, fmDepth: 14 });
    }
  }

  playRobotTurn(robotId) {
    if (!this.settings.movementEnabled) return;
    if (!this._canPlay(`turn_${robotId}`, 250)) return;
    const rv = this._robotVol(robotId);
    if (rv <= 0.01) return;

    const th = this._theme();
    const pr = this._profile(robotId);
    const f = pr.baseFreq * th.pitchMult;

    this._tone({ freq: f * 1.1, endFreq: f * 1.4, dur: 0.09, gain: 0.07 * rv, type: th.waveSecondary, filterFreq: 1800 });
    this._noise({ dur: 0.05, gain: 0.03 * rv, filterType: 'bandpass', freq: 2200, q: 3.0 });
  }

  playRobotStop(robotId) {
    if (!this.settings.movementEnabled) return;
    if (!this._canPlay(`stop_${robotId}`, 280)) return;
    const rv = this._robotVol(robotId);
    if (rv <= 0.01) return;

    const th = this._theme();
    const pr = this._profile(robotId);
    const f = pr.baseFreq * th.pitchMult;

    this._tone({ freq: f * 1.25, endFreq: f * 0.65, dur: 0.16, gain: 0.11 * rv, type: th.waveSecondary, filterFreq: 1100 });
    if (pr.style === 'heavy_amr') {
      this._noise({ dur: 0.1, delay: 0.02, gain: 0.07 * rv, filterType: 'bandpass', freq: 1400, endFreq: 480 });
    }
  }

  playRobotArrive(robotId) {
    if (!this.settings.movementEnabled) return;
    if (!this._canPlay(`arrive_${robotId}`, 300)) return;
    const rv = this._robotVol(robotId);
    if (rv <= 0.01) return;

    const th = this._theme();
    const pr = this._profile(robotId);
    const f = pr.baseFreq * th.pitchMult;
    this._tone({ freq: f * 1.2, endFreq: f * 0.9, dur: 0.14, gain: 0.1 * rv, type: 'triangle', filterFreq: 1600 });
    this._tone({ freq: 620 * th.pitchMult, dur: 0.09, delay: 0.05, gain: 0.07 * rv, type: 'sine', filterFreq: 3200 });
  }

  // ═══════════════════════════════════════════════════════════════
  //  C. SCANNING & PARCEL PICKUP SOUNDS
  // ═══════════════════════════════════════════════════════════════

  playScan(robotId) {
    if (!this.settings.scanningEnabled) return;
    if (!this._canPlay(`scan_${robotId}`, 450)) return;
    const rv = this._robotVol(robotId);
    if (rv <= 0.01) return;

    const th = this._theme();
    const f = 580 * th.pitchMult;
    // Sweeping laser scan + intelligent confirmation ping
    this._tone({ freq: f, endFreq: f * 2.1, dur: 0.18, gain: 0.11 * rv, type: 'sine', filterFreq: 4200, fmFreq: 32, fmDepth: th.fmDepth * 0.6 });
    this._tone({ freq: f * 2.2, dur: 0.09, delay: 0.15, gain: 0.09 * rv, type: 'triangle', filterFreq: 4600 });
  }

  playPickupSequence(robotId) {
    if (!this.settings.pickupEnabled) return;
    if (!this._canPlay(`pickup_${robotId}`, 380)) return;
    const rv = this._robotVol(robotId);
    if (rv <= 0.01) return;

    const th = this._theme();
    const pr = this._profile(robotId);
    const base = 360 * th.pitchMult;

    // 1. Parcel detection & laser lock
    this._tone({ freq: base * 1.4, endFreq: base * 2.1, dur: 0.11, delay: 0.0, gain: 0.11 * rv, type: 'sine', filterFreq: 3600 });
    // 2. Magnetic/mechanical latch click + hydraulic lift
    this._noise({ dur: 0.07, delay: 0.09, gain: 0.12 * rv, filterType: 'bandpass', freq: 1900, endFreq: 850, q: 3.2 });
    this._tone({ freq: pr.baseFreq * th.pitchMult, endFreq: pr.baseFreq * 1.55 * th.pitchMult, dur: 0.18, delay: 0.11, gain: 0.16 * rv, type: th.wavePrimary, filterFreq: 1400 });
    // 3. Technical pickup confirmation chime
    this._tone({ freq: base * 2.0, dur: 0.09, delay: 0.24, gain: 0.11 * rv, type: 'triangle', filterFreq: 4200 });
    this._tone({ freq: base * 2.5, dur: 0.14, delay: 0.31, gain: 0.13 * rv, type: 'sine', filterFreq: 4800 });
  }

  // ═══════════════════════════════════════════════════════════════
  //  D. DELIVERY & TASK COMPLETION SOUNDS
  // ═══════════════════════════════════════════════════════════════

  playDeliverySequence(robotId) {
    if (!this.settings.deliveryEnabled) return;
    if (!this._canPlay(`delivery_${robotId}`, 450)) return;
    const rv = this._robotVol(robotId);
    if (rv <= 0.01) return;

    const th = this._theme();
    const base = 330 * th.pitchMult;

    // 1. Pneumatic release & parcel placement thud
    this._noise({ dur: 0.09, delay: 0.0, gain: 0.1 * rv, filterType: 'bandpass', freq: 1500, endFreq: 520, q: 2.5 });
    this._tone({ freq: 140 * th.pitchMult, endFreq: 72 * th.pitchMult, dur: 0.14, delay: 0.02, gain: 0.16 * rv, type: 'triangle', filterFreq: 450 });

    // 2. Futuristic ascending harmonic confirmation chord
    this._tone({ freq: base * 1.5, dur: 0.14, delay: 0.12, gain: 0.12 * rv, type: 'sine', filterFreq: 4400 });
    this._tone({ freq: base * 2.0, dur: 0.16, delay: 0.20, gain: 0.13 * rv, type: 'sine', filterFreq: 4800 });
    this._tone({ freq: base * 3.0, dur: 0.28, delay: 0.28, gain: 0.14 * rv, type: 'triangle', filterFreq: 5200 });
  }

  playTaskAssigned(robotId) {
    if (!this.settings.deliveryEnabled && !this.settings.scanningEnabled) return;
    if (!this._canPlay(`assign_${robotId}`, 250)) return;
    const rv = this._robotVol(robotId);
    if (rv <= 0.01) return;

    const th = this._theme();
    const f = 480 * th.pitchMult;
    this._tone({ freq: f, dur: 0.08, gain: 0.1 * rv, type: 'triangle', filterFreq: 3400 });
    this._tone({ freq: f * 1.5, dur: 0.12, delay: 0.07, gain: 0.11 * rv, type: 'sine', filterFreq: 4000 });
  }

  // ═══════════════════════════════════════════════════════════════
  //  EMERGENCY STOP ALERT
  // ═══════════════════════════════════════════════════════════════

  playEmergencyStop() {
    if (!this._canPlay('estop', 600)) return;
    const th = this._theme();
    // Distinctive two-tone industrial/sci-fi klaxon + power-down sweep
    for (let i = 0; i < 2; i++) {
      const d = i * 0.24;
      this._tone({ freq: 580 * th.pitchMult, endFreq: 420 * th.pitchMult, dur: 0.18, delay: d, gain: 0.22, type: 'sawtooth', filterFreq: 2100, fmFreq: 24, fmDepth: 30 });
    }
    this._tone({ freq: 240, endFreq: 52, dur: 0.45, delay: 0.46, gain: 0.2, type: 'triangle', filterFreq: 680 });
    this._noise({ dur: 0.22, delay: 0.46, gain: 0.12, filterType: 'bandpass', freq: 1200, endFreq: 300 });
  }

  // ═══════════════════════════════════════════════════════════════
  //  E. WAREHOUSE AMBIENT SOUNDSCAPE
  // ═══════════════════════════════════════════════════════════════

  startAmbient() {
    if (!this.ctx || this.ctx.state !== 'running') return;
    if (this.ambientNodes) return;

    const th = this._theme();
    const now = this.ctx.currentTime;

    // Low-level futuristic facility hum (55Hz + 110Hz) + subtle modulated shimmer
    const osc1 = this.ctx.createOscillator();
    osc1.type = 'sine';
    osc1.frequency.setValueAtTime(55 * th.pitchMult, now);

    const osc2 = this.ctx.createOscillator();
    osc2.type = 'triangle';
    osc2.frequency.setValueAtTime(110.5 * th.pitchMult, now);

    const lfo = this.ctx.createOscillator();
    lfo.type = 'sine';
    lfo.frequency.setValueAtTime(0.18, now);

    const lfoGain = this.ctx.createGain();
    lfoGain.gain.setValueAtTime(140, now);

    const filter = this.ctx.createBiquadFilter();
    filter.type = 'lowpass';
    filter.frequency.setValueAtTime(260, now);
    filter.Q.setValueAtTime(1.5, now);

    const g1 = this.ctx.createGain();
    g1.gain.setValueAtTime(0.28, now);
    const g2 = this.ctx.createGain();
    g2.gain.setValueAtTime(0.11, now);

    lfo.connect(lfoGain);
    lfoGain.connect(filter.frequency);

    osc1.connect(g1);
    osc2.connect(g2);
    g1.connect(filter);
    g2.connect(filter);
    filter.connect(this.ambientGain);

    osc1.start(now);
    osc2.start(now);
    lfo.start(now);

    this.ambientNodes = { osc1, osc2, lfo, lfoGain, filter, g1, g2 };
  }

  stopAmbient() {
    if (!this.ambientNodes) return;
    const nodes = this.ambientNodes;
    this.ambientNodes = null;
    try {
      nodes.osc1.stop();
      nodes.osc2.stop();
      nodes.lfo.stop();
      nodes.osc1.disconnect();
      nodes.osc2.disconnect();
      nodes.lfo.disconnect();
      nodes.lfoGain.disconnect();
      nodes.filter.disconnect();
      nodes.g1.disconnect();
      nodes.g2.disconnect();
    } catch (_) {}
  }

  // ═══════════════════════════════════════════════════════════════
  //  THEME PREVIEW
  // ═══════════════════════════════════════════════════════════════

  async previewTheme(themeName = null) {
    await this.unlockAudio();
    if (!this.ctx || this.ctx.state !== 'running') return false;

    const prevTheme = this.settings.theme;
    if (themeName && SOUND_THEMES[themeName]) {
      this.settings.theme = themeName;
      this._applyGains();
    }

    this.lastActivityAt = performance.now();
    const th = this._theme();
    const f = 320 * th.pitchMult;

    // 1. Signature theme sweep
    this._tone({ freq: f * 0.5, endFreq: f * 1.4, dur: 0.28, delay: 0.0, gain: 0.2, type: th.wavePrimary, filterFreq: 2200, fmFreq: 22, fmDepth: th.fmDepth });
    // 2. Scanner pulse
    this._tone({ freq: f * 1.8, endFreq: f * 2.6, dur: 0.16, delay: 0.24, gain: 0.14, type: 'sine', filterFreq: 4200 });
    // 3. Mechanical latch + harmonic confirmation chord
    this._noise({ dur: 0.07, delay: 0.38, gain: 0.1, filterType: 'bandpass', freq: 1800 });
    this._tone({ freq: f * 1.5, dur: 0.16, delay: 0.44, gain: 0.13, type: th.waveSecondary, filterFreq: 3800 });
    this._tone({ freq: f * 2.25, dur: 0.26, delay: 0.54, gain: 0.15, type: 'sine', filterFreq: 4800 });

    if (themeName && themeName !== prevTheme) {
      // Keep selected theme if caller only wanted preview; caller updates theme explicitly if desired
      setTimeout(() => {
        this.settings.theme = prevTheme;
        this._applyGains();
      }, 950);
    }
    return true;
  }

  getVisualizerBins(outArray) {
    if (!this.analyser || !this.unlocked || !this.settings.masterEnabled) {
      outArray.fill(0);
      return false;
    }
    this.analyser.getByteFrequencyData(outArray);
    return true;
  }

  dispose() {
    this.stopAmbient();
    if (this.ctx) {
      try {
        this.ctx.close();
      } catch (_) {}
      this.ctx = null;
    }
    this.unlocked = false;
  }
}

export const soundEngine = new SoundEngine();
export default soundEngine;
