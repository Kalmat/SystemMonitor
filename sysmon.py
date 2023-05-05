#!/usr/bin/python3
# -*- coding: utf-8 -*-

__version__ = "2.0.0"

import datetime as dt
import glob
import logging
import math
import os
import platform
import queue
import subprocess
import sys
import threading
import tkinter as tk
import traceback

import psutil
from pynvml.smi import nvidia_smi
import pywinctl as pwc
from kalmatools import utils
from pynput import keyboard

if sys.platform == "win32":
    import wmi

import settings

Qprocess = queue.Queue()


class GetData(threading.Thread):

    def __init__(self, keep, callback):
        super().__init__()

        if settings.print_to_file:
            sys.stdout = open(settings.output_file, "w")

        self.keep = keep
        self.callback = callback

        # General variables
        self.show_sys_data = False
        self.sys_data = []
        self.sensors_data = []
        self.query_cpu = True
        self.query_gpu = True
        self.queryNVML = True
        self.callback_job = None
        self.sys_info_printed = False
        self.mouse_X_pos = 0
        self.mouse_Y_pos = 0
        self.done = False
        self.game_mode = False
        self.video = None
        self.gpu_fps = 0
        self.NVSMI_command = 'nvidia-smi'
        self.nvsmi = None

        self.cpu_data = {}
        self.cpu_static_data = {}
        self.gpu_data = {}
        self.gpu_static_data = {}
        self.targetGPU = ""

        # Initial Actions
        if "Windows" in settings.archOS:
            self.win_initialize_data()
            self.sys_drive = os.getenv("SystemDrive")
        else:
            self.sys_drive = "/"
        self.get_cpu_static_data()
        self.get_gpu_static_data()

        # LibreHardwareMonitor output
        if settings.print_sys_info:
            subsensors = settings.win_subsensors_enabled
            settings.win_subsensors_enabled = True
            self.sys_info_file_handle = open(settings.sys_info_file, 'w')
            self.get_cpu_data()
            self.sys_info_file_handle.close()
            self.sys_info_printed = True
            settings.win_subsensors_enabled = subsensors

    def changeSysData(self, show_sys_data):
        self.show_sys_data = show_sys_data

    def changeMode(self, mode):
        self.game_mode = mode

    ######### WINDOWS FUNCTIONS #########################

    def win_initialize_data(self):
        # https://stackoverflow.com/questions/3262603/accessing-cpu-temperature-in-python (Neo)
        # REMEMBER TO: Right-click on the .dll -> "Properties" -> "General" -> click "Unblock"

        # This gave me the clue: https://github.com/NaturalBornCamper/system-monitor/
        import clr  # pythonnet, not clr module
        clr.AddReference(utils.resource_path(__file__, 'resources/LibreHardwareMonitorLib'))

        # noinspection PyUnresolvedReferences
        from LibreHardwareMonitor import Hardware

        self.handle = Hardware.Computer()
        self.handle.IsCpuEnabled = True
        self.handle.IsGpuEnabled = True
        if settings.print_sys_info:
            self.handle.IsMemoryEnabled = True
            self.handle.IsMotherboardEnabled = True
            self.handle.IsControllerEnabled = True
            self.handle.IsNetworkEnabled = True
            self.handle.IsStorageEnabled = True
        self.handle.Open()

    def get_cpu_data(self):

        if "Windows" in settings.archOS:
            self.win_get_cpu_data()
        else:
            self.linux_get_cpu_data()

    def win_get_cpu_data(self):

        cpu_usage = 0.0
        core_usage = []
        core_clock = []
        core_avg_temp = 0.0
        core_temp = []
        cpu_fanspeed = 0.0
        mb_temps = []
        mb_fans = []
        mb_fans_rpm = []
        gpu_temp = 0.0
        gpu_fans = []
        gpu_fans_rpm = []
        gpu_fanspeed = 0.0
        gpu_usage = 0
        gpu_power = 0
        cpu_name = self.cpu_static_data.get("name", "Unknown")
        mb_name = "Unknown"

        cpu = core = load = gpu = fan = usage = power = False
        for i in self.handle.Hardware:
            i.Update()
            for sensor in i.Sensors:

                if settings.print_sys_info and not self.sys_info_printed:
                    hw_type = sensor.Hardware.Identifier.ToString() + " (" + str(sensor.Hardware.HardwareType) + ")"
                    sn_type = sensor.Identifier.ToString() + " (" + str(sensor.SensorType) + ")"
                    data = str(u"HW %s Type %s name %s Sensor #%i name %s: %s %s" %
                               (hw_type, sn_type, sensor.Hardware.Name, sensor.Index, sensor.Name, sensor.Value, "\n"))
                    self.sys_info_file_handle.write(data)

                if sensor.Value is not None:

                    if ".CPU." in sensor.Hardware.ToString():
                        # ['Accept', 'ActivateSensor', 'Close', 'Closing', 'CoreString', 'CpuId', 'DeactivateSensor', 'EnergyUnitsMultiplier', 'Equals', 'Finalize', 'GetHashCode', 'GetMsrs', 'GetReport', 'GetType', 'HardwareType', 'HasModelSpecificRegisters', 'HasTimeStampCounter', 'Identifier', 'Index', 'MemberwiseClone', 'Name', 'Overloads', 'Parent', 'Properties', 'ReferenceEquals', 'SensorAdded', 'SensorRemoved', 'Sensors', 'SubHardware', 'TimeStampCounterFrequency', 'ToString', 'Traverse', 'Update', '__call__', '__class__', '__delattr__', '__delitem__', '__dir__', '__doc__', '__eq__', '__format__', '__ge__', '__getattribute__', '__getitem__', '__gt__', '__hash__', '__init__', '__init_subclass__', '__iter__', '__le__', '__lt__', '__module__', '__ne__', '__new__', '__overloads__', '__reduce__', '__reduce_ex__', '__repr__', '__setattr__', '__setitem__', '__sizeof__', '__str__', '__subclasshook__', '_active', '_coreCount', '_cpuId', '_family', '_model', '_name', '_packageType', '_settings', '_stepping', '_threadCount', 'add_Closing', 'add_SensorAdded', 'add_SensorRemoved', 'get_CpuId', 'get_EnergyUnitsMultiplier', 'get_HardwareType', 'get_HasModelSpecificRegisters', 'get_HasTimeStampCounter', 'get_Identifier', 'get_Index', 'get_Name', 'get_Parent', 'get_Properties', 'get_Sensors', 'get_SubHardware', 'get_TimeStampCounterFrequency', 'remove_Closing', 'remove_SensorAdded', 'remove_SensorRemoved', 'set_Name']
                        # ['CompareTo', 'Equals', 'Finalize', 'GetHashCode', 'GetType', 'MemberwiseClone', 'Overloads', 'ReferenceEquals', 'ToString', '__call__', '__class__', '__delattr__', '__delitem__', '__dir__', '__doc__', '__eq__', '__format__', '__ge__', '__getattribute__', '__getitem__', '__gt__', '__hash__', '__init__', '__init_subclass__', '__iter__', '__le__', '__lt__', '__module__', '__ne__', '__new__', '__overloads__', '__reduce__', '__reduce_ex__', '__repr__', '__setattr__', '__setitem__', '__sizeof__', '__str__', '__subclasshook__', 'op_Equality', 'op_GreaterThan', 'op_Inequality', 'op_LessThan']
                        # print(sensor.Hardware.ToString(), sensor.Hardware.Identifier, sensor.Identifier)

                        cpu_name = sensor.Hardware.Name
                        if "/temperature" in sensor.Identifier.ToString() and sensor.Name == "Core Average":
                            core_avg_temp = sensor.Value
                            cpu = True
                        elif "/temperature" in sensor.Identifier.ToString() and 0 <= int(
                                sensor.Index) < psutil.cpu_count(False):
                            core_temp.append(sensor.Value)
                            if len(core_temp) == psutil.cpu_count(False):
                                core = True
                        elif "/load" in sensor.Identifier.ToString() and "CPU Total" in sensor.Name:
                            cpu_usage = sensor.Value
                            load = True
                        elif "/load" in sensor.Identifier.ToString() and "CPU Core" in sensor.Name:
                            core_usage.append(sensor.Value)
                        elif "/clock" in sensor.Identifier.ToString() and "CPU Core" in sensor.Name:
                            core_clock.append(sensor.Value)

                    elif ".Gpu." in sensor.Hardware.ToString():

                        if self.targetGPU in sensor.Hardware.Identifier.ToString():

                            if "/temperature" in sensor.Identifier.ToString() and sensor.Name == "GPU Core":
                                gpu_temp = sensor.Value
                                gpu = True
                            elif "/fan" in sensor.Identifier.ToString() and "GPU Fan" in sensor.Name:
                                gpu_fans_rpm.append(sensor.Value)
                            elif "/control" in sensor.Identifier.ToString() and "GPU Fan" in sensor.Name:
                                gpu_fans.append(sensor.Value)
                                fan = True
                            elif "/load" in sensor.Identifier.ToString() and "GPU Core" in sensor.Name:
                                gpu_usage = sensor.Value
                                usage = True
                            elif "/power" in sensor.Identifier.ToString() and "GPU Package" in sensor.Name:
                                gpu_power = sensor.Value
                                power = True

            if settings.win_subsensors_enabled:
                for j in i.SubHardware:
                    j.Update()
                    for subsensor in j.Sensors:
                        if settings.print_sys_info and not self.sys_info_printed:
                            hw_type = subsensor.Hardware.Identifier.ToString() + " (" + str(
                                subsensor.Hardware.HardwareType) + ")"
                            data = str(u"\tHardware %s type %s name %s SubSensor #%i name %s: %s %s" %
                                       (subsensor.Hardware.Parent.Name, hw_type, subsensor.Hardware.Name,
                                        subsensor.SensorType, subsensor.Name, subsensor.Value, "\n"))
                            self.sys_info_file_handle.write(data)

                        if ".mainboard." in subsensor.Hardware.ToString():
                            mb_name = subsensor.Hardware.Parent.Name
                            # Not sure what every subsensor means!
                            # Check: https://superuser.com/questions/1754739/how-to-find-the-position-of-a-sensor
                            #        https://www.nuvoton.com/resource-files/NCT6796D_Datasheet_V0_6.pdf
                            if "/temperature" in subsensor.Identifier.ToString() and "Temperature" in subsensor.Name:
                                mb_temps.append((subsensor.Name, subsensor.Index, subsensor.Value))
                            elif "/fan" in subsensor.Identifier.ToString() and "Fan" in subsensor.Name:
                                mb_fans_rpm.append((subsensor.Name, subsensor.Index, subsensor.Value))
                            elif "/control" in subsensor.Identifier.ToString() and "Fan" in subsensor.Name:
                                mb_fans.append((subsensor.Name, subsensor.Index, subsensor.Value))

        if not cpu:
            if core:
                core_avg_temp = sum(core_temp) / max(1, len(core_temp))
            elif not load:
                self.query_cpu = False

        # Trying to get same values than Task Manager... but with no success
        # if core_usage and core_clock:
        #     try:
        #         diffsize = len(core_usage) / len(core_clock)
        #         maxfreq = psutil.cpu_freq().max
        #         result = []
        #         for i in range(len(core_usage)):
        #             result.append(core_usage[i] * (core_clock[int(i / diffsize)] / maxfreq))
        #         cpu_usage = round(sum(result) / len(result))
        #     except:
        #         pass

        for fan in mb_fans:
            # Didn't find a way to identify CPU
            # TODO: Assuming first non-zero fan is the CPU Fan... but most likely, it's not!!!
            if fan[2] != 0:
                cpu_fanspeed = fan[2]

        if gpu and fan:
            gpu_fanspeed = sum(gpu_fans) / len(gpu_fans)

        if gpu and usage and power and fan:
            self.query_gpu = False

        try:
            self.cpu_data["usage"] = int(cpu_usage)
        except:
            self.cpu_data["usage"] = 0
        try:
            self.cpu_data["temp"] = int(core_avg_temp)
        except:
            self.cpu_data["temp"] = 0
        try:
            self.cpu_data["cpu_fanspeed"] = int(cpu_fanspeed)
        except:
            self.cpu_data["cpu_fanspeed"] = 0
        self.cpu_data["mb_temp"] = mb_temps
        self.cpu_data["mb_fans"] = mb_fans

        try:
            self.gpu_data["usage"] = int(gpu_usage)
        except:
            self.gpu_data["usage"] = 0
        try:
            self.gpu_data["temp"] = int(gpu_temp)
        except:
            self.gpu_data["temp"] = 0
        try:
            self.gpu_data["fanspeed"] = int(gpu_fanspeed)
        except:
            self.gpu_data["fanspeed"] = 0
        try:
            self.gpu_data["power"] = int(gpu_power)
        except:
            self.gpu_data["power"] = 0

        self.cpu_static_data["name"] = cpu_name
        self.cpu_static_data["mb_name"] = mb_name

    def win_get_gpu_names(self):

        cards = []
        try:
            pc = wmi.WMI()
            for gpu in pc.Win32_VideoController():
                cards.append(gpu.Caption.replace("(R)", "").replace("(TM)", "").replace("Corporation", ""))
        except:
            logging.error(traceback.format_exc())

        return cards

    ######### LINUX FUNCTIONS #########################

    def linux_get_cpu_data(self):

        core_avg_temp = 0.0
        core_temp = []
        mb_temp = 0.0
        mb_name = "Unknown"
        twarn = 65
        tcrit = 75

        if hasattr(psutil, "sensors_temperatures"):
            try:
                temps = psutil.sensors_temperatures()
            except:
                temps = None
                core_temp = [0]
                logging.error(traceback.format_exc())

            if temps is not None:
                for name, entries in temps.items():
                    for entry in entries:

                        if settings.print_sys_info and not self.sys_info_printed:
                            data = str(u"Name: %s Current: %s High: %s Critical: %s %s" %
                                       (str(entry.label or name), str(entry.current), str(entry.high),
                                        str(entry.critical), "\n"))
                            self.sys_info_file_handle.write(data)

                        if entry.label[:4] == "Core":
                            core_temp.append(utils.to_float(entry.current))
                            twarn = utils.to_float(entry.high)
                            tcrit = utils.to_float(entry.critical)

                        elif entry.label == "SYSTIN":
                            mb_name = str(entry.label or name)
                            mb_temp = utils.to_float(entry.current)

                        # CPUTIN - Motherboard's CPU temp (different from CoreTemp which is the sensor on the processor)
                        # AUXTIN - power supply temp sensor, if there is one
                        # SYSTIN - Motherboard
                        # TMPINx - Not sure

                core_avg_temp = utils.to_float(sum(core_temp) / max(1.0, len(core_temp)))

            else:
                logging.warning("WARNING: psutil, can't read any temperature. Try with root privileges")
                self.query_cpu = False
        else:
            logging.warning("WARNING: psutil, platform not supported for temperature sensors")
            self.query_cpu = False

        if not self.cpu_data:
            self.cpu_data = {}
        try:
            self.cpu_data["temp"] = int(core_avg_temp)
        except:
            self.cpu_data["temp"] = 0
        try:
            self.cpu_data["mb_temp"] = int(mb_temp)
        except:
            self.cpu_data["mb_temp"] = 0
        self.cpu_data["cpu_fanspeed"] = 0
        self.cpu_static_data["mb_name"] = mb_name
        self.cpu_static_data["twarn"] = twarn
        self.cpu_static_data["tcrit"] = tcrit

    def linux_get_gpu_names(self):

        try:
            sp = subprocess.Popen(['lshw', '-C', 'display'], **utils.subprocess_args(include_stdout=True))
            out_str = sp.communicate()
            search_str = out_str[0].decode().split("\n")
        except:
            search_str = []
            logging.error(traceback.format_exc())

        cards = []
        for i in range(len(search_str) - 3):
            if "*-display" in search_str[i]:
                cards.append(search_str[i + 3].split(": ")[1].replace("Corporation", " ") +
                             search_str[i + 2].split(": ")[1].replace("[", "").replace("]", "").strip())

        return cards

    ######### COMMON FUNCTIONS #########################

    def get_cpu_name(self, archOS):

        if "Windows" in archOS:
            return platform.processor()

        elif "Darwin" in archOS:
            os.environ['PATH'] = os.environ['PATH'] + os.pathsep + '/usr/sbin'
            command = "sysctl -n machdep.cpu.brand_string"
            return subprocess.check_output(command).strip()

        elif "Linux" in archOS:
            command = "cat /proc/cpuinfo"
            all_info = subprocess.check_output(command, shell=True).strip()
            for line in all_info.decode().split("\n"):
                if "model name" in line:
                    return line.split(": ")[1].replace("CPU ", "").replace("(TM)", "").replace("(R)", "")

        return "Unknown"

    def get_cpu_static_data(self):

        self.cpu_static_data["name"] = self.get_cpu_name(settings.archOS)
        self.cpu_static_data["twarn"] = 65
        self.cpu_static_data["tcrit"] = 75
        self.cpu_static_data["tmax"] = 105

    def get_gpu_name(self, archOS):

        gpu_name = "Unknown"
        # The order of keys in this dict is important, so NVIDIA will be returned if present, then Intel, and so on...
        # Not sure what AMD/ATI cards will return and how to identify if they are integrated/dedicated
        gpu_installed = {"amd": False, "ati": False, "intel": False, "nvidia": False}

        if "Windows" in archOS:
            gpu_names = self.win_get_gpu_names()
        else:
            gpu_names = self.linux_get_gpu_names()

        for card in gpu_names:
            for key in gpu_installed.keys():
                brand = key + " "
                if brand in card.lower():
                    gpu_installed[key] = True
                    if gpu_name == "Unknown":
                        gpu_name = card

        if gpu_installed.get("amd", False) or gpu_installed.get("ati", False):
            logging.warning("WARNING: ATI/AMD cards not tested, you might want to check:")
            logging.warning("         - aticonfig (https://www.unixmen.com/howto-install-ati-display-driver-in-ubuntu/), or")
            logging.warning("         - pyADL (https://github.com/bitshiftio/pyADL)")

        elif gpu_name == "Unknown":
            logging.warning("WARNING: Could not find any compatible Graphic Card!")
            logging.warning("         Installed Graphic Cards: "+', '.join(x for x in gpu_names))

        return gpu_name, gpu_installed

    def get_gpu_static_data(self):

        twarn = 89.0
        tcrit = 91.0
        tmax = 94.0
        pwarn = pcrit = pmax = 150

        name, gpu_installed = self.get_gpu_name(settings.archOS)
        self.gpu_static_data = {"name": name, "gpu_installed": gpu_installed,
                                "twarn": twarn, "tcrit": tcrit, "tmax": tmax,
                                "pwarn": pwarn, "pcrit": pcrit, "pmax": pmax}

        if gpu_installed.get("nvidia", False):
            self.get_nvidia_static_data_nvml()
            if not self.queryNVML:
                self.get_nvidia_static_data()
        elif gpu_installed.get("amd", False) or gpu_installed.get("ati", False):
            pass
        elif gpu_installed.get("intel", False):
            self.win_subsensors_enabled = True
        else:
            self.query_gpu = False

        # Not sure how ATI/AMD will look like, much more if integrated (modern CPUs name will end by "G")
        if self.gpu_static_data["gpu_installed"]["nvidia"]:
            self.targetGPU = "gpu-nvidia"
        elif self.gpu_static_data["gpu_installed"]["ati"]:
            self.targetGPU = "atigpu"
        elif self.gpu_static_data["gpu_installed"]["amd"]:
            self.targetGPU = "amdgpu"
        elif self.gpu_static_data["gpu_installed"]["intel"]:
            self.targetGPU = "-intel-integrated"
        else:
            self.targetGPU = ""

    def get_nvidia_static_data_nvml(self):

        if self.nvsmi is None:
            self.nvsmi = nvidia_smi.getInstance()
        output = self.nvsmi.DeviceQuery('temperature.gpu,power.limit')
        gpuData = output.get("gpu", {})
        if gpuData:
            gpuData = gpuData[0]

        try:
            self.gpu_static_data["tmax"] = int(gpuData.get("temperature", {}).get("gpu_temp_max_threshold", 0))
        except:
            self.gpu_static_data["tmax"] = 0
        try:
            tcrit = int(gpuData.get("temperature", {}).get("gpu_temp_slow_threshold", 0))
        except:
            tcrit = 0
        self.gpu_static_data["tcrit"] = tcrit
        self.gpu_static_data["twarn"] = tcrit * 0.8
        try:
            pmax = int(gpuData.get("power_readings", {}).get("power_limit", 0))
        except:
            pmax = 0
        self.gpu_static_data["pmax"] = pmax or 150
        self.gpu_static_data["pwarn"] = pmax * 0.75 or 150
        self.gpu_static_data["pcrit"] = pmax * 0.9 or 150

    def get_nvidia_static_data(self):

        if "Windows" in settings.archOS:
            # command = r'C:\Program Files\NVIDIA Corporation\NVSMI\nvidia-smi.exe'
            dir = glob.glob("C:/Windows/System32/DriverStore/FileRepository/nv_dispi.inf_amd64*")
            if len(dir) > 0:
                self.NVSMI_command = os.path.join(dir[0], self.NVSMI_command + ".exe")

        try:
            sp = subprocess.Popen([self.NVSMI_command, '-q', '-d', 'TEMPERATURE'],
                                  **utils.subprocess_args(include_stdout=True))
            out_str = sp.communicate()
            out_str = out_str[0].decode().split("\n")

            for line in out_str:
                if "GPU Slowdown" in line:
                    self.gpu_static_data["tcrit"] = utils.to_float(line.split(": ")[1][:-1].strip()) - 5.0
                elif "GPU Shutdown" in line:
                    self.gpu_static_data["tmax"] = utils.to_float(line.split(": ")[1][:-1].strip())
                elif "GPU Max Operating" in line:
                    self.gpu_static_data["tmax"] = utils.to_float(line.split(": ")[1][:-1].strip()) - 8.0

            sp = subprocess.Popen([self.NVSMI_command,
                                   '--query-gpu=gpu_name,power.limit',
                                   '--format=csv,noheader,nounits'],
                                  **utils.subprocess_args(include_stdout=True))

            out_str = sp.communicate()
            out_str = out_str[0].decode().replace("\n", "").replace("\r", "").split(", ")

            try:
                self.gpu_static_data["name"] = out_str[0]
            except:
                self.gpu_static_data["name"] = self.gpu_static_data.get("name", "Unknown")
            try:
                pmax = int(float(out_str[1]))
            except:
                pmax = 0
            self.gpu_static_data["pmax"] = pmax or 150
            self.gpu_static_data["pwarn"] = pmax * 0.75 or 150
            self.gpu_static_data["pcrit"] = pmax * 0.9 or 150
        except:
            logging.error(traceback.format_exc())

    def get_gpu_data(self):

        gpu_installed = self.gpu_static_data.get("gpu_installed", [])

        if gpu_installed.get("nvidia", False):
            if self.queryNVML:
                self.get_nvidia_data_nvml()
            if not self.queryNVML:
                self.get_nvidia_data()

        elif gpu_installed.get("amd", False) or gpu_installed.get("ati", False):
            self.get_ati_data()

        else:
            self.query_gpu = False

    def get_nvidia_data_nvml(self):
        # https://medium.com/devoops-and-universe/monitoring-nvidia-gpus-cd174bf89311
        # https://docs.nvidia.com/deploy/nvml-api/

        try:
            if self.nvsmi is None:
                self.nvsmi = nvidia_smi.getInstance()
            output = self.nvsmi.DeviceQuery('gpu_name,utilization.gpu,fan.speed,temperature.gpu,power.draw,power.limit')
            gpuData = output.get("gpu", {})
            if gpuData:
                gpuData = gpuData[0]

            self.gpu_static_data["product_name"] = "name"
            try:
                self.gpu_data["usage"] = int(gpuData.get("utilization", {}).get("gpu_util", 0)) or self.gpu_data.get(
                    "usage", 0)
            except:
                self.gpu_data["usage"] = self.gpu_data.get("usage", 0)
            try:
                self.gpu_data["fanspeed"] = int(
                    self.gpu_data.get("fanspeed", gpuData.get("fan_speed", 0))) or self.gpu_data.get("fanspeed", 0)
            except:
                self.gpu_data["fanspeed"] = self.gpu_data.get("fanspeed", 0)
            try:
                self.gpu_data["temp"] = int(gpuData.get("temperature", {}).get("gpu_temp", 0)) or self.gpu_data.get(
                    "temp", 0)
            except:
                self.gpu_data["temp"] = self.gpu_data.get("temp", 0)
            try:
                self.gpu_data["power"] = int(
                    gpuData.get("power_readings", {}).get("power_draw", 0)) or self.gpu_data.get("power", 0)
            except:
                self.gpu_data["power"] = self.gpu_data.get("power", 0)

        except:
            self.queryNVML = False

    def get_nvidia_data(self):
        # WARNING: On Ubuntu, NVIDIA-SMI will only work with proprietary drivers (not *-open)
        # https://www.microway.com/hpc-tech-tips/nvidia-smi_control-your-gpus/
        # https://developer.download.nvidia.com/compute/DCGM/docs/nvidia-smi-367.38.pdf

        try:
            sp = subprocess.Popen([self.NVSMI_command,
                                   '--query-gpu=gpu_name,temperature.gpu,fan.speed,utilization.gpu,power.draw',
                                   '--format=csv,noheader,nounits'],
                                  **utils.subprocess_args(include_stdout=True))
            out_str = sp.communicate()
            out_str = out_str[0].decode().replace("\n", "").replace("\r", "").split(", ")

            try:
                self.gpu_data["name"] = int(out_str[0]) or self.gpu_data.get("name", "Unknown")
            except:
                self.gpu_data["name"] = self.gpu_data.get("name", "Unknown")
            try:
                self.gpu_data["temp"] = int(out_str[1]) or self.gpu_data.get("temp", 0)
            except:
                self.gpu_data["temp"] = self.gpu_data.get("temp", 0)
            try:
                self.gpu_data["fanspeed"] = int(out_str[2]) or self.gpu_data.get("fanspeed", 0)
            except:
                self.gpu_data["fanspeed"] = self.gpu_data.get("fanspeed", 0)
            try:
                self.gpu_data["usage"] = int(out_str[3]) or self.gpu_data.get("usage", 0)
            except:
                self.gpu_data["usage"] = self.gpu_data.get("usage", 0)
            try:
                self.gpu_data["power"] = int(out_str[4]) or self.gpu_data.get("power", 0)
            except:
                self.gpu_data["power"] = self.gpu_data.get("power", 0)

        except:
            self.query_gpu = False
            logging.error(traceback.format_exc())

    def get_ati_data(self):

        # Try: 'aticonfig --odgt' (GPU Temperature) and 'aticonfig --pplib-cmd "get fanspeed 0"' (GPU Fan)
        # Maybe it doesn't work if not using two separate calls (command)
        command = 'aticonfig --odgt --odgc --pplib-cmd "get fanspeed 0"'
        sp = subprocess.Popen(command, **utils.subprocess_args(include_stdout=True))
        out_str = sp.communicate()
        out_str = out_str[0].decode().replace("\n", "").split(", ")
        # Not sure if the command works and how its result will look like!!!
        # Must investigate how to get name, twarn, tcrit and tmax values too!!!
        self.gpu_data["temp"] = out_str[1]
        self.gpu_data["fanspeed"] = out_str[2]

    def get_sys_data(self, archOS, sys_data=None):

        if not sys_data:
            sys_data.append(("Name", platform.node()))
            if "Windows" in archOS:
                sys_data.append(("OS", ' '.join([platform.system(), platform.release()])))
                sys_data.append(("Ver", platform.version()))
            else:
                if "-with-" in settings.archOS:
                    sys_data.append(("OS", settings.archOS.rsplit("-with-")[1]))
                else:
                    sys_data.append(("OS", settings.archOS))
                sys_data.append(("Ver", platform.release()))
            sys_data.append(("CPU", self.cpu_static_data.get("name", "")))
            sys_data.append(("GPU", self.gpu_static_data.get("name", "")))
            sys_data.append(("Boot",
                             str(dt.datetime.now() - dt.datetime.fromtimestamp(psutil.boot_time())).rsplit(":", 1)[
                                 0].replace(":", "h") + "m"))
        else:
            sys_data[5] = ("Boot",
                           str(dt.datetime.now() - dt.datetime.fromtimestamp(psutil.boot_time())).rsplit(":", 1)[
                               0].replace(":", "h") + "m")

        return sys_data

    def get_sensors(self):

        if "Windows" in settings.archOS:
            cpu_percent = self.cpu_data.get("usage")
        else:
            try:
                cpu_percent = int(psutil.cpu_percent())
            except:
                cpu_percent = 0.0
                logging.error(traceback.format_exc())

        try:
            memory_percent = int(psutil.virtual_memory().percent)
        except:
            memory_percent = 0.0
            logging.error(traceback.format_exc())

        try:
            disk_percent = int(psutil.disk_usage(self.sys_drive).percent)
        except:
            disk_percent = 0.0
            logging.error(traceback.format_exc())

        sensors = {"cpu": cpu_percent, "mem": memory_percent, "dsk": disk_percent}

        return sensors

    def getFPS(self, fps):
        self.gpu_fps = fps

    def run(self):
        self.timer = utils.Timer()
        self.timer.start(1000, self.getData, start_now=True)

    def getData(self):

        if self.keep.is_set():

            # CPU Data (OS-dependent)
            if self.query_cpu:
                self.get_cpu_data()

            # GPU Data
            if self.query_gpu:
                self.get_gpu_data()

            # System Data
            if self.show_sys_data:
                self.sys_data = self.get_sys_data(settings.archOS, self.sys_data)

            # Other sensors data
            sensors = self.get_sensors()

            # Info to monitor
            self.sensors_data = []
            if self.game_mode:
                self.sensors_data.append(("FPS", self.gpu_fps, "", 240, 29, 23))
            self.sensors_data.append(("CPU Usage", sensors.get("cpu", 0), "%", 100, 75, 90))
            self.sensors_data.append(("CPU Temp", self.cpu_data.get("temp", 0), settings.uniTmp,
                                      self.cpu_static_data.get("tmax", 0), self.cpu_static_data.get("twarn", 0),
                                      self.cpu_static_data.get("tcrit", 0)))
            self.sensors_data.append(("Mem Usage", sensors.get("mem", 0), "%", 100, 75, 90))
            if not self.game_mode:
                self.sensors_data.append(("Disk Usage", sensors.get("dsk", 0), "%", 100, 75, 90))
            self.sensors_data.append(("GPU Usage", self.gpu_data.get("usage", 0), "%", 100, 75, 90))
            self.sensors_data.append(("GPU Temp", self.gpu_data.get("temp", 0), settings.uniTmp,
                                      self.gpu_static_data.get("tmax", 0), self.gpu_static_data.get("twarn", 0),
                                      self.gpu_static_data.get("tcrit", 0)))
            self.sensors_data.append(("GPU Fan", self.gpu_data.get("fanspeed", 0), "%", 100, 85, 95))
            self.sensors_data.append(("GPU Power", self.gpu_data.get("power", 0), "W",
                                      self.gpu_static_data.get("pmax", 150), self.gpu_static_data.get("pwarn", 150),
                                      self.gpu_static_data.get("pcrit", 150)))

            self.callback(self.sensors_data, self.sys_data)

        else:
            self.timer.stop()


