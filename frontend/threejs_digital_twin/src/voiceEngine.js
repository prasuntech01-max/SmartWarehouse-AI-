/**
 * SmartWarehouse AI — Futuristic AI Voice Announcement Engine
 * ══════════════════════════════════════════════════════════════
 * Priority-queued, cooldown-guarded Web Speech + Web Audio comms system.
 * Pairs crisp synthetic speech with subtle sci-fi radio/telemetry cues
 * and smooth ambient ducking. 100% offline, zero external APIs.
 */

import soundEngine from './soundEngine.js';

export const VOICE_PROFILES = {
  british_female: {
    id: 'british_female',
    label: 'BRITISH FEMALE AI',
    subtitle: 'Elegant British English female AI assistant',
    pitch: 1.04,
    rate: 0.94,
    cueFreq: 520,
    cueType: 'sine',
    gender: 'female',
    langPrefix: 'en-gb',
  },
  american_female: {
    id: 'american_female',
    label: 'AMERICAN FEMALE AI',
    subtitle: 'Clear, warm American English female AI assistant',
    pitch: 1.02,
    rate: 0.97,
    cueFreq: 560,
    cueType: 'triangle',
    gender: 'female',
    langPrefix: 'en-us',
  },
  command_ai: {
    id: 'command_ai',
    label: 'COMMAND AI',
    subtitle: 'Deep military-style industrial command voice',
    pitch: 0.72,
    rate: 0.92,
    cueFreq: 310,
    cueType: 'sawtooth',
    gender: 'male',
    langPrefix: 'en',
  },
  alien_core: {
    id: 'alien_core',
    label: 'ALIEN CORE',
    subtitle: 'Futuristic synthetic alien core voice',
    pitch: 0.62,
    rate: 0.84,
    cueFreq: 210,
    cueType: 'sine',
    gender: 'male',
    langPrefix: 'en',
  },
  cyber_robot: {
    id: 'cyber_robot',
    label: 'CYBER ROBOT',
    subtitle: 'Electronic robotic communication',
    pitch: 0.86,
    rate: 1.03,
    cueFreq: 480,
    cueType: 'square',
    gender: 'male',
    langPrefix: 'en',
  },
  neural_ai: {
    id: 'neural_ai',
    label: 'NEURAL AI',
    subtitle: 'Clean advanced AI assistant voice',
    pitch: 1.0,
    rate: 0.98,
    cueFreq: 560,
    cueType: 'triangle',
    gender: 'female',
    langPrefix: 'en',
  },
  alert_system: {
    id: 'alert_system',
    label: 'ALERT SYSTEM',
    subtitle: 'Powerful emergency and safety voice',
    pitch: 0.78,
    rate: 1.04,
    cueFreq: 640,
    cueType: 'sawtooth',
    gender: 'male',
    langPrefix: 'en',
  },
};

export const DEFAULT_VOICE_SETTINGS = {
  voiceEnabled: true,
  voiceVolume: 0.9,
  voiceProfile: 'command_ai',
  emergencyVoiceProfile: 'match_selected',
  voiceMovement: true,
  voiceParcels: true,
  voiceEmergency: true,
  voiceSystem: true,
};

const VOICE_STORAGE_KEY = 'sw_voice_settings_v1';

class VoiceEngine {
  constructor() {
    this.supported = typeof window !== 'undefined' && 'speechSynthesis' in window && typeof SpeechSynthesisUtterance !== 'undefined';
    this.settings = this._loadSettings();
    this.queue = [];
    this.speaking = false;
    this.currentPriority = 0;
    this.cooldowns = new Map();
    this.voices = [];

    if (this.supported) {
      this._refreshVoices();
      try {
        window.speechSynthesis.addEventListener?.('voiceschanged', () => this._refreshVoices());
      } catch (_) {}
    }
  }

  _loadSettings() {
    const base = { ...DEFAULT_VOICE_SETTINGS };
    try {
      const raw = window.localStorage?.getItem(VOICE_STORAGE_KEY);
      if (raw) Object.assign(base, JSON.parse(raw));
    } catch (_) {}
    return base;
  }

  _saveSettings() {
    try {
      window.localStorage?.setItem(VOICE_STORAGE_KEY, JSON.stringify(this.settings));
    } catch (_) {}
  }

  _refreshVoices() {
    if (!this.supported) return;
    try {
      this.voices = window.speechSynthesis.getVoices() || [];
    } catch (_) {
      this.voices = [];
    }
  }

