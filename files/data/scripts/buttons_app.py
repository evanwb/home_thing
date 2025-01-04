"""
Buttons monitoring, to integrate with Home Assistant
"""
# pylint: disable=global-statement,line-too-long,broad-exception-caught,logging-fstring-interpolation

# https://stackoverflow.com/questions/5060710/format-of-dev-input-event
# https://homeassistantapi.readthedocs.io/en/latest/usage.html
# https://homeassistantapi.readthedocs.io/en/latest/api.html#homeassistant_api.Client
# https://github.com/maximehk/ha_lights/blob/main/ha_lights/ha_lights.py


import subprocess
import time
import struct
import contextlib
import warnings
import logging
import os

from threading import Thread
from threading import Event as ThreadEvent

import requests
import urllib3
from urllib3.exceptions import InsecureRequestWarning

from homeassistant_api import Client, State

# user-configurable settings are all in button_settings.py
from buttons_settings import LEVEL_INCREMENT
from buttons_settings import HA_SERVER, HA_TOKEN
from buttons_settings import BUTTON1, BUTTON2, BUTTON3, BUTTON4, BUTTON5, BUTTON_ESC

# All the device buttons are part of event0, which appears as a keyboard
# 	buttons along the edge are: 1, 2, 3, 4, m
# 	next to the knob: ESC
#	knob click: Enter
# Turning the knob is a separate device, event1, which also appears as a keyboard
#	turning the knob corresponds to the left and right arrow keys

DEV_BUTTONS = '/dev/input/event0'
DEV_KNOB = '/dev/input/event1'

BACKLIGHT = "/sys/devices/platform/backlight/backlight/aml-bl/brightness"
BRIGHTNESS = 100


# for event0, these are the keycodes for buttons
BUTTONS_CODE_MAP = {
    2: '1',
    3: '2',
    4: '3',
    5: '4',
    50: 'm',
    28: 'ENTER',
    1: 'ESC',
}

# for event1, when the knob is turned it is always keycode 6, but value changes on direction
KNOB_LEFT = 4294967295  # actually -1 but unsigned int so wraps around
KNOB_RIGHT = 1

# https://github.com/torvalds/linux/blob/v5.5-rc5/include/uapi/linux/input.h#L28
# long int, long int, unsigned short, unsigned short, unsigned int
EVENT_FORMAT = 'llHHI'
EVENT_SIZE = struct.calcsize(EVENT_FORMAT)

# global for HA Client
HA_CLIENT:Client = None

DOUBLE_PRESS_THRESHOLD = 0.3 
media_ctrl = False

# suppress warnings about invalid certs
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
old_merge_environment_settings = requests.Session.merge_environment_settings

logformat = logging.Formatter('%(created)f %(levelname)s [%(filename)s:%(lineno)d]: %(message)s')
logger = logging.getLogger('buttons')
logger.setLevel(logging.DEBUG)

fh = logging.FileHandler('/var/log/buttons.log')
fh.setLevel(logging.DEBUG)
fh.setFormatter(logformat)
logger.addHandler(fh)

ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
ch.setFormatter(logformat)
logger.addHandler(ch)

current_light = "light.bedroom_lights"
current_media = 'media_player.lisa'
muted = {}
sleep = False

try:
    with open("/home/superbird/light", "r") as file:
        current_light = file.read().strip()
except Exception as e:
    logger.info(e)
    
logger.info(f"Current light is: {current_light}")
@contextlib.contextmanager
def no_ssl_verification():
    """
    context manager that monkey patches requests and changes it so that verify=False is the default and suppresses the warning
        https://stackoverflow.com/questions/15445981/how-do-i-disable-the-security-certificate-check-in-python-requests
    """
    opened_adapters = set()

    def merge_environment_settings(self, url, proxies, stream, verify, cert):
        # Verification happens only once per connection so we need to close
        # all the opened adapters once we're done. Otherwise, the effects of
        # verify=False persist beyond the end of this context manager.
        opened_adapters.add(self.get_adapter(url))

        settings = old_merge_environment_settings(self, url, proxies, stream, verify, cert)
        settings['verify'] = False

        return settings

    requests.Session.merge_environment_settings = merge_environment_settings

    try:
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', InsecureRequestWarning)
            yield
    finally:
        requests.Session.merge_environment_settings = old_merge_environment_settings

        for adapter in opened_adapters:
            try:
                adapter.close()
            except Exception:
                pass