class GetFPS_Linux(threading.Thread):
    # https://linuxhint.com/show_fps_counter_linux_games/
    # https://dri.freedesktop.org/wiki/libGL/
    # https://notebookgpu.blogspot.com/2018/08/monitorizar-graficos-hibridos-en-linux.html
    # https://refspecs.linuxfoundation.org/LSB_1.3.0/gLSB/gLSB/libgl.html
    # https://docs.mesa3d.org/install.html
    # https://stackoverflow.com/questions/39205116/how-to-initialize-opengl-with-glxchoosefbconfig-and-ctypes-module
    # https://www.reddit.com/r/linux_gaming/comments/au3k4p/mesa_vulkan_hud_now_has_fps_counter_and_is/

    def __init__(self, keep, callback):
        super().__init__()

        self.keep = keep
        self.callback = callback

        global Qprocess
        self.Qprocess = Qprocess

        self.appName = ""
        self.sp = None
        self.dumpFile = None

    def changeAppName(self, appName):

        self.appName = appName
        self.resetDumpFile()

        if self.appName:
            # TODO: all these options rely on mesa drivers (is there a way to do it with NVIDIA drivers? Maybe *-open drivers?)
            # https://github.com/NVIDIA/nvidia-query-resource-opengl

            # https://www.reddit.com/r/linux_gaming/comments/au3k4p/mesa_vulkan_hud_now_has_fps_counter_and_is/
            # Requires libGL.so (normally shipped when using mesa drivers)  --> works intermitently, don't know why
            cmd1 = r"LIBGL_SHOW_FPS=1 %s 2>&1 | tee /dev/stderr | sed -u -n -e '/^libGL: FPS = /{s/.* \([^ ]*\)= /\1/;p}'" % self.appName  # > fps" % self.appName
            # Requires mesa-utils (sudo apt install mesa-utils)
            cmd2 = 'GALLIUM_HUD_PERIOD=0.5 GALLIUM_HUD_DUMP_DIR=. GALLIUM_HUD_VISIBLE=false GALLIUM_HUD=simple,fps %s' % self.appName
            # For Vulkan:
            # cmd3 = 'VK_LAYER_PATH=/opt/mesa-master/share/vulkan/explicit_layer.d LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/opt/mesa-master/share/vulkan/explicit_layer.d VK_INSTANCE_LAYERS=VK_LAYER_MESA_overlay VK_LAYER_MESA_OVERLAY_POSITION=bottom-left' % self.appName
            cmd3 = 'VK_LAYER_PATH=./resources/:$VK_LAYER_PATH VK_INSTANCE_LAYERS=VK_LAYER_LUNARG_api_dump' % self.appName
            # Check this: https://vulkan.lunarg.com/doc/sdk/1.3.236.0/windows/api_dump_layer.html
            # And this: https://github.com/LunarG/VulkanTools and https://github.com/LunarG/VulkanTools/blob/master/layersvt/VkLayer_api_dump.json.in
            # The format seems to be .json, and the library to use is libVkLayer_api_dump.so (not sure if it must be pre-loaded with LD_LIBRARY_PATH)

            self.sp = subprocess.Popen(cmd2, shell=True, encoding="utf-8",
                                       # env={**os.environ, "PYTHONUNBUFFERED": "1"}, start_new_session=True,
                                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL)
            with self.Qprocess.mutex:
                self.Qprocess.queue.clear()
            self.Qprocess.put(self.sp)
            self.callback(0)

    def run(self) -> None:

        while self.keep.is_set():

            if self.dumpFile is None and self.sp is not None and self.sp.poll() is None:
                try:
                    self.dumpFile = open("fps", "r")

                except:
                    self.dumpFile = None

            if self.dumpFile is not None:
                line = self.dumpFile.readline()
                if line:
                    fps = line.split(".")[0]
                    self.callback(fps)

            # If using LIBGL_SHOW_FPS this is a better solution (not using a file)
            # fps = 0
            # logging.debug("READ")
            # line = self.sp.stdout.readline()
            # logging.debug("LINE", line)
            # fps = line.split(".")[0]
            # logging.debug("FPS", fps)
            # self.callback(fps)

        self.resetDumpFile()

    def resetDumpFile(self):

        if self.sp is not None:
            try:
                subprocess.Popen.kill(self.sp)
            except:
                pass
        self.sp = None

        if self.dumpFile is not None and not self.dumpFile.closed:
            self.dumpFile.close()

        if os.path.exists("fps"):
            try:
                os.remove("fps")
            except:
                pass
        self.dumpFile = None


