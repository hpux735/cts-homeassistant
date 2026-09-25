"""Test data for Corvallis Transit System."""

DOMAIN = "corvallis_transit"
PROJECT = "1"
ROUTE = "2"
ROUTE_NAME = "9th st/hospital"
STOP = "5"
STOP_NAME = "NW 9th St & NW Maxine Ave"
UNIQUE_ID = f"{PROJECT}_{ROUTE}_{STOP}"

MAP_DATA = {
    "Bounds": {"X0": -1, "Y0": -1, "X1": 1, "Y1": 1},
    "Connectors": [],
    "Platforms": [
        {"Tag": 5, "No": "#10976", "Name": STOP_NAME, "X": 1, "Y": 2},
        {"Tag": 6, "No": "#10977", "Name": "Another Stop", "X": 3, "Y": 4},
        {"Tag": 7, "No": "#10911", "Name": STOP_NAME, "X": 1, "Y": 1},
    ],
    "Projects": [
        {
            "Tag": 1,
            "Name": "Corvallis Transit System",
            "Routes": [
                {
                    "No": ROUTE,
                    "Name": ROUTE_NAME,
                    "Platforms": [5, 6, 7],
                }
            ],
        },
        {
            "Tag": 2,
            "Name": "Philomath Connection",
            "Routes": [{"No": "PC", "Name": "philomath/osu", "Platforms": [5]}],
        },
    ],
}

ARRIVAL_DATA = {
    "Tag": 5,
    "Created": "9:14 AM",
    "Projects": [
        {
            "Tag": 1,
            "Routes": [
                {
                    "No": ROUTE,
                    "Name": ROUTE_NAME,
                    "Destinations": [
                        {
                            "Name": "Downtown Transit Center",
                            "Trips": [
                                {"ET": 18, "ST": None},
                                {"ET": 4, "ST": None},
                            ],
                        }
                    ],
                }
            ],
        }
    ],
    "Expires": "2026-09-25T16:00:00Z",
}

CONFIG = {
    "project": PROJECT,
    "project_name": "Corvallis Transit System",
    "route": ROUTE,
    "route_name": ROUTE_NAME,
    "route_label": f"{ROUTE}. {ROUTE_NAME}",
    "stop": STOP,
    "platform_tag": STOP,
    "platform_name": STOP_NAME,
}
