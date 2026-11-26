# -*- coding: utf-8 -*-
"""core/sensor.py

Definition of simulated IoT sensor objects used by Module 11.

The implementation is deliberately lightweight and deterministic – all
random‑based values are driven by a `random.Random` instance supplied by
`IoTManager`.  This makes unit testing reproducible and keeps the rest of
the codebase free from hidden nondeterminism.

Only simulation‑mode data is produced; a field ``data_source`` is set to
``"SIMULATED"`` for every reading.  When a real MQTT transport is added in
future the same dataclass can be reused – the source string will then be
``"HARDWARE"``.
"""

from __future__ import annotations

import enum
import random
from dataclasses import dataclass, field
from typing import Any, Callable, List, Tuple


class SensorType(str, enum.Enum):
    """Enumerates the supported sensor categories.

    The values are lower‑case strings to make JSON‑serialisation easier.
    """

    ULTRASONIC = "ultrasonic"  # distance in metres (0‑5 m)
    INFRARED = "infrared"      # bool obstacle detection
    TEMPERATURE = "temperature"  # °C
    SMOKE = "smoke"            # 0‑1 (fractional concentration)
    GAS = "gas"                # 0‑1 (fractional concentration)
    HUMIDITY = "humidity"      # % relative humidity (0‑100)
    BATTERY = "battery"        # % remaining charge
    MOTOR_TEMPERATURE = "motor_temperature"  # °C
    MOVEMENT = "movement"      # enum: stationary, moving, stopped

    @property
    def unit(self) -> str:
        """Human‑readable unit for the sensor type."""
        return {
            self.ULTRASONIC: "m",
            self.INFRARED: "bool",
            self.TEMPERATURE: "°C",
            self.SMOKE: "ratio",
            self.GAS: "ratio",
            self.HUMIDITY: "%",
            self.BATTERY: "%",
            self.MOTOR_TEMPERATURE: "°C",
            self.MOVEMENT: "state",
        }[self]


@dataclass
class SensorThresholds:
    """Thresholds that trigger warning / critical / emergency levels.

    All values are optional – a ``None`` entry means the level is not
    applicable for that sensor type.
    """

    warning: float | None = None
    critical: float | None = None
    emergency: float | None = None

    def evaluate(self, value: float) -> str:
        """Return a severity label based on the supplied ``value``.

        Labels are ``"NORMAL"``, ``"WARNING"``, ``"CRITICAL"`` or
        ``"EMERGENCY"``.
        """
        if self.emergency is not None and value >= self.emergency:
            return "EMERGENCY"
        if self.critical is not None and value >= self.critical:
            return "CRITICAL"
        if self.warning is not None and value >= self.warning:
            return "WARNING"
        return "NORMAL"


@dataclass
class SensorReading:
    """A single telemetry sample from a sensor.

    ``timestamp`` is the simulation tick (int).  ``value`` holds the raw
    numeric reading; for boolean‑type sensors the value is ``0.0`` or
    ``1.0``.
    """

    timestamp: int
    value: float
    severity: str = "NORMAL"
    data_source: str = "SIMULATED"  # or "HARDWARE"


