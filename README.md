<p align="center">
  <img src="logo.png" alt="RNX" width="300">
</p>

# RNX UPDU Integration for Home Assistant

[![HACS Validation](https://github.com/Newspicel/rnx-homeassistant/actions/workflows/validate.yml/badge.svg)](https://github.com/Newspicel/rnx-homeassistant/actions/workflows/validate.yml)
[![hassfest](https://github.com/Newspicel/rnx-homeassistant/actions/workflows/hassfest.yml/badge.svg)](https://github.com/Newspicel/rnx-homeassistant/actions/workflows/hassfest.yml)
[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=newspicel&repository=rnx-homeassistant)

Custom [Home Assistant](https://www.home-assistant.io/) integration for the [RNX UPDU®](https://www.rnx.ch/de_CH/updu) (Universal Power Distribution Unit). Provides real-time power monitoring and outlet control over the local network.

## Features

- **Power monitoring** per outlet and PDU-level: power (W), current (A), voltage (V), energy (kWh), power factor, apparent power (VA), reactive power (var)
- **Outlet switching** to turn individual outlets on or off
- **Power cycle** button per outlet
- **Controller reboot** button
- **Relay state** binary sensor per outlet

## Installation

### HACS (recommended)

1. Open HACS in Home Assistant
2. Go to **Integrations** > **Custom repositories**
3. Add `https://github.com/julian/rnx-homeassistant` as an **Integration**
4. Search for "RNX UPDU" and install
5. Restart Home Assistant

### Manual

1. Copy the `custom_components/rnx_pdu` directory into your Home Assistant `custom_components` folder
2. Restart Home Assistant

## Configuration

1. Go to **Settings** > **Devices & Services** > **Add Integration**
2. Search for "RNX UPDU"
3. Enter the host (IP address or hostname), username, and password of your PDU

## Entities

Each outlet exposes:

| Entity | Type | Description |
|--------|------|-------------|
| Power | Sensor | Active power in watts |
| Current | Sensor | RMS current in amps |
| Voltage | Sensor | RMS voltage in volts |
| Energy | Sensor | Cumulative energy in kWh |
| Power factor | Sensor | Power factor |
| Apparent power | Sensor | Apparent power in VA |
| Reactive power | Sensor | Reactive power in var |
| Relay | Binary sensor | Physical relay state |
| Switch | Switch | Turn outlet on/off |
| Power cycle | Button | Power-cycle the outlet |

The PDU device also exposes the same seven sensors aggregated, plus a **Reboot** button.

## Disclaimer

This project is not affiliated with, endorsed by, or associated with [RNX Switzerland](https://www.rnx.ch). RNX, UPDU, and related trademarks are the property of their respective owners. This integration is an independent, community-driven project that communicates with RNX UPDU® devices over the local network.

## License

This project is licensed under the [MIT License](LICENSE).
