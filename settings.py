#!/usr/bin/python3
# -*- coding: utf-8 -*-

import json
import os
import platform

from kalmatools import utils, tkutils

resources_folder = "resources/"
system_caption = "System Monitor by alef"

with open("settings.json", "r") as file:
    config = json.load(file)

archOS = platform.system()
to_bool = (lambda x: x.lower() in ("true", "y", "yes"))
style = config.get("style", "pie")
styles = config.get("available_styles", ["pie"])
update_d = int(config.get("update_data", "300"))
update = int(config.get("update_system_mode", "1000"))
update_g = int(config.get("update_game_mode", "350"))
orientation = bool(config.get("orientation", "horizontal") == "horizontal")
show_hide_key = config.get("show_hide_key", "m")
win_subsensors_enabled = to_bool(config.get("win_subsensors_enabled", False))
print_sys_info = to_bool(config.get("print_sys_info", False))
sys_info_file = config.get("sys_info_file")
print_to_file = to_bool(config.get("print_to_file", False))
output_file = config.get("output_file")

# SIZES
# This will affect the size of the whole thing
gauge_size = int(config.get("gauge_size"))

# ICONS
icons_folder = utils.resource_path(__file__, config.get("icons_folder"))
if icons_folder[-1:] != os.sep:
    icons_folder += os.sep
system_icon = icons_folder + config.get("system_icon")
gauge_frame = icons_folder + config.get("gauge_frame")
gauge_shadow = icons_folder + config.get("gauge_shadow")
menu_selected = icons_folder + "tick.png"
menu_not_selected = icons_folder + "notick.png"

# FONTS
fonts_folder = utils.resource_path(__file__, config.get("fonts_folder"))
if fonts_folder[-1:] != os.sep:
    fonts_folder += os.sep
font = gauge_font = "FreeSans"
font_file = fonts_folder + config.get("font_file")
gauge_font_file = fonts_folder + config.get("gauge_font_file")
if "Linux" in archOS:
    if tkutils.tkLoadFont(font_file, font):
        font = config.get("font")
    if tkutils.tkLoadFont(gauge_font_file, gauge_font):
        gauge_font = config.get("gauge_font")
else:
    if utils.load_font(archOS, font_file, True, False):
        font = config.get("font")
    if utils.load_font(archOS, gauge_font_file, True, False):
        gauge_font = config.get("gauge_font")

# COLORS
bg_color = config.get("background_color")
opacity = float(config.get("opacity"))
transparent_bg = to_bool(config.get("transparent_bg"))
titles_color = config.get("titles_font_color")
gtype_color = config.get("gauge_type_color")
gind_color = config.get("gauge_indicator_color")
gsafe_color = config.get("gauge_safe_color")
gwarn_color = config.get("gauge_warn_color")
gcrit_color = config.get("gauge_critic_color")
gnoavail_color = config.get("gauge_no_available_color")
sys_name_color = config.get("system_name_color")
sys_value_color = config.get("system_value_color")
fsafe_color = config.get("fps_safe_color")
fbg_color = config.get("fps_background_color")

# OTHER
degree_sign = u'\N{DEGREE SIGN}'
uniTmp = u'\N{DEGREE CELSIUS}'  # Unicode for Celsius Degree symbol
