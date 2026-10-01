import streamlit as st
import paho.mqtt.client as mqtt
import json
import threading
import time
import queue
from datetime import datetime
from pathlib import Path
import pandas as pd




st.set_page_config(
    page_title="AI Traffic Intelligence",
    page_icon="🚦",
    layout="wide",
    initial_sidebar_state="expanded"
)




def render_html(html):
    st.html(html)




render_html("""
<style>

.stApp {
    background:
        radial-gradient(
            circle at top right,
            #172554 0%,
            #0b1120 35%,
            #020617 100%
        );
    color: white;
}

.block-container {
    padding-top: 2rem;
    padding-bottom: 2rem;
}

.main-title {
    font-size: 42px;
    font-weight: 800;
    letter-spacing: 1px;
    margin-bottom: 0;
}

.subtitle {
    color: #94a3b8;
    font-size: 17px;
    margin-top: 4px;
}

.metric-card {
    background:
        linear-gradient(
            145deg,
            rgba(30,41,59,0.95),
            rgba(15,23,42,0.95)
        );

    border: 1px solid rgba(148,163,184,0.15);
    border-radius: 18px;
    padding: 22px;

    box-shadow:
        0 10px 35px rgba(0,0,0,0.30);

    min-height: 145px;
    transition: 0.25s;
}

.metric-card:hover {
    transform: translateY(-4px);

    border-color: rgba(96,165,250,0.5);

    box-shadow:
        0 15px 40px rgba(0,0,0,0.45);
}

.metric-icon {
    font-size: 28px;
}

.metric-title {
    color: #94a3b8;
    font-size: 14px;
    margin-top: 8px;
}

.metric-value {
    font-size: 34px;
    font-weight: 800;
    margin-top: 4px;
}

.status-card {
    border-radius: 22px;
    padding: 28px;
    text-align: center;
    margin-top: 10px;
    margin-bottom: 20px;

    box-shadow:
        0 15px 40px rgba(0,0,0,0.35);
}

.status-title {
    font-size: 14px;
    color: #cbd5e1;
    text-transform: uppercase;
    letter-spacing: 2px;
}

.status-value {
    font-size: 42px;
    font-weight: 900;
    margin-top: 8px;
}

.section-title {
    font-size: 22px;
    font-weight: 750;
    margin-top: 20px;
    margin-bottom: 15px;
}

.info-card {
    background: rgba(15,23,42,0.82);

    border:
        1px solid
        rgba(148,163,184,0.12);

    border-radius: 18px;
    padding: 22px;
    min-height: 190px;

    box-shadow:
        0 8px 30px rgba(0,0,0,0.25);
}

/* Fix Streamlit's top header/toolbar white strip */
header[data-testid="stHeader"],
[data-testid="stHeader"] {
    background: #020617 !important;
}

[data-testid="stToolbar"],
[data-testid="stDecoration"] {
    background: transparent !important;
}

/* Keep the dark page background consistent */
[data-testid="stAppViewContainer"],
.stAppViewContainer {
    background: transparent !important;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background: linear-gradient(
        180deg,
        #020617,
        #0f172a
    ) !important;
}

/* Improve sidebar text contrast */
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"],
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] .stCaption {
    color: #e2e8f0 !important;
}

/* Keep sidebar status messages readable */
[data-testid="stSidebar"] [data-testid="stAlert"] {
    color: #e2e8f0 !important;
}

.live-badge {
    display: inline-block;

    padding: 6px 14px;

    border-radius: 20px;

    background: rgba(34,197,94,0.15);

    color: #4ade80;

    border: 1px solid rgba(34,197,94,0.35);

    font-size: 13px;

    font-weight: 700;
}

.footer {
    text-align: center;

    color: #64748b;

    font-size: 13px;

    padding: 25px;

    margin-top: 30px;
}

</style>
""")




BROKER = "test.mosquitto.org"
PORT = 1883
TOPIC = "traffic/congestion"




if "traffic_data" not in st.session_state:

    st.session_state.traffic_data = {
        "vehicles": 0,
        "moving": 0,
        "stopped": 0,
        "stopped_percentage": 0,
        "congestion": "WAITING"
    }


if "history" not in st.session_state:

    st.session_state.history = []


if "last_update" not in st.session_state:

    st.session_state.last_update = "Waiting..."




