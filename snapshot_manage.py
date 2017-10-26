#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Author: Saul Bertuccio
# Date: ven 30 giugno 2017

# Applicativo per la gestione degli snapshot delle VM per cartella


from __future__ import print_function

from pyVim.task import WaitForTasks
from pyVmomi import vim

# Custom libs
from libs.datacenter import Datacenter
from libs.utils import checkDate, getBaseArgs

# Config
from configs.vcenterparams import VcenterParams

import argparse
import time
import getpass
import sys

from datetime import datetime

# Cartelle
#  SDM-Dinamico
#

def progressMeter():
    while True:
        for cursor in '|/-\\':
            yield cursor

spinner = progressMeter()

def powerVm(vmlist, mode):

    tasks = []
    if mode == 'off':
        sys.stdout.write('Spengo le VM:\n')
        oper = 'spegnimento'
        check = lambda vm: vm.isOn()
        not_oper = 'spenta'
    else: 
        sys.stdout.write('Accendo le VM:\n')
        oper = 'accensione'
        check = lambda vm: not vm.isOn()
        not_oper = 'accesa'

    for vm in vmlist:

        if check(vm):
            sys.stdout.write("-- VM %s in %s\n" % (vm.name, oper))
            tasks.append(vm.power(mode=mode, async=True))
        else:
            sys.stdout.write("-- VM %s %s\n" % (vm.name, not_oper))

    WaitForTasks(tasks, onProgressUpdate=taskProgress)
    sys.stdout.write("Operazione completata.\n")

def createSnapshot(vmlist, snap_name, descrTpl = None, status='leave'):

    if descrTpl == None:
        descrTpl = "Snapshot del %s\n" % datetime.now().strftime("%Y-%m-%d %H:%M")
    
    tasks = []
    for vm in vmlist:
        sys.stdout.write("-- VM %s\n" % vm.name )
        tasks.append(vm.createSnapshot(snap_name, descrTpl, async=True))
    
    WaitForTasks(tasks, onProgressUpdate=taskProgress)
    sys.stdout.write("Snapshot create correttamente.\n")

def taskProgress(task, percentDone):
    sys.stdout.write(spinner.next())
    sys.stdout.flush()
    time.sleep(0.1)
    sys.stdout.write('\b')
    #print ('Task %s è completo al %s%%' % (task.info.name, percentDone))

def getSnapshotsListFromVm(vmlist, snapname):

    snap_list = []

    for vm in vmlist:
        snap = vm.snapshotByName(snapname)
        if snap:
            snap_list.append(snap)

    return snap_list

def deleteSnapshot(vmlist, snap_name, snap_list, cascade):

    msg = "Elimino snapshot %s:" % snap_name
    if cascade:
        msg = msg + " e tutti gli snapshot dipendenti."

    tasks = []
    sys.stdout.write(msg + '\n')

    for idx, snap in enumerate(snap_list):
        sys.stdout.write("-- VM %s\n" % vmlist[idx].name)
        tasks.append(snap.remove(async=True, removeChildren=cascade))

    WaitForTasks(tasks, onProgressUpdate=taskProgress)
    sys.stdout.write("Snapshot eliminate correttamente.\n")


def revertSnapshot(vmlist, snap_name):

    tasks = []
    sys.stdout.write("Revert snapshot %s:\n" % snap_name)
    for idx, snap in enumerate(snap_list):
        sys.stdout.write("-- VM %s\n" % vmlist[idx].name)
        tasks.append(snap.revert(async=True))
    
    WaitForTasks(tasks, onProgressUpdate=taskProgress)
    sys.stdout.write("Revert snapshot eseguito correttamente.\n")