@dataclass
class Sensor:
    """Dataclass representing a simulated IoT sensor.

    The ``update`` method generates a new reading using the provided
    ``rng``.  The generation logic is deliberately simple – it mirrors the
    behaviour of the original project’s deterministic demo and can be
    customised later without breaking the public API.
    """

    sensor_id: str
    sensor_type: SensorType
    device_id: str  # owning ESP32 identifier
    coord: Tuple[int, int]  # grid location (x, y)
    unit: str = field(init=False)
    thresholds: SensorThresholds = field(default_factory=SensorThresholds)
    history: List[SensorReading] = field(default_factory=list)
    connected: bool = True
    health_ok: bool = True
    # Function that, given (rng, step, simulator), returns a raw float value
    _generator: Callable[[random.Random, int, Any], float] = field(default=lambda rng, step, sim: 0.0, repr=False)

    def __post_init__(self) -> None:
        self.unit = self.sensor_type.unit

    def generate_reading(self, rng: random.Random, step: int, simulator: Any) -> SensorReading:
        """Create a new reading for the current simulation ``step``.

        ``simulator`` is the ``WarehouseSimulator`` instance – sensor logic
        can inspect robot positions or other world state for more realistic
        values.  The default generators are simple deterministic functions
        defined in ``_default_generators``.
        """
        if not self.connected:
            # Disconnected sensors produce a reading with severity ``EMERGENCY``
            value = 0.0
            severity = "EMERGENCY"
        else:
            raw = self._generator(rng, step, simulator)
            severity = self.thresholds.evaluate(raw)
            value = raw
        reading = SensorReading(timestamp=step, value=value, severity=severity)
        self.history.append(reading)
        # Keep a bounded history (last 100 samples) to avoid unbounded memory
        if len(self.history) > 100:
            self.history.pop(0)
        return reading

    # ---------------------------------------------------------------------
    # Helper: a registry of simple deterministic generators per sensor type
    # ---------------------------------------------------------------------
    @staticmethod
    def _default_generators() -> dict[SensorType, Callable[[random.Random, int, Any], float]]:
        def ultrasonic(rng: random.Random, step: int, sim: Any) -> float:
            # Return distance to the nearest robot (0‑5 m) – use rng for noise
            # If no robot nearby, default to 5.0
            min_dist = 5.0
            for r in sim.robots.values():
                dx = r.pos[0] - sim.grid.width // 2
                dy = r.pos[1] - sim.grid.height // 2
                # Euclidean distance scaled to metres (grid cell ≈ 1 m)
                dist = ((dx ** 2 + dy ** 2) ** 0.5)
                if dist < min_dist:
                    min_dist = dist
            # Add a small deterministic jitter
            return max(0.0, min(5.0, min_dist + rng.uniform(-0.1, 0.1)))

        def infrared(rng: random.Random, step: int, sim: Any) -> float:
            # Boolean obstacle detection – true if any robot is exactly on the
            # sensor cell, else false.
            for r in sim.robots.values():
                if r.pos == (sim.grid.width // 2, sim.grid.height // 2):
                    return 1.0
            return 0.0

        def temperature(rng: random.Random, step: int, sim: Any) -> float:
            # Base ambient temperature 22 °C plus slight increase when robots
            # are within 3 cells of the sensor.
            base = 22.0
            for r in sim.robots.values():
                if abs(r.pos[0] - sim.grid.width // 2) <= 3 and abs(r.pos[1] - sim.grid.height // 2) <= 3:
                    base += 0.5
            return base + rng.uniform(-0.2, 0.2)

        def smoke(rng: random.Random, step: int, sim: Any) -> float:
            # Random low background smoke, spikes to 1.0 when a fire hazard is
            # injected via the simulator (future integration).
            return rng.random() * 0.2

        def gas(rng: random.Random, step: int, sim: Any) -> float:
            return rng.random() * 0.1

        def humidity(rng: random.Random, step: int, sim: Any) -> float:
            return 40.0 + rng.random() * 20.0

        def battery(rng: random.Random, step: int, sim: Any) -> float:
            # Use the robot's battery if the sensor is attached to a robot.
            # For simplicity, map ``device_id`` to a robot id if possible.
            try:
                rid = int(simulation_id_to_robot_id(sim, step, device_id=""))
            except Exception:
                rid = None
            if rid and rid in sim.robots:
                return sim.robots[rid].battery
            return rng.uniform(50.0, 100.0)

        def motor_temp(rng: random.Random, step: int, sim: Any) -> float:
            # Simple model: increase with robot usage.
            try:
                rid = int(simulation_id_to_robot_id(sim, step, device_id=""))
            except Exception:
                rid = None
            if rid and rid in sim.robots:
                usage = sim.robots[rid].total_distance
                return 30.0 + usage * 0.05 + rng.uniform(-0.5, 0.5)
            return rng.uniform(25.0, 35.0)

        def movement(rng: random.Random, step: int, sim: Any) -> float:
            # Encode state as 0‑stationary, 1‑moving, 2‑stopped
            # For demo, return 1.0 if any robot is moving.
            for r in sim.robots.values():
                if r.state != "IDLE":
                    return 1.0
            return 0.0

        return {
            SensorType.ULTRASONIC: ultrasonic,
            SensorType.INFRARED: infrared,
            SensorType.TEMPERATURE: temperature,
            SensorType.SMOKE: smoke,
            SensorType.GAS: gas,
            SensorType.HUMIDITY: humidity,
            SensorType.BATTERY: battery,
            SensorType.MOTOR_TEMPERATURE: motor_temp,
            SensorType.MOVEMENT: movement,
        }

    @classmethod
    def create(
        cls,
        sensor_id: str,
        sensor_type: SensorType,
        device_id: str,
        coord: Tuple[int, int],
        thresholds: SensorThresholds | None = None,
    ) -> "Sensor":
        """Factory method that wires the appropriate deterministic generator.

        ``thresholds`` may be omitted; a sensible default is provided for
        each type based on typical operational ranges.
        """
        generators = cls._default_generators()
        gen = generators.get(sensor_type)
        if gen is None:
            raise ValueError(f"No generator defined for sensor type {sensor_type}")
        if thresholds is None:
            # Reasonable defaults – these are *not* safety‑critical, merely
            # useful for demos.
            if sensor_type == SensorType.TEMPERATURE:
                thresholds = SensorThresholds(warning=30.0, critical=40.0, emergency=45.0)
            elif sensor_type == SensorType.SMOKE:
                thresholds = SensorThresholds(warning=0.3, critical=0.6, emergency=0.8)
            elif sensor_type == SensorType.GAS:
                thresholds = SensorThresholds(warning=0.2, critical=0.5, emergency=0.7)
            elif sensor_type == SensorType.BATTERY:
                thresholds = SensorThresholds(warning=30.0, critical=20.0, emergency=10.0)
            else:
                thresholds = SensorThresholds()
        return cls(
            sensor_id=sensor_id,
            sensor_type=sensor_type,
            device_id=device_id,
            coord=coord,
            thresholds=thresholds,
            _generator=gen,
        )

# Helper used by the battery/motor generators – maps a device ID to a robot ID.
# This is a lightweight placeholder; the real implementation will be more
# sophisticated when devices are explicitly linked to robots.
def simulation_id_to_robot_id(sim: Any, step: int, device_id: str) -> int | None:
    """Attempt to resolve a device ID to a robot ID.

    The current project does not store a direct mapping, so we simply return
    ``None``.  The function exists so that the generator signatures stay
    stable when a proper mapping is added later.
    """
    return None
