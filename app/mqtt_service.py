"""MQTT bridge — Home Assistant discovery, state publish, command subscribe."""

from __future__ import annotations

import json
import logging
import ssl
import threading
import time
import uuid
from typing import Any, Dict, List, Optional, Set, Tuple

import paho.mqtt.client as mqtt

from .app_settings import load_settings
from .denon_client import DenonSetupClient
from .denon_control import (
    DenonControl,
    SUPPORTED_MODELS,
    parse_entities,
    resolve_command_from_id,
)
from .denon_power import read_main_zone_power
from .mqtt_ha_naming import (
    build_ha_entity_id_map,
    discovery_topic_id,
    slugify,
    unique_id,
)
from .mqtt_settings import (
    cert_path,
    entity_enabled,
    load_mqtt_settings,
    load_published_discovery,
    mqtt_control_layout,
    save_published_discovery,
)
from .protocol_loader import CONTROL_LAYOUT_BOTH, CONTROL_LAYOUT_MORE, normalize_layout, load_telnet_commands

log = logging.getLogger("denon.mqtt")

_HA_COMPONENT = {
    "toggle": "switch",
    "enum": "select",
    "slider": "number",
    "stepper": "number",
    "action": "button",
    "query": "button",
    "raw": "text",
}


class MqttBridge:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._client: Optional[mqtt.Client] = None
        self._settings: Dict[str, Any] = {}
        self._app: Any = None
        self._connected = False
        self._last_error: Optional[str] = None
        self._last_publish_at: Optional[float] = None
        self._last_states: Dict[str, str] = {}
        self._poll_stop = threading.Event()
        self._poll_thread: Optional[threading.Thread] = None
        self._device_id: Optional[str] = None
        self._subscribed = False
        self._control_index: Dict[str, Dict[str, Any]] = {}

    def _device_identifier(self) -> str:
        topic = str(self._settings.get("topic") or "denon_avr")
        return f"denon_avr_manager_{slugify(topic.replace('/', '_'))}"

    def _load_catalog(self) -> Dict[str, Any]:
        app = self._app
        host = getattr(app.state, "default_host", None) if app else None
        if not host:
            return {"sections": [], "controls": []}
        settings = load_settings()
        model = str(settings.get("avr_model") or "AVR-X1200W")
        if model not in SUPPORTED_MODELS:
            model = "AVR-X1200W"
        layout = mqtt_control_layout(self._settings)
        ctrl = DenonControl(DenonSetupClient(host))
        return ctrl.catalog(
            model=model,
            show_zone2=bool(settings.get("show_zone2")),
            show_zone3=bool(settings.get("show_zone3")),
            layout=layout,
        )

    def _refresh_control_index(self) -> None:
        cat = self._load_catalog()
        self._control_index = {
            str(c.get("id")): c for c in (cat.get("controls") or []) if c.get("id")
        }

    def _resolve_mqtt_command(self, control_id: str, value: Any) -> tuple[str, bool]:
        if not self._control_index:
            self._refresh_control_index()
        control = self._control_index.get(control_id)
        if not control:
            raise KeyError(f"unknown control id: {control_id}")
        kind = control.get("kind")
        allow_raw = bool(control.get("allow_raw"))
        if kind == "raw":
            cmd = str(value or "").strip()
            if not cmd:
                raise ValueError("raw command requires a telnet payload")
            return cmd, True
        if kind == "action":
            cmd = str(control.get("command") or "").strip()
            if not cmd:
                raise ValueError(f"action {control_id} has no command")
            return cmd, False
        if kind == "query":
            cmd = str(control.get("query") or control.get("command") or "").strip()
            if not cmd:
                raise ValueError(f"query {control_id} has no query")
            if "?" not in cmd:
                cmd = f"{cmd}?"
            return cmd, True
        return resolve_command_from_id(control_id, value), allow_raw

    def status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "enabled": bool(self._settings.get("enabled")),
                "connected": self._connected,
                "last_error": self._last_error,
                "last_publish_at": self._last_publish_at,
                "host": self._settings.get("host"),
                "topic": self._settings.get("topic"),
                "control_layout": mqtt_control_layout(self._settings),
            }

    def configure_app(self, app: Any) -> None:
        self._app = app

    def restart(self) -> None:
        self.stop()
        settings = load_mqtt_settings()
        self._settings = settings
        if not settings.get("enabled"):
            log.debug("MQTT disabled — skip connect")
            return
        host = str(settings.get("host") or "").strip()
        if not host:
            self._last_error = "MQTT host is not configured"
            log.warning("MQTT enabled but host is empty")
            return
        log.info("MQTT connecting to %s:%s …", host, settings.get("port") or 1883)
        self._start_client(settings)
        self._start_poll_loop()

    def stop(self) -> None:
        self._poll_stop.set()
        if self._poll_thread and self._poll_thread.is_alive():
            self._poll_thread.join(timeout=3)
        self._poll_thread = None
        self._poll_stop.clear()
        with self._lock:
            client = self._client
            if client is not None and self._connected:
                try:
                    self._publish_availability("offline")
                except Exception:
                    pass
            self._client = None
            self._connected = False
            self._subscribed = False
        if client is not None:
            try:
                client.loop_stop()
                client.disconnect()
            except Exception:
                pass

    def refresh_discovery(self) -> None:
        """Re-sync HA discovery without full MQTT reconnect."""
        with self._lock:
            if not self._connected or self._client is None:
                return
            self._refresh_control_index()
            self._sync_discovery()
            try:
                self._refresh_and_publish()
            except Exception as e:
                log.warning("MQTT state refresh after discovery sync failed: %s", e)

    def apply_settings(self, settings: Dict[str, Any]) -> None:
        """Apply saved settings and sync discovery when already connected."""
        with self._lock:
            self._settings = settings
        if self._connected and self._client is not None:
            self.refresh_discovery()
        else:
            self.restart()

    def notify_entities(self, entities: Dict[str, Any]) -> None:
        if not self._settings.get("enabled") or not self._connected:
            return
        try:
            self._publish_entities(entities)
        except Exception as e:
            log.warning("MQTT publish failed: %s", e)

    def _start_poll_loop(self) -> None:
        self._poll_stop.clear()
        self._poll_thread = threading.Thread(
            target=self._poll_worker,
            name="mqtt-poll",
            daemon=True,
        )
        self._poll_thread.start()

    def _poll_worker(self) -> None:
        while not self._poll_stop.is_set():
            settings = load_mqtt_settings()
            interval = max(5, int(settings.get("refresh_sec") or 30))
            if settings.get("enabled") and self._connected:
                try:
                    self._refresh_and_publish()
                except Exception as e:
                    log.warning("MQTT poll refresh failed: %s", e)
            if self._poll_stop.wait(interval):
                break

    def _refresh_and_publish(self) -> None:
        app = self._app
        if app is None:
            return
        host = getattr(app.state, "default_host", None)
        if not host:
            return
        ctrl: Optional[DenonControl] = getattr(app.state, "denon_control", None)
        if ctrl is None:
            http = DenonSetupClient(host)
            ctrl = DenonControl(http)
        power = None
        try:
            power = read_main_zone_power(DenonSetupClient(host))
        except Exception:
            power = None
        model = str(load_settings().get("avr_model") or "AVR-X1200W")
        layout = mqtt_control_layout(self._settings)
        snap_layout = CONTROL_LAYOUT_MORE if layout == CONTROL_LAYOUT_BOTH else layout
        snap = ctrl.status_snapshot(
            refresh=False,
            power=power,
            model=model,
            layout=snap_layout,
        )
        self._publish_entities(snap.get("entities") or {})

    def _start_client(self, settings: Dict[str, Any]) -> None:
        host = str(settings.get("host") or "").strip()
        port = int(settings.get("port") or 1883)
        client_id = f"denon-avr-manager-{uuid.uuid4().hex[:10]}"
        client = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            client_id=client_id,
            protocol=mqtt.MQTTv311,
        )
        user = str(settings.get("username") or "").strip()
        pwd = str(settings.get("password") or "")
        if user:
            client.username_pw_set(user, pwd or None)
        self._apply_tls(client, settings)
        client.on_connect = self._on_connect
        client.on_disconnect = self._on_disconnect
        client.on_message = self._on_message
        with self._lock:
            self._client = client
            self._settings = settings
            self._last_error = None
        try:
            client.connect_async(host, port, keepalive=60)
            client.loop_start()
            log.debug("MQTT connect_async issued for %s:%s", host, port)
        except Exception as e:
            self._last_error = str(e)
            log.warning("MQTT connect failed: %s", e)

    def _apply_tls(self, client: mqtt.Client, settings: Dict[str, Any]) -> None:
        mode = str(settings.get("tls_mode") or "none")
        if mode == "none":
            return
        if mode == "tls_insecure":
            client.tls_set(cert_reqs=ssl.CERT_NONE)
            client.tls_insecure_set(True)
            return
        if mode == "tls_default":
            client.tls_set()
            return
        ca = cert_path(settings.get("ca_cert_file") or "")
        cert = cert_path(settings.get("client_cert_file") or "")
        key = cert_path(settings.get("client_key_file") or "")
        if mode == "tls_ca":
            if ca:
                client.tls_set(ca_certs=str(ca))
            else:
                client.tls_set()
            return
        if mode == "tls_client_cert":
            client.tls_set(
                ca_certs=str(ca) if ca else None,
                certfile=str(cert) if cert else None,
                keyfile=str(key) if key else None,
            )

    def _on_connect(self, client, userdata, flags, reason_code, properties=None) -> None:
        rc = getattr(reason_code, "value", reason_code)
        if rc != 0:
            self._last_error = f"MQTT connect rc={rc}"
            self._connected = False
            log.warning("MQTT on_connect failed rc=%s", rc)
            return
        self._connected = True
        self._last_error = None
        log.info("MQTT connected to %s", self._settings.get("host"))
        self._refresh_control_index()
        self._publish_availability("online")
        self._publish_discovery()
        topic = str(self._settings.get("topic") or "denon_avr")
        client.subscribe(f"{topic}/+/set")
        client.subscribe(f"{topic}/command")
        self._subscribed = True
        threading.Thread(
            target=self._safe_initial_publish,
            name="mqtt-initial-publish",
            daemon=True,
        ).start()

    def _safe_initial_publish(self) -> None:
        try:
            self._refresh_and_publish()
        except Exception as e:
            log.warning("MQTT initial publish failed: %s", e)

    def _on_disconnect(self, client, userdata, flags, reason_code, properties=None) -> None:
        self._connected = False
        rc = getattr(reason_code, "value", reason_code)
        if rc != 0:
            self._last_error = f"MQTT disconnected rc={rc}"

    def _on_message(self, client, userdata, msg) -> None:
        topic = str(msg.topic or "")
        payload_raw = (msg.payload or b"").decode("utf-8", errors="replace").strip()
        base = str(self._settings.get("topic") or "denon_avr")
        if not topic.startswith(f"{base}/"):
            return
        suffix = topic[len(base) + 1 :]
        if suffix == "command":
            return
        if not suffix.endswith("/set"):
            return
        control_id = suffix[: -len("/set")]
        if not control_id:
            return
        if not entity_enabled(self._settings, control_id):
            return
        value: Any = payload_raw
        if self._settings.get("json_style"):
            try:
                parsed = json.loads(payload_raw)
                if isinstance(parsed, dict) and "value" in parsed:
                    value = parsed["value"]
                else:
                    value = parsed
            except json.JSONDecodeError:
                pass
        self._execute_control(control_id, value)

    def _execute_control(self, control_id: str, value: Any) -> None:
        app = self._app
        if app is None:
            return
        host = getattr(app.state, "default_host", None)
        if not host:
            return
        try:
            cmd, allow_raw = self._resolve_mqtt_command(control_id, value)
            ctrl: Optional[DenonControl] = getattr(app.state, "denon_control", None)
            if ctrl is None:
                http = DenonSetupClient(host)
                ctrl = DenonControl(http)
                app.state.denon_control = ctrl
            result = ctrl.send(cmd, allow_raw=allow_raw)
            power = None
            try:
                power = read_main_zone_power(DenonSetupClient(host))
            except Exception:
                power = None
            lines = list(result.get("responses") or []) + ctrl.telnet.cached_lines()
            layout = mqtt_control_layout(self._settings)
            entities = parse_entities(lines, power=power, layout=layout)
            self._publish_entities(entities)
            responses = list(result.get("responses") or [])
            if responses:
                payload = " | ".join(responses)
                client = self._client
                if client is not None and self._connected:
                    topic = self._state_topic(control_id)
                    client.publish(topic, payload, retain=False)
                    self._last_states[control_id] = payload
        except Exception as e:
            log.warning("MQTT command %s=%r failed: %s", control_id, value, e)

    def _device_block(self) -> Dict[str, Any]:
        settings = self._settings
        app = self._app
        avr_model = str(load_settings().get("avr_model") or "AVR-X1200W")
        host = ""
        if app is not None:
            host = str(getattr(app.state, "default_host", "") or "")
        block: Dict[str, Any] = {
            "identifiers": [self._device_identifier()],
            "name": str(settings.get("device_name") or "Denon AVR"),
            "manufacturer": "Denon",
            "model": avr_model,
            "sw_version": "DENON-AVR-MANAGER",
        }
        if host:
            block["configuration_url"] = f"http://{host}/"
        return block

    def _controls_for_publish(self) -> List[Dict[str, Any]]:
        cat = self._load_catalog()
        out: List[Dict[str, Any]] = []
        for c in cat.get("controls") or []:
            cid = str(c.get("id") or "")
            kind = c.get("kind")
            if not cid or kind not in _HA_COMPONENT:
                continue
            src = c.get("source_layout")
            if not entity_enabled(self._settings, cid, source_layout=src):
                continue
            out.append(c)
        return out

    def _discovery_entry(self, control: Dict[str, Any], entity_id_map: Dict[str, str]) -> Optional[Dict[str, str]]:
        built = self._discovery_config(control, entity_id_map)
        if not built:
            return None
        component, cfg = built
        cid = str(control.get("id") or "")
        prefix = str(self._settings.get("discovery_prefix") or "homeassistant")
        discovery_topic = f"{prefix}/{component}/{discovery_topic_id(self._settings, cid)}/config"
        return {
            "discovery_topic": discovery_topic,
            "state_topic": str(cfg.get("state_topic") or ""),
            "control_id": cid,
            "component": component,
            "payload": json.dumps(cfg),
        }

    def _unpublish_discovery_entry(self, entry: Dict[str, str]) -> None:
        client = self._client
        if client is None:
            return
        dtopic = str(entry.get("discovery_topic") or "")
        if dtopic:
            client.publish(dtopic, "", retain=True)
        stopic = str(entry.get("state_topic") or "")
        if stopic:
            client.publish(stopic, "", retain=True)
        cid = str(entry.get("control_id") or "")
        if cid and cid in self._last_states:
            del self._last_states[cid]

    def _sync_discovery(self) -> None:
        if not self._settings.get("ha_discovery"):
            for old in load_published_discovery():
                self._unpublish_discovery_entry(old)
            save_published_discovery([])
            return
        client = self._client
        if client is None:
            return
        entity_id_map = self._entity_id_map()
        new_entries: List[Dict[str, str]] = []
        new_topics: Set[str] = set()
        for control in self._controls_for_publish():
            row = self._discovery_entry(control, entity_id_map)
            if not row:
                continue
            new_entries.append(
                {
                    "discovery_topic": row["discovery_topic"],
                    "state_topic": row["state_topic"],
                    "control_id": row["control_id"],
                }
            )
            new_topics.add(row["discovery_topic"])
            client.publish(row["discovery_topic"], row["payload"], retain=True)

        old_entries = load_published_discovery()
        for old in old_entries:
            if old.get("discovery_topic") not in new_topics:
                self._unpublish_discovery_entry(old)

        save_published_discovery(new_entries)
        log.info(
            "MQTT discovery synced: %d active, %d removed",
            len(new_entries),
            sum(1 for o in old_entries if o.get("discovery_topic") not in new_topics),
        )

    def _object_id(self, control_id: str) -> str:
        """Legacy alias — stable unique_id for MQTT topics."""
        return unique_id(self._settings, control_id)

    def _entity_id_map(self) -> Dict[str, str]:
        controls = self._controls_for_publish()
        items: List[Dict[str, Any]] = []
        for c in controls:
            kind = c.get("kind")
            component = _HA_COMPONENT.get(kind)
            if not component:
                continue
            items.append(
                {
                    "id": c.get("id"),
                    "label": c.get("label"),
                    "ha_component": component,
                }
            )
        return build_ha_entity_id_map(self._settings, items)

    def _state_topic(self, control_id: str) -> str:
        base = str(self._settings.get("topic") or "denon_avr")
        return f"{base}/{control_id}/state"

    def _command_topic(self, control_id: str) -> str:
        base = str(self._settings.get("topic") or "denon_avr")
        return f"{base}/{control_id}/set"

    def _availability_topic(self) -> str:
        base = str(self._settings.get("topic") or "denon_avr")
        return f"{base}/status"

    def _publish_availability(self, state: str) -> None:
        client = self._client
        if client is None:
            return
        topic = self._availability_topic()
        client.publish(topic, state, retain=True)

    def _discovery_config(
        self, control: Dict[str, Any], entity_id_map: Dict[str, str]
    ) -> Optional[Tuple[str, Dict[str, Any]]]:
        cid = str(control.get("id") or "")
        kind = control.get("kind")
        component = _HA_COMPONENT.get(kind)
        if not component:
            return None
        name = str(control.get("label") or cid)
        default_eid = entity_id_map.get(cid)
        cfg: Dict[str, Any] = {
            "name": name,
            "unique_id": self._object_id(cid),
            "state_topic": self._state_topic(cid),
            "command_topic": self._command_topic(cid),
            "availability_topic": self._availability_topic(),
            "payload_available": "online",
            "payload_not_available": "offline",
            "device": self._device_block(),
        }
        if default_eid:
            cfg["default_entity_id"] = default_eid
        if kind == "toggle":
            cfg.update(
                {
                    "payload_on": "ON",
                    "payload_off": "OFF",
                    "state_on": "ON",
                    "state_off": "OFF",
                }
            )
        elif kind == "enum":
            options = [
                str(o.get("label") or o.get("command") or "")
                for o in (control.get("options") or [])
            ]
            options = [o for o in options if o]
            if not options:
                return None
            cfg["options"] = options
        elif kind in {"slider", "stepper"}:
            lo = control.get("min")
            hi = control.get("max")
            if lo is not None:
                cfg["min"] = float(lo)
            if hi is not None:
                cfg["max"] = float(hi)
            cfg["step"] = 1.0
            if control.get("unit"):
                cfg["unit_of_measurement"] = str(control["unit"])
        elif kind == "action":
            cmd = str(control.get("command") or "")
            if cmd:
                cfg["payload_press"] = cmd
        elif kind == "query":
            cmd = str(control.get("query") or control.get("command") or "")
            if cmd and "?" not in cmd:
                cmd = f"{cmd}?"
            if cmd:
                cfg["payload_press"] = cmd
        elif kind == "raw":
            cfg["mode"] = "text"
            cfg["max"] = 64
        return component, cfg

    def _publish_discovery(self) -> None:
        self._sync_discovery()

    def _entity_state_payload(self, control: Dict[str, Any], entity: Dict[str, Any]) -> Optional[str]:
        kind = control.get("kind")
        if self._settings.get("json_style"):
            return json.dumps(entity)
        if kind == "toggle":
            return "ON" if entity.get("on") else "OFF"
        if kind == "enum":
            return str(entity.get("label") or entity.get("display") or "")
        if kind in {"slider", "stepper"}:
            val = entity.get("value")
            if val is None:
                return str(entity.get("display") or "")
            return str(val)
        if kind in {"action", "query", "raw"}:
            return str(entity.get("display") or entity.get("raw") or "")
        return str(entity.get("display") or entity.get("value") or "")

    def _publish_entities(self, entities: Dict[str, Any]) -> None:
        client = self._client
        if client is None or not self._connected:
            return
        controls_by_id = {
            str(c.get("id")): c for c in self._controls_for_publish() if c.get("id")
        }
        changed = False
        for cid, control in controls_by_id.items():
            entity = entities.get(cid)
            if not entity:
                continue
            payload = self._entity_state_payload(control, entity)
            if payload is None:
                continue
            prev = self._last_states.get(cid)
            if prev == payload:
                continue
            topic = self._state_topic(cid)
            client.publish(topic, payload, retain=True)
            self._last_states[cid] = payload
            changed = True
        if changed:
            self._last_publish_at = time.time()

    def build_ha_manual_config(self) -> Dict[str, Any]:
        settings = self._settings or load_mqtt_settings()
        base = str(settings.get("topic") or "denon_avr")
        entity_id_map = self._entity_id_map()
        mqtt_block: Dict[str, List[Dict[str, Any]]] = {}
        for control in self._controls_for_publish():
            built = self._discovery_config(control, entity_id_map)
            if not built:
                continue
            component, cfg = built
            entry: Dict[str, Any] = {
                "name": cfg["name"],
                "state_topic": cfg["state_topic"],
                "command_topic": cfg["command_topic"],
                "availability_topic": cfg["availability_topic"],
                "payload_available": "online",
                "payload_not_available": "offline",
                "unique_id": cfg["unique_id"],
            }
            if cfg.get("default_entity_id"):
                entry["default_entity_id"] = cfg["default_entity_id"]
            if component == "switch":
                entry.update(
                    {
                        "payload_on": "ON",
                        "payload_off": "OFF",
                        "state_on": "ON",
                        "state_off": "OFF",
                    }
                )
            elif component == "select":
                entry["options"] = cfg.get("options") or []
            elif component == "number":
                if "min" in cfg:
                    entry["min"] = cfg["min"]
                if "max" in cfg:
                    entry["max"] = cfg["max"]
                entry["step"] = cfg.get("step", 1)
                if cfg.get("unit_of_measurement"):
                    entry["unit_of_measurement"] = cfg["unit_of_measurement"]
            elif component == "button":
                if cfg.get("payload_press"):
                    entry["payload_press"] = cfg["payload_press"]
            elif component == "text":
                entry["mode"] = cfg.get("mode", "text")
            mqtt_block.setdefault(component, []).append(entry)
        return {
            "mqtt": mqtt_block,
            "topic_base": base,
            "broker": {
                "host": settings.get("host"),
                "port": settings.get("port"),
                "username": settings.get("username") or None,
                "tls": settings.get("tls_mode") != "none",
            },
            "note": (
                "Paste the mqtt: block into configuration.yaml or use MQTT Discovery "
                "when HA Discovery is enabled in DENON AVR MANAGER."
            ),
        }


_bridge = MqttBridge()


def get_mqtt_bridge() -> MqttBridge:
    return _bridge


def notify_entities(entities: Dict[str, Any]) -> None:
    _bridge.notify_entities(entities)


def restart_mqtt_bridge() -> None:
    _bridge.restart()


def refresh_mqtt_discovery() -> None:
    _bridge.refresh_discovery()


def stop_mqtt_bridge() -> None:
    _bridge.stop()
