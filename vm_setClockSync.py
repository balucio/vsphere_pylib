#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Author: Saul Bertuccio
# Date: ven 12 luglio 2017

# Imposta il clock sync per le VM


from __future__ import print_function

# Custom libs
from libs.datacenter import Datacenter

from libs.utils import checkDate, getBaseArgs
from configs.vcenterparams import VcenterParams
from pyVim.task import WaitForTasks

import argparse
import time
import getpass
import sys

import copy
import json
import csv

from datetime import datetime


# DEBUG
from pprint import pprint

def GetArgs():
    """
    Gestione degli argomenti
    """
    PARS=VcenterParams()
    parser = getBaseArgs(PARS)

    parser.add_argument('-f', '--folder', required=False, action='store', default='/',
                            help='Percorso assoluto della cartella sul datacenter contenente le VM per cui elencare tag e categorie.')


    parser.add_argument('--autosync', required=False, action='store', choices=['si', 'no'], default = None,
                        help="Specifica se attivare o disattivare il sync dell'orologio")

    args = parser.parse_args()
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
    except Exception, e:
        sys.stderr.write(str(e))
        sys.exit(1)

    try:
        vms = vmdtc.getVirtualMachineList(folder = args.folder, recursive = True)
    except Exception, e:
        sys.stderr.write(str(e))
        sys.exit(1)

    if not vms:
        sys.stderr.write("Attenzione: nessuna Macchina virtuale trovata nella cartella %s\n" % args.folder)
        sys.exit(1)

    for vm in vms:
        try:
            enabled = vm.clockSync()
            if enabled:
                sys.stdout.write("VM %s sincronizzazione abilitata\n" % vm.name)
            else:
                sys.stdout.write("VM %s sincronizzazione non abilitata\n" % vm.name)

            if args.autosync is not None:

                if args.autosync == 'si':
                    if not enabled:
                        sys.stdout.write("-- abilito sincronizzazione\n")
                        vm.clockSync(True)
                else:
                    if enabled:
                        sys.stdout.write("-- disattivo sincronizzazione\n")
                        vm.clockSync(False)
            else:
                sys.stdout.write("-- nessuna modifica\n")

        except Exception, e:
            sys.stderr.write("Errore VM %s, probabilmente non sono installati i VMWare Tools (%s)\n" % (vm.name, str(e)))


#
# Avvio l'applicazione
if __name__ == "__main__":
    main()
