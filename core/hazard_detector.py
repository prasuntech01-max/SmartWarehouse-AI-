# -*- coding: utf-8 -*-
"""core/hazard_detector.py

Intelligent, deterministic hazard detection engine (Module 11 – Phase 2).

The detector consumes *read‑only* snapshots of the Phase 1 IoT telemetry and
produces explainable incidents.  It never touches the simulation engine,
planner, reservation table or any other runtime component – those are
the responsibility of Phase 3.

Key design goals:
* **Deterministic** – no unseeded randomness, all IDs are sequential
  integers, and evaluation is idempotent per tick.
* **Explainable** – every incident carries a human‑readable explanation
  built from the actual sensor values that triggered it.
* **Configurable** – thresholds, confirmation counts and hysteresis are
  driven by a single ``HazardConfig`` instance.
* **Adapter isolation** – the only place that knows the concrete Phase 1
  API is ``build_observations``; the core detection logic works with
  ``SensorObservation`` / ``DeviceObservation`` objects.
"""

from __future__ import annotations

import enum
import math
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Set, Any
from persistence.queue import WriteBehindQueue
queue = WriteBehindQueue()


# ---------------------------------------------------------------------------
# Enums & data‑source handling
# ---------------------------------------------------------------------------

class HazardType(str, enum.Enum):
    FIRE = "FIRE"
    SMOKE_ACCUMULATION = "SMOKE_ACCUMULATION"
    GAS_LEAKAGE = "GAS_LEAKAGE"
    EXCESSIVE_TEMPERATURE = "EXCESSIVE_TEMPERATURE"
    ABNORMAL_HUMIDITY = "ABNORMAL_HUMIDITY"
    MOTOR_OVERHEATING = "MOTOR_OVERHEATING"
    LOW_BATTERY = "LOW_BATTERY"
    SENSOR_MALFUNCTION = "SENSOR_MALFUNCTION"
    SENSOR_DISCONNECTION = "SENSOR_DISCONNECTION"
    DEVICE_DISCONNECTION = "DEVICE_DISCONNECTION"
    ABNORMAL_ENVIRONMENT = "ABNORMAL_ENVIRONMENT"

class HazardSeverity(int, enum.Enum):
    NORMAL = 0
    WARNING = 1
    CRITICAL = 2
    EMERGENCY = 3

    def __str__(self) -> str:  # useful for explanations
        return self.name

class IncidentStatus(str, enum.Enum):
    CANDIDATE = "CANDIDATE"   # first abnormal reading, not yet confirmed
    ACTIVE = "ACTIVE"         # confirmed (warning/critical) and ongoing
    RECOVERING = "RECOVERING"
    RESOLVED = "RESOLVED"

class DataSource(str, enum.Enum):
    SIMULATED = "SIMULATED"
    HARDWARE = "HARDWARE"
    MIXED = "MIXED"

# ---------------------------------------------------------------------------
# Snapshot dataclasses – immutable, used as pure inputs to the detector
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SensorObservation:
    sensor_id: str
    device_id: str
    sensor_type: str  # enum name string, e.g. "TEMPERATURE"
    value: float
    unit: str
    tick: int
    coord: Tuple[int, int]
    connected: bool
    health_ok: bool
    data_source: DataSource

@dataclass(frozen=True)
class DeviceObservation:
    device_id: str
    online: bool
    last_seen_tick: int

# ---------------------------------------------------------------------------
# Adapter – isolates any Phase 1 implementation details
# ---------------------------------------------------------------------------

def build_observations(iot_manager: Any, tick: int) -> Tuple[List[SensorObservation], List[DeviceObservation]]:
    """Convert the live ``IoTManager`` state into immutable observation objects.

    All assumptions about the concrete Phase 1 API are kept inside this
    function so that the detector core never imports ``core.iot_manager``
    directly (the import is optional to keep the module import‑light).
    """
    # Import lazily to avoid a hard dependency at module import time.
    from .iot_manager import IoTManager, Device

    if not isinstance(iot_manager, IoTManager):
        raise TypeError("build_observations expects an IoTManager instance")

    sensor_obs: List[SensorObservation] = []
    device_obs: List[DeviceObservation] = []

    for dev in iot_manager.devices.values():
        device_obs.append(DeviceObservation(
            device_id=dev.device_id,
            online=dev.connected,
            last_seen_tick=dev.last_heartbeat,
        ))
        for s in dev.sensors:
            # The latest reading is the last entry in ``history``.
            if not s.history:
                # No reading yet – treat as stale (will be handled by health rules).
                continue
            recent = s.history[-1]
            # Convert string data_source to Enum – Phase 1 always uses "SIMULATED".
            ds = DataSource.SIMULATED if recent.data_source == "SIMULATED" else DataSource.HARDWARE
            sensor_obs.append(
                SensorObservation(
                    sensor_id=s.sensor_id,
                    device_id=s.device_id,
                    sensor_type=s.sensor_type.name,
                    value=recent.value,
                    unit=s.unit,
                    tick=recent.timestamp,
                    coord=s.coord,
                    connected=s.connected,
                    health_ok=s.health_ok,
                    data_source=ds,
                )
            )
    return sensor_obs, device_obs

