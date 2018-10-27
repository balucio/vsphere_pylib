#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Author: Saul Bertuccio
# Date: gio 1 febbraio 2017

# Imposta i tag per la vm

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
import yaml

from datetime import datetime


from pprint import pprint


# DEBUG
from pprint import pprint

def GetArgs():
    """
    Gestione degli argomenti
    """
    PARS=VcenterParams()
    parser = getBaseArgs(PARS)

    parser.add_argument('-n', '--vmname', required=True, action='store',
                            help='Nome della VM per la quale impostare tag e categorie.')

    # type = lambda s : s.upper()
    parser.add_argument('-t', '--tags', required=True, nargs='+', action='store',
                        help='Elenco dei tag che devono essere associati alla macchina virtuale.')

    args = parser.parse_args()

    if args.user == 'sysadmin':
        args.password = PARS.SYSADMINPASSWORD

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
        vms = vmdtc.getVirtualMachineByName(name=args.vmname)
    except Exception, e:
        sys.stderr.write(str(e))
        sys.exit(1)

    if not vms:
        sys.stderr.write("Attenzione: nessuna Macchina virtuale trovata nella cartella %s\n" % args.folder)
        sys.exit(1)

    # ottengo tutti i tags dal nome

    tags = []
    for t in args.tags:
        tag = vmdtc.getTagByName(t)
        vms.setTag(tag, vmdtc)

#
# Avvio l'applicazione
if __name__ == "__main__":
    main()
