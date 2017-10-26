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

from pyVim.task import WaitForTask

class Snapshot(object):

	def __init__(self, snapshot, location):

		self._snapshot = snapshot
		self._location = location

	@property
	def name(self):
		return self._snapshot.name

	@property
	def location(self):
		return self._location

	@property
	def snapshot(self):
		return self._snapshot.snapshot

	def remove(self, async=False, removeChildren=True):

		task = self.snapshot.RemoveSnapshot_Task(removeChildren)

		if (async):
			return task

		WaitForTask(task)
		return task


	def revert(self, async=False):

		task = self.snapshot.RevertToSnapshot_Task()

		if (async):
			return task

		WaitForTask(task)
		return task

