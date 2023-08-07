"""Config flow for ezviz_cn ac integration."""

from __future__ import annotations

import logging
import requests
import binascii
import socket
import base64
import re
import sys
import time
import asyncio
import voluptuous as vol
from hashlib import md5

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers.selector import SelectSelector, SelectSelectorConfig, SelectSelectorMode
from collections import OrderedDict

from .const import (
    DOMAIN, 
    CONF_APP_KEY,
    CONF_APP_SECRET,
    CONF_DEVICES,
    CONF_DEVICE_SERIAL,
    CONF_OPTIONS,
    CONF_UPDATE_INTERVAL,
    CONF_CAMERA_INTERVAL,
    CONF_SWITCHS,
    CONF_BUTTONS,
    )
from configparser import ConfigParser
try: import simplejson
except ImportError: import json as simplejson

_LOGGER = logging.getLogger(__name__)

@config_entries.HANDLERS.register(DOMAIN)
class FlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """handle config flow for this integration"""
    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return OptionsFlow(config_entry)
        
        
    def __init__(self):
        """Initialize."""
        self._errors = {}
    
    def sendHttpPost(self,url,data):
        try:
            resp = requests.post(url, data = data, timeout=20)
            return resp

        except Exception as e:
            _LOGGER.error("requst url:{url} Error:{err}".format(url=url,err=e))
            return ""

    async def async_step_user(self, user_input={}):
        self._errors = {}
        if user_input is not None:
            config_data = {}
            appkey = user_input[CONF_APP_KEY]
            appsecret = user_input[CONF_APP_SECRET]
            #deviceserial = user_input[CONF_Device_Serial]
            devices = []
            
            self._appkey = appkey
            self._appsecret = appsecret
            # self._deviceserial = deviceserial   
            
            _params = {"accessToken": ""}
            _apikey = {"appKey": self._appkey,
                    "appSecret": self._appsecret
                    }
            _LOGGER.debug(_apikey)
            response = await self.hass.async_add_executor_job(
                self.sendHttpPost, 'https://open.ys7.com/api/lapp/token/get', _apikey
            )
            _LOGGER.debug(response.json())
            if response.json()["code"] == "200":
                _LOGGER.info('Flow Config GET_TOKEN_SUCCESS')
                _token = response.json()['data']['accessToken']
                _params = {"accessToken": _token}
                response = await self.hass.async_add_executor_job(
                    self.sendHttpPost, 'https://open.ys7.com/api/lapp/device/list', _params
                )
                _LOGGER.debug(response.json())
                for deviceSerial in response.json()["data"]:
                    devices.append(deviceSerial["deviceSerial"])
                
            elif response.json()["code"]:
                _LOGGER.error("Error API return, code=%s, msg=%s",response.json()['code'],response.json()['msg'])
                self._errors["base"] = "invalid_auth"
                return await self._show_config_form(user_input)
            else:
                _LOGGER.error("Error API return, code=%s, msg=%s",response.json()['code'],response.json()['msg'])
                self._errors["base"] = "unkown"
                return await self._show_config_form(user_input)

            _LOGGER.debug(
                "ezviz_cn successfully, save data for ezviz_cn: %s, devices: %s",
                appkey,
                devices,
            )
            await self.async_set_unique_id(f"ezviz_cn-{self._appkey}")
            self._abort_if_unique_id_configured()

            config_data[CONF_APP_KEY] = appkey
            config_data[CONF_APP_SECRET] = appsecret
            config_data[CONF_DEVICES] = devices

            return self.async_create_entry(title=f"ezviz_cn-{appkey[0:8]}", data=config_data)

        return await self._show_config_form(user_input)

    async def _show_config_form(self, user_input):

        data_schema = OrderedDict()
        data_schema[vol.Required(CONF_APP_KEY, default = "")] = str
        data_schema[vol.Required(CONF_APP_SECRET, default = "")] = str        

        return self.async_show_form(
            step_id="user", data_schema=vol.Schema(data_schema), errors=self._errors
        )


class OptionsFlow(config_entries.OptionsFlow):
    """Config flow options for autoamap."""

    def __init__(self, config_entry):
        """Initialize autoamap options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        return await self.async_step_user()

    async def async_step_user(self, user_input=None):
        """Handle a flow initialized by the user."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)
        listoptions = []  
        for deviceconfig in self.config_entry.data.get(CONF_DEVICES,[]):
            listoptions.append({"value": deviceconfig, "label": deviceconfig})

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_UPDATE_INTERVAL,
                        default=self.config_entry.options.get(CONF_UPDATE_INTERVAL, 30),
                    ): vol.All(vol.Coerce(int), vol.Range(min=3, max=600)),
                    vol.Optional(
                        CONF_CAMERA_INTERVAL,
                        default=self.config_entry.options.get(CONF_CAMERA_INTERVAL, 120),
                    ): vol.All(vol.Coerce(int), vol.Range(min=3, max=3600)),
                    vol.Optional(
                        CONF_DEVICE_SERIAL, 
                        default=self.config_entry.options.get(CONF_DEVICE_SERIAL,[])): SelectSelector(
                        SelectSelectorConfig(
                            options=listoptions,
                            multiple=True,translation_key=CONF_DEVICE_SERIAL
                            )
                    ),
                    vol.Optional(CONF_SWITCHS, default=self.config_entry.options.get(CONF_SWITCHS,["on_off"])): SelectSelector(
                            SelectSelectorConfig(
                                options=[
                                    {"value": "on_off", "label": "开关(遮蔽)"},                                    
                                    {"value": "soundswitch", "label": "麦克风"},
                                ], 
                                multiple=True,translation_key=CONF_SWITCHS
                            )
                        ),
                }
            ),
        )
