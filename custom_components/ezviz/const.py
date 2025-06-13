"""Constants for the ezviz_cn integration."""

DOMAIN = "ezviz"

######### CONF KEY
CONF_APP_KEY = 'appkey'
CONF_APP_SECRET = 'appsecret'
CONF_DEVICE_SERIAL='deviceserial'
CONF_DEVICES = "devices"
CONF_OPTIONS = "options"


ATTR_UPDATE_TIME = "更新时间"
ATTRIBUTION = "C6CN"

COORDINATOR = "coordinator"
CONF_UPDATE_INTERVAL = "update_interval_seconds"
CONF_CAMERA_INTERVAL = "update_camera_seconds"

UNDO_UPDATE_LISTENER = "undo_update_listener"

CONF_BUTTONS = "buttons"
CONF_SWITCHS = "switchs"
CONF_SENSORS = "sensors"
CONF_CAMERAS = "cameras"
CONF_STATE_DETECTION_RULES = "state_detection_rules"

SWITCH_TYPES = {
    'on_off': ['ezviz_onoff', '摄像头开关', 'mdi:toggle-switch'],
    'defence': ['ezviz_defence', '摄像头移动侦测', 'mdi:alarm-light'],
    'soundswitch': ['ezviz_soundswitch', '设备麦克风', 'mdi:microphone'],  
}

BUTTON_TYPES = {
    "stop": {
        "name": "停止",
        "device_class": "restart",
        "icon": "mdi:stop",
        "direc": "",
        "action": "stop",
    },
    "capture": {
        "name": "抓拍",
        "device_class": "restart",
        "icon": "mdi:camera",
        "direc": "",
        "action": "capture",
    },
    "up": {
        "name": "上",
        "device_class": "restart",
        "icon": "mdi:arrow-up-thick",
        "direc": 0,
        "action": "move",
    },
    "down": {
        "name": "下",
        "device_class": "restart",
        "icon": "mdi:arrow-down-thick",
        "direc": 1,
        "action": "move",
    },
    "left": {
        "name": "左",
        "device_class": "restart",
        "icon": "mdi:arrow-left-thick",
        "direc": 2,
        "action": "move",
    },
    "right": {
        "name": "右",
        "device_class": "restart",
        "icon": "mdi:arrow-right-thick",
        "direc": 3,
        "action": "move",
    },
    "upleft": {
        "name": "左上",
        "device_class": "restart",
        "icon": "mdi:arrow-top-left-thick",
        "direc": 4,
        "action": "move",
    },
    "downleft": {
        "name": "左下",
        "device_class": "restart",
        "icon": "mdi:arrow-bottom-left-thick",
        "direc": 5,
        "action": "move",
    },
    "upright": {
        "name": "右上",
        "device_class": "restart",
        "icon": "mdi:mdi:arrow-top-left-thick",
        "direc": 6,
        "action": "move",
    },
    "downright": {
        "name": "右下",
        "device_class": "restart",
        "icon": "mdi:arrow-bottom-right-thick",
        "direc": 7,
        "action": "move",
    },
    "zoombig": {
        "name": "放大",
        "device_class": "restart",
        "icon": "mdi:magnify-plus",
        "direc": 8,
        "action": "move",
    },
    "zoomsmall": {
        "name": "缩小",
        "device_class": "restart",
        "icon": "mdi:magnify-minus",
        "direc": 9,
        "action": "move",
    },
    "zoomnear": {
        "name": "近焦距",
        "device_class": "restart",
        "icon": "mdi:magnify-minus-cursor",
        "direc": 10,
        "action": "move",
    },
    "zoomfar": {
        "name": "远焦距",
        "device_class": "restart",
        "icon": "mdi:magnify-plus-cursor",
        "direc": 11,
        "action": "move",
    },
    "zoomauto": {
        "name": "自动控制",
        "device_class": "restart",
        "icon": "mdi:autorenew",
        "direc": 16,
        "action": "move",
    },
    "vehicleprops": {
        "name": "车牌识别",
        "device_class": "restart",
        "icon": "mdi:car-search",
        "direc": "",
        "action": "vehicleprops",
    },
    "humandetect": {
        "name": "人形检测",
        "device_class": "restart",
        "icon": "mdi:human",
        "direc": "",
        "action": "humandetect",
    },
    "humanbody": {
        "name": "人体属性识别",
        "device_class": "restart",
        "icon": "mdi:human-male-female-child",
        "direc": "",
        "action": "humanbody",
    },
    "facedetect": {
        "name": "人脸检测",
        "device_class": "restart",
        "icon": "mdi:face-agent",
        "direc": "",
        "action": "facedetect",
    },
    "liveget": {
        "name": "获取直播地址(5分钟)",
        "device_class": "restart",
        "icon": "mdi:monitor-eye",
        "direc": "",
        "action": "liveget",
    }    
}



SENSOR_TYPES = {
    "status": {
        "key": "onlinestatus",
        "translation_key": "onlinestatus",
        "entity_registry_enabled_default": "True",
        "icon": "mdi:check-network-outline"
    },
    "offlineNotify": {
        "key": "offlinenotify",
        "translation_key": "offlinenotify",
        "entity_registry_enabled_default": "false",
        "icon": "mdi:message-alert"
    },
    "netAddress": {
        "key": "wan_ip",
        "translation_key": "wan_ip",
        "icon": "mdi:wan"
    },
    "defence": {
        "key": "alarmstatus",
        "translation_key": "alarmstatus",
        "entity_registry_enabled_default": "True",
        "icon": "mdi:alarm-light-outline"
    },    
    "alarmSoundMode": {
        "key": "alarm_sound_mod",
        "translation_key": "alarm_sound_mod",
        "entity_registry_enabled_default": "True",
        "icon": "mdi:surround-sound"
    },    
    # "battery_level": {
        # "key": "battery_level",
        # "native_unit_of_measurement": "PERCENTAGE",
        # "device_class": "battery_level"
    # },
    # "last_alarm_time": {
        # "key": "last_alarm_time",
        # "translation_key": "last_alarm_time",
        # "entity_registry_enabled_default": "false"
    # },
    # "Seconds_Last_Trigger": {
        # "key": "Seconds_Last_Trigger",
        # "translation_key": "seconds_last_trigger",
        # "entity_registry_enabled_default": "false"
    # },
    # "last_alarm_pic": {
        # "key": "last_alarm_pic",
        # "translation_key": "last_alarm_pic",
        # "entity_registry_enabled_default": "false"
    # },
    # "supported_channels": {
        # "key": "supported_channels",
        # "translation_key": "supported_channels"
    # },
    # "local_ip": {
        # "key": "local_ip",
        # "translation_key": "local_ip"
    # },    
    # "PIR_Status": {
        # "key": "PIR_Status",
        # "translation_key": "pir_status"
    # },
    # "last_alarm_type_code": {
        # "key": "last_alarm_type_code",
        # "translation_key": "last_alarm_type_code"
    # },
    # "last_alarm_type_name": {
        # "key": "last_alarm_type_name",
        # "translation_key": "last_alarm_type_name"
    # }
}


ALARMSOUNDMODE = ["短叫", "长叫","静音"]
DEFENCE = ["撤防", "布防"]
ON_OFF = ["启用遮蔽", "关闭遮蔽"]
OFFLINENOTIFY = ["设备下线通知已关闭", "设备下线通知已开启"]
ONLINESTATUS = ["不在线", "在线"]