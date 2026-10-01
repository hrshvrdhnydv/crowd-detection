from mqtt_client import publish_traffic_data

publish_traffic_data(
    vehicles=25,
    moving=8,
    stopped=17,
    stopped_percentage=68.0,
    congestion="HIGH"
)

print("Test completed.")