  _pickBrowserVoice(profile) {
    if (!this.voices || this.voices.length === 0) this._refreshVoices();
    if (!this.voices || this.voices.length === 0) return null;

    const enVoices = this.voices.filter(v => String(v.lang).toLowerCase().startsWith('en'));
    const pool = enVoices.length > 0 ? enVoices : this.voices;

    const femaleRx = /libby|sonia|hazel|kate|serena|susan|martha|aria|jenny|zira|samantha|ava|allison|victoria|emma|amy|female|natural/i;
    const maleRx = /david|mark|daniel|george|james|ryan|guy|alex|male/i;

    if (profile.gender === 'female') {
      const langPrefix = (profile.langPrefix || 'en').toLowerCase();
      const langPool = pool.filter(v => String(v.lang).toLowerCase().startsWith(langPrefix));
      const exactFemale = langPool.find(v => femaleRx.test(v.name) && !maleRx.test(v.name));
      if (exactFemale) return exactFemale;
      const langNonMale = langPool.find(v => !maleRx.test(v.name));
      if (langNonMale) return langNonMale;
      const anyFemale = pool.find(v => femaleRx.test(v.name) && !maleRx.test(v.name));
      if (anyFemale) return anyFemale;
    } else {
      const deep = pool.find(v => maleRx.test(v.name));
      if (deep) return deep;
    }
    return pool[0];
  }

  updateSettings(partial) {
    if (!partial || typeof partial !== 'object') return;
    for (const k of Object.keys(DEFAULT_VOICE_SETTINGS)) {
      if (partial[k] !== undefined) {
        this.settings[k] = partial[k];
      }
    }
    this._saveSettings();
    if (!this.settings.voiceEnabled) {
      this.clearQueue();
    }
  }

  clearQueue() {
    this.queue = [];
    this.speaking = false;
    this.currentPriority = 0;
    if (this.supported) {
      try {
        window.speechSynthesis.cancel();
      } catch (_) {}
    }
    this._restoreAmbientDuck();
  }

  _duckAmbient() {
    if (soundEngine.ctx && soundEngine.ambientGain && soundEngine.settings.ambientEnabled) {
      const now = soundEngine.ctx.currentTime;
      soundEngine.ambientGain.gain.setTargetAtTime(soundEngine.settings.ambientVolume * 0.16, now, 0.05);
    }
  }

  _restoreAmbientDuck() {
    if (soundEngine.ctx && soundEngine.ambientGain) {
      const now = soundEngine.ctx.currentTime;
      const target = soundEngine.settings.ambientEnabled ? soundEngine.settings.ambientVolume * 0.45 : 0.0;
      soundEngine.ambientGain.gain.setTargetAtTime(target, now, 0.12);
    }
  }

  _playCommsCue(profile, isEmergency = false, isClosing = false) {
    if (!soundEngine.ctx || soundEngine.ctx.state !== 'running') return;
    if (!soundEngine.settings.masterEnabled) return;
    const f = profile.cueFreq || 380;
    const vol = Math.min(0.18, 0.12 * this.settings.voiceVolume);
    if (isEmergency && !isClosing) {
      soundEngine._tone({ freq: f, endFreq: f * 1.25, dur: 0.1, gain: vol, type: 'sawtooth', filterFreq: 2400 });
      soundEngine._tone({ freq: f * 1.3, endFreq: f * 0.9, dur: 0.1, delay: 0.09, gain: vol, type: 'sawtooth', filterFreq: 2400 });
    } else if (!isClosing) {
      // Subtle radio squelch + AI comms-open tone
      soundEngine._noise({ dur: 0.045, gain: vol * 0.55, filterType: 'bandpass', freq: 2100, q: 3.5 });
      soundEngine._tone({ freq: f, endFreq: f * 1.35, dur: 0.09, delay: 0.015, gain: vol, type: profile.cueType, filterFreq: 2800 });
    } else {
      // Short comms-close click
      soundEngine._tone({ freq: f * 1.2, endFreq: f * 0.8, dur: 0.06, gain: vol * 0.7, type: 'triangle', filterFreq: 2400 });
    }
  }

