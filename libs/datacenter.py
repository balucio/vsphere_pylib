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

import ssl
import requests
import atexit

from os import path
from utils import getPathComponents
from requests.packages.urllib3.exceptions import InsecureRequestWarning

from pyVmomi import vim
from pyVim.connect import SmartConnect, Disconnect

from vmware.vapi.lib.connect import get_requests_connector
from vmware.vapi.security.session import create_session_security_context
from vmware.vapi.security.user_password import create_user_password_security_context
from vmware.vapi.stdlib.client.factories import StubConfigurationFactory

from com.vmware.cis_client import Session
from com.vmware.vapi.std_client import DynamicID
from com.vmware.cis.tagging_client import (
    Category, Tag, TagAssociation, CategoryModel, TagModel)

from virtualmachine import VirtualMachine

class Datacenter(object):

    def __init__(self, host, user, password, port, datacenter):

        requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

        self._category_svc = None
        self._tag_association = None
        self._tag_svc = None

        self._vmh = self._connect(host, user, password, port)

        if not self._vmh:
            raise SystemError("Impossibile collegarsi all'host VMWare con le credenziali specificate.")

        atexit.register(Disconnect, self._vmh)

        self._datacenter = self._getDatacenter(datacenter)

        if not self._datacenter:
            raise SystemError("Il datacenter %s non esiste nell'host %s" % (datacenter_name, host))

        self._vApiInit(host, user, password)

    @property
    def isSessionActive(self):
        sm = self._vmh.content.sessionManager
        sid = sm.currentSession.key
        username = sm.currentSession.userName
        return sm.SessionIsActive(sid, username)

    @property
    def propertyCollector(self):
        return self._vmh.RetrieveContent().propertyCollector

    @property
    def tagSvc(self):

        if self._tag_svc is not None:
            return self._tag_svc

        self._tag_svc = Tag(self._config)
        return self._tag_svc

    @property
    def categorySvc(self):

        if self._category_svc is not None:
            return self._category_svc

        self._category_svc = Category(self._config)
        return self._category_svc

    @property
    def tagAssociationSvc(self):

        if self._tag_association is not None:
            return self._tag_association

        self._tag_association = TagAssociation(self._config)
        return self._tag_association

    def getFolderByName(self, folder_path):

        folder_path = path.normpath(folder_path)
        components = getPathComponents(folder_path)

        if not components:
            return self._datacenter.vmFolder

        # Datacenter root virtual machine folders
        folders = self._datacenter.vmFolder.childEntity

        for name in components:

            folder = self._findFolderByName(folders, name)

            if folder:
                folders = folder.childEntity
            else:
                raise SystemError("La cartella %s non esiste sul datacenter (subpath %s)." % (folder_path, name))

        return folder

    def getVirtualMachineByMoId(self, moid):
        """Lookup a vm from a given moId string (like "vm-123" """

        vm_obj = vim.VirtualMachine(moid)

        try:
            vm_obj._stub = self._vmh._stub
        except Exception:
            raise Exception('Impossibile trovare una VM con moid {}'.format(moid))
        
        return VirtualMachine(vm_obj)

    def getVirtualMachineByName(self, name, folder = None):
        """Return VM object using PyVmomi"""

        recursive = True

        if folder is None or folder == '/':

            content = self._vmh.content
            container = content.rootFolder
            viewType = [vim.VirtualMachine]
            vmView = content.viewManager.CreateContainerView(container,
                                                             viewType,
                                                             recursive)
            vms = vmView.view
            for vm in vms:
                if vm.name == name:
                    return VirtualMachine(vm)
            raise Exception('Impossibile trovare una VM con nome {}\n'.format(name))

        vmList = self.getVirtualMachineList(folder, recursive)

        for vm in vmList:
            if vm.name == name:
                return vm

        raise Exception('Impossibile trovare una VM con nome {}\n'.format(name))

    def getVirtualMachineIpAddress(self, ip):
        """Return VM object using PyVmomi"""

        searchIndex = self._vmh.RetrieveContent().searchIndex
        _vms = searchIndex.FindAllByIp(ip=ip, vmSearch=True)
        vms = []
        oid = []

        for vm in _vms:
            if vm._moId not in oid:
                oid.append(vm._moId)
                vms.append( VirtualMachine(vm) )

        return vms

    def getVirtualMachineList(self, folder = None, recursive = False, template = False):

        if (type(folder) == str):
            container = self.getFolderByName(folder)
        elif (type(folder) == vim.Folder):
            container = folder
        elif folder is None:
            container = self.getFolderByName('/')

        containers = [container]

        while containers:

            container = containers.pop()

            for child in container.childEntity:

                if type(child) == vim.VirtualMachine:

                    if template or not self._isVmTemplate(child):
                        yield VirtualMachine(child)

                elif type(child) == vim.Folder and recursive == True:
                    containers.append(child)

        raise StopIteration

    def getVirtualMachineCategoriesAndTags(self, obj):

        if  type(obj) == str and obj[:3] != 'vm-':
            vid = self.getVirtualMachineByName(obj)._moId
        elif type(obj) == vim.VirtualMachine:
            vid = obj._moId
        elif type(obj) == VirtualMachine:
            vid = obj.moId
        else:
            vid = obj

        cats_and_tags = {}
        tags = self._getTagsForObject(vid)

        for tag in tags:

            cid = tag.category_id

            if cid not in cats_and_tags:
                cat = self.categorySvc.get(cid)
                cats_and_tags[cid] = {'category' : cat, 'tags' : [] }

            cats_and_tags[cid]['tags'].append(tag)

        return cats_and_tags

    def createCategory(name, description, cardinality):
        """create a category. User who invokes this needs create category privilege."""
        category = self.categorySvc.CreateSpec()
        category.name = name
        category.description = description
        category.cardinality = cardinality
        category.associable_types = set()
        return self.categorySvc.create(category)

    def deleteCategory(category):
        """Deletes an existing tag category; User needs delete privilege on category."""
        cat_id = category.id if type(category) == CategoryModel else category
        category_svc.delete(cat_id)

    def getCategoriesList(self):
        """Return categores list """
        return  self._getSvcObjList(self.categorySvc)

    def getCategoryByName(self, name):
        """Return category object given category name string"""
        return self._searchSvcObjByName(self.categorySvc, name)

    def getTagsInCategory(self, category):
        """Return list of tag objects for a given category"""
        cat_id = category.id if type(category) == CategoryModel else category

        try:
            tag_id_list = self.tagSvc.list_tags_for_category(cat_id)
            tag_obj_list = [self.tagSvc.get(tid) for tid in tag_id_list]
        except:
            tag_obj_list = []

        return tag_obj_list

    def createTag(name, description, category):
        """Creates a Tag"""
        cat_id = category.id if type(category) == CategoryModel else category
        tag = self.tagSvc.CreateSpec()
        tag.name = name
        tag.description = description
        tag.category_id = cat_id
        return self.tagSvc.create(tag)

    def updateTag(tag, description):
        """Update the description of an existing tag. User needs edit privilege on tag. """
        tag_id = tag.id if type(tag) == TagModel else tag

        tag = self.tagSvc.UpdateSpec()
        tag.setDescription = description
        self.tagSvc.update(tag_id, tag)

    def deleteTag(tag):
        """Delete an existing tag. User needs delete privilege on tag."""
        tag_id = tag.id if type(tag) == TagModel else tag
        self.tagSvc.delete(tag_id)

    def getTagByName(self, name):
        """Return tag object given tag name string"""
        return self._searchSvcObjByName(self.tagSvc, name)

    def getTagsList(self):
        """Return tags list"""
        return  self._getSvcObjList(self.tagSvc)

    def _connect(self, host, user, password, port):

        if hasattr(ssl, '_create_unverified_context'):
            context = ssl._create_unverified_context()

        return SmartConnect(host=host,
                            user=user,
                            pwd=password,
                            port=port,
                            sslContext=context)

    def _vApiInit(self, host, user, password, proto = 'https', msg_type = 'json'):

        """
        The authenticated stub configuration object can be used to issue requests against vCenter.
        The _config object stores the session identifier that can be used to issue authenticated
        requests against vCenter.
        """
        session = requests.Session()
        session.verify = False
        api_url = '{0}://{1}/api'.format(proto, host)

        self._connector = get_requests_connector(session=session, url=api_url)
        self._config  = StubConfigurationFactory.new_std_configuration(self._connector)
        

        # Creating security context loging for vAPI endpoint authentication
        sec_context_login = create_user_password_security_context(user, password)
        self._config.connector.set_security_context(sec_context_login)

        # Create the stub for the session service and login by creating a session.
        session_svc = Session(self._config)
        session_id = session_svc.create()

        # Successful authentication.  Store the session identifier in the security
        # context of the stub config and use that for all subsequent remote requests
        session_security_context = create_session_security_context(session_id)
        self._config.connector.set_security_context(session_security_context)

    def _getDatacenter(self, name):

        content = self._vmh.RetrieveContent()

        for dc in content.rootFolder.childEntity:
            if dc.name == name:
                return dc

        return None

    def _findFolderByName(self, folders, name):

        # ciclo ogni oggetto all'interno del gruppo
        for obj in folders:
            #  torno se nome uguale e si tratta di un folder (attributo childEntity presente)
            if obj.name == name and type(obj) == vim.Folder:
                return obj

        return None

    def _getSvcObjList(self, svc_obj):

        """Return a list of svc object """
        list = []

        for obj in svc_obj.list():
            list.append(svc_obj.get(obj))

        return list

    def _searchSvcObjByName(self, svc_obj, name):

        """Return svc object by name"""
        for obj in svc_obj.list():

            if svc_obj.get(obj).name == name:
                return svc_obj.get(obj)

        return None

    def _getTagsForObject(self, obj, vs_type='VirtualMachine'):
        """List tag objects for given id/object """
        d_obj = obj if type(obj) == DynamicID else DynamicID(type=vs_type, id=obj)
        tag_ids = self.tagAssociationSvc.list_attached_tags(d_obj)
        tags = []
        for tid in tag_ids:
            tags.append(self.tagSvc.get(tid))
        return tags

    def _getTaggedObjects(self, tag):
        """Returns a list of DynamicID objects with objects details
        given a tag object or id string"""
        # TODO: Return VM objects rather than DynamicID objects.
        tag_id = tag.id if type(tag) == TagModel else tag
        vms = self.tagAssociationSvc.list_attached_objects(tag_id)
        return vms

    def _addTagToObject(self, tag, obj, vs_type='VirtualMachine'):
        """Given a tag id/object and a vmware object(Dynamic ID object or id)
        Attach the tag to the object
        """
        tag_id = tag.id if type(tag) == TagModel else tag
        d_obj = obj if type(obj) == DynamicID else DynamicID(type=vs_type, id=obj)

        self.tagAssociationSvc.attach(tag_id=tag_id, object_id=d_obj)

        if not self._checkObjectHasTag(tag, obj, vs_type):
            raise SystemError("Impossibile aggiungere il Tag alla VM")

    def _removeTagFromObject(self, tag, obj, vs_type='VirtualMachine'):
        """Given a tag id/object and a vmware object(Dynamic ID object or id)
        Detach the tag to the object
        """
        tag_id = tag.id if type(tag) == TagModel else tag
        obj_did = obj if type(obj) == DynamicID else DynamicID(type=vs_type, id=obj)

        result = self.tagAssociationSvc.detach(tag_id=tag_id, object_id=obj_did)
        return result

    def _checkObjectHasTag(self, tag, obj, vs_type='VirtualMachine'):

        tag_id = tag.id if type(tag) == TagModel else tag

        tags = self._getTagsForObject(obj, vs_type)

        attached = False

        for t in tags:
            if t.id == tag_id:
                attached = True
                break

        return attached




    def _isVmTemplate(self, vm):
        try:
            return vm.config.template
        except:
            return False
