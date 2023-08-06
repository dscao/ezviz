"""Ezviz Entities"""
import logging
import time
import datetime
import json
import requests
from async_timeout import timeout
from aiohttp.client_exceptions import ClientConnectorError

from homeassistant.components.button import ButtonEntity

from .const import (
    COORDINATOR, 
    DOMAIN, 
    UNDO_UPDATE_LISTENER,
    CONF_STATE_DETECTION_RULES,
    CONF_SWITCHS,
    CONF_BUTTONS,
    BUTTON_TYPES,
)

TIMEOUT_SECONDS=10
_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Add entities from a config_entry."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]
    _LOGGER.debug(coordinator.data)   
    buttons = []
    
    if coordinator.data.get("devicelistinfo"):
        devices = coordinator.data.get("devicelistinfo")
        evzizcameras = coordinator.data.get("cameralistinfo")
        _LOGGER.debug(devices)
        _LOGGER.debug(evzizcameras)
        if isinstance(devices, list):
            for device in devices:
                for devicechannel in evzizcameras:
                    if devicechannel["deviceSerial"] == device["deviceSerial"] and devicechannel["permission"] == -1:
                    
                        buttontypes = {}
                        if coordinator.data[device["deviceSerial"]+"-capacity"].get("support_ptz") == '1':
                            buttontypes["stop"] = BUTTON_TYPES["stop"]
                            buttontypes["up"] = BUTTON_TYPES["up"]
                            buttontypes["down"] = BUTTON_TYPES["down"]
                            buttontypes["left"] = BUTTON_TYPES["left"]
                            buttontypes["right"] = BUTTON_TYPES["right"]
                            buttontypes["upleft"] = BUTTON_TYPES["upleft"]
                            buttontypes["downleft"] = BUTTON_TYPES["downleft"]
                            buttontypes["upright"] = BUTTON_TYPES["upright"]
                            buttontypes["downright"] = BUTTON_TYPES["downright"]
                        if coordinator.data[device["deviceSerial"]+"-capacity"].get("ptz_45",'0' ) == '0':
                            buttontypes["upleft"] = None
                            buttontypes["downleft"] = None
                            buttontypes["upright"] = None
                            buttontypes["downright"] = None
                        if coordinator.data[device["deviceSerial"]+"-capacity"].get("ptz_top_bottom",'0') == '0':
                            buttontypes["up"] = None
                            buttontypes["down"] = None
                        if coordinator.data[device["deviceSerial"]+"-capacity"].get("ptz_left_right",'0') =='0':
                            buttontypes["left"] = None
                            buttontypes["right"] = None
                        if coordinator.data[device["deviceSerial"]+"-capacity"].get("ptz_zoom") =='1':
                            buttontypes["zoombig"] = BUTTON_TYPES["zoombig"]
                            buttontypes["zoomsmall"] = BUTTON_TYPES["zoomsmall"]
                        if coordinator.data[device["deviceSerial"]+"-capacity"].get("support_capture") =='1':
                            buttontypes["capture"] = BUTTON_TYPES["capture"]
                            buttontypes["vehicleprops"] = BUTTON_TYPES["vehicleprops"]
                            buttontypes["humandetect"] = BUTTON_TYPES["humandetect"]
                            buttontypes["humanbody"] = BUTTON_TYPES["humanbody"]
                            buttontypes["facedetect"] = BUTTON_TYPES["facedetect"]
                        buttontypes["liveget"] = BUTTON_TYPES["liveget"]


                        buttontypes = {key: value for key, value in buttontypes.items() if value is not None}        
                        for button in buttontypes:
                            buttons.append(EzvizButton(hass, button, coordinator, device["deviceSerial"], devicechannel["channelNo"]))

            async_add_entities(buttons, False)