  /**
   * Queue a context-aware voice announcement.
   * @param {string} text - Spoken phrase.
   * @param {object} opts
   * @param {'movement'|'parcels'|'emergency'|'system'} opts.category
   * @param {number} opts.priority - 1=movement, 2=parcel/system, 3=emergency
   * @param {string} opts.dedupeKey - Cooldown key
   * @param {number} opts.cooldownMs - Minimum interval between identical/similar announcements
   * @param {boolean} opts.force - Bypass category toggle (for Test buttons)
   */
  announce(text, { category = 'system', priority = 2, dedupeKey = null, cooldownMs = 3500, force = false } = {}) {
    if (!text) return false;
    if (!soundEngine.settings.masterEnabled && !force) return false;
    if (!this.settings.voiceEnabled && !force) return false;

    if (!force) {
      if (category === 'movement' && !this.settings.voiceMovement) return false;
      if (category === 'parcels' && !this.settings.voiceParcels) return false;
      if (category === 'emergency' && !this.settings.voiceEmergency) return false;
      if (category === 'system' && !this.settings.voiceSystem) return false;
    }

    const now = performance.now();
    if (dedupeKey && !force) {
      const prev = this.cooldowns.get(dedupeKey) || 0;
      if (now - prev < cooldownMs) return false;
      this.cooldowns.set(dedupeKey, now);
    }

    const isEmergency = category === 'emergency' || priority >= 3;
    const item = { text, category, priority, isEmergency };

    // Emergency alerts preempt lower-priority speech immediately
    if (isEmergency) {
      this.queue = this.queue.filter(q => q.isEmergency);
      if (this.speaking && this.currentPriority < 3 && this.supported) {
        try { window.speechSynthesis.cancel(); } catch (_) {}
        this.speaking = false;
      }
      this.queue.unshift(item);
    } else {
      // Drop oldest low-priority item if queue is full so speech stays real-time
      if (this.queue.length >= 3) {
        if (priority <= 1) return false;
        const lowIdx = this.queue.findIndex(q => q.priority <= 1);
        if (lowIdx >= 0) this.queue.splice(lowIdx, 1);
        else this.queue.shift();
      }
      this.queue.push(item);
      this.queue.sort((a, b) => b.priority - a.priority);
    }

    this._processNext();
    return true;
  }

  _processNext() {
    if (this.speaking || this.queue.length === 0) return;

    const item = this.queue.shift();
    const emgSel = this.settings.emergencyVoiceProfile;
    const profileId = (item.isEmergency && emgSel && emgSel !== 'match_selected')
      ? emgSel
      : this.settings.voiceProfile;
    const profile = VOICE_PROFILES[profileId] || VOICE_PROFILES.command_ai;

    this.speaking = true;
    this.currentPriority = item.priority;
    this._duckAmbient();
    this._playCommsCue(profile, item.isEmergency, false);

    if (!this.supported) {
      setTimeout(() => {
        this.speaking = false;
        this.currentPriority = 0;
        this._restoreAmbientDuck();
        this._processNext();
      }, 350);
      return;
    }

    try {
      const utt = new SpeechSynthesisUtterance(item.text);
      const v = this._pickBrowserVoice(profile);
      if (v) utt.voice = v;
      utt.pitch = profile.pitch;
      utt.rate = profile.rate;
      const master = soundEngine.settings.masterEnabled ? soundEngine.settings.masterVolume : 0.75;
      utt.volume = Math.max(0.0, Math.min(1.0, master * this.settings.voiceVolume));

      let finished = false;
      const done = () => {
        if (finished) return;
        finished = true;
        this._playCommsCue(profile, item.isEmergency, true);
        this.speaking = false;
        this.currentPriority = 0;
        this._restoreAmbientDuck();
        setTimeout(() => this._processNext(), 140);
      };

      utt.onend = done;
      utt.onerror = done;
      // Safety timeout in case a browser speech engine hangs without firing onend
      setTimeout(done, 7500);

      window.speechSynthesis.speak(utt);
    } catch (_) {
      this.speaking = false;
      this.currentPriority = 0;
      this._restoreAmbientDuck();
    }
  }

  async testVoice(profileId = null) {
    await soundEngine.unlockAudio();
    const pid = profileId || this.settings.voiceProfile;
    const prev = this.settings.voiceProfile;
    this.settings.voiceProfile = pid;
    const label = (VOICE_PROFILES[pid] || VOICE_PROFILES.command_ai).label;
    const ok = this.announce(
      `${label} online. SmartWarehouse autonomous fleet telemetry nominal.`,
      { category: 'system', priority: 2, force: true }
    );
    this.settings.voiceProfile = prev;
    return ok;
  }

  async testEmergency(profileId = null) {
    await soundEngine.unlockAudio();
    const pid = (!profileId || profileId === 'match_selected') ? this.settings.voiceProfile : profileId;
    const prev = this.settings.emergencyVoiceProfile;
    this.settings.emergencyVoiceProfile = pid;
    const ok = this.announce(
      'Warning. Emergency stop activated. All affected autonomous units are stopping. Please stand by.',
      { category: 'emergency', priority: 3, force: true }
    );
    this.settings.emergencyVoiceProfile = prev;
    return ok;
  }

  getStatus() {
    return {
      supported: this.supported,
      voiceCount: this.voices.length,
      speaking: this.speaking,
      queueLength: this.queue.length,
      voiceEnabled: this.settings.voiceEnabled,
      voiceProfile: this.settings.voiceProfile,
      emergencyVoiceProfile: this.settings.emergencyVoiceProfile,
    };
  }
}

export const voiceEngine = new VoiceEngine();
export default voiceEngine;
