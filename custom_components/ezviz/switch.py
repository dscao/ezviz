"""Ezviz Entities"""
import logging
import time
import datetime
import json
import requests
from async_timeout import timeout
from aiohttp.client_exceptions import ClientConnectorError

from homeassistant.components.switch import SwitchEntity

from .const import (
    COORDINATOR, 
    DOMAIN, 
    UNDO_UPDATE_LISTENER,
    CONF_STATE_DETECTION_RULES,
    CONF_SWITCHS,
    CONF_BUTTONS,
    SWITCH_TYPES,
)

TIMEOUT_SECONDS=10
_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Add Switchentities from a config_entry."""      
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR] 
    switchs = []
    _LOGGER.debug(coordinator.data)   
    if coordinator.data.get("devicelistinfo"):
        devices = coordinator.data.get("devicelistinfo")
        evzizcameras = coordinator.data.get("cameralistinfo")
        _LOGGER.debug(devices)
        _LOGGER.debug(evzizcameras)
        if isinstance(devices, list):
            for device in devices:
                switchtypes = {}
                switchtypes["soundswitch"] = SWITCH_TYPES["soundswitch"]
                if coordinator.data[device["deviceSerial"]+"-capacity"].get("support_privacy") == '1':
                    switchtypes["on_off"] = SWITCH_TYPES["on_off"]
                if coordinator.data[device["deviceSerial"]+"-capacity"].get("support_defence") == '1':
                    switchtypes["defence"] = SWITCH_TYPES["defence"]
                switchtypes = {key: value for key, value in switchtypes.items() if value is not None}    
                for swtich in switchtypes:
                    switchs.append(EzvizSwitch(hass, swtich, coordinator, device["deviceSerial"]))
            async_add_entities(switchs, False)
            

class EzvizSwitch(SwitchEntity):
    _attr_has_entity_name = True
    def __init__(self, hass, kind, coordinator, deviceserial):
        """Initialize."""
        super().__init__()
        self.kind = kind
        self.coordinator = coordinator
        self._deviceserial = deviceserial
        self._state = None

        self._devicename = None
        self._deviceType = None
        self._deviceVersion = None
        
        for switchdata in self.coordinator.data["devicelistinfo"]:
            if switchdata["deviceSerial"] == self._deviceserial:
                self._devicename = switchdata["deviceName"]
                self._deviceType = switchdata["deviceType"]
                self._deviceVersion = switchdata["deviceVersion"]

                
        self._attr_device_info = {
            "identifiers": {(DOMAIN, self._deviceserial)},
            "name": self._devicename,
            "manufacturer": "Ezviz",
            "model": self._deviceType,
            "sw_version": self._deviceVersion,
        }
        self._attr_device_class = "switch"
        self._attr_entity_registry_enabled_default = True
        self._hass = hass
        self._name = SWITCH_TYPES[self.kind][1]
        self._turn_on_body = ""
        self._turn_off_body = ""
        self._change = True
        self._switchonoff = None
        
        self._listswitch = self.coordinator.data.get(self._deviceserial)
        self._switchonoff = self._listswitch[self.kind]
                
        self._is_on = self._switchonoff == 1
        self._state = "on" if self._is_on == True else "off"


   
    @property
    def name(self):
        """Return the name."""
        return f"{self._name}"

    @property
    def unique_id(self):
        return f"{DOMAIN}_switch_{self.kind}_{self._deviceserial}"

        
    @property
    def should_poll(self):
        """Return the polling requirement of the entity."""
        return False
        
    @property
    def extra_state_attributes(self):
        """Return device state attributes."""
        attrs = {}
        attrs["ezviz_accesstoken"] = self.coordinator.data["params"]["accessToken"]
        attrs["defence"] = self._listswitch["defence"]
        attrs["alarmSoundMode"] = self._listswitch["alarmSoundMode"]
        attrs["netAddress"] = self._listswitch["netAddress"]
        attrs["uptime"] = self._listswitch["updateTime"]
        attrs["querytime"] = self.coordinator.data["updatetime"]
        
        return attrs
        
    @property
    def icon(self):
        """Return the icon."""
        return SWITCH_TYPES[self.kind][2]

    @property
    def is_on(self):
        """Check if switch is on."""        
        return self._is_on

    async def async_turn_on(self, **kwargs):
        """Turn switch on."""
        self._is_on = True
        self._change = False
        await self._switch("on")
        self._switchonoff = "on"
        self.async_write_ha_state()


    async def async_turn_off(self, **kwargs):
        """Turn switch off."""
        self._is_on = False
        self._change = False
        await self._switch("off")
        self._switchonoff = "off"
        self.async_write_ha_state()

    async def async_added_to_hass(self):
        """Connect to dispatcher listening for entity data notifications."""
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )

    async def async_update(self):
        """Update entity."""
        #await self.coordinator.async_request_refresh()
        
        self._listswitch = self.coordinator.data.get(self._deviceserial)
        self._switchonoff = self._listswitch[self.kind]
                
        self._is_on = self._switchonoff == 1
        self._state = "on" if self._is_on == True else "off"
        
    def is_json(self, jsonstr):
        try:
            json.loads(jsonstr)
        except ValueError:
            return False
        return True

    def sendHttpPost(self, url, data):
        try:            
            resp = requests.post(url, data = data, timeout=TIMEOUT_SECONDS)
            _LOGGER.debug(url)
            json_text = resp.text
            if self.is_json(json_text):
                resdata = json.loads(json_text)
            else:
                resdata = resp
            return resdata
        except Exception as e:
            _LOGGER.error("requst url:{url} Error:{err}".format(url=url,err=e))
            return None 
        
    async def _switch(self, action): 
        _LOGGER.debug(self.kind)
        if self.kind == "on_off":
            url = "https://open.ys7.com/api/lapp/device/scene/switch/set"
            
            ctrl = {"accessToken": self.coordinator.data["params"]["accessToken"],
                    "deviceSerial": self._deviceserial,               
                   }
            _LOGGER.debug(action)
            if action == "on":
                ctrl["enable"] = '0'
            elif action == "off":
                ctrl["enable"] = '1'
            else:
                ctrl["enable"]= None
                
        elif self.kind == "soundswitch":
            url = "https://open.ys7.com/api/lapp/camera/video/sound/set"
            
            ctrl = {"accessToken": self.coordinator.data["params"]["accessToken"],
                    "deviceSerial": self._deviceserial,               
                   }
            _LOGGER.debug(action)
            if action == "on":
                ctrl["enable"] = '1'
            elif action == "off":
                ctrl["enable"] = '0'
            else:
                ctrl["enable"]= None
                
        elif self.kind == "defence":
            url = "https://open.ys7.com/api/lapp/device/defence/set"
            
            ctrl = {"accessToken": self.coordinator.data["params"]["accessToken"],
                    "deviceSerial": self._deviceserial,
                   }
            _LOGGER.debug(action)
            if action == "on":
                ctrl["isDefence"] = '1'
                _LOGGER.debug(ctrl)
            elif action == "off":                
                ctrl["isDefence"] = '0'
                _LOGGER.debug(ctrl)
            else:
                ctrl["isDefence"]= None
                _LOGGER.debug(ctrl)  
        else:
        
            actionstr = "1" if action == "on" else "0"            
            url = "https://open.ys7.com/api/deviceconfig/v3/devices/" + self._deviceserial + "/0/" + actionstr + "/" + SWITCH_TYPES[self.kind][3] + "/switchStatus"            
            ctrl = {"accessToken": self.coordinator.data["params"]["accessToken"],
                    "deviceSerial": self._deviceserial,
                   } 
            _LOGGER.debug(ctrl)  
        
        try:
            async with timeout(10): 
                resdata = await self._hass.async_add_executor_job(self.sendHttpPost, url, ctrl)
        except (
            ClientConnectorError
        ) as error:
            raise UpdateFailed(error)
        _LOGGER.debug("Requests remaining: %s, ctrl: %s", url, ctrl)
        _LOGGER.debug(resdata)
  


