# Corvallis Transit System for Home Assistant

This custom integration adds a timestamp sensor for a selected Corvallis Transit System route and stop.

## Installation with HACS

1. Open HACS and go to **Integrations**.
2. Open the menu, choose **Custom repositories**, and add [`https://github.com/hpux735/cts-homeassistant`](https://github.com/hpux735/cts-homeassistant).
3. Select **Integration** as the repository category.
4. Install **Corvallis Transit System** and restart Home Assistant.

For a private or unpublished repository, HACS must be able to access the repository through your GitHub account.

## Manual Installation

Copy `custom_components/corvallis_transit` into the Home Assistant `config/custom_components` directory, restart Home Assistant, and add **Corvallis Transit System** from Settings > Devices & services.

The integration reads the public CTS API and does not require an API key.

## Sensor

Each configured route and stop creates one `Next bus` sensor. Its state is the next live arrival as a timestamp. Attributes include `upcoming` arrival minutes, destination, route, stop, and the CTS update time.
