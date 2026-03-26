# 🌱 Smart Greenhouse Monitor

A complete ESP32 firmware project that turns your greenhouse into an AI-manageable environment. Built with [jettyd](https://jettyd.com) — the IoT middleware for AI agents.

**Flash your ESP32. Your AI agent can now read sensors and control your pump.**

---

## What it does

- 🌡️ **Monitors air** — temperature + humidity every 30 seconds (DHT22)
- 💧 **Monitors soil** — moisture percentage via ADC (capacitive sensor)
- 🚿 **Auto-waters** — relay triggers pump when soil moisture drops below 30%
- 🤖 **AI-controllable** — any LLM with HTTP access can read sensors and send commands
- 📡 **Works offline** — JettyScript rules run on the device even without internet

---

## Hardware

| Component | Part | Notes |
|-----------|------|-------|
| Microcontroller | ESP32-S3, C3, or C6 | Any dev board |
| Temperature + Humidity | DHT22 / AM2302 | 3-pin sensor |
| Soil Moisture | Capacitive sensor (v1.2) | Avoid resistive — they corrode |
| Relay Module | 5V relay with optocoupler | For water pump |
| LED | Any 3mm/5mm LED | Status indicator |
| Water pump | 3–5V mini submersible | 5V USB-powered works great |
| Resistor | 330Ω | LED current limiting |

**Total component cost: ~$15**

---

## Wiring

```
ESP32-S3/C3/C6
├── GPIO 4  ──────── DHT22 data pin (with 10kΩ pull-up to 3.3V)
├── GPIO 5  ──────── Soil moisture sensor AO (analog output)
├── GPIO 6  ──────── Relay IN (active-low)
├── GPIO 8  ──────── LED anode (via 330Ω resistor to GND)
├── 3.3V    ──────── DHT22 VCC, sensor VCC
└── GND     ──────── DHT22 GND, sensor GND, relay GND, LED cathode

Relay module:
├── VCC ──── 5V (from dev board USB power)
├── GND ──── GND
├── IN  ──── GPIO 6
├── COM ──── 5V (pump power)
└── NO  ──── Pump + terminal
```

```
              3.3V
               │
              10kΩ
               │
DHT22 ────────┤GPIO 4     GPIO 8 ────330Ω──── LED ──── GND
               │
        ┌──────────────────────┐
        │       ESP32-S3       │
        │                      │
        │   GPIO 5 ────────────┤──── Soil moisture AO
        │   GPIO 6 ────────────┤──── Relay IN
        └──────────────────────┘
```

---

## Quick start

```bash
# 1. Clone
git clone https://github.com/jettydiot/example-greenhouse my-greenhouse
cd my-greenhouse

# 2. Fetch the jettyd SDK
make setup

# 3. Set your credentials in sdkconfig.defaults
#    CONFIG_JETTYD_FLEET_TOKEN="ft_your_token"   ← from app.jettyd.com
#    CONFIG_JETTYD_WIFI_SSID="YourNetwork"
#    CONFIG_JETTYD_WIFI_PASSWORD="YourPassword"

# 4. Flash
make flash-monitor
```

Get your fleet token at **[app.jettyd.com](https://app.jettyd.com)** after signing up.

---

## What happens on first boot

```
I (1200) jettyd_wifi: Connecting to WiFi...
I (3800) jettyd_wifi: Connected — IP: 192.168.1.42
I (4100) jettyd_prov: Provisioning... fleet_token=ft_...
I (5200) jettyd_prov: Provisioned! device_key=dk_a1b2c3...
I (5600) jettyd_mqtt: Connected to mqtt.jettyd.com
I (5800) jettyd: Jettyd running
I (5800) jettyd: Drivers: 4    ← air, soil, pump, status
I (5800) jettyd: Rules: 0      ← push jettyscript.json to add rules
```

After provisioning:
1. Device appears in `app.jettyd.com` dashboard with a green **● Online** badge
2. Telemetry starts flowing — air temp/humidity, soil moisture, RSSI, chip temp
3. You can read sensors and send commands immediately via the API

---

## Push the JettyScript rules

The `jettyscript.json` file contains rules that run **on the device** — no cloud round-trip:

```bash
# Get your API key from app.jettyd.com → Settings
export JETTYD_API_KEY="tk_..."
export DEVICE_ID="your-device-id"

# Push the rules
curl -X POST "https://api.jettyd.com/v1/devices/$DEVICE_ID/config" \
  -H "Authorization: Bearer $JETTYD_API_KEY" \
  -H "Content-Type: application/json" \
  -d @jettyscript.json
```

Rules included:

| Rule | Trigger | Action |
|------|---------|--------|
| `auto-water` | soil < 30% | Switch pump on for 10 seconds |
| `temp-alert` | temp > 35°C | Publish warning alert |
| `humidity-alert` | humidity > 90% | Publish info alert |
| `status-led-online` | MQTT connected | Slow blink (5s) |
| `status-led-offline` | MQTT disconnected | Fast blink (1s) |

---

## Control with AI

Once your device is provisioned, any AI agent with HTTP access can read sensors and control the pump:

```bash
# Read all sensor readings (device shadow)
curl -H "Authorization: Bearer $JETTYD_API_KEY" \
  https://api.jettyd.com/v1/devices/$DEVICE_ID/shadow

# Response:
# {
#   "reported": {
#     "air.temperature": 24.3,
#     "air.humidity": 67.1,
#     "soil.moisture": 42.5,
#     "system.rssi": -58,
#     "system.chip_temp": 51.2
#   }
# }

# Manually trigger watering
curl -X POST \
  -H "Authorization: Bearer $JETTYD_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"command_type": "switch_on", "payload": {"target": "pump", "duration_sec": 10}}' \
  https://api.jettyd.com/v1/devices/$DEVICE_ID/commands

# Ask Claude / GPT / OpenClaw about your greenhouse
# "What's the temperature in the greenhouse?"
# "Is the soil too dry? Should I water?"
# "Turn on the pump for 5 seconds"
```

### With OpenClaw (MCP)
```bash
npx @jettyd/mcp
# Then ask your AI assistant:
# "List my devices and show the greenhouse sensor readings"
```

---

## Customise

Edit `device.yaml` to change GPIO pins or add sensors. The build system auto-generates the C code:

```yaml
# Add a relay for a ventilation fan
drivers:
  - name: relay
    instance: "fan"
    config:
      pin: 7
      active_high: false
```

Then rebuild: `make flash`

Add a corresponding rule to `jettyscript.json`:
```json
{
  "id": "auto-ventilate",
  "condition": { "sensor": "air.humidity", "op": ">", "value": 85 },
  "actions": [
    { "action": "switch_on", "target": "fan", "duration_sec": 300 }
  ]
}
```

---

## Dashboard

After flashing, open **[app.jettyd.com](https://app.jettyd.com)** to see:
- Live telemetry charts (temperature, humidity, soil moisture)
- Command history (when the pump last ran)
- Device shadow (current vs desired state)
- Online/offline status

---

## Links

- 📖 [QuickStart guide](https://docs.jettyd.com/quickstart)
- 📦 [Firmware SDK](https://github.com/jettydiot/jettyd-firmware) — MIT licensed
- 📋 [Device template](https://github.com/jettydiot/jettyd-firmware-template)
- 🤖 [MCP server](https://www.npmjs.com/package/@jettyd/mcp)
- 🌐 [jettyd.com](https://jettyd.com)

---

## License

MIT — see [LICENSE](LICENSE).

Built with 🦞 by [jettyd](https://jettyd.com)
