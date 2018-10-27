#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Author: Saul Bertuccio
# Date: ven 12 luglio 2017

# Elenco tag e categorie per tutte le VM o le VM in una cartella del Vcenter


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

def csvAdapt(data):
    d = {}
    for k, v in data.iteritems():
        d[k] = v if type(v) == str else '|'.join(str(x) for x in v)

    return d

def getWriter(ftype, fh, fields):

    if ftype == 'csv':
        csv_writer = csv.DictWriter(fh, fieldnames=fields)
        csv_writer.writeheader()
        return lambda dict: csv_writer.writerow(csvAdapt(dict))
        csv_writer.writerow

    elif ftype == 'json':
        return lambda dict: fh.write(json.dumps(dict) + '\n')
    else:
        raise Exception("Errore: parametro tipo %s non supportato" % ftype )

def GetArgs():
    """
    Gestione degli argomenti
    """
    PARS=VcenterParams()
    parser = getBaseArgs(PARS)

    parser.add_argument('-i', '--ip', required=True, action='store', help='Ip da ricercare')

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
        vms = vmdtc. getVirtualMachineIpAddress(args.ip)
    except Exception, e:
        sys.stderr.write(str(e))
        sys.exit(1)

    if not vms:
        sys.stderr.write("Attenzione: nessuna Macchina virtuale trovata con ip %s\n" % args.ip)
        sys.exit(1)

    # Get list of categories name removing default VSPHERE categores

    for vm in vms:
        print(vm.name)

#
# Avvio l'applicazione
if __name__ == "__main__":
    main()