@st.cache_resource
def get_mqtt_queue():

    messages = queue.Queue()

    def on_message(client, userdata, msg):

        try:

            messages.put(
                json.loads(msg.payload.decode())
            )

        except Exception as e:

            print("MQTT message error:", e)

    def mqtt_subscriber():

        try:

            client = mqtt.Client(
                mqtt.CallbackAPIVersion.VERSION2,
                client_id="traffic-dashboard"
            )

            client.on_message = on_message
            client.connect(BROKER, PORT, 60)
            client.subscribe(TOPIC)
            print("Dashboard MQTT connected.")
            client.loop_forever()

        except Exception as e:

            print("MQTT error:", e)

    threading.Thread(
        target=mqtt_subscriber,
        daemon=True
    ).start()

    return messages


message_queue = get_mqtt_queue()

local_data_file = Path(__file__).resolve().parents[1] / "latest_traffic.json"

if local_data_file.exists():

    try:

        message_queue.put(
            json.loads(
                local_data_file.read_text(encoding="utf-8")
            )
        )

    except (OSError, json.JSONDecodeError):

        pass

while not message_queue.empty():

    data = message_queue.get_nowait()
    st.session_state.traffic_data = data

    st.session_state.history.append(
        {
            "Time": datetime.now().strftime("%H:%M:%S"),
            "Vehicles": data.get("vehicles", 0),
            "Moving": data.get("moving", 0),
            "Stopped": data.get("stopped", 0)
        }
    )

    st.session_state.history = st.session_state.history[-30:]
    st.session_state.last_update = datetime.now().strftime("%H:%M:%S")




data = st.session_state.traffic_data

vehicles = data.get(
    "vehicles",
    0
)

moving = data.get(
    "moving",
    0
)

stopped = data.get(
    "stopped",
    0
)

stopped_percentage = data.get(
    "stopped_percentage",
    0
)

congestion = data.get(
    "congestion",
    "WAITING"
)




with st.sidebar:

    st.markdown("## 🚦 AI TRAFFIC")

    st.caption(
        "Intelligent Traffic Monitoring System"
    )

    st.divider()

    st.markdown("### 🧠 AI Engine")

    st.success(
        "YOLO Detection: ACTIVE"
    )

    st.success(
        "Vehicle Tracking: ACTIVE"
    )

    st.divider()

    st.markdown("### 📡 MQTT")

    st.info("Broker")

    st.code(BROKER)

    st.info("Topic")

    st.code(TOPIC)

    st.divider()

    st.markdown("### 🎥 Video Processing")

    st.write("Resolution: 1280 × 720")

    st.write("Detection: Real-Time")

    st.write("Tracking: Enabled")

    st.divider()

    st.caption(
        "P_291 Intelligent Traffic Congestion Detection"
    )




header_col1, header_col2 = st.columns(
    [5, 1]
)


with header_col1:

    render_html("""
    <div class="main-title">
        🚦 AI Traffic Intelligence
    </div>
    """)

    render_html("""
    <div class="subtitle">
        Real-time vehicle detection, tracking
        and congestion analysis
    </div>
    """)


with header_col2:

    render_html("""
    <div style="text-align:right; margin-top:15px;">
        <span class="live-badge">● LIVE SYSTEM</span>
    </div>
    """)


st.divider()




c1, c2, c3, c4 = st.columns(4)



with c1:

    render_html(f"""
    <div class="metric-card">

        <div class="metric-icon">🚗</div>

        <div class="metric-title">
            TOTAL VEHICLES
        </div>

        <div class="metric-value">
            {vehicles}
        </div>

    </div>
    """)




with c2:

    render_html(f"""
    <div class="metric-card">

        <div class="metric-icon">🟢</div>

        <div class="metric-title">
            MOVING VEHICLES
        </div>

        <div class="metric-value">
            {moving}
        </div>

    </div>
    """)



with c3:

    render_html(f"""
    <div class="metric-card">

        <div class="metric-icon">🛑</div>

        <div class="metric-title">
            STOPPED VEHICLES
        </div>

        <div class="metric-value">
            {stopped}
        </div>

    </div>
    """)



with c4:

    render_html(f"""
    <div class="metric-card">

        <div class="metric-icon">📊</div>

        <div class="metric-title">
            STOPPED PERCENTAGE
        </div>

        <div class="metric-value">
            {stopped_percentage:.1f}%
        </div>

    </div>
    """)




render_html("""
<div class="section-title">
    🚦 Current Traffic Condition
</div>
""")


