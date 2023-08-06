"""Ezviz Entities"""
import logging
import time
import datetime
import json
import requests
from async_timeout import timeout
from aiohttp.client_exceptions import ClientConnectorError

from homeassistant.components.camera import Camera
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
    cameras = []
    if coordinator.data.get("devicelistinfo"):
        devices = coordinator.data.get("devicelistinfo")
        evzizcameras = coordinator.data.get("cameralistinfo")
        _LOGGER.debug(evzizcameras)   
        if isinstance(devices, list):
            for device in devices:
                for devicechannel in evzizcameras:
                    if devicechannel["deviceSerial"] == device["deviceSerial"] and devicechannel["permission"] == -1:
                        if coordinator.data.get(device["deviceSerial"])["model"].startswith("CS-DP"):
                            cameratype = "montion"
                        else:
                            cameratype = "capture"
                        cameras.append(EzvizCamera(hass, coordinator, device["deviceSerial"], devicechannel["channelNo"], cameratype))
            async_add_entities(cameras, False)
    
           
    platform = entity_platform.async_get_current_platform()        
    platform.async_register_entity_service(
        "capture",
        {},
        "_capture",
        #supports_response=SupportsResponse.ONLY,
    )
    platform.async_register_entity_service(
        "humandetect",
        {
            vol.Required("picurl"): cv.string,
            vol.Optional("operation"): cv.string,
        },
        "_humandetect",
        #supports_response=SupportsResponse.ONLY,
    )
    


