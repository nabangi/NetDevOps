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
Napalm driver for Cumulus.

Read https://napalm.readthedocs.io for more information.
"""

from __future__ import print_function
from __future__ import unicode_literals

import re
import json
import ipaddress
from datetime import datetime
from pytz import timezone
from collections import defaultdict

from netmiko import ConnectHandler
from netmiko.ssh_exception import NetMikoTimeoutException
import napalm.base.constants as C
from napalm.base.utils import py23_compat
from napalm.base.utils import string_parsers
from napalm.base.base import NetworkDriver
from napalm.base.exceptions import (
    ConnectionException,
    MergeConfigException
    )


class CumulusDriver(NetworkDriver):
    """Napalm driver for Cumulus."""

    def __init__(self, hostname, username, password, timeout=60, optional_args=None):
        """Constructor."""
        self.device = None
        self.hostname = hostname
        self.username = username
        self.password = password
        self.timeout = timeout
        self.loaded = False
        self.changed = False

        if optional_args is None:
            optional_args = {}

        # Netmiko possible arguments
        netmiko_argument_map = {
            'port': None,
            'verbose': False,
            'global_delay_factor': 1,
            'use_keys': False,
            'key_file': None,
            'ssh_strict': False,
            'system_host_keys': False,
            'alt_host_keys': False,
            'alt_key_file': '',
            'ssh_config_file': None,
            'secret': password,
            'allow_agent': False
        }

        # Build dict of any optional Netmiko args
        self.netmiko_optional_args = {
                k: optional_args.get(k, v)
                for k, v in netmiko_argument_map.items()
            }
        self.port = optional_args.get('port', 22)
        self.sudo_pwd = optional_args.get('sudo_pwd', self.password)

    def open(self):
        try:
            self.device = ConnectHandler(device_type='linux',
                                         host=self.hostname,
                                         username=self.username,
                                         password=self.password,
                                         **self.netmiko_optional_args)
        except NetMikoTimeoutException:
            raise ConnectionException('Cannot connect to {}'.format(self.hostname))

    def close(self):
        self.device.disconnect()

    def is_alive(self):
        return {
            'is_alive': self.device.remote_conn.transport.is_active()
        }

    def load_merge_candidate(self, filename=None, config=None):
        if not filename and not config:
            raise MergeConfigException('filename or config param must be provided.')

        self.loaded = True

        if filename is not None:
            with open(filename, 'r') as f:
                candidate = f.readlines()
        else:
            candidate = config

        if not isinstance(candidate, list):
            candidate = [candidate]

        candidate = [line for line in candidate if line]
        for command in candidate:
            output = self._send_command(command)
            if "error" in output or "not found" in output:
                raise MergeConfigException("Command '{0}' cannot be applied.".format(command))

    def discard_config(self):
        if self.loaded:
            self._send_command('net abort')
            self.loaded = False

    def compare_config(self):
        if self.loaded:
            diff = self._send_command('net pending')
            return re.sub(r'\x1b\[\d+m', '', diff)
        return ''

    def commit_config(self, message=""):
        if self.loaded:
            self._send_command('net commit')
            self.changed = True
            self.loaded = False

    def rollback(self):
        if self.changed:
            self._send_command('net rollback last')
            self.changed = False

    def _send_command(self, command):
        response = self.device.send_command(command)
        if 'Permission denied' or 'ERROR: 'in response:
            try:
                if self.netmiko_optional_args.get('secret'):
                    self.device.enable()
                    response = self.device.send_command(command)
                    self.device.exit_enable_mode()
                    return response
            except ValueError:
                raise ConnectionException('Super User Elevation Required. Set Netmiko secret argument')

    def get_facts(self):
        facts = {
            'vendor': py23_compat.text_type('Cumulus')
        }

        # Get "net show hostname" output.
        hostname = self._send_command('hostname')

        # Get "net show system" output.
        show_system_output = self._send_command('net show system')
        for line in show_system_output.splitlines():
            if 'build' in line.lower():
                os_version = line.split()[-1]
                model = ' '.join(line.split()[1:3])
            elif 'uptime' in line.lower():
                uptime = line.split()[-1]

        # Get "decode-syseeprom" output.
        decode_syseeprom_output = self._send_command('decode-syseeprom')
        for line in decode_syseeprom_output.splitlines():
            if 'serial number' in line.lower():
                serial_number = line.split()[-1]

        # Get "net show interface all json" output.
        interfaces = self._send_command('net show interface all json')
        # Handling bad send_command_timing return output.
        try:
            interfaces = json.loads(interfaces)
        except ValueError:
            interfaces = json.loads(self.device.send_command('net show interface all json'))

        facts['hostname'] = facts['fqdn'] = py23_compat.text_type(hostname)
        facts['os_version'] = py23_compat.text_type(os_version)
        facts['model'] = py23_compat.text_type(model)
        facts['uptime'] = string_parsers.convert_uptime_string_seconds(uptime)
        facts['serial_number'] = py23_compat.text_type(serial_number)
        facts['interface_list'] = string_parsers.sorted_nicely(interfaces.keys())
        return facts

    def get_arp_table(self):

        """
        'show arp' output example:
        Address                  HWtype  HWaddress           Flags Mask            Iface
        10.129.2.254             ether   00:50:56:97:af:b1   C                     eth0
        192.168.1.134                    (incomplete)                              eth1
        192.168.1.1              ether   00:50:56:ba:26:7f   C                     eth1
        10.129.2.97              ether   00:50:56:9f:64:09   C                     eth0
        192.168.1.3              ether   00:50:56:86:7b:06   C                     eth1
        """
        output = self._send_command('arp -n')
        output = output.split("\n")
        output = output[1:]
        arp_table = list()

        for line in output:
            line = line.split()
            if "incomplete" in line[1]:
                macaddr = py23_compat.text_type("00:00:00:00:00:00")
            else:
                macaddr = py23_compat.text_type(line[2])

            arp_table.append(
                {
                    'interface': py23_compat.text_type(line[-1]),
                    'mac': macaddr,
                    'ip': py23_compat.text_type(line[0]),
                    'age': 0.0
                }
            )
        return arp_table

    def get_ntp_stats(self):
        """
        'ntpq -np' output example
             remote           refid      st t when poll reach   delay   offset  jitter
        ==============================================================================
         116.91.118.97   133.243.238.244  2 u   51   64  377    5.436  987971. 1694.82
         219.117.210.137 .GPS.            1 u   17   64  377   17.586  988068. 1652.00
         133.130.120.204 133.243.238.164  2 u   46   64  377    7.717  987996. 1669.77
        """

        output = self._send_command("net show time ntp servers")
        output = output.split("\n")[2:]
        ntp_stats = list()

        for ntp_info in output:
            if len(ntp_info) > 0:
                remote, refid, st, t, when, hostpoll, reachability, delay, offset, \
                    jitter = ntp_info.split()

                # 'remote' contains '*' if the machine synchronized with NTP server
                synchronized = "*" in remote

                match = re.search(r'(\d+\.\d+\.\d+\.\d+)', remote)
                ip = match.group(1)

                when = when if when != '-' else 0

                ntp_stats.append({
                    "remote": py23_compat.text_type(ip),
                    "referenceid": py23_compat.text_type(refid),
                    "synchronized": bool(synchronized),
                    "stratum": int(st),
                    "type": py23_compat.text_type(t),
                    "when": py23_compat.text_type(when),
                    "hostpoll": int(hostpoll),
                    "reachability": int(reachability),
                    "delay": float(delay),
                    "offset": float(offset),
                    "jitter": float(jitter)
                })
        return ntp_stats

    def ping(self,
             destination,
             source=C.PING_SOURCE,
             ttl=C.PING_TTL,
             timeout=C.PING_TIMEOUT,
             size=C.PING_SIZE,
             count=C.PING_COUNT,
             vrf=C.PING_VRF):

        deadline = timeout * count

        command = "ping %s " % destination
        command += "-t %d " % int(ttl)
        command += "-w %d " % int(deadline)
        command += "-s %d " % int(size)
        command += "-c %d " % int(count)
        if source != "":
            command += "interface %s " % source

        ping_result = dict()
        output_ping = self._send_command(command)

        if "Unknown host" in output_ping:
            err = "Unknown host"
        else:
            err = ""

        if err is not "":
            ping_result["error"] = err
        else:
            # 'packet_info' example:
            # ['5', 'packets', 'transmitted,' '5', 'received,' '0%', 'packet',
            # 'loss,', 'time', '3997ms']
            packet_info = output_ping.split("\n")

            if ('transmitted' in packet_info[-2]):
                packet_info = packet_info[-2]
            else:
                packet_info = packet_info[-3]

            packet_info = [x.strip() for x in packet_info.split()]

            sent = int(packet_info[0])
            received = int(packet_info[3])
            lost = sent - received

            # 'rtt_info' example:
            # ["0.307/0.396/0.480/0.061"]
            rtt_info = output_ping.split("\n")

            if len(rtt_info[-1]) > 0:
                rtt_info = rtt_info[-1]
            else:
                rtt_info = rtt_info[-2]

            match = re.search(r"([\d\.]+)/([\d\.]+)/([\d\.]+)/([\d\.]+)", rtt_info)

            if match is not None:
                rtt_min = float(match.group(1))
                rtt_avg = float(match.group(2))
                rtt_max = float(match.group(3))
                rtt_stddev = float(match.group(4))
            else:
                rtt_min = None
                rtt_avg = None
                rtt_max = None
                rtt_stddev = None

            ping_responses = list()
            response_info = output_ping.split("\n")

            for res in response_info:
                match_res = re.search(r"from\s([\d\.]+).*time=([\d\.]+)", res)
                if match_res is not None:
                    ping_responses.append(
                      {
                        "ip_address": match_res.group(1),
                        "rtt": float(match_res.group(2))
                      }
                    )

            ping_result["success"] = dict()

            ping_result["success"] = {
                "probes_sent": sent,
                "packet_loss": lost,
                "rtt_min": rtt_min,
                "rtt_max": rtt_max,
                "rtt_avg": rtt_avg,
                "rtt_stddev": rtt_stddev,
                "results": ping_responses
            }

            return ping_result

    def _get_interface_neighbors(self, neighbors_list):
        neighbors = []
        for neighbor in neighbors_list:
            temp = {}
            temp['hostname'] = neighbor['adj_hostname']
            temp['port'] = neighbor['adj_port']
            neighbors.append(temp)
        return neighbors

    def get_lldp_neighbors(self):
        """Cumulus get_lldp_neighbors."""
        lldp = {}
        command = 'net show interface all json'

        try:
            intf_output = json.loads(self._send_command(command))
        except ValueError:
            intf_output = json.loads(self.device.send_command(command))

        for interface in intf_output:
            if intf_output[interface]['iface_obj']['lldp'] is not None:
                lldp[interface] = self._get_interface_neighbors(
                                        intf_output[interface]['iface_obj']['lldp'])
        return lldp

    def get_interfaces(self):
        interfaces = {}
        # Get 'net show interface all json' output.
        output = self._send_command('net show interface all json')
        # Handling bad send_command_timing return output.
        try:
            output_json = json.loads(output)
        except ValueError:
            output_json = json.loads(self.device.send_command('net show interface all json'))
        for interface in output_json.keys():
            interfaces[interface] = {}
            if output_json[interface]['linkstate'] == "UP":
                interfaces[interface]['is_up'] = True 
                interfaces[interface]['is_enabled'] = True
            elif output_json[interface]['linkstate'] == 'DN':
                interfaces[interface]['is_up'] = False
                interfaces[interface]['is_enabled'] = True
            else:
                # Link state is ADMIN DOWN
                interfaces[interface]['is_up'] = False
                interfaces[interface]['is_enabled'] = False
            interfaces[interface]['description'] = py23_compat.text_type(
                                            output_json[interface]['iface_obj']['description'])
            speed_map = {'100M': 100, '1G': 1000, '10G': 10000, '40G': 40000, '100G': 100000}
            try:
                interfaces[interface]['speed'] = speed_map[output_json[interface]['speed']]
            except KeyError:
                interfaces[interface]['speed'] = -1

            interfaces[interface]['mac_address'] = py23_compat.text_type(
                                            output_json[interface]['iface_obj']['mac'])
        # Calculate last interface flap time. Dependent on router daemon
        # Send command to determine if router daemon is running. Not dependent on quagga or frr
        daemon_check = self._send_command("sudo vtysh -c 'show version'")
        if 'Exiting: failed to connect to any daemons.' in daemon_check:
            for interface in interfaces.keys():
                interfaces[interface]['last_flapped'] = -1
        else:
            show_int_output = self._send_command("sudo vtysh -c 'show interface'")
            remote_system_date = self._send_command('date "+%Y/%m/%d %H:%M:%S.%6N"')
            remote_system_date = datetime.strptime(remote_system_date, "%Y/%m/%d %H:%M:%S.%f")
            split_int_output = list(filter(None, re.split("(?!Interface Type)Interface", show_int_output)))
            for block in split_int_output:
                split_block = block.split("\n")
                for line in split_block:
                    if 'line protocol' in line:
                        interface = line.split()
                        interface = interface[0]
                    if 'Link ups' in line:
                        if int(line.split()[2]) < 2:
                            never_flapped = True
                            break
                        else:
                            never_flapped = False
                            last_link_up_date = line.split()[4] + " " + line.split()[5]
                            last_link_up_date = datetime.strptime(last_link_up_date, "%Y/%m/%d %H:%M:%S.%f")
                    else: 
                        never_flapped = False
                        if 'Link downs' in line:
                            last_link_down_date = line.split()[4] + " " + line.split()[5]
                            last_link_down_date = datetime.strptime(last_link_down_date, "%Y/%m/%d %H:%M:%S.%f")
                if never_flapped:
                    interfaces[interface]['last_flapped'] = -1
                else:
                    if last_link_up_date > last_link_down_date:
                        interfaces[interface]['last_flapped']  = (remote_system_date - last_link_up_date).total_seconds()
                    else:
                        interfaces[interface]['last_flapped']  = (remote_system_date - last_link_down_date).total_seconds()
        return interfaces

    def get_interfaces_ip(self):
        interfaces_ip = {}
        # Get net show interface all json output.
        output = self._send_command('net show interface all json')
        # Handling bad send_command_timing return output.
        try:
            output_json = json.loads(output)
        except ValueError:
            output_json = json.loads(self.device.send_command('net show interface all json'))
        for interface in output_json:
            if not output_json[interface]['iface_obj']['ip_address']['allentries']:
                continue
            else:
                for ip_address in output_json[interface]['iface_obj']['ip_address']['allentries']:
                    ip_ver = ipaddress.ip_interface(py23_compat.text_type(ip_address)).version
                    ip_ver = 'ipv{}'.format(ip_ver)
                    ip, prefix = ip_address.split('/')
                    interfaces_ip.update({interface: {ip_ver: {ip: {'prefix_length': int(prefix)}}}})

        return interfaces_ip

    def get_config(self, retrieve='all'):
        # Initialise the configuration dictionary
        configuration = {
            'startup': '',
            'running': '',
            'candidate': '',
        }

        if retrieve in ('running', 'all'):
            # Get net show configuration output.
            output = self._send_command('net show configuration')

            configuration['running'] = py23_compat.text_type(output)

        if retrieve in ('candidate', 'all'):
            # Get net pending output.
            output = self._send_command('net pending json')

            configuration['candidate'] = py23_compat.text_type(output)

        return configuration

    def get_bgp_neighbors(self):
        vrf = 'global'
        bgp_neighbors = {vrf: {}}
        bgp_neighbor = {}
        supported_afis = ['ipv4 unicast', 'ipv6 unicast']
        bgp_summary_output = self._send_command('net show bgp summary json')
        dev_bgp_summary = json.loads(bgp_summary_output)
        bgp_neighbors_output = self._send_command('net show bgp neighbor json')
        dev_bgp_neighbors = json.loads(bgp_neighbors_output)
        for afi in dev_bgp_summary:
            if not (afi.lower() in supported_afis) or not dev_bgp_summary[afi]:
                continue
            bgp_neighbors[vrf]['router_id'] = dev_bgp_summary[afi]['routerId']
            bgp_neighbors[vrf].setdefault("peers", {})
            for peer in dev_bgp_summary[afi]['peers']:
                bgp_neighbor = {}
                bgp_neighbor['local_as'] = dev_bgp_neighbors[peer]['localAs']
                bgp_neighbor['remote_as'] = dev_bgp_neighbors[peer]['remoteAs']
                bgp_neighbor['remote_id'] = dev_bgp_neighbors[peer]['remoteRouterId']
                uptime = dev_bgp_neighbors[peer].get('bgpTimerUpMsec', "")
                bgp_neighbor['description'] = dev_bgp_neighbors[peer].get("nbrDesc", '')
                if dev_bgp_neighbors[peer]['bgpState'] == 'Established':
                    is_up = True
                else:
                    is_up = False
                    uptime = -1
                if dev_bgp_neighbors[peer].get('adminShutDown', False):
                    is_enabled = False
                else:
                    is_enabled = True
                bgp_neighbor['is_up'] = is_up
                bgp_neighbor['is_enabled'] = is_enabled
                bgp_neighbor['uptime'] = int(uptime / 1000)
                bgp_neighbor.setdefault("address_family", {})
                for af, af_details in dev_bgp_neighbors[peer]['addressFamilyInfo'].items():
                    af = af.lower()
                    if not (af in supported_afis):
                        continue
                    route_info = {}
                    bgp_peer_advertised_routes = self._send_command('net show bgp {} neighbor {} '
                                                                    'advertised-routes json'
                                                                    .format(af, peer))
                    dev_bgp_peer_advertised_routes = \
                        json.loads(bgp_peer_advertised_routes.replace('n\n', ''))
                    peer_advertised_routes = dev_bgp_peer_advertised_routes['totalPrefixCounter']
                    if not is_enabled:
                        dev_bgp_summary[af]['peers'][peer]['prefixReceivedCount'] = -1
                        peer_advertised_routes = -1
                        af_details['acceptedPrefixCounter'] = -1
                    route_info['received_prefixes'] = \
                        dev_bgp_summary[af]['peers'][peer]['prefixReceivedCount']
                    route_info['sent_prefixes'] = int(peer_advertised_routes)
                    route_info['accepted_prefixes'] = af_details['acceptedPrefixCounter']
                    bgp_neighbor['address_family'][af.split()[0]] = route_info
                bgp_neighbors[vrf]['peers'][peer] = bgp_neighbor

        return bgp_neighbors

    def get_snmp_information(self):
        snmp_config_output = self._send_command('net show configuration snmp-server')
        contact = system_name = location = ""
        snmp_information = {}
        snmp_values = {}
        community_list = []
        snmp_values.setdefault("community", {})
        for parse_snmp_value in snmp_config_output.splitlines():
            if "readonly-community" in parse_snmp_value or \
                    "readonly-community-v6" in parse_snmp_value:
                community_value = parse_snmp_value.strip().split()[1]
                acl = parse_snmp_value.lstrip().split()[3]
                if acl == "any":
                    acl = "N/A"
                if community_value in community_list:
                    """
                    Unlike other routers that use ACL for
                    snmp access-control, Cumulus directly defines
                    authorized hosts as part of SNMP config.
                    E.g:
                    snmp-server
                       listening-address all
                       readonly-community private_multi_host access 10.10.10.1
                       system-contact NOC
                       system-location LAB
                       system-name cumulus-rtr-1
                    This creates a problem as NAPALM snmp object
                    shows access-list name as key of community string.
                    To best present the authorized-host info in the SNMP object,
                    we show comma separate string of them as key of SNMP community.
                    """
                    acl = snmp_values["community"][community_value]["acl"] + "," + acl
                    snmp_values["community"][community_value] = {"acl": acl, "mode": "ro"}
                else:
                    community_list.append(community_value)
                    snmp_values["community"][community_value] = {"acl": acl, "mode": "ro"}
            system_contact_parse = re.search(r'.*system-contact.(\D.*)', parse_snmp_value.strip())
            if system_contact_parse:
                contact = system_contact_parse.groups()[0]
            system_location_parse = re.search(r'.*system-location.(\D.*)', parse_snmp_value.strip())
            if system_location_parse:
                location = system_location_parse.groups()[0]
            system_name_parse = re.search(r'.*system-name.(\D.*)', parse_snmp_value.strip())
            if system_name_parse:
                system_name = system_name_parse.groups()[0]
        snmp_information = snmp_values
        snmp_information["contact"] = contact
        snmp_information["chassis_id"] = system_name
        snmp_information["location"] = location

        return snmp_information
