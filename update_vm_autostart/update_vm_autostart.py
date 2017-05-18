#!/usr/bin/python

#
# Copyright (c) 2016-2017 Hristo Malinov <hristo.malinov@gmail.com>
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer
#    in this position and unchanged.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE AUTHOR(S) ``AS IS'' AND ANY EXPRESS OR
# IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES
# OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
# IN NO EVENT SHALL THE AUTHOR(S) BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT
# NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF

'''
A basic script to update autostart configuration of a VMware
virtual machine. Prerequisites:
 - pip install pyvmomi
'''

from __future__ import print_function

import pyVmomi
from pyVmomi import vim
from pyVmomi import vmodl
from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vmodl

import sys
import argparse
import atexit
import getpass
import requests
import ConfigParser

# Default start delay
defstartdelay = 600
# Special vmware hosts that needs to start first
l = ['ldap', 'mainrouter', 'dns']



def config_parser(config_file, section):
    """
    Returns dict from parsed file and section 
    """
    config = ConfigParser.ConfigParser()
    if config.read(config_file):
        data = dict(config.items(section))
        return data
    return None


def vcenter_connection():
    config = "config.properties"
    vcenter_conf = config_parser(config, 'VCENTER')
    host = vcenter_conf['host']
    user = vcenter_conf['user']
    pwd = vcenter_conf['pwd']
    port = vcenter_conf['port']
    
    try:
        si = SmartConnect(host=host,user=user,
                          pwd=pwd,port=port)
    except Exception as e:
        print("Error: ", e)
        raise SystemExit
    atexit.register(Disconnect, si)
    content = si.RetrieveContent()
    return si, content


def get_obj(content, vimtype, name):
    """
     Get the vsphere object associated with a given text name
    """
    obj = None
    container = content.viewManager.CreateContainerView(content.rootFolder, vimtype, True)
    for c in container.view:
        if c.name == name:
            obj = c
            break
    return obj


def enable_autostart(host):
    print(">>> The selected host is " + host.name)
    try:
        powerinfo = host.config.host.configManager.autoStartManager.config.powerInfo
    except AttributeError as e:
        return None
    hostDefSettings = vim.host.AutoStartManager.SystemDefaults()
    hostDefSettings.enabled = True
    hostDefSettings.startDelay = int(defstartdelay)
    autostart_vm = []
    for machine in powerinfo:
        if machine.startAction != 'none':
            autostart_vm.append(machine.key.name)
    for vm in host.vm:
        if vm.name not in autostart_vm:
            spec = host.configManager.autoStartManager.config
            spec.defaults = hostDefSettings
            auto_power_info = vim.host.AutoStartManager.AutoPowerInfo()
            auto_power_info.key = vm
            if vm.runtime.powerState == "poweredOn":
                print("\tUpdating autostart for:", vm.name)
                auto_power_info.startAction = 'systemDefault'
                auto_power_info.startDelay = 600
                if any(word in vm.name for word in l):
                    auto_power_info.startDelay = 300
                auto_power_info.startOrder = -1
                auto_power_info.stopAction = 'systemDefault'
                auto_power_info.stopDelay = -1
                auto_power_info.waitForHeartbeat = 'systemDefault'
            try:
                spec.powerInfo = [auto_power_info]
                host.configManager.autoStartManager.ReconfigureAutostart(spec)
            except Exception as e:
                print(vm.name, "Error: ", e)
            


def main():
    si, content = vcenter_connection()

    for dc in content.rootFolder.childEntity:
        print("\nDATACENTER: ", dc.name, "\n")
        for cluster in dc.hostFolder.childEntity:
            if cluster.name == 'PROD':
                for host in cluster.host:
                    enable_autostart(host)

    
    
if __name__ == '__main__':
    main()