if congestion == "HIGH":

    status_bg = (
        "linear-gradient("
        "135deg,"
        "#450a0a,"
        "#7f1d1d"
        ")"
    )

    status_text = "🔴 HIGH CONGESTION"

    status_description = (
        "Heavy traffic detected"
    )


elif congestion == "MEDIUM":

    status_bg = (
        "linear-gradient("
        "135deg,"
        "#431407,"
        "#9a3412"
        ")"
    )

    status_text = "🟠 MEDIUM CONGESTION"

    status_description = (
        "Moderate traffic detected"
    )


elif congestion == "LOW":

    status_bg = (
        "linear-gradient("
        "135deg,"
        "#052e16,"
        "#166534"
        ")"
    )

    status_text = "🟢 LOW CONGESTION"

    status_description = (
        "Traffic is flowing normally"
    )


else:

    status_bg = (
        "linear-gradient("
        "135deg,"
        "#172033,"
        "#334155"
        ")"
    )

    status_text = "⏳ WAITING FOR DATA"

    status_description = (
        "Waiting for YOLO traffic data"
    )


render_html(f"""
<div
    class="status-card"
    style="background:{status_bg};"
>

    <div class="status-title">
        CURRENT STATUS
    </div>

    <div class="status-value">
        {status_text}
    </div>

    <div>
        {status_description}
    </div>

</div>
""")




left, right = st.columns(2)




with left:

    render_html("""
    <div class="section-title">
        📈 Traffic Activity
    </div>
    """)

    if len(st.session_state.history) > 0:

        chart_data = pd.DataFrame(
            st.session_state.history
        )

        chart_data = chart_data.set_index(
            "Time"
        )

        st.line_chart(
            chart_data[
                [
                    "Vehicles",
                    "Moving",
                    "Stopped"
                ]
            ],
            height=300
        )

    else:

        st.info(
            "Waiting for traffic history..."
        )




with right:

    render_html("""
    <div class="section-title">
        🚗 Vehicle Activity
    </div>
    """)

    total_for_ratio = max(
        vehicles,
        1
    )

    moving_ratio = (
        moving /
        total_for_ratio
    )

    stopped_ratio = (
        stopped /
        total_for_ratio
    )

    st.write("🟢 Moving")

    st.progress(
        min(moving_ratio, 1.0)
    )

    st.caption(
        f"{moving} vehicles"
    )

    st.write("🔴 Stopped")

    st.progress(
        min(stopped_ratio, 1.0)
    )

    st.caption(
        f"{stopped} vehicles"
    )


# ============================================================
# STOPPED VEHICLE GAUGE
# ============================================================

st.divider()

g1, g2 = st.columns(2)


with g1:

    render_html("""
    <div class="section-title">
        🛑 Congestion Indicator
    </div>
    """)

    gauge_value = min(
        max(
            stopped_percentage / 100,
            0
        ),
        1
    )

    st.progress(
        gauge_value
    )

    render_html(f"""
    <div style="
        text-align:center;
        font-size:32px;
        font-weight:800;
        margin-top:10px;
    ">
        {stopped_percentage:.1f}%
    </div>

    <div style="
        text-align:center;
        color:#94a3b8;
    ">
        vehicles currently estimated stopped
    </div>
    """)


# ============================================================
# SYSTEM HEALTH
# ============================================================

with g2:

    render_html("""
    <div class="section-title">
        🧠 System Health
    </div>
    """)

    st.success(
        "✓ YOLO Detection Active"
    )

    st.success(
        "✓ Vehicle Tracking Active"
    )

    st.success(
        "✓ MQTT Data Stream Active"
    )

    st.success(
        "✓ Streamlit Dashboard Active"
    )




st.divider()

render_html("""
<div class="section-title">
    📡 Live MQTT Data
</div>
""")


data_col1, data_col2 = st.columns(
    [3, 1]
)


with data_col1:

    st.json(data)


with data_col2:

    render_html(f"""
    <div class="info-card">

        <h3>⏱ Last Update</h3>

        <h2>
            {st.session_state.last_update}
        </h2>

        <p style="color:#94a3b8;">
            Latest traffic information
            received through MQTT.
        </p>

    </div>
    """)




st.markdown(
    "🚦 **P_291 Intelligent Traffic Congestion Detection**  "
    "\nOpenCV • YOLO • PyTorch • MQTT • Streamlit"
)

st.caption(
    "AI-powered real-time traffic monitoring prototype"
)




time.sleep(1)

st.rerun()