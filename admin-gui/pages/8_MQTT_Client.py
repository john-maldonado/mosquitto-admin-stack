"""Streamlit page providing a simple MQTT subscription client."""

import os
import queue
from datetime import datetime
from typing import Any, Dict
from uuid import uuid4

import streamlit as st
from streamlit_autorefresh import st_autorefresh
from paho.mqtt import client as mqtt

import common as c

# ------------------------------ Auth -----------------------------------------
if not c.require_login():
    st.stop()

st.set_page_config(page_title="MQTT Client", page_icon="📡", layout="wide")
c.set_active_page("mqtt_client")
st.title("MQTT Client")

st.caption(
    "Subscribe to a topic on the local Mosquitto broker and inspect the last 100 "
    "messages that arrive."
)

# Periodically refresh the page so queued MQTT events are rendered promptly.
st_autorefresh(interval=2000, key="mqtt_client_autorefresh")

# ------------------------------ Session state --------------------------------
def _init_state() -> None:
    if st.session_state.get("mqtt_state_initialized"):
        return

    st.session_state.setdefault("mqtt_cleanup_registered", False)
    st.session_state["mqtt_client"] = None
    st.session_state["mqtt_client_id"] = f"mosq-admin-{uuid4().hex[:8]}"
    st.session_state["mqtt_connected"] = False
    st.session_state["mqtt_subscription"] = ""
    st.session_state["mqtt_subscription_qos"] = 0
    st.session_state["mqtt_latest"] = None
    st.session_state["mqtt_messages"] = []
    st.session_state["mqtt_status"] = []
    st.session_state["mqtt_event_q"] = queue.Queue()
    st.session_state["mqtt_last_error"] = None
    st.session_state.setdefault("mqtt_host", "mosquitto")
    st.session_state.setdefault("mqtt_port", 1883)
    st.session_state.setdefault("mqtt_topic_input", "")
    st.session_state.setdefault("mqtt_username", "")
    st.session_state.setdefault("mqtt_password", "")
    st.session_state.setdefault("mqtt_use_tls", False)
    default_ca = c.CAFILE if os.path.exists(c.CAFILE) else ""
    st.session_state.setdefault("mqtt_tls_ca", default_ca)
    st.session_state.setdefault("mqtt_tls_insecure", False)
    st.session_state["mqtt_state_initialized"] = True

    if not st.session_state.get("mqtt_cleanup_registered"):
        c.register_page_cleanup("mqtt_client", _cleanup_mqtt_session)
        st.session_state["mqtt_cleanup_registered"] = True


def _append_status(message: str) -> None:
    entries = st.session_state.get("mqtt_status", [])
    entries.append((datetime.utcnow(), message))
    st.session_state["mqtt_status"] = entries[-50:]


def _decode_payload(payload: bytes) -> str:
    try:
        return payload.decode("utf-8")
    except UnicodeDecodeError:
        return "0x" + payload.hex()


def _on_connect(client: mqtt.Client, userdata: queue.Queue, flags: Dict[str, Any], reason_code: int, properties: Any = None) -> None:
    userdata.put(("connect", reason_code))


def _on_disconnect(client: mqtt.Client, userdata: queue.Queue, reason_code: int, properties: Any = None) -> None:
    userdata.put(("disconnect", reason_code))


def _on_message(client: mqtt.Client, userdata: queue.Queue, message: mqtt.MQTTMessage) -> None:
    userdata.put(("message", message.topic, message.payload, message.qos, message.retain))


def _process_event_queue() -> None:
    q = st.session_state.get("mqtt_event_q")
    if not q:
        return

    client = st.session_state.get("mqtt_client")
    while True:
        try:
            event = q.get_nowait()
        except queue.Empty:
            break

        kind = event[0]
        if kind == "connect":
            code = event[1]
            description = mqtt.connack_string(code)
            if code == 0:
                st.session_state["mqtt_connected"] = True
                st.session_state["mqtt_last_error"] = None
                _append_status(f"Connected: {description}")
                topic = st.session_state.get("mqtt_subscription")
                qos = st.session_state.get("mqtt_subscription_qos", 0)
                if topic and client is not None:
                    client.subscribe(topic, qos=qos)
                    _append_status(f"Re-subscribed to {topic} (QoS {qos})")
            else:
                st.session_state["mqtt_connected"] = False
                st.session_state["mqtt_last_error"] = description
                _append_status(f"Connection failed: {description}")
        elif kind == "disconnect":
            code = event[1]
            st.session_state["mqtt_connected"] = False
            description = mqtt.error_string(code)
            _append_status(f"Disconnected: {description}")
        elif kind == "message":
            topic, payload, qos, retain = event[1:5]
            text = _decode_payload(payload)
            received_at = datetime.utcnow()
            st.session_state["mqtt_latest"] = {
                "topic": topic,
                "payload": text,
                "qos": qos,
                "retain": bool(retain),
                "received_at": received_at.strftime("%Y-%m-%d %H:%M:%S UTC"),
            }
            messages = st.session_state.get("mqtt_messages", [])
            messages.append(
                {
                    "topic": topic,
                    "payload": text,
                    "received_at": received_at,
                }
            )
            st.session_state["mqtt_messages"] = messages[-100:]