class GetFPS_Win(threading.Thread):

    def __init__(self, keep, callback):
        super().__init__()

        self.keep = keep
        self.callback = callback

        global Qprocess
        self.Qprocess = Qprocess

        # This is great! but... how to get the .dll file???
        # https://github.com/Andrey1994/fps_inspector_sdk
        # self.lib = ctypes.cdll.LoadLibrary(utils.resource_path(__file__, os.path.join('resources', 'PresentMon.dll')))

        self.cmd = [utils.resource_path(__file__, "resources/PresentMon-1.8.0-x64.exe"), '-output_stdout',
                    '-no_top', '-stop_existing_session', '-session_name', 'sysmon']
        self.sp = subprocess.Popen(self.cmd, shell=False, env={**os.environ, "PYTHONUNBUFFERED": "1"},
                                   encoding="utf-8", universal_newlines=True,
                                   creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
                                   stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL)
        self.Qprocess.put(self.sp)

        self.appName = ""
        self.lastSeen = 0
        self.second = 0
        self.currentSecond = 0
        self.msBtwPresents = 0
        self.presentsCount = 0

    def changeAppName(self, appName):
        self.appName = appName
        self.callback(0)

    def run(self):

        # Discard header
        _ = self.sp.stdout.readline()

        while self.keep.is_set():

            line = self.sp.stdout.readline()
            line = line.split(",")

            if len(line) > 9:
                self.currentSecond = int(line[7].split(".")[0])  # Seconds since PresentMon started

                if self.second < self.currentSecond:
                    self.second = self.currentSecond
                    if self.presentsCount > 0:
                        fps = int(1000 / (self.msBtwPresents / self.presentsCount))
                        # fps = self.presentsCount
                    else:
                        fps = 0
                    self.callback(fps)
                    self.msBtwPresents = 0
                    self.presentsCount = 0

                if self.appName and self.appName.lower() in line[0].lower():
                    self.msBtwPresents += float(line[9])
                    self.presentsCount += 1

        subprocess.Popen.kill(self.sp)
        self.cmd = [utils.resource_path(__file__, "resources/PresentMon-1.8.0-x64.exe"), '-terminate_existing']
        self.sp = subprocess.Popen(self.cmd, shell=False, env={**os.environ, "PYTHONUNBUFFERED": "1"},
                                   encoding="utf-8", universal_newlines=True,
                                   creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
                                   stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL)
        subprocess.Popen.kill(self.sp)