def GetArgs():
    """
    Gestione degli argomenti
    """
    PARS=VcenterParams()
    parser = getBaseArgs(PARS)

    today = datetime.now()

    def_date = today.strftime(PARS.DATEFORMAT)

    subcommand = parser.add_subparsers(help='comando (help per aiuto)', dest="command")

    snap_create = subcommand.add_parser('create', help='Creazione snaphost (create help per aiuto)')
    snap_delete = subcommand.add_parser('delete', help='Cancellazione snaphost (delete help per aiuto)')
    snap_revert = subcommand.add_parser('revert', help='Revert snaphost (revert help per aiuto)')

    snap_create.add_argument('-f', '--folder', required=True, action='store',
                            help='Percorso assoluto della cartella sul datacenter contenente le VM per cui creare gli snapshot.')

    snap_create.add_argument('date', nargs='?', action='store', type=checkDate, default=def_date,
                            help='Data da usare come nome degli snapshot (predefinita %s)' % def_date)

    snap_delete.add_argument('-f', '--folder', required=True, action='store',
                            help='Percorso assoluto della cartella sul datacenter contenente le VM da cui eliminare gli snapshot.')

    snap_delete.add_argument('date', action='store', type=checkDate,
                            help='Data che verrà usata come nome per gli snapshot da eliminare.')

    snap_delete.add_argument('-c', '--cascade', action='store_true', required=False,
                            help='Se specificato verrà eliminato lo snapshot specificato e tutti gli snapshot dipendenti.')

    snap_revert.add_argument('date', action='store', type=checkDate,
                            help='Data snapshot da ripristinare')

    snap_revert.add_argument('-f', '--folder', required=True, action='store',
                            help='Percorso assoluto della cartella sul datacenter contenente le VM da riportare allo snapshot specificato.')

    args = parser.parse_args()

    if args.user == PARS.ADMINUSER:
        args.password = PARS.ADMINPASSWORD
    return args

def main():

    # Parsing argomenti
    args = GetArgs()

    if args.password:
      password = args.password
    else:
      password = getpass.getpass(prompt='Inserire la password per l\'host %s e l\'utente %s: ' % (args.host,args.user))

    # Connessione al vcenter e oggetto DataCenter
    try:
        vmdtc = Datacenter(host=args.host,
                           user=args.user,
                           password=password,
                           port=int(args.port),
                           datacenter = args.datacenter)

    except vim.fault.InvalidLogin:
        sys.stderr.write("Nome utente o password errati.\n")
        sys.exit(1)

    except Exception, e:
        sys.stderr.write(str(e))
        sys.exit(1)

    try:
        vms = [ vm for vm in vmdtc.getVirtualMachineList(folder = args.folder, recursive = False)]

    except Exception, e:
        sys.stderr.write(str(e))
        sys.exit(1)

    if not vms:
        sys.stderr.write("Attenzione: nessuna Macchina virtuale trovata nella cartella %s\n" % args.folder)
        sys.exit(1)

    snap_name = args.date.strftime(VcenterParams().DATEFORMAT)

    snap_list = getSnapshotsListFromVm(vms, snap_name)

    try:
        if args.command == 'create':

            if len(snap_list) > 0:
                raise RuntimeError("Lo snapshot %s è già presente su una o più delle VM selezionate.\n" % snap_name)

            vms.sort(key=lambda vm: vm.name, reverse=True)
            powerVm(vms, 'off')
            createSnapshot(vms, snap_name)
            powerVm(vms, 'on')

        elif args.command == 'revert':

            if len(vms) != len(snap_list):
                raise RuntimeError("Lo snapshot %s non è presente su tutte le VM selezionate" % snap_name)

                revertSnapshot(vms, snap_name)
                vms.sort(key=lambda vm: vm.name, reverse=True)
                powerVm(vms, 'on')

        elif args.command == 'delete':

            if len(vms) != len(snap_list):
                raise RuntimeError("Lo snapshot %s non è presente su tutte le VM selezionate\n" % snap_name)

            deleteSnapshot(vms, snap_name, snap_list, args.cascade)

    except Exception, e:
        raise
        sys.stderr.write(str(e))
        sys.exit(1)

    sys.exit(0)

# Avvio l'applicazione
if __name__ == "__main__":
    main()