def translate_event(etype: int, code: int, value: int) -> str:
    """
    Translate combination of type, code, value into string representing button pressed
    """
    if etype == 1 and value == 1:
        # button press
        if code in BUTTONS_CODE_MAP:
            return BUTTONS_CODE_MAP[code]
    if etype == 2:
        if code == 6:
            # knob turn
            if value == KNOB_RIGHT:
                return 'RIGHT'
            if value == KNOB_LEFT:
                return 'LEFT'
    return 'UNKNOWN'

def toggle_backlight():
    global sleep
    data = None
    with open(BACKLIGHT, 'r') as file:
        data = int(file.read().rstrip())
    sleep = not sleep
    if data == 0:
        os.system(f"echo 100 > {BACKLIGHT}")
    else:
        os.system(f"echo 0 > {BACKLIGHT}")
    
def backlight_serivce():
    global sleep

    while True:
        # Check the display status using xset
        try:
            display_status = subprocess.check_output("DISPLAY=:0 xset -q | grep 'Monitor is' | awk '{print $3}'", shell=True, text=True).strip()
        except subprocess.CalledProcessError:
            display_status = "Unknown"

        # Set the backlight brightness based on display status
        if display_status == "Off" or sleep:
            with open(BACKLIGHT, "w") as f:
                f.write("0")
                os.system("DISPLAY=:0 xinput disable TouchScreen")
        elif display_status != "Off":
            with open(BACKLIGHT, "w") as f:
                f.write(str(BRIGHTNESS))
                os.system("DISPLAY=:0 xinput enable TouchScreen")

        # Wait before checking again
        time.sleep(0.1)

def set_current_light(light):
    global current_light
    current_light = light
    HA_CLIENT.set_state(State(entity_id="input_text.current_light", state=current_light))
    logger.info(f'current light {current_light}')
    os.system(f'echo "{current_light}" > /home/superbird/light')

def process_key(item):
    if "light." in item:
        set_current_light(item)
        #set_current_light(item)
    elif "switch." in item:
        switch_domain = HA_CLIENT.get_domain('switch')
        switch_domain.toggle(entity_id=item)
        logger.info(f"Toggling {item}")
    elif "scene." in item:
        scene_domain = HA_CLIENT.get_domain('scene')
        scene_domain.turn_on(entity_id=item)
        logger.info(f"Running scene {item}")
    elif "input_button." in item:
        scene_domain = HA_CLIENT.get_domain('input_button')
        scene_domain.press(entity_id=item)
        logger.info(f"Pressing {item}")
    elif "toggle"==item:
        global media_ctrl
        media_ctrl = False if media_ctrl else True
        logger.info(f"Media control toggled: {media_ctrl}")

    
def handle_button(pressed_key: str):
    """
    Decide what to do in response to a button press
    """
    # check for presets
    if pressed_key in ['1', '2', '3', '4', 'm']:

        if pressed_key == '1':
            process_key(BUTTON1[0])
        if pressed_key == '2':
            process_key(BUTTON2[0])
        if pressed_key == '3':
            process_key(BUTTON3[0])
        if pressed_key == '4':
            process_key(BUTTON4[0])
        if pressed_key == 'm':
            toggle_backlight()
            #process_key(BUTTON5[0])
        
    elif pressed_key in ['ESC', 'ENTER', 'LEFT', 'RIGHT']:
        if pressed_key == 'ENTER':
            if media_ctrl:
                volume_mute()
            else:
                light_toggle(current_light)
        elif pressed_key == 'LEFT':
            cmd_lower()
        elif pressed_key == 'RIGHT':
            cmd_raise()
        if pressed_key == 'ESC':
            if media_ctrl:
                play_pause()
            else:
                light_toggle(current_light)