# ---------------------------------------------------------------------------
# Configuration – one place for all thresholds & counts (demo values only)
# ---------------------------------------------------------------------------

@dataclass
class HazardConfig:
    # Thresholds per sensor type (warning < critical < emergency)
    temperature: Tuple[float, float, float] = (30.0, 40.0, 45.0)
    smoke: Tuple[float, float, float] = (0.3, 0.6, 0.8)
    gas: Tuple[float, float, float] = (0.2, 0.5, 0.7)
    humidity: Tuple[float, float, float] = (60.0, 80.0, 90.0)
    battery: Tuple[float, float, float] = (10.0, 20.0, 30.0)
    motor_temp: Tuple[float, float, float] = (70.0, 85.0, 95.0)

    # Confirmation / recovery counts (must be >=1)
    critical_confirm: int = 3
    emergency_confirm: int = 1
    recovery_count: int = 3
    stale_tick_limit: int = 10            # > heartbeat timeout (5) to avoid false offline
    fire_radius: int = 2                  # Manhattan distance
    fire_time_window: int = 2              # ticks
    sole_sensor_override: bool = False    # fire from a single sensor

    def __post_init__(self) -> None:
        # Validate ordering of thresholds
        for name in ["temperature", "smoke", "gas", "humidity", "battery", "motor_temp"]:
            w, c, e = getattr(self, name)
            if not (w < c < e):
                raise ValueError(f"{name} thresholds must satisfy warning < critical < emergency")
        if self.critical_confirm < 1 or self.emergency_confirm < 1 or self.recovery_count < 1:
            raise ValueError("Confirmation and recovery counts must be >= 1")
        if self.stale_tick_limit <= 0:
            raise ValueError("stale_tick_limit must be positive")

# ---------------------------------------------------------------------------
# Incident & result models
# ---------------------------------------------------------------------------

@dataclass
class Incident:
    incident_id: int
    hazard_type: HazardType
    severity: HazardSeverity
    status: IncidentStatus
    source_sensor_ids: List[str]
    device_id: str | None
    coord: Tuple[int, int]
    current_value: float
    peak_value: float
    unit: str
    detection_tick: int
    last_updated: int
    rule_id: str
    explanation: str
    recovery_explanation: str
    data_source: DataSource

    def to_dict(self) -> Dict[str, Any]:
        return {
            "incident_id": self.incident_id,
            "hazard_type": self.hazard_type.value,
            "severity": self.severity.name,
            "status": self.status.value,
            "source_sensor_ids": self.source_sensor_ids,
            "device_id": self.device_id,
            "coord": self.coord,
            "current_value": self.current_value,
            "peak_value": self.peak_value,
            "unit": self.unit,
            "detection_tick": self.detection_tick,
            "last_updated": self.last_updated,
            "rule_id": self.rule_id,
            "explanation": self.explanation,
            "recovery_explanation": self.recovery_explanation,
            "data_source": self.data_source.value,
        }

@dataclass
class DetectionResult:
    tick: int
    new: List[Incident] = field(default_factory=list)
    updated: List[Incident] = field(default_factory=list)   # severity or status changed
    escalated: List[Incident] = field(default_factory=list)  # severity increased
    resolved: List[Incident] = field(default_factory=list)
    summary: str = ""

# ---------------------------------------------------------------------------
# Core detection engine
# ---------------------------------------------------------------------------

