import paho.mqtt.client as mqtt
import json
from pathlib import Path


LOCAL_DATA_FILE = Path(__file__).resolve().parent / "latest_traffic.json"


# ============================================================
# MQTT SETTINGS
# ============================================================

BROKER = "test.mosquitto.org"
PORT = 1883

TOPIC = "traffic/congestion"


# ============================================================
# CREATE MQTT CLIENT
# ============================================================

client = mqtt.Client(
    mqtt.CallbackAPIVersion.VERSION2,
    client_id="traffic-congestion-system"
)


# ============================================================
# CONNECT TO BROKER
# ============================================================

try:

    client.connect(BROKER, PORT, 60)
    client.loop_start()

    print("MQTT connected successfully.")

except Exception as e:

    print("MQTT connection failed:")
    print(e)


# ============================================================
# PUBLISH FUNCTION
# ============================================================

def publish_traffic_data(
    vehicles,
    moving,
    stopped,
    stopped_percentage,
    congestion
):

    data = {
        "vehicles": vehicles,
        "moving": moving,
        "stopped": stopped,
        "stopped_percentage": round(
            stopped_percentage,
            2
        ),
        "congestion": congestion
    }


    message = json.dumps(data)

    LOCAL_DATA_FILE.write_text(
        message,
        encoding="utf-8"
    )


    result = client.publish(
        TOPIC,
        message
    )


    if result.rc == mqtt.MQTT_ERR_SUCCESS:

        print(
            "MQTT:",
            message
        )

    else:

        print("MQTT publish failed.")