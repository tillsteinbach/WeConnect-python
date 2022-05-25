from enum import Enum


class Domain(Enum):
    ALL = 'all'
    ALL_CAPABLE = 'allCapable'
    ACCESS = 'access'
    AUTOMATION = 'automation'
    USER_CAPABILITIES = 'userCapabilities'
    CHARGING = 'charging'
    CLIMATISATION = 'climatisation'
    FUEL_STATUS = 'fuelStatus'
    VEHICLE_LIGHTS = 'vehicleLights'
    LV_BATTERY = 'lvBattery'
    READINESS = 'readiness'
    VEHICLE_HEALTH_INSPECTION = 'vehicleHealthInspection'
    VEHICLE_HEALTH_WARNINGS = 'vehicleHealthWarnings'
    OIL_LEVEL = 'oilLevel'
    MEASUREMENTS = 'measurements'
    BATTERY_SUPPORT = 'batterySupport'
    PARKING = 'parking'

    def __str__(self):
        return self.value
