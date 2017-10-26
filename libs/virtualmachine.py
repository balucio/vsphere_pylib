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
        elif mode == vim.VirtualMachinePowerState.suspended or mode.lower() == 'suspend':
            activity = self._vm.SuspendVm
        else:
            raise ValueError('Invalid power mode.')

        task = activity()

        if (async):
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
        if (async):
            return task

        WaitForTask(task, onProgressUpdate=progressCallBack)

        return task

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