def _disconnect_client(add_status: bool = True) -> None:
    client = st.session_state.get("mqtt_client")
    if not client:
        return

    try:
        client.unsubscribe(st.session_state.get("mqtt_subscription") or "")
    except Exception:
        pass

    try:
        client.disconnect()
    except Exception:
        pass

    try:
        client.loop_stop()
    except Exception:
        pass

    st.session_state["mqtt_client"] = None
    st.session_state["mqtt_connected"] = False
    if add_status:
        _append_status("Client disconnected")
    st.session_state["mqtt_messages"] = []


def _cleanup_mqtt_session() -> None:
    _disconnect_client(add_status=False)


def _connect_client(host: str, port: int) -> None:
    _disconnect_client(add_status=False)

    client_id = st.session_state.get("mqtt_client_id") or f"mosq-admin-{uuid4().hex[:8]}"
    q = queue.Queue()
    st.session_state["mqtt_event_q"] = q

    client = mqtt.Client(client_id=client_id, userdata=q)
    client.on_connect = _on_connect
    client.on_disconnect = _on_disconnect
    client.on_message = _on_message

    username = (st.session_state.get("mqtt_username") or "").strip()
    if username:
        password = st.session_state.get("mqtt_password") or None
        client.username_pw_set(username=username, password=password)

    use_tls = bool(st.session_state.get("mqtt_use_tls"))
    if use_tls:
        ca_path = (st.session_state.get("mqtt_tls_ca") or "").strip()
        try:
            if ca_path:
                client.tls_set(ca_certs=ca_path)
            else:
                client.tls_set()
        except Exception as exc:
            st.session_state["mqtt_client"] = None
            st.session_state["mqtt_connected"] = False
            st.session_state["mqtt_last_error"] = f"TLS setup failed: {exc}"
            _append_status(f"TLS setup failed: {exc}")
            return

        try:
            client.tls_insecure_set(bool(st.session_state.get("mqtt_tls_insecure")))
        except Exception as exc:
            st.session_state["mqtt_client"] = None
            st.session_state["mqtt_connected"] = False
            st.session_state["mqtt_last_error"] = f"TLS verification configuration failed: {exc}"
            _append_status(f"TLS verification configuration failed: {exc}")
            return

    try:
        client.connect(host, int(port), keepalive=60)
    except Exception as exc:
        st.session_state["mqtt_client"] = None
        st.session_state["mqtt_connected"] = False
        st.session_state["mqtt_last_error"] = str(exc)
        _append_status(f"Connection error: {exc}")
        return

    client.loop_start()
    st.session_state["mqtt_client"] = client
    st.session_state["mqtt_last_error"] = None
    scheme = "TLS" if use_tls else "TCP"
    _append_status(f"Connecting to {host}:{port} over {scheme}…")
    if username:
        _append_status("Authenticating with username/password")


def _subscribe(topic: str, qos: int) -> None:
    topic = topic.strip()
    if not topic:
        _append_status("Topic filter is required to subscribe.")
        return

    client = st.session_state.get("mqtt_client")
    if client is None:
        st.session_state["mqtt_last_error"] = "Not connected"
        _append_status("Connect to the broker before subscribing.")
        return

    existing = st.session_state.get("mqtt_subscription")
    if existing and existing != topic:
        try:
            client.unsubscribe(existing)
            _append_status(f"Unsubscribed from {existing}")
        except Exception as exc:
            _append_status(f"Error unsubscribing from {existing}: {exc}")

    result, _mid = client.subscribe(topic, qos=qos)
    if result == mqtt.MQTT_ERR_SUCCESS:
        st.session_state["mqtt_subscription"] = topic
        st.session_state["mqtt_subscription_qos"] = qos
        st.session_state["mqtt_latest"] = None
        st.session_state["mqtt_messages"] = []
        _append_status(f"Subscribed to {topic} (QoS {qos})")
    else:
        _append_status(f"Failed to subscribe to {topic}: {mqtt.error_string(result)}")


