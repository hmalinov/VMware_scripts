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
A basic script to hot add memory of a VMware virtual machine.
Prerequisites:
 - pip install pyvmomi
 - enable hot memory plug in virtual machine
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

mem_increase = int(sys.argv[1])
vm_name = sys.argv[2]


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

def print_exit(msg):
    print(msg)
    sys.exit(1)
    return None


def vm_memory_upgrade(vm, mem):
    if not vm.config.memoryHotAddEnabled:
        print_exit("ERROR: Memory hotadd is not enabled!")
    # Define desired memory in the Spec and apply the change
    spec = vim.vm.ConfigSpec()
    spec.memoryMB = mem
    task = vm.Reconfigure(spec)
    while True:
        if task.info.state == 'running':
            continue
        elif task.info.state == 'success':
            current_mem = vm.summary.config.memorySizeMB
            break
        else:
            print_exit("ERROR: Memory increase task status: %s" % task.info.state)
    if mem != current_mem:
        print_exit("ERROR:Memory was not changed!Current memory is:%s" % current_mem)
    return True


def main():
    si, content = vcenter_connection()
    vm = get_obj(content, [vim.VirtualMachine], vm_name)
    if not vm:
        print_exit("ERROR: Could not get object")

    host = vm.runtime.host
    host_memory = float(host.summary.hardware.memorySize / 1024 / 1024)
    host_vm_total = int(mem_increase)
    for vmware in host.vm:
        host_vm_total = host_vm_total + vmware.summary.config.memorySizeMB

    if (host_vm_total  / host_memory) > 0.98:
        print("WARNING: HOST memory usage is over 98% ")
        print("WARNING: Consider migrating the vmware on another host")
    if vm_memory_upgrade(vm, mem_increase):
        print("INFO: VCenter memory increase task finished successfully. Starting linux hot add memory job...")
    
    
if __name__ == '__main__':
    main()
    