class SysMon(tk.Tk):

    def __init__(self):
        tk.Tk.__init__(self)

        if utils.checkInstances(settings.system_caption) > 0:
            raise Exception("Only one program instance allowed. Exiting...")

        self.firstRun = True

        global Qprocess
        self.Qprocess = Qprocess

        # Window attributes
        self.title(settings.system_caption)
        self.overrideredirect(True)
        if "Windows" in settings.archOS:
            if len(sys.argv) == 1 or (len(sys.argv) > 1 and sys.argv[1] != "not_admin"):
                self.win_get_admin()
            from ctypes import windll
            windll.shcore.SetProcessDpiAwareness(1)
            self.attributes('-toolwindow', True)
        elif "Linux" in settings.archOS:
            self.attributes("-type", "dock")
        else:
            raise NotImplementedError
        self.attributes('-topmost', True)
        self.configure(bg=settings.bg_color)
        self.wait_visibility(
            self)  # Required for Linux. Must go after overrideredirect, but before setting opacity ("-alpha")
        if settings.opacity < 1.0:
            self.wm_attributes("-alpha", settings.opacity)

        # Define settings and variables
        self.sensors_data = {}
        self.sys_data = {}
        self.monitor = None
        self.X = self.Y = self.W = self.H = 0

        self.show_sys_data = False
        self.game_mode = False
        self.sys_mode_lap = settings.update
        self.game_mode_lap = settings.update_g
        self.mouse_X_pos = 0
        self.mouse_Y_pos = 0

        self.gauge_radius = settings.gauge_size * self.winfo_screenheight() / 1440
        self.size_gap = int(self.gauge_radius / 8)
        self.size_gap1 = int(self.gauge_radius / 13)
        self.size_gap2 = int(self.gauge_radius / 10)
        self.gauge_font_size = int(self.gauge_radius * 0.6)
        self.font_size = self.gauge_font_size / 2.5

        # Prepare UI
        self.horizontal = settings.orientation
        self.setupUI(firstRun=True)
        self.window = pwc.Window(self.frame())
        x, y = self.recalcPos(0, 0)
        self.geometry('+{0}+{1}'.format(x, y))

        # Event bindings
        self.bind('<Button-1>', self.on_click)
        self.bind('<Button-3>', self.startConfig)
        self.bind('<B1-Motion>', self.on_motion)

        # Settings window
        self.confNotStarted = True
        self.config = Config(self)
        self.config.withdraw()

        self.altPressed = False
        self.ctlPressed = False
        self.listener = keyboard.Listener(
            on_press=self.on_press,
            on_release=self.on_release
        )
        self.listener.start()
        self.menu = None

        # Starting workers threads
        self.keep = threading.Event()
        self.keep.set()
        self.display = threading.Event()

        self.get_data = GetData(self.keep, self.displayData)
        self.get_data.daemon = True
        self.get_data.start()

        if "Windows" in settings.archOS:
            self.get_fps = GetFPS_Win(self.keep, self.get_data.getFPS)
        else:
            self.get_fps = GetFPS_Linux(self.keep, self.get_data.getFPS)
        self.getTargetApp()
        self.get_fps.daemon = True
        self.get_fps.start()

    def setupUI(self, firstRun=False):

        if firstRun:

            # Widgets
            self.gauge_frame = tk.PhotoImage(file=settings.icons_folder + "gauge_frame.png")
            self.gauge_frame = self.gauge_frame.subsample(int(self.gauge_frame.width() / (self.gauge_radius * 2)),
                                                          int(self.gauge_frame.height() / (self.gauge_radius * 2)))

            self.gauge_shadow = tk.PhotoImage(file=settings.icons_folder + "gauge_shadow.png")
            self.gauge_shadow = self.gauge_shadow.subsample(int(self.gauge_shadow.width() / (self.gauge_radius * 2)),
                                                            int(self.gauge_shadow.height() / (self.gauge_radius / 10)))

            self.sys_label = tk.Label(self, text="", justify="left", anchor="center", bg=settings.bg_color,
                                      font=(settings.font, int(self.font_size)), fg=settings.sys_name_color)

            self.style = settings.style
            self.styles = settings.styles

            self.titles_labels = []
            self.gauge_canvas = []
            self.shadow_canvas = []
            self.shadow_canvas2 = []
            self.values_labels = []
            self.valuest_labels = []
            self.gauge_lines = []
            self.gauge_arcs = []
            self.gauge_arcs2 = []

            for i in range(8):
                self.gauge_canvas.append(tk.Canvas(self, width=self.gauge_frame.width(), height=int(self.gauge_radius * 0.9),
                                                   bg=settings.bg_color, highlightthickness=0, relief='flat'))
                self.values_labels.append(tk.Label(self, bg=settings.bg_color, font=(settings.gauge_font, int(self.gauge_font_size)),
                                                   fg=settings.gsafe_color, padx=0, pady=0))
                self.valuest_labels.append(tk.Label(self, bg=settings.bg_color, font=(settings.font, int(self.gauge_font_size / 2)),
                                                    fg=settings.gsafe_color, padx=0, pady=0))
                self.shadow_canvas.append(tk.Canvas(self, width=self.gauge_shadow.width(), height=int(self.gauge_radius * 0.1),
                                                    bg=settings.bg_color, highlightthickness=0, relief='flat'))
                self.shadow_canvas[i].create_image(0, 0, image=self.gauge_shadow, anchor=tk.NW)
                self.titles_labels.append(tk.Label(self, text="", bg=settings.bg_color,
                                                   font=(settings.font, int(self.font_size)), fg=settings.titles_color))
                self.gauge_lines.append(None)
                self.gauge_arcs.append(None)
                self.gauge_arcs2.append(None)

        # Placing widgets as per selected style
        if self.style in ("conky", "numbers"):

            if self.horizontal:

                for i in range(len(self.gauge_canvas)):
                    self.titles_labels[i].grid(row=3, column=i * 2, columnspan=2, sticky=tk.S,
                                               padx=0, pady=0, ipadx=0, ipady=0)
                    self.shadow_canvas[i].grid_remove()
                    if self.game_mode and i == 0:
                        self.gauge_canvas[i].grid_remove()
                        self.valuest_labels[i].grid_remove()
                        self.values_labels[i].grid(row=1, rowspan=2, column=i * 2, columnspan=2, sticky=tk.E + tk.W,
                                                   padx=0, pady=0, ipadx=self.size_gap, ipady=0)
                    else:
                        self.gauge_canvas[i].grid(row=0, rowspan=4, column=i * 2, columnspan=2, padx=(3, 3),
                                                  pady=(self.size_gap1, self.size_gap1), ipadx=self.size_gap * 2,
                                                  ipady=self.size_gap2 * 7)
                        if self.style == "numbers":
                            self.gauge_canvas[i].configure(highlightthickness=1,
                                                           highlightbackground=settings.gnoavail_color)
                            self.values_labels[i].grid(row=1, rowspan=3, column=i * 2, columnspan=1, sticky=tk.E,
                                                       padx=0, pady=(0, self.size_gap * 2), ipadx=0, ipady=0)
                            self.valuest_labels[i].grid(row=2, rowspan=1, column=(i * 2) + 1, columnspan=1,
                                                        sticky=tk.W + tk.N,
                                                        padx=0, pady=(0, self.size_gap * 2), ipadx=0, ipady=0)
                        else:
                            self.gauge_canvas[i].configure(highlightthickness=0)
                            self.values_labels[i].grid(row=2, rowspan=2, column=i * 2, columnspan=1, sticky=tk.E + tk.N,
                                                       padx=0, pady=(0, self.size_gap * 2), ipadx=0, ipady=0)
                            self.valuest_labels[i].grid(row=2, rowspan=2, column=(i * 2) + 1, columnspan=1,
                                                        sticky=tk.W + tk.N,
                                                        padx=0, pady=(0, self.size_gap * 2), ipadx=0, ipady=0)

            else:

                for i in range(len(self.gauge_canvas)):
                    self.shadow_canvas[i].grid_remove()
                    if self.game_mode and i == 0:
                        self.titles_labels[i].grid(row=0 + i * 4, column=0, columnspan=2, sticky="",
                                                   padx=0, pady=0, ipadx=0, ipady=0)
                        self.gauge_canvas[i].grid_remove()
                        self.valuest_labels[i].grid_remove()
                        self.values_labels[i].grid(row=1, rowspan=2, column=0, columnspan=4, sticky="",
                                                   padx=0, pady=(0, self.size_gap), ipadx=self.size_gap, ipady=0)
                    else:
                        self.titles_labels[i].grid(row=3 + i * 4, column=0, columnspan=2, sticky="",
                                                   padx=0, pady=(self.size_gap * 5, 0), ipadx=0, ipady=0)
                        self.gauge_canvas[i].grid(row=i * 4, rowspan=4, column=0, columnspan=2,
                                                  padx=(self.size_gap1, self.size_gap1),
                                                  pady=(self.size_gap1, self.size_gap1), ipadx=self.size_gap * 2,
                                                  ipady=self.size_gap2 * 7)
                        if self.style == "numbers":
                            self.gauge_canvas[i].configure(highlightthickness=1,
                                                           highlightbackground=settings.gnoavail_color)
                            self.valuest_labels[i].grid(row=2 + i * 4, rowspan=1, column=1, columnspan=1,
                                                        sticky=tk.W + tk.S,
                                                        padx=0, pady=(0, 0), ipadx=0, ipady=0)
                            self.values_labels[i].grid(row=1 + i * 4, rowspan=3, column=0, columnspan=1, sticky=tk.E,
                                                       padx=0, pady=(0, self.size_gap * 2), ipadx=0, ipady=0)
                        else:
                            self.gauge_canvas[i].configure(highlightthickness=0)
                            self.valuest_labels[i].grid(row=3 + i * 4, rowspan=2, column=1, columnspan=1,
                                                        sticky=tk.W + tk.N,
                                                        padx=0, pady=(0, self.size_gap * 2), ipadx=0, ipady=0)
                            self.values_labels[i].grid(row=2 + i * 4, rowspan=2, column=0, columnspan=1, sticky=tk.E,
                                                       padx=0, pady=(0, self.size_gap * 2), ipadx=0, ipady=0)
        else:

            if self.horizontal:

                for i in range(len(self.gauge_canvas)):
                    self.titles_labels[i].grid(row=0, column=i + i * 2, columnspan=2, pady=0, ipadx=0, ipady=0)
                    self.gauge_canvas[i].configure(highlightthickness=0)
                    if self.game_mode and i == 0:
                        self.gauge_canvas[i].grid_remove()
                        self.shadow_canvas[i].grid_remove()
                        self.valuest_labels[i].grid_remove()
                        self.values_labels[i].grid(row=1, rowspan=5, column=i * 2, columnspan=2, sticky=tk.E + tk.W,
                                                   padx=0, pady=(0, self.size_gap * 2), ipadx=self.size_gap, ipady=0)
                    else:
                        self.gauge_canvas[i].grid(row=1, rowspan=2, column=i + i * 2, columnspan=2,
                                                  padx=(self.size_gap, 0), pady=0, ipadx=0, ipady=0)
                        self.shadow_canvas[i].grid(row=3, column=i + i * 2, columnspan=2,
                                                   padx=0, pady=0, ipadx=0, ipady=0)
                        self.valuest_labels[i].grid(row=4, column=i + i * 2 + 1, columnspan=1, sticky=tk.W + tk.N,
                                                    padx=0, pady=0, ipadx=0, ipady=0)
                        self.values_labels[i].grid(row=4, rowspan=2, column=i + i * 2, columnspan=1, sticky=tk.E,
                                                   padx=0, pady=0, ipadx=0, ipady=0)

            else:

                for i in range(len(self.gauge_canvas)):
                    self.titles_labels[i].grid(row=i + i * 4, column=0, columnspan=2,
                                               padx=0, pady=(self.size_gap * 3, 0), ipadx=0, ipady=0)
                    self.gauge_canvas[i].configure(highlightthickness=0)
                    self.shadow_canvas[i].grid_remove()
                    if self.game_mode and i == 0:
                        self.titles_labels[i].grid(row=i + i * 4, column=0, columnspan=4, padx=0,
                                                   pady=(self.size_gap * 3, 0), ipadx=0,
                                                   ipady=0)
                        self.gauge_canvas[i].grid_remove()
                        self.valuest_labels[i].grid_remove()
                        self.values_labels[i].grid(row=1 + i * 4, rowspan=2, column=0, columnspan=4, sticky=tk.E + tk.W,
                                                   padx=0, pady=0, ipadx=self.size_gap, ipady=0)
                        self.shadow_canvas[i].grid(row=3 + i * 4, column=0,
                                                   padx=0, pady=(0, self.size_gap * 2), ipadx=0, ipady=0, columnspan=4)
                    else:
                        self.titles_labels[i].grid(row=i + i * 4, column=0, columnspan=2,
                                                   padx=0, pady=(self.size_gap * 3, 0), ipadx=0, ipady=0)
                        self.gauge_canvas[i].grid(row=i + i * 4, rowspan=3, column=2, columnspan=2,
                                                  padx=0, pady=0, ipadx=0, ipady=0, sticky=tk.S)
                        self.valuest_labels[i].grid(row=i + 1 + i * 4, column=1, columnspan=1, sticky=tk.W,
                                                    padx=0, pady=0, ipadx=0, ipady=0)
                        self.values_labels[i].grid(row=i + 1 + i * 4, rowspan=2, column=0, columnspan=1, sticky=tk.E,
                                                   padx=0, pady=0, ipadx=0, ipady=0)
                        self.shadow_canvas[i].grid(row=i + 3 + i * 4, column=2, columnspan=2,
                                                   padx=0, pady=0, ipadx=0, ipady=0, sticky=tk.N)

        self.setupSysDataUI()
        self.update()
        if not firstRun:
            self.displayData(self.sensors_data, self.sys_data)

    def win_get_admin(self):

        ret = utils.win_run_as_admin(force_admin=False)

        if not ret:
            if ret is False:
                logging.warning("WARNING: Could not gain admin privileges. Exec it as admin to avoid missing some data")
                if sys.argv[0][-3:] != ".py":
                    sys.exit()
            else:
                sys.exit()

        return ret

    def getTargetApp(self, appName=""):

        if appName:
            path = appName.rsplit(os.sep, 1)
            if len(path) > 0:
                name = path[1]
            else:
                name = appName
        else:
            if "Windows" in settings.archOS:
                win = pwc.getActiveWindow()
                name = "dwm.exe"
                if win:
                    try:
                        appName = win.getAppName()
                    except:
                        appName = ""
                    if (appName and appName != "explorer.exe" and "sysmon" not in appName.lower()):
                        name = appName
            elif len(sys.argv) > 1:
                name = sys.argv[1]
            else:
                name = ""
        self.get_fps.changeAppName(name)
        self.appName = name

    def setupSysDataUI(self):

        self.sys_label.grid_remove()

        cols, rows = self.grid_size()
        if self.horizontal:
            self.sys_label.grid(row=0, rowspan=rows, column=cols, columnspan=1, sticky=tk.W)
        else:
            self.sys_label.grid(row=rows, column=0, columnspan=cols, sticky=tk.W)
        self.geometry("")

    def drawSysData(self):

        if self.show_sys_data:
            if not self.sys_label.grid_info():
                self.setupSysDataUI()

            titles = ""
            for i, item in enumerate(self.sys_data):
                titles += item[0] + ":\t" + item[1] + "\n"

            self.sys_label.configure(text=titles[:-1])

        elif self.sys_label.grid_info():
            self.sys_label.grid_remove()
            self.geometry("")

    def drawGauge(self, i, title, radius, gauge_color, index_size, value, vtype, vtype_color, vmin, vmax, warn,
                  crit, back_color, index_color, title_color, min_color, safe_color, warn_color, crit_color, font,
                  font_size, vtype_font):

        value = int(utils.to_float(value))
        text = str(value)
        pad = "0" * (3 - len(text)) if not vtype else ""
        colors = [(crit, crit_color), (warn, warn_color), (vmin + 0.001, safe_color), (vmin, min_color)]
        color = safe_color
        if not vtype and value == 0:
            color = gauge_color
        else:
            for item in colors:
                if (vtype and value >= item[0]) or (not vtype and value <= item[0]):
                    color = item[1]
                    break

        self.gauge_canvas[i].delete("all")
        if self.style in ("gauge", "arc", "arc_with_indicator"):
            self.gauge_canvas[i].create_image(0, 0, image=self.gauge_frame, anchor=tk.NW)

        if vtype:

            if self.style == "conky":
                self.gauge_arcs2[i] = self.gauge_canvas[i].create_arc(self.size_gap, self.size_gap,
                                                                      self.gauge_canvas[i].winfo_width() - self.size_gap * 4,
                                                                      self.gauge_canvas[i].winfo_height(), start=225,
                                                                      extent=-225, style=tk.ARC,
                                                                      width=self.size_gap * 2,
                                                                      outline=gauge_color, fill=back_color)
                try:
                    extent = min(-2, int(-value * (225 / max(1, vmax))))
                except:
                    extent = 0
                self.gauge_arcs[i] = self.gauge_canvas[i].create_arc(self.size_gap, self.size_gap,
                                                                     self.gauge_canvas[i].winfo_width() - self.size_gap * 4,
                                                                     self.gauge_canvas[i].winfo_height(), start=225,
                                                                     extent=extent, style=tk.ARC,
                                                                     width=self.size_gap * 2,
                                                                     outline=color, fill=back_color)
            elif self.style == "pie":
                self.gauge_arcs2[i] = self.gauge_canvas[i].create_arc(self.size_gap * 2, 0,
                                                                      self.gauge_canvas[i].winfo_width() - self.size_gap * 2,
                                                                      self.gauge_canvas[i].winfo_height() * 2,
                                                                      start=180, extent=-180, style=tk.PIESLICE,
                                                                      width=0, outline="", fill=gauge_color)
                extent = min(-1, int(-value * (180 / max(1, vmax))))
                self.gauge_arcs[i] = self.gauge_canvas[i].create_arc(self.size_gap * 2, 0,
                                                                     self.gauge_canvas[i].winfo_width() - self.size_gap * 2,
                                                                     self.gauge_canvas[i].winfo_height() * 2, start=180,
                                                                     extent=extent, style=tk.PIESLICE, width=0,
                                                                     outline="", fill=color)

            elif self.style in ("arc", "arc_with_indicator"):
                self.gauge_arcs2[i] = self.gauge_canvas[i].create_arc(self.size_gap * 2, self.size_gap,
                                                                      self.gauge_canvas[i].winfo_width() - self.size_gap * 2,
                                                                      self.gauge_canvas[i].winfo_height() * 2 - self.size_gap,
                                                                      start=180, extent=-180, style=tk.ARC,
                                                                      width=self.size_gap * 2,
                                                                      outline=gauge_color, fill="")
                extent = min(-1, int(-value * (180 / max(1, vmax))))
                self.gauge_arcs[i] = self.gauge_canvas[i].create_arc(self.size_gap * 2, self.size_gap,
                                                                     self.gauge_canvas[i].winfo_width() - self.size_gap * 2,
                                                                     self.gauge_canvas[i].winfo_height() * 2 - self.size_gap,
                                                                     start=180, extent=extent, style=tk.ARC,
                                                                     width=self.size_gap * 2,
                                                                     outline=color, fill="")

            if self.style in ("gauge", "arc_with_indicator"):
                x = self.gauge_canvas[i].winfo_width() / 2
                y = int(self.gauge_canvas[i].winfo_height() * 0.9)
                rotation = 180 * ((value - vmin) / max(1, (vmax - vmin))) - 90
                endx = x + int(radius * 0.8) * math.sin(math.radians(rotation))
                endy = y + int(radius * 0.8) * (-1) * math.cos(math.radians(rotation))
                self.gauge_lines[i] = self.gauge_canvas[i].create_line(x, y + self.size_gap1, endx,
                                                                       endy + self.size_gap1, width=index_size,
                                                                       fill=index_color if self.style == "gauge" else color)

        if vtype:
            self.titles_labels[i].configure(text=title, fg=title_color)
        else:
            self.titles_labels[i].configure(text=title + ":" + self.appName.split(os.sep, 1)[-1].rsplit(".")[0][:12],
                                            fg=title_color)
        self.valuest_labels[i].configure(text=vtype, fg=color,
                                         font=(vtype_font, int(font_size * (0.3 if self.style == "numbers" else 0.5))))
        if vtype or settings.fbg_color == settings.bg_color:
            self.values_labels[i].configure(text=pad + text, font=(font, font_size), bg=back_color,
                                            fg=vtype_color if vtype_color != -1 else color, borderwidth=0,
                                            relief="flat")
        else:
            self.values_labels[i].configure(text=pad + text, font=(font, font_size), bg=settings.fbg_color,
                                            fg=vtype_color if vtype_color != -1 else color, borderwidth=4,
                                            relief="groove")

    def displayData(self, sensors_data, sys_data):

        if self.state() == "normal":
            self.window.alwaysOnTop()

        self.sensors_data = sensors_data
        self.sys_data = sys_data

        self.drawSysData()

        for i, gauge in enumerate(self.sensors_data):
            self.drawGauge(
                i=i,
                title=gauge[0],
                radius=self.gauge_radius,
                gauge_color=settings.gnoavail_color,
                index_size=self.gauge_radius / 10,
                value=gauge[1],
                vtype=gauge[2],
                vtype_color=-1,
                vmin=0,
                vmax=gauge[3],
                warn=gauge[4],
                crit=gauge[5],
                back_color=settings.bg_color,
                index_color=settings.gind_color,
                title_color=settings.sys_name_color,
                min_color=settings.gnoavail_color,
                safe_color=settings.gsafe_color if gauge[2] else settings.fsafe_color,
                warn_color=settings.gwarn_color,
                crit_color=settings.gcrit_color,
                font=settings.gauge_font,
                font_size=int(self.gauge_font_size * (1.8 if not gauge[2] or self.style == "numbers" else 1)),
                vtype_font=settings.font
            )

    def changeMode(self, mode):
        if mode != self.game_mode:
            self.game_mode = mode
            self.get_data.changeMode(self.game_mode)
            if self.game_mode:
                self.window.acceptInput(False)
            else:
                self.window.acceptInput(True)
            if self.show_sys_data:
                self.setupSysDataUI()
            self.setupUI()

    def changeStyle(self, style):
        style = self.styles[style]
        if self.style != style:
            self.style = style
            if self.show_sys_data:
                self.setupSysDataUI()
            self.setupUI()

    def changeOrientation(self, orientation):
        if self.horizontal != orientation:
            self.horizontal = orientation
            if self.show_sys_data:
                self.setupSysDataUI()
            self.setupUI()

    def changeSysData(self, show_sys_data):
        if self.show_sys_data != show_sys_data:
            self.show_sys_data = show_sys_data
            self.get_data.changeSysData(self.show_sys_data)
            if self.show_sys_data:
                self.setupSysDataUI()

    def showWindow(self, event=None):
        if self.state() != "normal":
            self.maximize()
        else:
            self.minimize()

    def on_click(self, e):
        if not self.game_mode:
            e.widget.focus_force()
            self.mouse_X_pos = self.winfo_pointerx() - self.winfo_x()
            self.mouse_Y_pos = self.winfo_pointery() - self.winfo_y()

    def on_motion(self, e):
        if not self.game_mode:
            x, y = self.recalcPos(e.x_root - self.mouse_X_pos, e.y_root - self.mouse_Y_pos)
            self.geometry('+{0}+{1}'.format(x, y))

    def startConfig(self, e):
        if self.config.state() == "withdrawn":
            if self.confNotStarted:
                self.confNotStarted = False
                self.X, self.Y, self.W, self.H = pwc.getWorkArea()
                self.config.geometry('+{0}+{1}'.format(self.X + 20, self.H - self.config.winfo_reqheight() - 20))
            self.config.deiconify()
        self.config.attributes('-topmost', True)
        self.config.attributes('-topmost', False)

    def minimize(self):
        self.state('withdrawn')  # Use this for fake roots (or it will generate two icons)
        # self.state('iconic')   # Use this for non-fake roots (or no icon will be present)

    def maximize(self, findApp=True):
        if "Windows" in settings.archOS and findApp:
            self.getTargetApp()
        self.state('normal')
        x, y = self.recalcPos(self.winfo_x(), self.winfo_y())
        if (x, y) != (self.winfo_x(), self.winfo_y()):
            self.geometry('+{0}+{1}'.format(x, y))

    def recalcPos(self, x, y):
        monitor = self.window.getDisplay()
        if self.monitor != monitor:
            self.monitor = monitor
            self.X, self.Y, self.W, self.H = pwc.getWorkArea(self.monitor)
        if x <= self.X + 20:
            x = self.X
        elif x + self.winfo_width() + 20 >= self.W:
            x = self.W - self.winfo_width()
        if y <= self.Y + 20:
            y = self.Y
        elif y + self.winfo_height() + 20 >= self.H:
            y = self.H - self.winfo_height()
        return x, y

    def on_press(self, key):
        if key == keyboard.Key.alt_l:
            self.altPressed = True
        elif key == keyboard.Key.ctrl_l:
            self.ctlPressed = True
        elif getattr(self.listener.canonical(key), "char", None) == settings.show_hide_key:
            if self.altPressed:
                if self.ctlPressed:
                    self.startConfig(None)
                else:
                    self.showWindow()
            self.altPressed = False
            self.ctlPressed = False

    def on_release(self, key):
        self.altPressed = False
        self.ctlPressed = False

    def closeAll(self):
        self.keep.clear()
        _ = keyboard.Listener.stop
        while not self.Qprocess.empty():
            p = self.Qprocess.get()
            subprocess.Popen.kill(p)
        self.get_fps.join()
        self.get_data.join()
        self.destroy()