def _clear_subscription() -> None:
    topic = st.session_state.get("mqtt_subscription")
    client = st.session_state.get("mqtt_client")
    if topic and client is not None:
        try:
            client.unsubscribe(topic)
        except Exception as exc:
            _append_status(f"Error unsubscribing from {topic}: {exc}")
        else:
            _append_status(f"Unsubscribed from {topic}")
    st.session_state["mqtt_subscription"] = ""
    st.session_state["mqtt_latest"] = None
    st.session_state["mqtt_messages"] = []


_init_state()
_process_event_queue()

# ------------------------------ Connection UI -------------------------------
with st.container(border=True):
    st.subheader("Connection")
    col_a, col_b, col_c = st.columns([3, 2, 1])
    with col_a:
        st.text_input("Broker host", key="mqtt_host", help="Use 'mosquitto' when running via docker-compose or 'localhost' otherwise.")
    with col_b:
        st.number_input("Port", key="mqtt_port", min_value=1, max_value=65535, step=1)
    with col_c:
        if st.session_state.get("mqtt_connected"):
            if st.button("Disconnect", use_container_width=True):
                _disconnect_client()
        else:
            if st.button("Connect", use_container_width=True):
                _connect_client(st.session_state.get("mqtt_host", "mosquitto"), st.session_state.get("mqtt_port", 1883))

    status_col1, status_col2 = st.columns(2)
    status_col1.metric("Connection", "Connected" if st.session_state.get("mqtt_connected") else "Disconnected")
    subscription_label = st.session_state.get("mqtt_subscription") or "None"
    status_col2.metric("Subscription", subscription_label)

    last_error = st.session_state.get("mqtt_last_error")
    if last_error and not st.session_state.get("mqtt_connected"):
        st.warning(last_error)

    with st.expander("Authentication", expanded=bool(st.session_state.get("mqtt_username"))):
        st.text_input("Username", key="mqtt_username", placeholder="Optional")
        st.text_input("Password", key="mqtt_password", type="password", placeholder="Optional")

    tls_expanded = bool(st.session_state.get("mqtt_use_tls"))
    with st.expander("TLS", expanded=tls_expanded):
        st.checkbox("Use TLS", key="mqtt_use_tls")
        ca_disabled = not st.session_state.get("mqtt_use_tls")
        st.text_input(
            "CA certificate path",
            key="mqtt_tls_ca",
            placeholder="/config/ca-root-cert.crt",
            disabled=ca_disabled,
        )
        st.checkbox(
            "Allow insecure connection (skip certificate verification)",
            key="mqtt_tls_insecure",
            disabled=ca_disabled,
        )
        ca_path = st.session_state.get("mqtt_tls_ca")
        if st.session_state.get("mqtt_use_tls") and ca_path:
            if not os.path.exists(ca_path):
                st.warning("CA certificate not found at the provided path.")

# ------------------------------ Subscription UI -----------------------------
with st.container(border=True):
    st.subheader("Subscription")
    if not st.session_state.get("mqtt_connected"):
        st.info("Connect to the broker to enable subscription controls.")

    st.text_input("Topic filter", key="mqtt_topic_input", placeholder="sensors/#")
    qos = st.selectbox("QoS", options=[0, 1, 2], index=st.session_state.get("mqtt_subscription_qos", 0))

    col_sub, col_clear = st.columns([1, 1])
    with col_sub:
        st.button(
            "Subscribe",
            use_container_width=True,
            disabled=not st.session_state.get("mqtt_connected"),
            on_click=_subscribe,
            kwargs={
                "topic": st.session_state.get("mqtt_topic_input", ""),
                "qos": qos,
            },
        )
    with col_clear:
        st.button(
            "Clear subscription",
            use_container_width=True,
            disabled=not st.session_state.get("mqtt_subscription"),
            on_click=_clear_subscription,
        )

# ------------------------------ Message history -----------------------------
st.subheader("Recent messages")
message_entries = list(reversed(st.session_state.get("mqtt_messages", [])))
if message_entries:
    table_rows = [
        {
            "Topic": entry.get("topic", ""),
            "Message": entry.get("payload", ""),
            "Timestamp": entry["received_at"].strftime("%Y-%m-%d %H:%M:%S UTC")
            if isinstance(entry.get("received_at"), datetime)
            else str(entry.get("received_at", "")),
        }
        for entry in message_entries
    ]
    st.dataframe(table_rows, hide_index=True, use_container_width=True)
else:
    st.info("No messages received yet.")

# ------------------------------ Event log -----------------------------------
st.subheader("Event log")
log_entries = list(reversed(st.session_state.get("mqtt_status", [])))
if not log_entries:
    st.caption("No events recorded yet.")
else:
    for ts, message in log_entries:
        st.write(f"{ts.strftime('%H:%M:%S')} — {message}")

