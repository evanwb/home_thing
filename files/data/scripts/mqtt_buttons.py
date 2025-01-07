import time
import json

mqtt_username = "mqtt_user"
mqtt_password =  "mqtt_pass"
mqtt_host = "10.6.0.21"
mqtt_port = 1883



device_id = "home_thing_og"

device_name = "Home Thing OG"

device_params = {
                    "identifiers": [
                        device_id
                    ],
                    "name": device_name,
                    "model": "Car Thing",
                    "manufacturer": "Spotify"
                }

entities = [
    {
    "topic": f"homeassistant/sensor/{device_id}/brightness/config",
    "payload": {
            "name": "Display Brightness",
            "state_topic": f"homeassistant/sensor/{device_id}/brightness/state",
            "state_class": "measurement",
            "unit_of_measurement": "%",
            "value_template": "{{ value }}",
            "unique_id": f"{device_id}_brightness",
            "device": device_params,
            "icon": "mdi:brightness-7",
            "platform": "mqtt"
        }
    }, 


    # Buttons
    {
    "topic": f"homeassistant/sensor/{device_id}/b1/config",
    "payload": ({
        "name": "Button 1",
        "state_topic": f"homeassistant/sensor/{device_id}/b1/state",
        "unique_id": f"{device_id}_b1",
        "device": device_params,
        "icon": "mdi:button-pointer",
        "platform": "mqtt"
    })
    }, 

    {
        "topic": f"homeassistant/sensor/{device_id}/b2/config",
        "payload": ({
            "name": "Button 2",
            "state_topic": f"homeassistant/sensor/{device_id}/b2/state",
            "unique_id": f"{device_id}_b2",
            "device": device_params,
            "icon": "mdi:button-pointer",
            "platform": "mqtt"
        })
    },
   
    {
        "topic": f"homeassistant/sensor/{device_id}/b3/config",
        "payload": ({
            "name": "Button 3",
            "state_topic": f"homeassistant/sensor/{device_id}/b3/state",
            "unique_id": f"{device_id}_b3",
            "device": device_params,
            "icon": "mdi:button-pointer",
            "platform": "mqtt"
        })
    },
    {
        "topic": f"homeassistant/sensor/{device_id}/b4/config",
        "payload": ({
            "name": "Button 4",
            "state_topic": f"homeassistant/sensor/{device_id}/b4/state",
            "unique_id": f"{device_id}_b4",
            "device": device_params,
            "icon": "mdi:button-pointer",
            "platform": "mqtt"
        })
    },
    {
        "topic": f"homeassistant/sensor/{device_id}/enter/config",
        "payload": ({
            "name": "Enter Button",
            "state_topic": f"homeassistant/sensor/{device_id}/enter/state",
            "unique_id": f"{device_id}_enter",
            "device": device_params,
            "icon": "mdi:radiobox-marked",
            "platform": "mqtt"
        })
    },
    {
        "topic": f"homeassistant/sensor/{device_id}/knob/config",
        "payload": ({
            "name": "Knob",
            "state_topic": f"homeassistant/sensor/{device_id}/knob/state",
            "unique_id": f"{device_id}_knob",
            "device": device_params,
            "icon": "mdi:knob",
            "platform": "mqtt"
        })
    },


    # Text
    {
    "topic": f"homeassistant/text/{device_id}/current_media/config",
    "payload": ({
        "name": "Current Media Player",
        "command_topic": f"homeassistant/text/{device_id}/current_media/command",
        "state_topic": f"homeassistant/text/{device_id}/current_media/state",
        "unique_id": f"{device_id}_current_media",
        "device": device_params,
        "icon": "mdi:television",
        "platform": "mqtt"
    })
    },
    {
    "topic": f"homeassistant/text/{device_id}/current_light/config",
    "payload": ({
        "name": "Current Light",
        "command_topic": f"homeassistant/text/{device_id}/current_light/command",
        "state_topic": f"homeassistant/text/{device_id}/current_light/state",
        "unique_id": f"{device_id}_current_light",
        "device": device_params,
        "icon": "mdi:lightbulb",
        "platform": "mqtt"
    })
    }
    
]




