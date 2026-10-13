#!/bin/bash
# Quick Mosquitto install & config for Lucy on Raspberry Pi OS

set -e

echo "=== Installing Mosquitto MQTT Broker ==="
sudo apt update
sudo apt install -y mosquitto mosquitto-clients

echo "=== Enabling & starting service ==="
sudo systemctl enable mosquitto
sudo systemctl start mosquitto

echo "=== Basic status ==="
sudo systemctl status mosquitto --no-pager

echo ""
echo "Mosquitto is running on port 1883 (localhost)."
echo "Test with:"
echo "  mosquitto_sub -t 'home/devices/+/set' -v"
echo "  mosquitto_pub -t 'home/devices/lampu_teras/set' -m '{\"state\":\"ON\"}'"