class EzvizCamera(Camera):
    """The representation of a Demo camera."""
    _attr_has_entity_name = True
    def __init__(self, hass, coordinator, deviceserial, channelno, cameratype):
        """Initialize ezviz camera component."""
        super().__init__()
        self.coordinator = coordinator
        self._deviceserial = deviceserial
        self._channelno = channelno
        self._cameratype = cameratype
        
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
        self._attr_device_class = "camera"
        self._attr_entity_registry_enabled_default = True
        self._hass = hass
        self._name = str(self._channelno) + "_" + self._cameratype
        self._attr_translation_key = self._cameratype
        
        self._listcamera = self.coordinator.data.get(self._deviceserial)
        
        self._capture_pic = None
        self._motion_status = False

        self._is_streaming = None
        self._is_video_history_enabled = False

        # Default to non-NestAware subscribed, but will be fixed during update
        self._time_between_snapshots = datetime.timedelta(seconds=30)
        self._last_image = None
        self._next_snapshot_at = None
        self._attr_unique_id = f"{DOMAIN}_{self._cameratype}_{self._deviceserial}_{self._channelno}"
        
        # 获取时间戳13位毫秒
        self._days = 3 #3天内的数据
        now = datetime.datetime.now()
        date = now + datetime.timedelta(days=0 - self._days)
        self._startTime = int(round(date.timestamp() * 1000))

        # 获取告警消息状态：2-所有，1-已读，0-未读
        self._status = 2



    def get_device_capture(self):
        url = "https://open.ys7.com/api/lapp/device/capture"            
        ctrl = {"accessToken": self.coordinator.data["params"]["accessToken"],
                "deviceSerial": self._deviceserial,
                "channelNo": self._channelno,
               }
        try:
            #async with timeout(10): 
            #    resdata = await self._hass.async_add_executor_job(self.sendHttpPost, url, ctrl)
            resdata = self.sendHttpPost(url, ctrl)
            self._capture_pic = resdata["data"].get("picUrl")
            _LOGGER.debug(self._capture_pic)
            return self._capture_pic
        except (
            ClientConnectorError
        ) as error:
            raise UpdateFailed(error)
        _LOGGER.debug("Requests remaining: %s", url)
        _LOGGER.debug(resdata)

    def get_device_message(self):
        url = "https://open.ys7.com/api/lapp/alarm/device/list"            
        ctrl = {"accessToken": self.coordinator.data["params"]["accessToken"],
                "deviceSerial": self._deviceserial,
                "startTime": self._startTime,
                "status": self._status
               }
        try:
            #async with timeout(10): 
                #resdata = await self._hass.async_add_executor_job(self.sendHttpPost, url, ctrl)
            resdata = self.sendHttpPost(url, ctrl)
            _LOGGER.debug(resdata)
            if len(resdata['data']) > 0:
                #_LOGGER.debug(resdata)
                alarmType = resdata['data'][0]['alarmType']
                alarmTime = resdata['data'][0]['alarmTime']
                alarmPicUrl = resdata['data'][0]['alarmPicUrl']
                strtime = datetime.datetime.fromtimestamp(alarmTime/1000)
                _LOGGER.debug(alarmPicUrl)
                return alarmPicUrl
        except (
            ClientConnectorError
        ) as error:
            raise UpdateFailed(error)
            return 'error'
        _LOGGER.debug("Requests remaining: %s", url)
        _LOGGER.debug(resdata)


    def _ready_for_snapshot(self, now):
        return (self._next_snapshot_at is None or
                now > self._next_snapshot_at)

    def camera_image(
              self, width: int , height: int
    ):
        """Return a faked still image response."""
        #_LOGGER.debug("camera_image")
        now = datetime.datetime.utcnow()  # dt_util.utcnow()
        if self._ready_for_snapshot(now):
            if self._cameratype == 'motion':
                _LOGGER.debug("is MaoYan")
                _LOGGER.debug(self._deviceserial)
                image_path = self.get_device_message()
            elif self._cameratype == 'capture' :
                _LOGGER.debug("not MaoYan")
                _LOGGER.debug(self._deviceserial)
                image_path = self.get_device_capture()
            #_LOGGER.debug("Get camera image: %s" % image_path)
            #_LOGGER.debug("Config: %s" % self._isMaoyan)
            _LOGGER.debug(image_path)
            if image_path == 'error':
                return None

            try:
                response = requests.get(image_path)
            except requests.exceptions.RequestException as error:
                _LOGGER.error("Error getting camera image: %s", error)
                _LOGGER.debug(image_path)
                return None

            self._next_snapshot_at = now + self._time_between_snapshots
            self._last_image = response.content

        return self._last_image

    @property
    def name(self):
        """Return the name of this camera."""
        return self._name

    @property
    def should_poll(self):
        """Camera should poll periodically."""
        return True
       
    async def async_added_to_hass(self):
        """Connect to dispatcher listening for entity data notifications."""
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )

    async def async_update(self):
        """Update entity."""
        await self.coordinator.async_request_refresh()
        
        
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

    async def _capture(self) -> None: #ServiceResponse:
        """Render an image with dall-e."""
        url = "https://open.ys7.com/api/lapp/device/capture"            
        ctrl = {"accessToken": self.coordinator.data["params"]["accessToken"],
                "deviceSerial": self._deviceserial,
                "channelNo": self._channelno,
               }
        return
        try:
            async with timeout(10): 
                response = await self._hass.async_add_executor_job(self.sendHttpPost, url, {}, ctrl)
                _LOGGER.debug(response)
        except (
            ClientConnectorError
        ) as error:
            raise HomeAssistantError(f"Error capture image: {err}") from err
        return response["data"].get("picUrl")
        
        
    async def _vehicleprops(self, picurl): 
        url = "https://open.ys7.com/api/lapp/intelligence/vehicle/analysis/props"
        ctrl = {"accessToken": self.coordinator.data["params"]["accessToken"],
                "dataType": 0,
                "image": picurl,
               }
        try:
            async with timeout(10):
                _LOGGER.debug("Requests remaining: %s", url)
                response = await self._hass.async_add_executor_job(self.sendHttpPost, url, {'Content-Type': 'application/x-www-form-urlencoded', 'Host': 'open.ys7.com'}, ctrl)
                #for vehicle in response["data"]:
                #    vehiclestr += vehicle["plateNumber"] + "("+ vehicle["vehicleModel"] +") | "
                _LOGGER.debug(response)
                return response
        except (
            ClientConnectorError
        ) as error:
            raise UpdateFailed(error)

        
    async def _humandetect(self, picurl, operation): 
        url = "https://open.ys7.com/api/lapp/intelligence/human/analysis/detect"
        ctrl = {"accessToken": self.coordinator.data["params"]["accessToken"],
                "dataType": 0,
                "image": picurl,
                "operation": operation,
               }
        _LOGGER.debug(ctrl)
        try:
            async with timeout(10): 
                _LOGGER.debug("Requests remaining: %s", url)
                response = await self._hass.async_add_executor_job(self.sendHttpPost, url, {'Content-Type': 'application/x-www-form-urlencoded', 'Host': 'open.ys7.com'}, ctrl)
                _LOGGER.debug(response)
                return response
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
                response = await self._hass.async_add_executor_job(self.sendHttpPost, url, {'Content-Type': 'application/x-www-form-urlencoded', 'Host': 'open.ys7.com'}, ctrl)
                _LOGGER.debug(response)
                return response
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
                response = await self._hass.async_add_executor_job(self.sendHttpPost, url, {'Content-Type': 'application/x-www-form-urlencoded', 'Host': 'open.ys7.com'}, ctrl)
                _LOGGER.debug(response)
                return response
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
                response = await self._hass.async_add_executor_job(self.sendHttpPost, url, {'Content-Type': 'application/x-www-form-urlencoded', 'Host': 'open.ys7.com'}, ctrl)
                _LOGGER.debug(response)
                return response["data"]["url"]
        except (
            ClientConnectorError
        ) as error:
            raise UpdateFailed(error)