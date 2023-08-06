"""gree integration."""
from __future__ import annotations
from async_timeout import timeout
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, Config
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
import json
import time
from urllib import request, parse
import logging
from datetime import timedelta
import voluptuous as vol
import requests
import asyncio

from .const import (
    DOMAIN,
    CONF_APP_KEY,
    CONF_APP_SECRET,
    CONF_DEVICES,
    CONF_DEVICE_SERIAL,
    CONF_OPTIONS,
    CONF_UPDATE_INTERVAL,
    COORDINATOR,
    UNDO_UPDATE_LISTENER,
    CONF_STATE_DETECTION_RULES,
    CONF_SWITCHS,
    CONF_BUTTONS, 
)
from homeassistant.exceptions import ConfigEntryNotReady

_LOGGER = logging.getLogger(__name__)

TIMEOUT_SECONDS=10

PLATFORMS: list[Platform] = [Platform.BUTTON, Platform.SWITCH, Platform.SENSOR, Platform.CAMERA]


async def async_setup(hass: HomeAssistant, config: Config) -> bool:
    """Set up configured wukongtv."""
    hass.data.setdefault(DOMAIN, {})    
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:

    appkey = entry.data[CONF_APP_KEY]
    appsecret = entry.data[CONF_APP_SECRET]
    devices = entry.data[CONF_DEVICES]
    
    update_interval_seconds = entry.options.get(CONF_UPDATE_INTERVAL, 10)    
    deviceserial = entry.options.get(CONF_DEVICE_SERIAL,[])
    
    _LOGGER.debug(devices)
    _LOGGER.debug(deviceserial)

    coordinator = DataUpdateCoordinator(hass, appkey, appsecret, devices, deviceserial, update_interval_seconds)
    
    await coordinator.async_refresh()

    if not coordinator.last_update_success:
        raise ConfigEntryNotReady

    undo_listener = entry.add_update_listener(update_listener)

    hass.data[DOMAIN][entry.entry_id] = {
        COORDINATOR: coordinator,
        UNDO_UPDATE_LISTENER: undo_listener,
    }

    for component in PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(entry, component)
        )
           
    return True

async def async_unload_entry(hass, entry):
    """Unload a config entry."""
    unload_ok = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(entry, component)
                for component in PLATFORMS
            ]
        )
    )

    hass.data[DOMAIN][entry.entry_id][UNDO_UPDATE_LISTENER]()

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
    

async def update_listener(hass, entry):
    """Update listener."""
    await hass.config_entries.async_reload(entry.entry_id)


class DataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data."""

    def __init__(self, hass, appkey, appsecret, devices, deviceserial, update_interval_seconds):
        """Initialize."""
        update_interval = timedelta(seconds=update_interval_seconds)

        _LOGGER.debug("Data will be update every %s", update_interval)
        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=update_interval)
        self._name = appkey[0:8]
        self._appkey = appkey
        self._appsecret = appsecret
        self._devices = devices
        self._deviceserial = deviceserial
        self._hass = hass        
        self._data = {}
        self.times = 0
        self._expiretime = 0
        self._params = {"accessToken": ""}
        self._apikey = {"appKey": self._appkey,
            "appSecret": self._appsecret
            }        
        self._data[self._deviceserial] = {}
        self._data["devicelistinfo"] = None
        self._data["cameralistinfo"] = None
        self._data[self._deviceserial+"-capacity"] = None

    def is_json(self, jsonstr):
        try:
            json.loads(jsonstr)
        except ValueError:
            return False
        return True
        
    def sendHttpRequest(self, url):
        try:            
            resp = requests.get(url,timeout=TIMEOUT_SECONDS)
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
            
    async def GetToken(self):
        response = await self._hass.async_add_executor_job(self.sendHttpPost,'https://open.ys7.com/api/lapp/token/get', self._apikey)
        #_LOGGER.debug(response)
        if response["code"] == '200':
            _LOGGER.info('GET_TOKEN_SUCCESS')
            _token = response['data']['accessToken']
            self._params["accessToken"] = _token
            self._expiretime = int(response['data']['expireTime'])
            self._data["params"] = self._params
        else:
            _LOGGER.error("Error API return in GetToken, code=%s, msg=%s",response['code'],response['msg'])
        
    async def GetDeviceListInfo(self):
        #_LOGGER.debug("getDeviceListinfo:"+self._appkey)
        response = await self._hass.async_add_executor_job(self.sendHttpPost,'https://open.ys7.com/api/lapp/device/list', {"accessToken": self._params["accessToken"]})
        _LOGGER.debug(response)
        if response["code"] == '200':
            self._data["devicelistinfo"] = response["data"]
        else:
            _LOGGER.error("Error API return in getDeviceListinfo, code=%s, msg=%s",response['code'],response['msg'])
            
    async def GetCameraListInfo(self):
        #_LOGGER.debug("getDeviceListinfo:"+self._appkey)
        response = await self._hass.async_add_executor_job(self.sendHttpPost,'https://open.ys7.com/api/lapp/camera/list', {"accessToken": self._params["accessToken"]})
        _LOGGER.debug(response)
        if response["code"] == '200':
            self._data["cameralistinfo"] = response["data"]
        else:
            _LOGGER.error("Error API return in getDeviceListinfo, code=%s, msg=%s",response['code'],response['msg'])
    
    async def GetDeviceCapacity(self, deviceserial):
        #_LOGGER.debug("GetDeviceCapacity: s%",deviceserial)
        self._params["deviceSerial"] = deviceserial
        response = await self._hass.async_add_executor_job(self.sendHttpPost,'https://open.ys7.com/api/lapp/device/capacity', self._params)
        if response["code"] == '200':
            self._data[deviceserial+"-capacity"] = response["data"]
        else:
            _LOGGER.error("Error API return in GetDeviceCapacity, code=%s, msg=%s",response['code'],response['msg'])
            
    async def GetDeviceInfo(self, deviceserial):
        #_LOGGER.debug("getDeviceinfo: s%",deviceserial)
        self._params["deviceSerial"] = deviceserial
        response = await self._hass.async_add_executor_job(self.sendHttpPost,'https://open.ys7.com/api/lapp/device/info', self._params)
        if response["code"] == '200':
            self._data[deviceserial] = response["data"]
        else:
            _LOGGER.error("Error API return in getDeviceinfo, code=%s, msg=%s",response['code'],response['msg'])
            
    async def GetDeviceSwitch(self, deviceserial):
        #_LOGGER.debug("GetDeviceSwitch: s%",deviceserial)
        self._params["deviceSerial"] = deviceserial
        response = await self._hass.async_add_executor_job(self.sendHttpRequest,"https://open.ys7.com/api/deviceconfig/v3/devices/" +
                                  self._deviceserial + "/switch/status/list?accessToken=" + self._params["accessToken"])
        _LOGGER.debug(response)
        if response["meta"]["code"] == 200:
            self._data[deviceserial]["switch"] = response["switchInfos"]
        else:
            _LOGGER.error("Error API return in GetDeviceSwitch, code=%s, msg=%s",response["meta"]["code"],response["meta"]['message'])            
            
    async def GetDeviceonoff(self, deviceserial):
        #_LOGGER.debug("GetDeviceonoff: s%",deviceserial)
        self._params["deviceSerial"] = deviceserial
        response = await self._hass.async_add_executor_job(self.sendHttpPost,'https://open.ys7.com/api/lapp/device/scene/switch/status', self._params)
        if response["code"] == '200':
            self._data[deviceserial]["on_off"] = 1 if response["data"]["enable"]==0 else 0
        else:
            _LOGGER.error("Error API return in GetDeviceonoff, code=%s, msg=%s",response['code'],response['msg'])
            
    async def GetDeviceSoundswitch(self, deviceserial):
        #_LOGGER.debug("GetDeviceonoff: s%",deviceserial)
        self._params["deviceSerial"] = deviceserial
        response = await self._hass.async_add_executor_job(self.sendHttpPost,'https://open.ys7.com/api/lapp/camera/video/sound/status', self._params)
        if response["code"] == '200':
            _LOGGER.debug(response["data"])
            self._data[deviceserial]["soundswitch"] = 1 if response["data"]["enable"]==1 else 0
        else:
            _LOGGER.error("Error API return in GetDeviceonoff, code=%s, msg=%s",response['code'],response['msg'])

    async def _async_update_data(self):
        """Update data via DataFetcher."""
        if self._expiretime < time.time()*1000 + 10*60*1000 : #提前10分钟更新token，防止switch操作时可能出现过期情况。
            tasks = [            
                asyncio.create_task(self.GetToken()),
            ]
            await asyncio.gather(*tasks)
        
        #if self._data.get("devicelistinfo")==None:
        tasks = [            
            asyncio.create_task(self.GetDeviceListInfo()),
        ]
        await asyncio.gather(*tasks)
        if self._data.get("cameralistinfo")==None:
            tasks = [            
                asyncio.create_task(self.GetCameraListInfo()),
            ]
            await asyncio.gather(*tasks)
            
        for switchdata in self._data["devicelistinfo"]:
            if self._data.get(switchdata["deviceSerial"]+"-capacity")==None:
                tasks = [            
                    asyncio.create_task(self.GetDeviceCapacity(switchdata["deviceSerial"])),
                ]
                await asyncio.gather(*tasks)
            tasks = [            
                asyncio.create_task(self.GetDeviceInfo(switchdata["deviceSerial"])), 
            ]
            await asyncio.gather(*tasks)
            tasks = [            
                asyncio.create_task(self.GetDeviceonoff(switchdata["deviceSerial"])),
            ]
            await asyncio.gather(*tasks)
            tasks = [            
                asyncio.create_task(self.GetDeviceSoundswitch(switchdata["deviceSerial"])),
            ]
            await asyncio.gather(*tasks)
            tasks = [            
                asyncio.create_task(self.GetDeviceSwitch(switchdata["deviceSerial"])),
            ]
            await asyncio.gather(*tasks)
            
        self._data["updatetime"] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())    
        _LOGGER.debug(self._data)
        return self._data
        