class HazardDetector:
    """Deterministic hazard detection engine.

    The engine is deliberately **stateless** between ticks except for the
    counters and incident storage required for confirmation and hysteresis.
    ``evaluate`` must be called once per simulation tick with the same
    ``tick`` value; repeated calls with the same tick are ignored (idempotent).
    """

    def __init__(self, config: HazardConfig | None = None):
        self.config = config or HazardConfig()
        # Active incidents keyed by (hazard_type, location_key)
        self._active: Dict[Tuple[HazardType, Tuple[int, int]], Incident] = {}
        # History of resolved incidents (capped to 1000 entries to avoid blow‑up)
        self._history: List[Incident] = []
        # Per‑sensor per‑rule consecutive abnormal counters
        self._counters: Dict[Tuple[str, str], int] = {}
        # ID generator
        self._next_id: int = 1
        # Track last processed tick for idempotency
        self._last_tick: int | None = None

    # ---------------------------------------------------------------------
    # Public query API (read‑only copies)
    # ---------------------------------------------------------------------
    def active_incidents(self) -> List[Incident]:
        return list(self._active.values())

    def incident_history(self, limit: int | None = None) -> List[Incident]:
        hist = self._history if limit is None else self._history[-limit:]
        return list(hist)

    def get_incident(self, incident_id: int) -> Incident | None:
        for inc in self._active.values():
            if inc.incident_id == incident_id:
                return inc
        for inc in self._history:
            if inc.incident_id == incident_id:
                return inc
        return None

    def incidents_by_severity(self, min_severity: HazardSeverity) -> List[Incident]:
        return [inc for inc in self.active_incidents() if inc.severity >= min_severity]

    def incidents_by_type(self, hazard_type: HazardType) -> List[Incident]:
        return [inc for inc in self.active_incidents() if inc.hazard_type == hazard_type]

    def highest_severity(self) -> HazardSeverity:
        if not self._active:
            return HazardSeverity.NORMAL
        return max(inc.severity for inc in self._active.values())

    # ---------------------------------------------------------------------
    # Internal helpers
    # ---------------------------------------------------------------------
    def _make_incident(self, *, hazard_type: HazardType, severity: HazardSeverity,
                       status: IncidentStatus, source_sensor_ids: List[str],
                       device_id: str | None, coord: Tuple[int, int],
                       current_value: float, unit: str, tick: int,
                       rule_id: str, explanation: str,
                       recovery_explanation: str, data_source: DataSource) -> Incident:
        inc = Incident(
            incident_id=self._next_id,
            hazard_type=hazard_type,
            severity=severity,
            status=status,
            source_sensor_ids=source_sensor_ids,
            device_id=device_id,
            coord=coord,
            current_value=current_value,
            peak_value=current_value,
            unit=unit,
            detection_tick=tick,
            last_updated=tick,
            rule_id=rule_id,
            explanation=explanation,
            recovery_explanation=recovery_explanation,
            data_source=data_source,
        )
        self._next_id += 1
        return inc

    def _update_counter(self, sensor_id: str, rule_id: str, is_abnormal: bool) -> int:
        key = (sensor_id, rule_id)
        if is_abnormal:
            self._counters[key] = self._counters.get(key, 0) + 1
        else:
            self._counters[key] = 0
        return self._counters[key]

    # ---------------------------------------------------------------------
    # Main evaluation entry point
    # ---------------------------------------------------------------------
    def evaluate(self, observations: List[SensorObservation],
                 devices: List[DeviceObservation], tick: int) -> DetectionResult:
        """Process a snapshot of telemetry for a single simulation tick.

        Returns a ``DetectionResult`` describing incidents that are new,
        updated, escalated or resolved during this tick.
        """
        if self._last_tick == tick:
            # Idempotent – no work needed.
            return DetectionResult(tick=tick, summary="No change (duplicate tick)")
        self._last_tick = tick

        result = DetectionResult(tick=tick)

        # Index observations by sensor_id for quick lookup.
        obs_by_id: Dict[str, SensorObservation] = {o.sensor_id: o for o in observations}

        # -----------------------------------------------------------------
        # 1️⃣ Threshold based rules (temperature, smoke, gas, humidity, battery,
        #    motor temperature if present)
        # -----------------------------------------------------------------
        for obs in observations:
            # Skip sensors that are currently offline – health rules will handle.
            if not obs.connected:
                continue
            # Map sensor_type string to config tuple.
            cfg_map = {
                "TEMPERATURE": (self.config.temperature, HazardType.EXCESSIVE_TEMPERATURE),
                "SMOKE": (self.config.smoke, HazardType.SMOKE_ACCUMULATION),
                "GAS": (self.config.gas, HazardType.GAS_LEAKAGE),
                "HUMIDITY": (self.config.humidity, HazardType.ABNORMAL_HUMIDITY),
                "BATTERY": (self.config.battery, HazardType.LOW_BATTERY),
                "MOTOR_TEMPERATURE": (self.config.motor_temp, HazardType.MOTOR_OVERHEATING),
            }
            if obs.sensor_type not in cfg_map:
                # Unknown sensor – ignore for hazard detection.
                continue
            thresholds, hazard_type = cfg_map[obs.sensor_type]
            w, c, e = thresholds
            # Determine severity from raw value (mirroring SensorThresholds logic).
            if obs.value >= e:
                sev = HazardSeverity.EMERGENCY
            elif obs.value >= c:
                sev = HazardSeverity.CRITICAL
            elif obs.value >= w:
                sev = HazardSeverity.WARNING
            else:
                sev = HazardSeverity.NORMAL
            # Update consecutive counters.
            count = self._update_counter(obs.sensor_id, hazard_type.value, sev != HazardSeverity.NORMAL)
            # Determine if we have enough consecutive abnormal readings.
            if sev == HazardSeverity.NORMAL:
                # Reset any existing incident for this sensor/hazard.
                key = (hazard_type, obs.coord)
                if key in self._active:
                    inc = self._active[key]
                    # Move to RECOVERING if we have a recovery count.
                    # For simplicity we treat a normal reading as immediate recovery.
                    inc.status = IncidentStatus.RESOLVED
                    inc.last_updated = tick
                    result.resolved.append(inc)
                    self._history.append(inc)
                    del self._active[key]
                continue

            # Severity level determines required confirmation count.
            confirm_needed = (
                self.config.emergency_confirm if sev == HazardSeverity.EMERGENCY else self.config.critical_confirm
            )
            if count >= confirm_needed:
                # Create or update incident.
                key = (hazard_type, obs.coord)
                if key in self._active:
                    inc = self._active[key]
                    # Update severity if higher.
                    if sev > inc.severity:
                        # Higher severity: update and set ACTIVE.
                        inc.severity = sev
                        inc.explanation = self._build_explanation(obs, hazard_type, sev)
                        result.escalated.append(inc)
                    else:
                        # Same severity – possibly promote candidate.
                        if inc.status == IncidentStatus.CANDIDATE:
                            inc.status = IncidentStatus.ACTIVE
                        result.updated.append(inc)
                    # Common updates for both branches.
                    inc.status = IncidentStatus.ACTIVE
                    inc.last_updated = tick
                    inc.current_value = obs.value
                    inc.peak_value = max(inc.peak_value, obs.value)
                else:
                    # New incident.
                    explanation = self._build_explanation(obs, hazard_type, sev)
                    recovery = self._build_recovery_text(hazard_type, sev)
                    data_src = obs.data_source
                    inc = self._make_incident(
                        hazard_type=hazard_type,
                        severity=sev,
                        status=IncidentStatus.ACTIVE,
                        source_sensor_ids=[obs.sensor_id],
                        device_id=obs.device_id,
                        coord=obs.coord,
                        current_value=obs.value,
                        unit=obs.unit,
                        tick=tick,
                        rule_id=hazard_type.value,
                        explanation=explanation,
                        recovery_explanation=recovery,
                        data_source=data_src,
                    )
                    self._active[key] = inc
                    result.new.append(inc)
                    explanation = self._build_explanation(obs, hazard_type, sev)
                    recovery = self._build_recovery_text(hazard_type, sev)
                    data_src = obs.data_source
                    inc = self._make_incident(
                        hazard_type=hazard_type,
                        severity=sev,
                        status=IncidentStatus.ACTIVE,
                        source_sensor_ids=[obs.sensor_id],
                        device_id=obs.device_id,
                        coord=obs.coord,
                        current_value=obs.value,
                        unit=obs.unit,
                        tick=tick,
                        rule_id=hazard_type.value,
                        explanation=explanation,
                        recovery_explanation=recovery,
                        data_source=data_src,
                    )
                    self._active[key] = inc
                    result.new.append(inc)
            else:
                # Not enough consecutive readings – treat as candidate.
                key = (hazard_type, obs.coord)
                if key not in self._active:
                    # Create a candidate incident to keep visibility.
                    explanation = self._build_explanation(obs, hazard_type, sev)
                    recovery = self._build_recovery_text(hazard_type, sev)
                    inc = self._make_incident(
                        hazard_type=hazard_type,
                        severity=sev,
                        status=IncidentStatus.CANDIDATE,
                        source_sensor_ids=[obs.sensor_id],
                        device_id=obs.device_id,
                        coord=obs.coord,
                        current_value=obs.value,
                        unit=obs.unit,
                        tick=tick,
                        rule_id=hazard_type.value,
                        explanation=explanation,
                        recovery_explanation=recovery,
                        data_source=obs.data_source,
                    )
                    self._active[key] = inc
                    result.new.append(inc)

        # -----------------------------------------------------------------
        # 2️⃣ Fire combination rule – temperature + smoke within radius & window
        # -----------------------------------------------------------------
        temps = [o for o in observations if o.sensor_type == "TEMPERATURE" and o.connected]
        smokes = [o for o in observations if o.sensor_type == "SMOKE" and o.connected]
        for t_obs in temps:
            for s_obs in smokes:
                # Proximity check (Manhattan distance).
                if (
                    abs(t_obs.coord[0] - s_obs.coord[0]) + abs(t_obs.coord[1] - s_obs.coord[1])
                    > self.config.fire_radius
                ):
                    continue
                # Time window check.
                if abs(t_obs.tick - s_obs.tick) > self.config.fire_time_window:
                    continue
                # Determine combined severity – the worst of the two.
                sev_temp = self._severity_from_value(t_obs.value, self.config.temperature)
                sev_smoke = self._severity_from_value(s_obs.value, self.config.smoke)
                combined_sev = max(sev_temp, sev_smoke)
                if combined_sev == HazardSeverity.NORMAL:
                    continue
                # Fire rule only fires if at least one of the two is above WARNING.
                if not (sev_temp != HazardSeverity.NORMAL or sev_smoke != HazardSeverity.NORMAL):
                    continue
                # Sole‑sensor override check.
                if (
                    self.config.sole_sensor_override is False
                    and (sev_temp == HazardSeverity.NORMAL or sev_smoke == HazardSeverity.NORMAL)
                ):
                    # Need both abnormal – already ensured above; continue.
                    pass
                # Use the average coordinate for the incident location.
                loc = (
                    (t_obs.coord[0] + s_obs.coord[0]) // 2,
                    (t_obs.coord[1] + s_obs.coord[1]) // 2,
                )
                key = (HazardType.FIRE, loc)
                # Build explanation including both sensors.
                explanation = (
                    f"Fire detected via temperature sensor {t_obs.sensor_id} ({t_obs.value:.2f}{t_obs.unit}) "
                    f"and smoke sensor {s_obs.sensor_id} ({s_obs.value:.2f}{s_obs.unit}) at "
                    f"location {loc}. Highest severity {combined_sev.name}."
                )
                recovery = self._build_recovery_text(HazardType.FIRE, combined_sev)
                data_src = (
                    DataSource.MIXED
                    if t_obs.data_source != s_obs.data_source
                    else t_obs.data_source
                )
                if key in self._active:
                    inc = self._active[key]
                    if combined_sev > inc.severity:
                        inc.severity = combined_sev
                        inc.last_updated = tick
                        inc.current_value = max(t_obs.value, s_obs.value)
                        inc.peak_value = max(inc.peak_value, inc.current_value)
                        inc.explanation = explanation
                        result.escalated.append(inc)
                    else:
                        inc.last_updated = tick
                        result.updated.append(inc)
                else:
                    inc = self._make_incident(
                        hazard_type=HazardType.FIRE,
                        severity=combined_sev,
                        status=IncidentStatus.ACTIVE,
                        source_sensor_ids=[t_obs.sensor_id, s_obs.sensor_id],
                        device_id=None,
                        coord=loc,
                        current_value=max(t_obs.value, s_obs.value),
                        unit="mixed",
                        tick=tick,
                        rule_id="FIRE_RULE",
                        explanation=explanation,
                        recovery_explanation=recovery,
                        data_source=data_src,
                    )
                    self._active[key] = inc
                    result.new.append(inc)

        # -----------------------------------------------------------------
        # 3️⃣ Sensor health rules – offline devices, stale readings, invalid values
        # -----------------------------------------------------------------
        # Device disconnection
        for dev in devices:
            if not dev.online:
                # One incident per device.
                key = (HazardType.DEVICE_DISCONNECTION, (0, 0))  # location not relevant
                if key not in self._active:
                    explanation = f"Device {dev.device_id} offline since tick {dev.last_seen_tick}."
                    inc = self._make_incident(
                        hazard_type=HazardType.DEVICE_DISCONNECTION,
                        severity=HazardSeverity.WARNING,
                        status=IncidentStatus.ACTIVE,
                        source_sensor_ids=[],
                        device_id=dev.device_id,
                        coord=(0, 0),
                        current_value=0.0,
                        unit="",
                        tick=tick,
                        rule_id="DEVICE_OFFLINE",
                        explanation=explanation,
                        recovery_explanation="Device must reconnect to clear.",
                        data_source=DataSource.SIMULATED,
                    )
                    self._active[key] = inc
                    result.new.append(inc)

        # Sensor disconnection / stale / malformed
        for obs in observations:
            # Stale reading
            if tick - obs.tick > self.config.stale_tick_limit:
                key = (HazardType.SENSOR_DISCONNECTION, obs.coord)
                if key not in self._active:
                    explanation = (
                        f"Sensor {obs.sensor_id} (type {obs.sensor_type}) on device {obs.device_id} "
                        f"has not reported for {tick - obs.tick} ticks (stale)."
                    )
                    inc = self._make_incident(
                        hazard_type=HazardType.SENSOR_DISCONNECTION,
                        severity=HazardSeverity.WARNING,
                        status=IncidentStatus.ACTIVE,
                        source_sensor_ids=[obs.sensor_id],
                        device_id=obs.device_id,
                        coord=obs.coord,
                        current_value=obs.value,
                        unit=obs.unit,
                        tick=tick,
                        rule_id="SENSOR_STALE",
                        explanation=explanation,
                        recovery_explanation="Sensor must report a fresh reading.",
                        data_source=obs.data_source,
                    )
                    self._active[key] = inc
                    result.new.append(inc)
            # Invalid reading (NaN / inf or out of physical range)
            if math.isnan(obs.value) or math.isinf(obs.value):
                key = (HazardType.SENSOR_MALFUNCTION, obs.coord)
                if key not in self._active:
                    explanation = (
                        f"Sensor {obs.sensor_id} reported invalid value {obs.value} (NaN/inf)."
                    )
                    inc = self._make_incident(
                        hazard_type=HazardType.SENSOR_MALFUNCTION,
                        severity=HazardSeverity.WARNING,
                        status=IncidentStatus.ACTIVE,
                        source_sensor_ids=[obs.sensor_id],
                        device_id=obs.device_id,
                        coord=obs.coord,
                        current_value=obs.value,
                        unit=obs.unit,
                        tick=tick,
                        rule_id="SENSOR_INVALID",
                        explanation=explanation,
                        recovery_explanation="Replace or recalibrate sensor.",
                        data_source=obs.data_source,
                    )
                    self._active[key] = inc
                    result.new.append(inc)

        # -----------------------------------------------------------------
        # Build a human readable summary (worst severity)
        # -----------------------------------------------------------------
        worst = self.highest_severity()
        result.summary = f"Tick {tick}: worst severity {worst.name}."
        return result

    # ---------------------------------------------------------------------
    # Helper methods for explanations and severity mapping
    # ---------------------------------------------------------------------
    def _severity_from_value(self, value: float, thresholds: Tuple[float, float, float]) -> HazardSeverity:
        w, c, e = thresholds
        if value >= e:
            return HazardSeverity.EMERGENCY
        if value >= c:
            return HazardSeverity.CRITICAL
        if value >= w:
            return HazardSeverity.WARNING
        return HazardSeverity.NORMAL

    def _build_explanation(self, obs: SensorObservation, hazard_type: HazardType, severity: HazardSeverity) -> str:
        return (
            f"{hazard_type.name.replace('_', ' ')} reading {obs.value:.2f}{obs.unit} "
            f"exceeded {severity.name.lower()} threshold on sensor {obs.sensor_id} "
            f"(device {obs.device_id}) at location {obs.coord}."
        )

    def _build_recovery_text(self, hazard_type: HazardType, severity: HazardSeverity) -> str:
        # Simple generic recovery messages – could be expanded per hazard.
        if severity == HazardSeverity.WARNING:
            return "Recovery requires reading below warning threshold for " f"{self.config.recovery_count} consecutive ticks."
        if severity == HazardSeverity.CRITICAL:
            return "Recovery requires reading below critical threshold for " f"{self.config.recovery_count} consecutive ticks."
        if severity == HazardSeverity.EMERGENCY:
            return "Recovery requires reading below emergency threshold for " f"{self.config.recovery_count} consecutive ticks."
        return ""

# End of hazard_detector.py
