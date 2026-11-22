# -*- coding: utf-8 -*-
"""core/iot_manager.py

IoT network manager for Module 11.

The manager owns a collection of simulated ESP32 devices.  Each device can
host multiple :class:`core.sensor.Sensor` objects.  The manager is
responsible for:

* deterministic tick‑based generation of sensor readings,
* tracking device connectivity via heart‑beats,
* exposing a simple API that the rest of the system (hazard detector,
  emergency response) can query.

All randomness is driven by a ``random.Random`` instance that is seeded at
construction time – this guarantees repeatable unit‑tests.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from .sensor import Sensor, SensorType, SensorThresholds


@dataclass
class Device:
    """Representation of a simulated ESP32 device.

    ``device_id`` is a unique string.  ``sensors`` holds the list of
    attached :class:`Sensor` objects.  ``connected`` reflects the simulated
    network status – a missing heartbeat for ``heartbeat_timeout`` steps
    flips this flag to ``False``.
    """

    device_id: str
    sensors: List[Sensor] = field(default_factory=list)
    connected: bool = True
    last_heartbeat: int = 0  # simulation step of the most recent ping
    heartbeat_timeout: int = 5  # steps after which a device is considered offline

    def ping(self, step: int) -> None:
        """Record a heartbeat at the given simulation ``step``.

        The UI can call this to simulate a device coming back online.
        """
        self.last_heartbeat = step
        self.connected = True

    def check_connectivity(self, current_step: int) -> None:
        """Mark the device as offline if the last heartbeat is stale.
        """
        if current_step - self.last_heartbeat > self.heartbeat_timeout:
            self.connected = False
        else:
            self.connected = True

    def add_sensor(self, sensor: Sensor) -> None:
        self.sensors.append(sensor)
        # Ensure the sensor's connection flag mirrors the device state.
        sensor.connected = self.connected


class IoTManager:
    """Central manager for all simulated IoT devices and sensors.

    The manager is deliberately lightweight – it does **not** perform any
    network I/O.  An optional MQTT transport can be attached later via the
    ``mqtt_connector`` module.
    """

    def __init__(self, seed: int = 12345) -> None:
        self._rng = random.Random(seed)
        self.devices: Dict[str, Device] = {}
        self._global_step: int = 0

    # ---------------------------------------------------------------------
    # Device registration & lookup
    # ---------------------------------------------------------------------
    def register_device(self, device_id: str, heartbeat_timeout: int = 5) -> Device:
        if device_id in self.devices:
            raise ValueError(f"Device {device_id!r} already registered")
        dev = Device(device_id=device_id, heartbeat_timeout=heartbeat_timeout)
        self.devices[device_id] = dev
        return dev

    def get_device(self, device_id: str) -> Device:
        return self.devices[device_id]

    # ---------------------------------------------------------------------
    # Sensor handling
    # ---------------------------------------------------------------------
    def create_sensor(
        self,
        sensor_id: str,
        sensor_type: SensorType,
        device_id: str,
        coord: Tuple[int, int],
        thresholds: SensorThresholds | None = None,
    ) -> Sensor:
        if device_id not in self.devices:
            raise ValueError(f"Device {device_id!r} not registered")
        sensor = Sensor.create(
            sensor_id=sensor_id,
            sensor_type=sensor_type,
            device_id=device_id,
            coord=coord,
            thresholds=thresholds,
        )
        self.devices[device_id].add_sensor(sensor)
        return sensor

    # ---------------------------------------------------------------------
    # Tick update – called once per simulation step
    # ---------------------------------------------------------------------
    def step_update(self, step: int, simulator: any) -> None:
        """Generate a fresh reading for every registered sensor.

        ``simulator`` is the active ``WarehouseSimulator`` instance – it is
        passed to each sensor's ``generate_reading`` so that the reading can
        depend on the current world state (e.g., robot proximity).
        """
        self._global_step = step
        for dev in self.devices.values():
            dev.check_connectivity(step)
            # Propagate device connectivity flag to its sensors
            for s in dev.sensors:
                s.connected = dev.connected
                s.generate_reading(self._rng, step, simulator)

    # ---------------------------------------------------------------------
    # Convenience accessors for UI / other modules
    # ---------------------------------------------------------------------
    def all_sensors(self) -> List[Sensor]:
        """Return a flattened list of all sensors across devices."""
        return [s for d in self.devices.values() for s in d.sensors]

    def latest_readings(self) -> List[dict]:
        """Return a list of dictionaries summarising the most recent reading
        of each sensor.  This format is convenient for Streamlit tables.
        """
        out = []
        for s in self.all_sensors():
            if s.history:
                recent = s.history[-1]
                out.append(
                    {
                        "sensor_id": s.sensor_id,
                        "type": s.sensor_type.value,
                        "device_id": s.device_id,
                        "coord": s.coord,
                        "value": recent.value,
                        "unit": s.unit,
                        "severity": recent.severity,
                        "timestamp": recent.timestamp,
                        "connected": s.connected,
                    }
                )
        return out
