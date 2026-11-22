# -*- coding: utf-8 -*-
"""core/mqtt_connector.py

Optional MQTT transport for future hardware integration.

The project must run without a broker; therefore the connector lazily
imports ``paho.mqtt.client`` and degrades gracefully when the library is
absent.  All public methods raise a clear ``ImportError`` if the optional
dependency cannot be loaded – this allows the simulation to continue in
pure‑simulated mode.

The interface mirrors a very small subset of the classic Paho client that
is sufficient for the planned future integration:

* ``connect(broker, port)`` – establish a TCP connection.
* ``publish(topic, payload)`` – send a UTF‑8 payload.
* ``subscribe(topic, callback)`` – register a callback for incoming
  messages (the callback receives ``topic`` and ``payload``).

The implementation stores a local ``messages`` list for unit‑testing –
when running without a real broker the ``publish`` method simply records the
sent messages so that tests can assert correct behaviour.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Callable, List, Tuple


@dataclass
class MQTTMessage:
    topic: str
    payload: str
    qos: int = 0
    retain: bool = False


class MQTTConnector:
    """Lightweight wrapper around the optional ``paho.mqtt.client`` library.

    If the library is unavailable, the connector works in *simulation mode*
    – calls are recorded in ``self.messages`` and no network activity occurs.
    """

    def __init__(self) -> None:
        self._client = None
        self.connected: bool = False
        self.messages: List[MQTTMessage] = []
        self._subscriptions: List[Tuple[str, Callable[[str, str], None]]] = []

    # ---------------------------------------------------------------------
    # Lazy import helper
    # ---------------------------------------------------------------------
    def _ensure_client(self) -> None:
        if self._client is not None:
            return
        try:
            import paho.mqtt.client as paho
        except Exception as exc:  # pragma: no cover – library not installed
            raise ImportError(
                "paho-mqtt is not installed; MQTTConnector can be used only "
                "in simulation mode. Install the package to enable real network "
                "communication."
            ) from exc
        client = paho.Client()
        client.on_message = self._on_message  # type: ignore[attr-defined]
        self._client = client

    def _on_message(self, client, userdata, msg):  # pragma: no cover
        payload = msg.payload.decode("utf-8")
        topic = msg.topic
        for sub_topic, callback in self._subscriptions:
            if topic == sub_topic:
                callback(topic, payload)

    # ---------------------------------------------------------------------
    # Public API
    # ---------------------------------------------------------------------
    def connect(self, broker: str = "localhost", port: int = 1883, keepalive: int = 60) -> None:
        """Connect to an MQTT broker.

        When ``paho-mqtt`` is unavailable the method simply marks the
        connector as ``connected`` without performing network I/O – this
        allows the rest of the simulation to proceed.
        """
        try:
            self._ensure_client()
        except ImportError:
            self.connected = True
            self.messages.append(MQTTMessage(topic="$SYS/CONNECT", payload=json.dumps({"broker": broker, "port": port})))
            return
        assert self._client is not None
        self._client.connect(broker, port, keepalive)
        self._client.loop_start()
        self.connected = True

    def publish(self, topic: str, payload: str | dict, qos: int = 0, retain: bool = False) -> None:
        """Publish a message.

        ``payload`` may be a ``dict`` – it will be JSON‑encoded.
        In simulation mode the message is stored in ``self.messages``.
        """
        if isinstance(payload, dict):
            payload_str = json.dumps(payload)
        else:
            payload_str = str(payload)
        if self._client is None:
            self.messages.append(MQTTMessage(topic=topic, payload=payload_str, qos=qos, retain=retain))
            return
        self._client.publish(topic, payload_str, qos=qos, retain=retain)

    def subscribe(self, topic: str, callback: Callable[[str, str], None]) -> None:
        """Subscribe to ``topic`` and register ``callback``.

        In simulation mode the callback is stored and will be invoked when a
        message is manually injected via ``_inject_message`` (used only in
        tests).
        """
        self._subscriptions.append((topic, callback))
        if self._client is not None:
            self._client.subscribe(topic)

    # ---------------------------------------------------------------------
    # Helper for tests – inject a message in simulation mode.
    # ---------------------------------------------------------------------
    def _inject_message(self, topic: str, payload: str) -> None:
        """Directly invoke callbacks with a fabricated message.

        This method is useful for unit tests when the real network stack is
        not present.
        """
        for sub_topic, callback in self._subscriptions:
            if sub_topic == topic:
                callback(topic, payload)
        self.messages.append(MQTTMessage(topic=topic, payload=payload))