def handle_button_double_press(pressed_key: str):
    """
    Decide what to do in response to a button press
    """

    logger.info(f'Double press: {pressed_key}')
    # check for presets
    if pressed_key in ['1', '2', '3', '4', 'm']:

        if pressed_key == '1':
            process_key(BUTTON1[1])
        if pressed_key == '2':
            process_key(BUTTON2[1])
        if pressed_key == '3':
            process_key(BUTTON3[1])
        if pressed_key == '4':
            process_key(BUTTON4[1])
        if pressed_key == 'm':
            process_key(BUTTON5[1])
        
    elif pressed_key in ['ESC', 'ENTER', 'LEFT', 'RIGHT']:
        if pressed_key == 'ENTER':
            if media_ctrl:
                pass #volume_mute()
            else:
                light_toggle(current_light)
        elif pressed_key == 'LEFT':
            cmd_lower()
        elif pressed_key == 'RIGHT':
            cmd_raise()
        if pressed_key == 'ESC':
            process_key(BUTTON_ESC[1])


def get_media_player():
    m = HA_CLIENT.get_entity(entity_id="input_text.current_media")
    player = m.get_state()
    if player == "unknown":
        player = "media_player.lisa"
    return player.state

def get_volume_level() -> int:
    """
    Get current brightness of a light
    """
    m = HA_CLIENT.get_entity(entity_id=current_media)
    level = m.get_state().attributes['volume_level']
    if level is None:
        level = 0
    return level

def get_light_level() -> int:
    """
    Get current brightness of a light
    """
    light = HA_CLIENT.get_entity(entity_id=current_light)
    level = light.get_state().attributes['brightness']
    if level is None:
        level = 0
    return level

def volume_mute():
    global muted
    volume = get_volume_level()
    media_player = get_media_player()
    is_muted = muted.get(media_player, [False, volume])
    m = HA_CLIENT.get_domain('media_player')
    m.volume_set(entity_id=media_player, volume_level=0 if is_muted[0] else is_muted[1])
    muted[media_player] = [not is_muted[0], volume]

def volume_up():
    m = HA_CLIENT.get_domain('media_player')
    m.volume_up(entity_id=get_media_player())

def volume_down():
    m = HA_CLIENT.get_domain('media_player')
    m.volume_down(entity_id=get_media_player())

def set_light_level(level: int):
    """
    Set light brightness
    """
    light_domain = HA_CLIENT.get_domain('light')
    light_domain.turn_on(entity_id=current_light, brightness=level)

def set_volume_level(level: int):
    """
    Set light brightness
    """
    m = HA_CLIENT.get_domain('media_player')
    m.set(entity_id=current_media, volume_level=level)

def play_pause():
    m = HA_CLIENT.get_domain('media_player')
    m.media_play_pause(entity_id=get_media_player())

def cmd_scene(entity_id: str):
    """
    Recall a scene / automation / script by entity id
        you can use any entity where turn_on is valid
    """
    if entity_id == '':
        return
    domain = entity_id.split('.')[0]
    logger.info(f'Recalling {domain}: {entity_id}')
    scene_domain = HA_CLIENT.get_domain(domain)
    scene_domain.turn_on(entity_id=entity_id)


def light_toggle(entiity_id):
    """
    Toggle the light for this room on/off
    """
    light_domain = HA_CLIENT.get_domain('light')
    light_domain.toggle(entity_id=entiity_id)
    set_current_light(entiity_id)
    


def cmd_lower():
    """
    Lower the level of the light for this room
    """
    if media_ctrl:
        logger.info(f'Lowering volume of {current_media}')
        volume_down()
        return

    current_level = get_light_level()
    new_level = current_level - LEVEL_INCREMENT
    new_level = max(new_level, 0)
    logger.info(f'New level: {new_level}')
    if new_level < current_level:
        set_light_level(new_level)

    logger.info(f'Lowering brightness of {current_light}')
    current_level = get_light_level()
    new_level = current_level - LEVEL_INCREMENT
    new_level = max(new_level, 0)
    logger.info(f'New level: {new_level}')
    if new_level < current_level:
        set_light_level(new_level)


