from beautifulhue.api import Bridge
from func_timer import func_timer
from time import sleep
import hue_interface
import ConfigParser
import threading
import urllib2
import utility
import random
import json
import ast

if utility.dll_check():
    import img_proc


# Class for running ScreenBloom thread
class ScreenBloom(threading.Thread):
    def __init__(self, update):
        super(ScreenBloom, self).__init__()
        self.stoprequest = threading.Event()
        self.update = float(update)

    def run(self):
        hue_interface.lights_on_off('On')
        while not self.stoprequest.isSet():
            run()
            sleep(.01)

    def join(self, timeout=None):
        self.stoprequest.set()
        super(ScreenBloom, self).join(timeout)


# Class for Screen object to hold values during runtime
class Screen(object):
    def __init__(self, bridge, ip, devicename, bulbs, bulb_settings, default, rgb, update,
                 update_buffer, max_bri, min_bri, zones, zone_state, color_mode,
                 black_rgb, display_index, party_mode, system_monitoring_enabled,
                 system_monitoring_mode, system_monitoring_interval, color_mode_enabled):
        self.bridge = bridge
        self.ip = ip
        self.devicename = devicename
        self.bulbs = bulbs
        self.bulb_settings = bulb_settings
        self.default = default
        self.rgb = rgb
        self.update = update
        self.update_buffer = update_buffer
        self.max_bri = max_bri
        self.min_bri = min_bri
        self.zones = zones
        self.zone_state = zone_state
        self.color_mode = color_mode
        self.black_rgb = black_rgb
        self.display_index = display_index
        self.party_mode = party_mode
        self.system_monitoring_enabled = system_monitoring_enabled
        self.system_monitoring_mode = system_monitoring_mode
        self.system_monitoring_interval = system_monitoring_interval
        self.color_mode_enabled = color_mode_enabled


def start():
    # Grab attributes from config file
    atr = initialize()
    global _screen
    _screen = Screen(*atr)


def get_screen_object():
    global _screen
    return _screen


# Grab attributes for screen instance
def initialize():
    config_dict = utility.get_config_dict()

    ip = config_dict['ip']
    username = config_dict['username']
    bridge = Bridge(device={'ip': ip}, user={'name': username})

    max_bri = config_dict['max_bri']
    min_bri = config_dict['min_bri']

    active_lights = [int(i) for i in config_dict['active'].split(',')]
    all_lights = [int(i) for i in config_dict['all_lights'].split(',')]

    # Check selected bulbs vs all known bulbs
    bulb_list = []
    for counter, bulb in enumerate(all_lights):
        try:
            if active_lights[counter]:
                bulb_list.append(bulb)
            else:
                bulb_list.append(0)
        except IndexError:
            bulb_list.append(0)

    bulb_settings = json.loads(config_dict['bulb_settings'])

    update = config_dict['update']
    update_buffer = config_dict['update_buffer']

    default = [int(i) for i in config_dict['default'].split(',')]
    black_rgb = [int(i) for i in config_dict['black_rgb'].split(',')]

    zones = ast.literal_eval(config_dict['zones'])
    zone_state = bool(config_dict['zone_state'])

    party_mode = bool(config_dict['party_mode'])
    display_index = config_dict['display_index']

    color_mode_enabled = config_dict['color_mode_enabled']
    color_mode = config_dict['color_mode']

    system_monitoring_enabled = config_dict['system_monitoring_enabled']
    system_monitoring_mode = config_dict['system_monitoring_mode']
    system_monitoring_interval = config_dict['system_monitoring_interval']

    return bridge, ip, username, bulb_list, bulb_settings, default, default, \
           update, update_buffer, max_bri, min_bri, zones, zone_state, color_mode, \
           black_rgb, display_index, party_mode, system_monitoring_enabled, \
           system_monitoring_mode, system_monitoring_interval, color_mode_enabled


# Get updated attributes, re-initialize screen object
def re_initialize():
    config = ConfigParser.RawConfigParser()
    config.read(utility.get_config_path())

    # Attributes
    at = initialize()

    global _screen
    _screen = Screen(*at)

    # Update bulbs with new settings
    results = img_proc.screen_avg(_screen)

    try:
        # Update Hue bulbs to avg color of screen
        if 'zones' in results:
            for zone in results['zones']:
                brightness = utility.get_brightness(_screen, int(_screen.max_bri), int(_screen.min_bri), zone['dark_ratio'])

                for bulb in zone['bulbs']:
                    hue_interface.send_rgb_to_bulb(bulb, zone['rgb'], brightness)
        else:
            update_bulbs(results['rgb'], results['dark_ratio'])
    except urllib2.URLError:
        print 'Connection timed out, continuing...'
        pass


# Updates Hue bulbs to specified RGB value
def update_bulbs(new_rgb, dark_ratio):
    global _screen
    send_light_commands(new_rgb, dark_ratio)
    _screen.rgb = new_rgb


# Set bulbs to saved default color
def update_bulb_default():
    global _screen
    default_rgb = _screen.default[0], _screen.default[1], _screen.default[2]
    send_light_commands(default_rgb, 0.0)


# Set bulbs to random RGB
def update_bulb_party():
    global _screen
    print '\nParty Mode!'
    party_color = utility.party_rgb()
    send_light_commands(party_color, 0.0, party=True)


def send_light_commands(rgb, dark_ratio, party=False):
    global _screen

    active_bulbs = [bulb for bulb in _screen.bulbs if bulb]
    for bulb in active_bulbs:
        bulb_settings = _screen.bulb_settings[unicode(bulb)]
        bulb_max_bri = bulb_settings['max_bri']
        bulb_min_bri = bulb_settings['min_bri']
        bri = utility.get_brightness(_screen, bulb_max_bri, bulb_min_bri, dark_ratio)

        if party:
            rgb = utility.party_rgb()
            try:
                bri = random.randrange(int(_screen.min_bri), int(bri) + 1)
            except ValueError as e:
                print e
                continue

        hue_interface.send_rgb_to_bulb(bulb, rgb, bri)


# Main loop
@func_timer
def run():
    sleep(float(_screen.update_buffer))

    if _screen.system_monitoring_enabled:  # Adds ~200ms to the loop
        ohw = utility.get_ohw_interface()
        ohw.sample()
        utility.get_system_temps(ohw.current_sample)

    if _screen.party_mode:
        update_bulb_party()
        sleep(float(_screen.update))
    else:
        results = img_proc.screen_avg(_screen)

        try:
            print '\n'
            if 'zones' in results:
                print 'Parse Method: zones | Color Mode: %s' % _screen.color_mode
                for zone in results['zones']:
                    for bulb in zone['bulbs']:
                        bulb_settings = _screen.bulb_settings[unicode(bulb)]
                        bulb_max_bri = bulb_settings['max_bri']
                        bulb_min_bri = bulb_settings['min_bri']
                        bri = utility.get_brightness(_screen, bulb_max_bri, bulb_min_bri, zone['dark_ratio'])
                        hue_interface.send_rgb_to_bulb(bulb, zone['rgb'], bri)
            else:
                print 'Parse Method: standard | Color Mode: %s' % _screen.color_mode
                rgb = results['rgb']
                dark_ratio = results['dark_ratio']
                update_bulbs(rgb, dark_ratio)
        except urllib2.URLError:
            print 'Connection timed out, continuing...'
            pass
