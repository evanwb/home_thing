"""
Settings for /scripts/buttons_app.py
"""
# pylint: disable=line-too-long

# Home Assistant address, including port
HA_SERVER = 'http://10.6.0.21:8123'

# long-lived token, https://www.home-assistant.io/docs/authentication/#your-account-profile
HA_TOKEN = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiIxZWQwNDNhODYzZDY0MzUzOGIwZGFjMDhlMjk0NmMxZCIsImlhdCI6MTczNTc4MDc5MywiZXhwIjoyMDUxMTQwNzkzfQ.Shz2qcC91D3eiYNVtPmAB8Wyi8km6_FnUewqzRV0RZ4'

# when you turn the knob, brightness will go up or down by this amount
#   brightness is 0 - 255
LEVEL_INCREMENT = 64


# assign a scene/automation/script to the button next to the knob, aka ESC
ESC_SCENE = 'scene.office_bright'

BUTTON1 = "light.floor_lamp" , "light.bedroom_lights" #"light.monitor_lights"
BUTTON2 = "light.bed_lights", None
BUTTON3 = "light.monitor_lights", None
BUTTON4 = "switch.outlet", "switch.rig_3"
BUTTON5 = "input_button.test", None
BUTTON_ESC = "light.bedroom_lights", "toggle"