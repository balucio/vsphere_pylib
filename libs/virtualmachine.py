#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Author: Saul Bertuccio
# Date: ven 30 giugno 2017

"""
Wrapper pyVmomi per la gestione delle VM
Require:
        https://github.com/vmware/pyvmomi
        VMware vCloud Suite SDK for Python for vSphere 6.0
"""

# Iterazione per ricerca su liste di oggetti
# next((x for x in snaplist if x.name=='STRINGADACERCARE'), None)

import time

from pyVmomi import vim
from pyVim.task import WaitForTask
from snapshot import Snapshot



class VirtualMachine(object):

    poweredOn = vim.VirtualMachinePowerState.poweredOn
    poweredOff = vim.VirtualMachinePowerState.poweredOff
    suspended = vim.VirtualMachinePowerState.suspended

    def __init__(self, vm):
        assert (type(vm) ==  vim.VirtualMachine)

        self._vm = vm

    @property
    def moId(self):
        return self._vm._moId

    @property
    def name(self):
        return self._vm.name

    @property
    def powerState(self):
        return self._vm.runtime.powerState

    def isOn(self):
        return  self._vm.runtime.powerState == vim.VirtualMachinePowerState.poweredOn

    def power(self, mode, async=True):

        if  mode ==  vim.VirtualMachinePowerState.poweredOn or mode.lower() == 'on':
            activity = self._vm.PowerOn
        elif mode == vim.VirtualMachinePowerState.poweredOff or mode.lower() == 'off':
            activity = self._vm.PowerOff
        elif mode == 'shutdown':
            activity = self._vm.ShutdownGuest
            # attendo che la VM sia spenta
            counter = 10
            while self.isOn() and counter>0:
                time.sleep(2)
                counter-=1

            if self.isOn():
                # Forzo un poweroff
                activity = self._vm.PowerOff
		
        elif mode == vim.VirtualMachinePowerState.suspended or mode.lower() == 'suspend':
            activity = self._vm.SuspendVm
        else:
            raise ValueError('Invalid power mode.')

        task = activity()

        if async:
           return task

        WaitForTask(task)
        return task

    def snapshotsList(self):

        if self._vm.snapshot is None:
            return []

        snap_root = self._vm.snapshot.rootSnapshotList

        return self._snapshotList(snap_root, '')


    def snapshotByName(self, name):
    
        snapList = self.snapshotsList()

        for snap in snapList:
            if snap.name == name:
                return snap

        return None

    def clockSync(self, state = None):

        if state == None:
            return self._vm.config.tools.syncTimeWithHost

        spec = vim.vm.ConfigSpec()
        spec.tools = vim.vm.ToolsConfigInfo()
        spec.tools.syncTimeWithHost = state

        return self._vm.ReconfigVM_Task(spec)

    def currentSnapshot(self):

        current_snapref = self._vm.snapshot.currentSnapshot
        snap_list = self._vm.snapshot.rootSnapshotList

        snapList = self.snapshotsList()

        for snap in snapList:
            if snap.snapshot == current_snapref:
                return snap

        return None

    def createSnapshot(self, name, description="", dumpMemory=False, quiesce=True, async=False, progressCallBack=None):

        task = self._vm.CreateSnapshot(name, description, dumpMemory, quiesce)
        if async:
            return task

        WaitForTask(task, onProgressUpdate=progressCallBack)

        return task

    def setTag(self, tag, vcenter):

       vcenter._addTagToObject(tag, self.moId, vs_type='VirtualMachine')

    def _snapshotList(self, snapshots, location):

        if not snapshots:
            return []

        snap_list = []

        for snapshot in snapshots:
            location = location + '/'
            snap = Snapshot(snapshot, location)

            snap_list.append(snap)
            snap_list = snap_list + self._snapshotList(snapshot.childSnapshotList, location + snapshot.name)

        return snap_list


    def addDisk(self, dsize, dtype = 'thin', async=False, progressCallBack=None):

        unit_number = 0
        controller = None
        # calcolo il numero di unità in base ai controller/dischi presenti sulla VM
        for dev in self._vm.config.hardware.device:
           if hasattr(dev.backing, 'fileName'):
               unit_number = int(dev.unitNumber) + 1
               # unit_number 7 reserved for scsi controller
               if unit_number == 7:
                   unit_number += 1
           if isinstance(dev, vim.vm.device.VirtualSCSIController):
               controller = dev

        if unit_number >= 16:
            raise NotImplementedError('Too many disk in this virtual machine')
 
        assert (controller is not None)
        # dimensione in kilobyte
        new_disk_kb = int(dsize) * 1024 * 1024

        # Definisco le caratteristiche del disco
        disk_spec = vim.vm.device.VirtualDeviceSpec()
        disk_spec.fileOperation = "create"
        disk_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.add
        disk_spec.device = vim.vm.device.VirtualDisk()
        disk_spec.device.backing = vim.vm.device.VirtualDisk.FlatVer2BackingInfo()
        disk_spec.device.backing.diskMode = 'persistent'
        disk_spec.device.unitNumber = unit_number
        disk_spec.device.capacityInKB = new_disk_kb
        disk_spec.device.controllerKey = controller.key

        if dtype == 'thin':
            disk_spec.device.backing.thinProvisioned = True

        # Creo una specifica di configurazione e aggiungo la definizione del disco
        spec = vim.vm.ConfigSpec()
        spec.deviceChange = [ disk_spec ]
        task = self._vm.ReconfigVM_Task(spec=spec)
        if async:
            return task

        WaitForTask(task, onProgressUpdate=progressCallBack)
	return task

