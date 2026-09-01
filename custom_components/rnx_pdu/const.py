"""Constants for the RNX UPDU integration."""

from __future__ import annotations

from enum import IntEnum

DOMAIN = "rnx_pdu"
DEFAULT_USERNAME = "admin"
DEFAULT_SCAN_INTERVAL = 10

# The values below mirror the UPDU Web API (BETA) as of firmware 4.4.0.
#
# Node types are deliberately absent: the API exposes `Node.type` as a bare
# integer with no enum in the OpenAPI schema, and the numbering differs between
# firmware versions -- this integration previously matched POM 5 / OUTLET 7 /
# SENSOR 9, while 4.4.0 reports 4 / 6 / 8. Nodes are therefore classified by
# which properties object they carry (`pom`, `outlet`, `sensor`) instead.


class RelayState(IntEnum):
    """State of an outlet relay."""

    OFF = 0
    ON = 1
    UNKNOWN = 2
    AUTO_OFF = 3


class MeterQuality(IntEnum):
    """Freshness of a meter reading."""

    NO_DATA = 0
    EXPIRED = 1
    OK = 2


class LedBrightness(IntEnum):
    """Front-panel LED brightness levels."""

    LOW = 0
    MEDIUM = 1
    HIGH = 2


class ConditionSeverity(IntEnum):
    """Severity of a monitoring condition."""

    WARNING = 1
    CRITICAL = 2


class ConditionType(IntEnum):
    """Type of a monitoring condition."""

    ABOVE_THRESHOLD = 1
    BELOW_THRESHOLD = 2
    FAULT = 3
    UNKNOWN = 4
    FAILOVER = 5
    LOW_VOLTAGE = 6


class ConditionMetric(IntEnum):
    """Metric a monitoring condition applies to."""

    METER_CURRENT = 1
    METER_VOLTAGE = 2
    OVP_FITNESS = 3
    RCM_RMS_CURRENT = 4
    RCM_DC_CURRENT = 5
    TEMPERATURE = 6
    RELATIVE_HUMIDITY = 7
    SYSTEM_POWER = 8
    DIFFERENTIAL_PRESSURE = 9
    BRANCH_STATE = 10
    SYSTEM_HEALTH = 11


# Bounds enforced by the device web UI for the outlet powercycle delay.
POWERCYCLE_DELAY_MIN = 0
POWERCYCLE_DELAY_MAX = 60
