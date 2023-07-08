from enum import Enum


class Domain(Enum):
    ALL = 'all'
    ALL_CAPABLE = 'allCapable'
    ACCESS = 'access'
    ACTIVEVENTILATION = 'activeventilation'
    AUTOMATION = 'automation'
    AUXILIARY_HEATING = 'auxiliaryheating'
    USER_CAPABILITIES = 'userCapabilities'
    CHARGING = 'charging'
    CHARGING_PROFILES = 'chargingProfiles'
    BATTERY_CHARGING_CARE = 'batteryChargingCare'
    CLIMATISATION = 'climatisation'
    CLIMATISATION_TIMERS = 'climatisationTimers'
    DEPARTURE_TIMERS = 'departureTimers'
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
    TRIPS = 'trips'

    def __str__(self):
        return self.value