class EzvizButton(ButtonEntity):
    """Define an entity."""
    _attr_has_entity_name = True
    def __init__(self, hass, kind, coordinator, deviceserial, channelno):
        """Initialize."""
        super().__init__()
        self.kind = kind
        self.coordinator = coordinator
        self._deviceserial = deviceserial
        self._channelno = channelno
        self._state = None
        self._devicename = None
        self._deviceType = None
        self._deviceVersion = None
        self._attr_icon = BUTTON_TYPES[self.kind]["icon"]
        _LOGGER.debug(self.kind)
        for buttondata in self.coordinator.data["devicelistinfo"]:
            if buttondata["deviceSerial"] == self._deviceserial:
                self._devicename = buttondata["deviceName"]
                self._deviceType = buttondata["deviceType"]
                self._deviceVersion = buttondata["deviceVersion"]

                
        self._attr_device_info = {
            "identifiers": {(DOMAIN, self._deviceserial)},
            "name": self._devicename,
            "manufacturer": "Ezviz",
            "model": self._deviceType,
            "sw_version": self._deviceVersion,
        }
        self._attr_device_class = "restart"
        self._attr_entity_registry_enabled_default = True
        self._hass = hass
        self._name = str(self._channelno) + "_" + BUTTON_TYPES[self.kind]['name']
        self._attr_translation_key = self.kind
        self._capture_pic = None
        self._vehicleprops_data = None
        self._humandetect_data = None
        self._humanbody_data = None
        self._facedetect_data = None        
        self._liveget_data = None

    @property
    def name(self):
        """Return the name."""
        return f"{self._name}"

    @property
    def unique_id(self):
        return f"{DOMAIN}_button_{self.kind}_{self._deviceserial}_{self._channelno}"
        
    @property
    def should_poll(self):
        """Return the polling requirement of the entity."""
        return True

    @property
    def state(self):
        """Return the state."""
        return self._state

        
    @property
    def device_class(self):
        """Return the unit_of_measurement."""
        if BUTTON_TYPES[self.kind].get("device_class"):
            return BUTTON_TYPES[self.kind]["device_class"]
    
    @property
    def extra_state_attributes(self):
        """Return device state attributes."""
        attrs = {}
        if self.kind == "capture":
            attrs["capture_pic"] = self._capture_pic
            attrs["querytime"] = self.coordinator.data["updatetime"]
        if self.kind == "vehicleprops":
            attrs["vehicleprops"] = self._vehicleprops_data
            attrs["capture_pic"] = self._capture_pic
            attrs["querytime"] = self.coordinator.data["updatetime"]
        if self.kind == "humandetect":
            attrs["humandetect"] = self._humandetect_data
            attrs["capture_pic"] = self._capture_pic
            attrs["querytime"] = self.coordinator.data["updatetime"] 
        if self.kind == "humanbody":
            attrs["humanbody"] = self._humanbody_data
            attrs["capture_pic"] = self._capture_pic
            attrs["querytime"] = self.coordinator.data["updatetime"]
        if self.kind == "facedetect":
            attrs["facedetect"] = self._facedetect_data
            attrs["capture_pic"] = self._capture_pic
            attrs["querytime"] = self.coordinator.data["updatetime"]
        if self.kind == "liveget":
            attrs["liveaddress"] = self._liveget_data
            attrs["querytime"] = self.coordinator.data["updatetime"] 
        return attrs
        
        
    def press(self) -> None:
        """Handle the button press."""

    async def async_press(self) -> None:
        """Handle the button press."""        
        await self._button(BUTTON_TYPES[self.kind]["action"],BUTTON_TYPES[self.kind]["direc"])
        

    async def async_added_to_hass(self):
        """Connect to dispatcher listening for entity data notifications."""
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )

    async def async_update(self):
        """Update entity."""
        #await self.coordinator.async_request_refresh()
        
        
    def is_json(self, jsonstr):
        try:
            json.loads(jsonstr)
        except ValueError:
            return False
        return True

    def sendHttpPost(self, url, header, data):
        try:            
            resp = requests.post(url, headers=header, data = data, timeout=TIMEOUT_SECONDS)
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
        
    async def _button(self, action, direc): 
        
        if action == "move":
            await self._move(direc)
            await self._stop()
                
        elif action == "stop":
            await self._stop()
            
        elif action == "capture":
            self._capture_pic = await self._capture()
            
        elif action == "vehicleprops":
            self._capture_pic = await self._capture()
            self._vehicleprops_data = await self._vehicleprops(self._capture_pic)
            
        elif action == "humandetect":            
            self._capture_pic = await self._capture()
            self._humandetect_data = await self._humandetect(self._capture_pic)
            
        elif action == "humanbody":
            self._capture_pic = await self._capture()
            self._humanbody_data = await self._humanbody(self._capture_pic)
            
        elif action == "facedetect":
            self._capture_pic = await self._capture()
            self._facedetect_data = await self._facedetect(self._capture_pic)
            
        elif action == "liveget":
            self._liveget_data = await self._liveget()
            
            
        
        
    async def _move(self, direc): 
        url = "https://open.ys7.com/api/lapp/device/ptz/start"
        ctrl = {"accessToken": self.coordinator.data["params"]["accessToken"],
            "deviceSerial": self._deviceserial, 
            "channelNo": self._channelno,
            "direction": direc,
            "speed": '1'
           }
        try:
            async with timeout(10): 
                resdata = await self._hass.async_add_executor_job(self.sendHttpPost, url, {}, ctrl)
        except (
            ClientConnectorError
        ) as error:
            raise UpdateFailed(error)
        
    async def _stop(self): 
        url = "https://open.ys7.com/api/lapp/device/ptz/stop"            
        ctrl = {"accessToken": self.coordinator.data["params"]["accessToken"],
                "deviceSerial": self._deviceserial, 
                "channelNo": self._channelno,
               }
        try:
            async with timeout(10): 
                resdata = await self._hass.async_add_executor_job(self.sendHttpPost, url, {}, ctrl)
        except (
            ClientConnectorError
        ) as error:
            raise UpdateFailed(error)
        
    async def _capture(self): 
        url = "https://open.ys7.com/api/lapp/device/capture"            
        ctrl = {"accessToken": self.coordinator.data["params"]["accessToken"],
                "deviceSerial": self._deviceserial,
                "channelNo": self._channelno,
               }
        try:
            async with timeout(10): 
                resdata = await self._hass.async_add_executor_job(self.sendHttpPost, url, {}, ctrl)
                return resdata["data"].get("picUrl")
        except (
            ClientConnectorError
        ) as error:
            raise UpdateFailed(error)
        
    async def _vehicleprops(self, picurl): 
        url = "https://open.ys7.com/api/lapp/intelligence/vehicle/analysis/props"
        ctrl = {"accessToken": self.coordinator.data["params"]["accessToken"],
                "dataType": 0,
                "image": picurl,
               }
        try:
            async with timeout(10):
                _LOGGER.debug("Requests remaining: %s", url)
                resdata = await self._hass.async_add_executor_job(self.sendHttpPost, url, {'Content-Type': 'application/x-www-form-urlencoded', 'Host': 'open.ys7.com'}, ctrl)
                #for vehicle in resdata["data"]:
                #    vehiclestr += vehicle["plateNumber"] + "("+ vehicle["vehicleModel"] +") | "
                _LOGGER.debug(resdata)
                return resdata
        except (
            ClientConnectorError
        ) as error:
            raise UpdateFailed(error)

        
    async def _humandetect(self, picurl): 
        url = "https://open.ys7.com/api/lapp/intelligence/human/analysis/detect"
        ctrl = {"accessToken": self.coordinator.data["params"]["accessToken"],
                "dataType": 0,
                "image": picurl,
                "operation": "number",
               }
        _LOGGER.debug(ctrl)
        try:
            async with timeout(10): 
                _LOGGER.debug("Requests remaining: %s", url)
                resdata = await self._hass.async_add_executor_job(self.sendHttpPost, url, {'Content-Type': 'application/x-www-form-urlencoded', 'Host': 'open.ys7.com'}, ctrl)
                _LOGGER.debug(resdata)
                return resdata
        except (
            ClientConnectorError
        ) as error:
            raise UpdateFailed(error)
        

        
    async def _humanbody(self, picurl): 
        url = "https://open.ys7.com/api/lapp/intelligence/human/analysis/body"
        ctrl = {"accessToken": self.coordinator.data["params"]["accessToken"],
                "dataType": 0,
                "image": picurl,
               }
        try:
            async with timeout(10):
                _LOGGER.debug("Requests remaining: %s", url)            
                resdata = await self._hass.async_add_executor_job(self.sendHttpPost, url, {'Content-Type': 'application/x-www-form-urlencoded', 'Host': 'open.ys7.com'}, ctrl)
                _LOGGER.debug(resdata)
                return resdata
        except (
            ClientConnectorError
        ) as error:
            raise UpdateFailed(error)
            
    async def _facedetect(self, picurl): 
        url = "https://open.ys7.com/api/lapp/intelligence/face/analysis/detect"
        ctrl = {"accessToken": self.coordinator.data["params"]["accessToken"],
                "dataType": 0,
                "image": picurl,
               }
        try:
            async with timeout(10):
                _LOGGER.debug("Requests remaining: %s", url)            
                resdata = await self._hass.async_add_executor_job(self.sendHttpPost, url, {'Content-Type': 'application/x-www-form-urlencoded', 'Host': 'open.ys7.com'}, ctrl)
                _LOGGER.debug(resdata)
                return resdata
        except (
            ClientConnectorError
        ) as error:
            raise UpdateFailed(error)
            
    async def _liveget(self): 
        url = "https://open.ys7.com/api/lapp/v2/live/address/get"
        ctrl = {"accessToken": self.coordinator.data["params"]["accessToken"],
                "deviceSerial": self._deviceserial,
                "channelNo": self._channelno,
                "protocol": '3',
                "expireTime": '300'
               }
        try:
            async with timeout(10):
                _LOGGER.debug("Requests remaining: %s", url)            
                resdata = await self._hass.async_add_executor_job(self.sendHttpPost, url, {'Content-Type': 'application/x-www-form-urlencoded', 'Host': 'open.ys7.com'}, ctrl)
                _LOGGER.debug(resdata)
                return resdata["data"]["url"]
        except (
            ClientConnectorError
        ) as error:
            raise UpdateFailed(error)
            