def cmd_raise():
    """
    Raise the level of the light for this room
    """
    if media_ctrl:
        logger.info(f'Raising volume of {current_media}')
        volume_up()
        return
    
    logger.info(f'Raising brightness of {current_light}')
    current_level = get_light_level()
    new_level = current_level + LEVEL_INCREMENT
    new_level = min(new_level, 255)
    logger.info(f'New level: {new_level}')
    if new_level > current_level:
        set_light_level( new_level)


class EventListener():
    """
    Listen to a specific /dev/eventX and call handle_button 
    """
    def __init__(self, device: str) -> None:
        self.device = device
        self.stopper = ThreadEvent()
        self.thread:Thread = None
        self.last_press_times = {}  # Store last press times for buttons
        self.press_flags = {}
        self.start()

    def start(self):
        """
        Start listening thread
        """
        logger.info(f'Starting listener for {self.device}')
        self.thread = Thread(target=self.listen, daemon=True)
        self.thread.start()

    def stop(self):
        """
        Stop listening thread
        """
        logger.info(f'Stopping listener for {self.device}')
        self.stopper.set()
        self.thread.join()


    def listen(self):
        """
        To run in thread, listen for events and call handle_buttons if applicable.
        """
        with open(self.device, "rb") as in_file:
            event = in_file.read(EVENT_SIZE)
            while event and not self.stopper.is_set():
                try:
                    (_sec, _usec, etype, code, value) = struct.unpack(EVENT_FORMAT, event)
                    event_str = translate_event(etype, code, value)

                    if event_str in ['1', '2', '3', '4', 'm', 'ENTER', 'ESC', 'LEFT', 'RIGHT']:
                        current_time = time.time()

                        # Check for double press
                        if event_str in self.last_press_times:
                            time_diff = current_time - self.last_press_times[event_str]
                            if time_diff <= DOUBLE_PRESS_THRESHOLD:
                                self.press_flags[event_str] = False  # Cancel pending single press
                                logger.info(f'Double press detected for {event_str}')
                                if event_str in ['LEFT', 'RIGHT']:
                                    self.schedule_single_press(event_str, current_time)
                                else:
                                    handle_button_double_press(event_str)
                            else:
                                self.schedule_single_press(event_str, current_time)
                        else:
                            self.schedule_single_press(event_str, current_time)

                        # Update last press time
                        self.last_press_times[event_str] = current_time

                    event = in_file.read(EVENT_SIZE)
                except Exception as e:
                    logger.error(f"Error in listener: {e}")
                    time.sleep(1)

    def schedule_single_press(self, button, current_time):
        """
        Schedule a single press with a small delay to allow for double-press detection.
        """
        self.press_flags[button] = True

        def delayed_single_press():
            time.sleep(DOUBLE_PRESS_THRESHOLD)
            if self.press_flags.get(button, False):  # Check if single press is still valid
                handle_button(button)

        Thread(target=delayed_single_press, daemon=True).start()


if __name__ == '__main__':
    # NOTE: we use no_ssl_verification context handler to nuke the obnoxiously difficult-to-disable SSL verification of requests
    logger.info('Starting buttons listeners')
   
    with no_ssl_verification():
        HA_CLIENT = None
        while HA_CLIENT == None:
            try:
                HA_CLIENT = Client(f'{HA_SERVER}/api', HA_TOKEN, global_request_kwargs={'verify': False}, cache_session=False)
            except Exception as e:
                print(e)
                time.sleep(0.5)

        EventListener(DEV_BUTTONS)
        EventListener(DEV_KNOB)
        # backlight_serivce()
        Thread(target=backlight_serivce, daemon=True).start()
        while True:
            time.sleep(1)
