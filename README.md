# Corvallis Transit System for Home Assistant

This custom integration adds live arrival sensors for selected Corvallis Transit System or Philomath Connection routes and stops. It uses the public CTS real-time API and does not require an API key.

## Installation with HACS

1. Open HACS and go to **Integrations**.
2. Open the menu, choose **Custom repositories**, and add [`https://github.com/hpux735/cts-homeassistant`](https://github.com/hpux735/cts-homeassistant).
3. Select **Integration** as the repository category.
4. Install **Corvallis Transit System** and restart Home Assistant.

For a private or unpublished repository, HACS must be able to access the repository through your GitHub account.

## Manual Installation

Copy `custom_components/corvallis_transit` into the Home Assistant `config/custom_components` directory, restart Home Assistant, and add **Corvallis Transit System** from Settings > Devices & services.

## Sensor

Each configured route and stop creates one `Next bus` sensor. Its state is the next live arrival as a timestamp. Attributes include `upcoming` arrival minutes, destination, route, stop, and the CTS update time. If CTS only provides scheduled times, they are exposed in the `scheduled` attribute and the sensor is unknown rather than presenting a misleading live timestamp.

## Configuration

The setup flow asks for:

- Transit agency: Corvallis Transit System or Philomath Connection.
- Route: A route offered by that agency.
- Stop: A stop served by that route.

Each agency, route, and stop combination can be configured only once. The integration polls CTS approximately once per minute and shares one request among sensors configured for the same stop.

## Use Cases

Use the timestamp sensor on a dashboard to see the next bus at a regular stop, or trigger a notification when the next arrival changes. The integration currently supports arrival sensors only; it does not control vehicles, stops, fares, or service alerts.

Example automation:

```yaml
automation:
  - alias: Notify when the next bus is available
    triggers:
      - trigger: state
        entity_id: sensor.next_bus
    conditions:
      - condition: template
        value_template: "{{ trigger.to_state.state not in ['unknown', 'unavailable'] }}"
    actions:
      - action: notify.mobile_app_phone
        data:
          message: >-
            The next bus arrives at {{ trigger.to_state.attributes.destination }}
            in {{ trigger.to_state.attributes.upcoming.split(', ')[0] }} minutes.

```

## Data Updates

The integration downloads the CTS map data during setup and uses it to populate the configuration flow. Arrival data is fetched from the public `PlatformET` endpoint about once per minute. Requests for multiple routes at the same stop are shared. Failed requests leave the existing entity unavailable until a later update succeeds.

## Troubleshooting

If the service is unavailable, the sensor becomes unavailable and Home Assistant retries on the normal polling schedule. Check the Home Assistant log for `custom_components.corvallis_transit` entries and confirm that `https://www.corvallistransit.com` is reachable from the Home Assistant host.

The CTS API is undocumented and provider-controlled. Route, stop, arrival, and map data can change without notice. A stale or removed route/stop must be removed and added again through the integration's config entries.

## Removal

Remove the configured Corvallis Transit System entries from Settings > Devices & services. To remove the integration files, uninstall it from HACS or delete `config/custom_components/corvallis_transit` and restart Home Assistant.

This integration provides sensors only. It does not provide service actions, custom triggers, or custom conditions.
