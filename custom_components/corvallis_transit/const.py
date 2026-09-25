"""Constants for the Corvallis Transit System integration."""

from typing import Final

DOMAIN: Final = "corvallis_transit"
API_BASE: Final = "https://www.corvallistransit.com/rtt/public/api/transit"
# The endpoint accepts zero as "latest". This avoids pinning the integration to
# the build number used by the provider's web application.
MAP_BUILD_NO: Final = "0"

CONF_PROJECT: Final = "project"
CONF_ROUTE: Final = "route"
CONF_ROUTE_NAME: Final = "route_name"
CONF_PLATFORM_TAG: Final = "platform_tag"
CONF_PLATFORM_NAME: Final = "platform_name"

UPDATE_INTERVAL_MINUTES: Final = 1
REQUEST_TIMEOUT_SECONDS: Final = 15
