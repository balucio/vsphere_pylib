# vsphere_pylib

### vSphere Python Library

It is a simple wrapper for "pyVmomi" and VMware vCloud API, in order to manage VM snapshot and Tags and Categories.

** Require: "pyVmomi" (https://github.com/vmware/pyvmomi) and VMware vCloud APIs (https://code.vmware.com/web/sdk/60/vcloudsuite-python)


### Tools:

- **snapshost_manage.py**: python script to manage VMs snapshots.
- **vm_tags.py**: python script to list all VMs Tags
- **vm_findby_ip.py**: python script to search a VM by their IP address (require VMWare Tools installed on VM)
- **vm_setClockSync.py**: python script to enable o disable clock sync (require VMWare Tools installed on VM)
- **vm_setTags.py**: python script to set a VM Tag
- **vmware_tags_to_ansible_vars.py**: this script will update or check Ansible hosts files. In update mode some TAGS and CATEGORIES are updated in ansible hosts file. In check mode the script will check that TAGS and CATEGORY in hosts file are the same in VCenter..

### Config:
- **configs/mailparams.py**: parameters for mail server (used by vmware_tags_to_ansible_vars.py).
- **configs/vcenterparams.py**: VCenter VMWare params.