class Config(tk.Toplevel):

    def __init__(self, parent):
        super().__init__(parent)

        self.parent = parent

        self.overrideredirect(True)
        if "Windows" in settings.archOS:
            self.attributes('-toolwindow', True)
        else:
            self.attributes('-type', 'dock')
        self.config(bg=settings.bg_color)

        self.font_size = 10
        self.mouse_X_pos = 0
        self.mouse_Y_pos = 0
        self.bind('<Button-1>', self.on_click)

        self.showMenu()

    def showMenu(self):

        bgcolor = settings.bg_color
        bgactcolor = "grey12"
        bgclickcolor = settings.gnoavail_color
        fgcolor = "GhostWhite"

        # self.canvas = tk.Canvas(self, bg="grey", highlightthickness=0)
        # self.canvas.grid(row=0, rowspan=19, column=0, columnspan=4)

        self.title_label = tk.Label(self, text="SysMon Settings")
        fontName = self.title_label["font"]
        font = fontName + " " + str(int(self.font_size * 1.5))
        boldFont = fontName + " " + str(int(self.font_size * 1.5)) + " bold"
        self.title_label.configure(bg=bgactcolor, fg=fgcolor, font=fontName + " " + str(int(self.font_size)),
                                   anchor=tk.W)
        self.title_label.bind('<B1-Motion>', self.on_motion)
        self.title_label.grid(row=1, column=0, columnspan=2, ipadx=20, ipady=5, sticky=tk.W + tk.E)
        self.exit_label = tk.Label(self, text="  x  ", bg=bgactcolor, fg=fgcolor,
                                   font=fontName + " " + str(int(self.font_size * 1.8)))
        self.exit_label.bind('<Enter>', lambda x: self.exit_label.configure(bg="red", fg="white"))
        self.exit_label.bind('<Leave>', lambda x: self.exit_label.configure(bg=bgactcolor, fg=fgcolor))
        self.exit_label.grid(row=1, column=3, sticky=tk.E)
        self.title_label.config(width=self.title_label.winfo_width(), height=self.exit_label.winfo_height())

        self.game_mode = tk.BooleanVar(master=self, value=self.parent.game_mode)
        self.mode_label = tk.Label(self, text="Mode")
        self.mode_label.configure(font=boldFont, bg=bgcolor, fg=fgcolor)
        self.mode_label.grid(row=2, column=0, columnspan=2, sticky=tk.W, padx=(20, 0), pady=(10, 0))
        self.mode_radio2 = tk.Radiobutton(self, text="System Mode", value=False, bg=bgcolor, fg=fgcolor,
                                          activebackground=bgactcolor, activeforeground=fgcolor, selectcolor=bgcolor,
                                          font=font, variable=self.game_mode,
                                          command=lambda: self.parent.changeMode(False), anchor=tk.W, relief="flat",
                                          highlightthickness=0)
        self.mode_radio2.grid(row=3, column=0, columnspan=2, sticky=tk.W + tk.E, padx=(50, 0))
        self.mode_radio2.bind('<Enter>', lambda x: self.mode_radio2.configure(bg=bgactcolor))
        self.mode_radio2.bind('<Leave>', lambda x: self.mode_radio2.configure(bg=bgcolor))
        self.mode_radio1 = tk.Radiobutton(self, text="Game Mode", value=True, bg=bgcolor, fg=fgcolor,
                                          activebackground=bgactcolor, activeforeground=fgcolor, selectcolor=bgcolor,
                                          font=font, variable=self.game_mode,
                                          command=lambda: self.parent.changeMode(True), anchor=tk.W, relief="flat",
                                          highlightthickness=0)
        self.mode_radio1.grid(row=4, column=0, columnspan=2, sticky=tk.W + tk.E, padx=(50, 0))
        self.mode_radio1.bind('<Enter>', lambda x: self.mode_radio1.configure(bg=bgactcolor))
        self.mode_radio1.bind('<Leave>', lambda x: self.mode_radio1.configure(bg=bgcolor))

        self.app_name = tk.Text(self, bg=bgclickcolor, fg=bgcolor, font=fontName + " " + str(int(self.font_size)),
                                height=1, width=35)
        self.app_name.grid(row=5, column=0, columnspan=2)
        self.app_name.grid_remove()
        self.defaultText = "Full path to game..."
        self.app_name.insert('1.0', self.defaultText)
        self.app_name.bind("<FocusIn>", self.focus_in)
        self.app_name.bind("<FocusOut>", self.focus_out)
        self.app_name.bind('<Return>', self.control_return)
        self.app_name.bind("<Delete>", self.control_delete)
        self.app_name.bind("<BackSpace>", self.control_delete)

        self.app_button = tk.Button(self, text="Go", bg=bgcolor, fg=fgcolor, command=self.getAppName)
        self.app_button.grid(row=5, column=3, sticky=tk.E)
        self.app_button.grid_remove()

        self.horizontal = tk.BooleanVar(master=self, value=self.parent.horizontal)
        self.orient_label = tk.Label(self, text="Orientation", bg=bgcolor, fg=fgcolor, font=boldFont)
        self.orient_label.grid(row=6, column=0, columnspan=2, sticky=tk.W, padx=(20, 0), pady=(10, 0))
        self.orient_radio1 = tk.Radiobutton(self, text="Horizontal", value=True, bg=bgcolor, fg=fgcolor,
                                            activebackground=bgactcolor, activeforeground=fgcolor, selectcolor=bgcolor,
                                            font=font, variable=self.horizontal,
                                            command=(lambda: self.parent.changeOrientation(True)), anchor=tk.W,
                                            relief="flat", highlightthickness=0)
        self.orient_radio1.grid(row=7, column=0, columnspan=2, sticky=tk.W + tk.E, padx=(50, 0))
        self.orient_radio1.bind('<Enter>', lambda x: self.orient_radio1.configure(bg=bgactcolor))
        self.orient_radio1.bind('<Leave>', lambda x: self.orient_radio1.configure(bg=bgcolor))
        self.orient_radio2 = tk.Radiobutton(self, text="Vertical", value=False, bg=bgcolor, fg=fgcolor,
                                            activebackground=bgactcolor, activeforeground=fgcolor, selectcolor=bgcolor,
                                            font=font, variable=self.horizontal,
                                            command=(lambda: self.parent.changeOrientation(False)), anchor=tk.W,
                                            relief="flat", highlightthickness=0)
        self.orient_radio2.grid(row=8, column=0, columnspan=2, sticky=tk.W + tk.E, padx=(50, 0))
        self.orient_radio2.bind('<Enter>', lambda x: self.orient_radio2.configure(bg=bgactcolor))
        self.orient_radio2.bind('<Leave>', lambda x: self.orient_radio2.configure(bg=bgcolor))

        self.style = tk.StringVar(master=self, value=self.parent.style)
        self.style_label = tk.Label(self, text="Theme", bg=bgcolor, fg=fgcolor, font=boldFont)
        self.style_label.grid(row=9, column=0, columnspan=2, sticky=tk.W, padx=(20, 0), pady=(10, 0))
        self.style_radio1 = tk.Radiobutton(self, text="Conky", value="conky", bg=bgcolor, fg=fgcolor,
                                           activebackground=bgactcolor, activeforeground=fgcolor, selectcolor=bgcolor,
                                           font=font, variable=self.style, command=(lambda: self.parent.changeStyle(0)),
                                           anchor=tk.W, relief="flat", highlightthickness=0)
        self.style_radio1.grid(row=10, column=0, columnspan=2, sticky=tk.W + tk.E, padx=(50, 0))
        self.style_radio1.bind('<Enter>', lambda x: self.style_radio1.configure(bg=bgactcolor))
        self.style_radio1.bind('<Leave>', lambda x: self.style_radio1.configure(bg=bgcolor))
        self.style_radio2 = tk.Radiobutton(self, text="Gauge", value="gauge", bg=bgcolor, fg=fgcolor,
                                           activebackground=bgactcolor, activeforeground=fgcolor, selectcolor=bgcolor,
                                           font=font, variable=self.style, command=(lambda: self.parent.changeStyle(1)),
                                           anchor=tk.W, relief="flat", highlightthickness=0)
        self.style_radio2.grid(row=11, column=0, columnspan=2, sticky=tk.W + tk.E, padx=(50, 0))
        self.style_radio2.bind('<Enter>', lambda x: self.style_radio2.configure(bg=bgactcolor))
        self.style_radio2.bind('<Leave>', lambda x: self.style_radio2.configure(bg=bgcolor))
        self.style_radio3 = tk.Radiobutton(self, text="Pie", value="pie", bg=bgcolor, fg=fgcolor,
                                           activebackground=bgactcolor, activeforeground=fgcolor, selectcolor=bgcolor,
                                           font=font, variable=self.style, command=(lambda: self.parent.changeStyle(2)),
                                           anchor=tk.W, relief="flat", highlightthickness=0)
        self.style_radio3.grid(row=12, column=0, columnspan=2, sticky=tk.W + tk.E, padx=(50, 0))
        self.style_radio3.bind('<Enter>', lambda x: self.style_radio3.configure(bg=bgactcolor))
        self.style_radio3.bind('<Leave>', lambda x: self.style_radio3.configure(bg=bgcolor))
        self.style_radio4 = tk.Radiobutton(self, text="Arc", value="arc", bg=bgcolor, fg=fgcolor,
                                           activebackground=bgactcolor, activeforeground=fgcolor, selectcolor=bgcolor,
                                           font=font, variable=self.style, command=(lambda: self.parent.changeStyle(3)),
                                           anchor=tk.W, relief="flat", highlightthickness=0)
        self.style_radio4.grid(row=13, column=0, columnspan=2, sticky=tk.W + tk.E, padx=(50, 0))
        self.style_radio4.bind('<Enter>', lambda x: self.style_radio4.configure(bg=bgactcolor))
        self.style_radio4.bind('<Leave>', lambda x: self.style_radio4.configure(bg=bgcolor))
        self.style_radio5 = tk.Radiobutton(self, text="Arc with Indicator", value="arc_with_indicator", bg=bgcolor,
                                           activebackground=bgactcolor, activeforeground=fgcolor, selectcolor=bgcolor,
                                           fg=fgcolor, font=font, variable=self.style,
                                           command=(lambda: self.parent.changeStyle(4)), anchor=tk.W, relief="flat",
                                           highlightthickness=0)
        self.style_radio5.grid(row=14, column=0, columnspan=2, sticky=tk.W + tk.E, padx=(50, 0))
        self.style_radio5.bind('<Enter>', lambda x: self.style_radio5.configure(bg=bgactcolor))
        self.style_radio5.bind('<Leave>', lambda x: self.style_radio5.configure(bg=bgcolor))
        self.style_radio6 = tk.Radiobutton(self, text="Numbers", value="textonly", bg=bgcolor,
                                           activebackground=bgactcolor, activeforeground=fgcolor, selectcolor=bgcolor,
                                           fg=fgcolor, font=font, variable=self.style,
                                           command=(lambda: self.parent.changeStyle(5)), anchor=tk.W, relief="flat",
                                           highlightthickness=0)
        self.style_radio6.grid(row=15, column=0, columnspan=2, sticky=tk.W + tk.E, padx=(50, 0))
        self.style_radio6.bind('<Enter>', lambda x: self.style_radio6.configure(bg=bgactcolor))
        self.style_radio6.bind('<Leave>', lambda x: self.style_radio6.configure(bg=bgcolor))

        self.sys_label = tk.Label(self, text="Show/Hide System Info", bg=bgcolor, fg=fgcolor, font=font, anchor=tk.W)
        self.sys_label.grid(row=16, column=0, columnspan=2, padx=(20, 0), pady=(10, 0), sticky=tk.W + tk.E)
        self.sys_label.bind('<Button-1>', lambda x: self.parent.changeSysData(not self.parent.show_sys_data))
        self.sys_label.bind('<Enter>', lambda x: self.sys_label.configure(bg=bgactcolor))
        self.sys_label.bind('<Leave>', lambda x: self.sys_label.configure(bg=bgcolor))

        self.show_hide_label = tk.Label(self, text="Show/Hide SysMon (alt+%s)" % settings.show_hide_key, bg=bgcolor,
                                        fg=fgcolor, font=font, anchor=tk.W)
        self.show_hide_label.grid(row=17, column=0, columnspan=2, padx=(20, 0), pady=(10, 0), sticky=tk.W + tk.E)
        self.show_hide_label.bind('<Button-1>', lambda x: self.parent.showWindow())
        self.show_hide_label.bind('<Enter>', lambda x: self.show_hide_label.configure(bg=bgactcolor))
        self.show_hide_label.bind('<Leave>', lambda x: self.show_hide_label.configure(bg=bgcolor))

        self.quit_label = tk.Label(self, text="Quit SysMon", bg=bgcolor, fg=fgcolor, font=font, anchor=tk.W)
        self.quit_label.grid(row=18, column=0, columnspan=2, padx=(20, 0), pady=10, sticky=tk.W + tk.E)
        self.quit_label.bind('<Button-1>', self.on_quit)
        self.quit_label.bind('<Enter>', lambda x: self.quit_label.config(bg=bgactcolor))
        self.quit_label.bind('<Leave>', lambda x: self.quit_label.config(bg=bgcolor))

        self.grid_columnconfigure(0, weight=1)

        # self.wait_visibility()
        # self.canvas.config(width=self.winfo_width(), height=self.winfo_height())
        # tkutils.round_rectangle(self, self.canvas, self.winfo_x(), self.winfo_y(),
        #                         self.winfo_x() + self.winfo_reqwidth(), self.winfo_y() + self.winfo_reqheight(),
        #                         bgcolor="grey", color=settings.bg_color)
        # tkutils.round_rectangle(self, self.canvas, self.winfo_x(), self.winfo_y(),
        #                         self.winfo_x() + self.winfo_reqwidth(), self.exit_label.winfo_y() + self.exit_label.winfo_reqheight(),
        #                         bgcolor="grey", color=bgactcolor)
        # self.canvas.create_text(100, 20, text="SysMon Settings", fill="white", font=font)

    def on_click(self, e):
        if e.widget == self.exit_label:
            self.withdraw()
        elif e.widget == self.title_label:
            self.mouse_X_pos = self.winfo_pointerx() - self.winfo_x()
            self.mouse_Y_pos = self.winfo_pointery() - self.winfo_y()
        else:
            if e.widget not in (self, self.title_label, self.exit_label):
                e.widget.configure(bg=settings.gnoavail_color)
            if "Linux" in settings.archOS:
                if e.widget == self.mode_radio1 or e.widget == self.app_name:
                    if not self.app_name.grid_info():
                        self.app_name.grid()
                        self.app_button.grid()
                    # self.app_name.focus_force()
                elif e.widget == self.mode_radio2 and self.app_name.grid_info():
                    self.app_name.grid_remove()
                    self.app_button.grid_remove()

    def on_motion(self, e):
        x, y = e.x_root - self.mouse_X_pos, e.y_root - self.mouse_Y_pos
        self.geometry('+{0}+{1}'.format(x, y))

    def on_quit(self, e):
        self.destroy()
        self.parent.closeAll()

    def focus_in(self, *args):
        if self.app_name.grid_info():
            text = self.app_name.get('1.0', tk.END).replace("\n", "")
            if text == self.defaultText:
                self.app_name.delete('1.0', tk.END)
                self.app_name.config(fg=settings.bg_color)
            self.app_name.focus_force()

    def focus_out(self, *args):
        if self.app_name.grid_info():
            text = self.app_name.get('1.0', tk.END).replace("\n", "")
            if text == "":
                self.app_name.insert('1.0', self.defaultText)
                self.app_name.config(fg=settings.bg_color)

    def control_return(self, *args):
        self.getAppName()
        return 'break'

    def getAppName(self):
        appName = self.app_name.get('1.0', tk.END).replace("\n", "")
        if appName and appName != self.defaultText and os.path.exists(appName):
            self.parent.getTargetApp(appName)
            self.app_name.config(fg=settings.bg_color)
        else:
            self.app_name.config(fg="red")

    def control_delete(self, *args):
        self.app_name.config(fg=settings.bg_color)


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING, filename='sysmon.log', filemode="w", format='%(asctime)s - %(message)s', datefmt="%Y/%m/%d, %H:%M:%S")
    root = SysMon()
    root.mainloop()
