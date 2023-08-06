"""Ezviz Entities"""
import logging
import time
import datetime
import json
import requests
from async_timeout import timeout
from aiohttp.client_exceptions import ClientConnectorError

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
)

import voluptuous as vol
from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    #ServiceResponse,
    #SupportsResponse,
)
from homeassistant.exceptions import (
    ConfigEntryNotReady,
    HomeAssistantError,
    TemplateError,
)
from homeassistant.helpers import config_validation as cv, selector, template, entity_platform
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import (
    COORDINATOR, 
    DOMAIN, 
    UNDO_UPDATE_LISTENER,
    CONF_STATE_DETECTION_RULES,
    CONF_SWITCHS,
    CONF_BUTTONS,
    SENSOR_TYPES,
    ALARMSOUNDMODE,
    DEFENCE,
    ON_OFF,
    OFFLINENOTIFY,
    ONLINESTATUS,
)

TIMEOUT_SECONDS=10
_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Add Sensorentities from a config_entry."""      
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR] 
    sensors = []
    _LOGGER.debug(coordinator.data)   
    if coordinator.data.get("devicelistinfo"):
        devices = coordinator.data.get("devicelistinfo")
        evzizcameras = coordinator.data.get("cameralistinfo")
        _LOGGER.debug(devices)
        _LOGGER.debug(evzizcameras)   
        if isinstance(devices, list):
            for device in devices:
                for sensor in SENSOR_TYPES:                    
                    sensors.append(EzvizSensor(hass, sensor, coordinator,device["deviceSerial"]))
            async_add_entities(sensors, False)
            
class EzvizSensor(CoordinatorEntity):
    """Define an bjtoon_health_code entity."""
    
    _attr_has_entity_name = True    

    def __init__(self, hass, kind, coordinator, deviceserial):
        """Initialize."""
        super().__init__(coordinator)
        self.kind = kind
        self.coordinator = coordinator
        self._deviceserial = deviceserial
        self._state = None
        self._devicename = None
        self._deviceType = None
        self._deviceVersion = None
        _LOGGER.debug(self.kind)
        for sensordata in self.coordinator.data["devicelistinfo"]:
            if sensordata["deviceSerial"] == self._deviceserial:
                self._devicename = sensordata["deviceName"]
                self._deviceType = sensordata["deviceType"]
                self._deviceVersion = sensordata["deviceVersion"]

                
        self._attr_device_info = {
            "identifiers": {(DOMAIN, self._deviceserial)},
            "name": self._devicename,
            "manufacturer": "Ezviz",
            "model": self._deviceType,
            "sw_version": self._deviceVersion,
        }
        self._hass = hass
        self._name = SENSOR_TYPES[self.kind]['key']
        self._attr_translation_key = SENSOR_TYPES[self.kind]['key']
        self._state = self.coordinator.data[self._deviceserial][self.kind]
        if self.kind == "on_off":
            self._state = ON_OFF[self.coordinator.data[self._deviceserial][self.kind]]
        if self.kind == "status":
            self._state = ONLINESTATUS[self.coordinator.data[self._deviceserial][self.kind]]
        if self.kind == "alarmSoundMode":
            self._state = ALARMSOUNDMODE[self.coordinator.data[self._deviceserial][self.kind]]
        if self.kind == "defence":
            self._state = DEFENCE[self.coordinator.data[self._deviceserial][self.kind]]
        if self.kind == "offlineNotify":
            self._state = OFFLINENOTIFY[self.coordinator.data[self._deviceserial][self.kind]]

    @property
    def name(self):
        """Return the name."""
        return f"{self._name}"

    @property
    def unique_id(self):
        return f"{DOMAIN}_sensor_{self.kind}_{self._deviceserial}"
        

    @property
    def should_poll(self):
        """Return the polling requirement of the entity."""
        return True

    @property
    def available(self):
        """Return True if entity is available."""
        return self.coordinator.last_update_success

    @property
    def state(self):
        """Return the state."""
        return self._state

    @property
    def icon(self):
        """Return the icon."""
        if SENSOR_TYPES[self.kind].get("icon"):
            return SENSOR_TYPES[self.kind].get("icon")
        
    @property
    def unit_of_measurement(self):
        """Return the unit_of_measurement."""
        if SENSOR_TYPES[self.kind].get("unit_of_measurement"):
            return SENSOR_TYPES[self.kind]["unit_of_measurement"]
        
    @property
    def device_class(self):
        """Return the unit_of_measurement."""
        if SENSOR_TYPES[self.kind].get("device_class"):
            return SENSOR_TYPES[self.kind]["device_class"]
        
    # @property
    # def state_attributes(self): 
        # attrs = {}
        # data = self.coordinator.data
        # if self.coordinator.data.get(self.kind + "_attrs"):
            # attrs = self.coordinator.data[self.kind + "_attrs"]
        # if data:            
            # attrs["querytime"] = self.coordinator.data["updatetime"]  
        # return attrs  

    async def async_added_to_hass(self):
        """Connect to dispatcher listening for entity data notifications."""
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )

    async def async_update(self):
        """Update entity."""
        #await self.coordinator.async_request_refresh()
        self._state = self.coordinator.data[self._deviceserial][self.kind]
        if self.kind == "on_off":
            self._state = ON_OFF[self.coordinator.data[self._deviceserial][self.kind]]
        if self.kind == "status":
            self._state = ONLINESTATUS[self.coordinator.data[self._deviceserial][self.kind]]
        if self.kind == "alarmSoundMode":
            self._state = ALARMSOUNDMODE[self.coordinator.data[self._deviceserial][self.kind]]
        if self.kind == "defence":
            self._state = DEFENCE[self.coordinator.data[self._deviceserial][self.kind]]
        if self.kind == "offlineNotify":
            self._state = OFFLINENOTIFY[self.coordinator.data[self._deviceserial][self.kind]]
