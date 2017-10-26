# vsphere_pylib

### vSphere Python Library**

Un semplice wrapper per la libreria "pyVmomi" e le API VMware vCloud, che consente la gestione degli snapshot dei Tag e delle Categorie.

** Richiede l'installazione di "pyVmomi" (https://github.com/vmware/pyvmomi) e le API VMware vCloud (https://code.vmware.com/web/sdk/60/vcloudsuite-python)


### Strumenti:

- **snapshost_manage.py**: script in python che esegue operazioni sugli snapshot delle macchine virtuali.
- **vm_tags.py**: script che elenca i tag presenti sulle VM
- **vmware_tags_to_ansible_vars.py**: questo script può essere usato per verificare che VM presentino TAG e CATEGORIE specifiche,  oppure per creare o aggiornare i file `hosts` e `hosts vars` di Ansibile a partire da un elenco di TAG e CATEGORIE specificati.


