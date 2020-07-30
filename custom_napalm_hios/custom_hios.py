# -*- coding: utf-8 -*-
# Copyright 2016 Dravetech AB. All rights reserved.
#
# The contents of this file are licensed under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with the
# License. You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations under
# the License.

"""
Napalm driver for HiOS.

Read https://napalm.readthedocs.io for more information.
"""

import re
from netmiko import ConnectHandler

from napalm.base import NetworkDriver
from napalm.base.exceptions import (
    ConnectionException,
    SessionLockedException,
    MergeConfigException,
    ReplaceConfigException,
    CommandErrorException,
)


class HiOSDriver(NetworkDriver):
    """Napalm driver for HiOS."""

    def __init__(self, hostname, username, password, timeout=60, optional_args=None):
        """Constructor."""
        self.device = None
        self.hostname = hostname
        self.username = username
        self.password = password
        self.timeout = timeout

        if optional_args is None:
            optional_args = {}
        self.transport = optional_args.get("transport", "ssh")
        self.profile = ["hios"]

        # Netmiko possible arguments
        netmiko_argument_map = {
            "port": None,
            "secret": "",
            "verbose": False,
            "keepalive": 30,
            "global_delay_factor": 1,
            "use_keys": False,
            "key_file": None,
            "ssh_strict": False,
            "system_host_keys": False,
            "alt_host_keys": False,
            "alt_key_file": "",
            "ssh_config_file": None,
        }
        # Build dict of any optional Netmiko args
        self.netmiko_optional_args = {}
        for k, v in netmiko_argument_map.items():
            try:
                self.netmiko_optional_args[k] = optional_args[k]
            except KeyError:
                pass
        self.global_delay_factor = optional_args.get("global_delay_factor", 1)
        self.port = optional_args.get("port", 22)

    def open(self):
        """Implement the NAPALM method open (mandatory)"""
        try:
            device_type = "cisco_ios"
            #if self.transport == "telnet":
            #    device_type = "hios_telnet"
            self.device = ConnectHandler(
                device_type=device_type,
                host=self.hostname,
                username=self.username,
                password=self.password,
                session_log="log",
                **self.netmiko_optional_args
            )
            # ensure in enable mode
            self.device.enable()
        except Exception:
            raise ConnectionException("Cannot connect to switch: %s:%s" % (self.hostname,
                                                                           self.port))

    def close(self):
        """Implement the NAPALM method close (mandatory)"""
        self.device.disconnect()

    def _send_command_paging(self, command):
        """Wrapper for self.device.send.command() with paging."""
        output = self.device.send_command_timing(command)
        if '--More-- or (q)uit' in output:
            output += self.device.send_command_timing("\n")
        return output

    def is_alive(self):
        """ Returns a flag with the state of the connection."""
        if self.device is None:
            return {"is_alive": False}
        try:
            if self.transport == "telnet":
                # Try sending IAC + NOP (IAC is telnet way of sending command
                # IAC = Interpret as Command (it comes before the NOP)
                self.device.write_channel(telnetlib.IAC + telnetlib.NOP)
                return {"is_alive": True}
            else:
                # SSH
                # Try sending ASCII null byte to maintain the connection alive
                null = chr(0)
                self.device.write_channel(null)
                return {"is_alive": self.device.remote_conn.transport.is_active()}
        except (socket.error, EOFError, OSError):
            # If unable to send, we can tell for sure that the connection is unusable
            return {"is_alive": False}

    def get_facts(self):
        """Return a set of facts from the devices."""
        # default values.
        facts = {
                'uptime': -1,
                'vendor': u'Hirschmann',
                'os_version': u'',
                'serial_number': u'',
                'model': u'',
                'hostname': u'',
                'fqdn': u'',
                'interface_list': []
                }

        show_sysinfo = self._send_command_paging("show sysinfo")

        uptime = re.search(r'System Up Time\.+ (.*)',show_sysinfo,re.MULTILINE)
        # 0 days 0 hrs 0 mins 0 secs
        udict = uptime.group(1).split(" ")
        uptime_seconds = (
            int(int(udict[6]))
            + int(udict[4]) * 60
            + int(udict[2]) * 60 * 60
            + int(udict[0]) * 60 * 60 * 24
        )

        os_version = re.search(r'Running Software Release\.+ (.*)',show_sysinfo,re.MULTILINE)
        serial_number = re.search(r'Serial Number \(Backplane\)\.+ (.*)',show_sysinfo,re.MULTILINE)
        model = re.search(r'Backplane Hardware Description\.+ (.*)',show_sysinfo,re.MULTILINE)
        hostname = re.search(r'System Name\.+ (.*)',show_sysinfo,re.MULTILINE)

        facts['uptime'] = uptime_seconds
        facts['os_version'] = os_version.group(1)
        facts['serial_number'] = serial_number.group(1)
        facts['model'] = model.group(1)
        facts['hostname'] = hostname.group(1)
        facts['fqdn'] = hostname.group(1)
        facts['interface_list'] = self._get_interface_list()

        return facts

    def get_config(self, retrieve="all", full=False, sanitized=False):
        """Get device config"""
        config = {"running": "", "candidate": ""}  # default values

        if retrieve.lower() in ["running", "all"]:
            running_config = self.device.send_command("show running-config")
            config["running"] = str(running_config)
            config["candidate"] = ""
        return config

    def _get_interface_list(self):
        """Get the list of all interfaces"""
        interface_list = []

        show_port_all = self._send_command_paging("show port all")
        for line in re.finditer(r'([0-9]\S+) .*',show_port_all,re.MULTILINE):
            interface_list.append(line.group(1))

        return interface_list
