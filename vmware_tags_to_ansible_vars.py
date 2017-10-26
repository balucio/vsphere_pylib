#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Author: Saul Bertuccio
# Date: ven 12 luglio 2017

# Gestione e aggiornamento tag per Ansible


from __future__ import print_function

# Custom libs
from libs.datacenter import Datacenter
from libs.sendmail import Mail
from libs.utils import checkDate, getBaseArgs

#configuration files
from configs.vcenterparams import VcenterParams
from configs.mailparams import MailParams

from pyVim.task import WaitForTasks

import argparse
import time
import getpass
import sys
import logging
import subprocess

import copy
import json
import csv
import os

from datetime import datetime

import yaml
import tempfile
import shutil

# Ansible API
from ansible.parsing.dataloader import DataLoader
from ansible.vars import VariableManager
from ansible.inventory import Inventory

MANDATORY_CATEGORY = ['TIPO','AREA','ASSET']
HOST_VARS_CATEGORY = ['TIPO','AREA','ASSET', 'SISTEMI']

ANSIBLE_VARS_DIR = "/etc/ansible"

def initLog(level = logging.INFO):

    log = logging.getLogger()
    log.setLevel(level)

    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(level)
    #formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    log.addHandler(ch)

    return log

LOG = initLog()

def verify(vcenter, vms, tags):

    msg = []

    for vm in vms:

        vmname = vm.name.lower()

        categories = vcenter.getVirtualMachineCategoriesAndTags(vm)
        not_present_cats = notAvailableCategories(categories, tags)

        if not_present_cats:
            LOG.warning("Attenzione: VM %s assenti le categorie: %s" % (vmname, ', '.join(not_present_cats)))
            msg.append("-- %s categorie assenti: %s" % (vmname, ', '.join(not_present_cats)))
        else:
            LOG.info("VM %s sono presenti le categorie: %s" % (vmname, ', '.join(tags)))

    if msg:
        msg.insert(0, "Riepilogo verifica presenza categorie sulle VM:")

    return msg

def update(vcenter, vms, tags, vars_dir, msg):

    # Creo un file temporaneo che conterrà il nuovo elenco
    hosts_tfd, hosts_tpath = tempfile.mkstemp()

    ansible_hosts_file = os.path.join(vars_dir, "hosts")

    current_hosts_vars = os.listdir(os.path.join(vars_dir, "host_vars"))

    #bashCommandTpl = "ansible-playbook /etc/ansible/playbook/ns/auth-e-syslog.yml -e hosts=%s"

    for vm in vms:

        categories = vcenter.getVirtualMachineCategoriesAndTags(vm)

        vmname = vm.name.lower()

        # Rimuovo il nome della VM dall'elenco dei file delle variabili di ansible
        try:
            current_hosts_vars.remove(vmname)
        except ValueError:
            pass

        # Variabili di ansible
        vars_file = os.path.join(vars_dir, "host_vars", vmname)

        LOG.info("Verifica variabili ansibile per VM %s, categorie %s" % (vmname, ', '.join(tags)))

        try:

            if updateTagValue(vars_file, categories, tags ):
                LOG.warning("File %s per la VM %s è stato aggiornato" % (vars_file, vmname))
                msg.append("VM %s: aggiornato il file %s" % (vmname, vars_file))

                #bashCommand = bashCommandTpl % vmname
                #process = subprocess.Popen(bashCommand.split(), stdout=subprocess.PIPE)
                #output, error = process.communicate()
            else:
                LOG.info("Nessuna modifica al file %s della VM %s" % (vars_file, vmname))

            # Scrivo il nome della VM nel file
            os.write(hosts_tfd, vmname + '\n')

        except Exception, e:
            LOG.error("%s" % e)
            LOG.error("VM %s impossibile aggiornare il file %s" % (vmname, vars_file))
            msg.append("VM %s: errore nell'aggiornamento del file %s" % (vmname, vars_file))

    # Overwrite old Hosts file
    os.close(hosts_tfd)
    shutil.copy(hosts_tpath, ansible_hosts_file)
    LOG.info("File hosts ansible correttamente aggiornato.")
    os.remove(hosts_tpath)

    if msg:
        msg.insert(0, "Riepilogo attività di allienamento degli hosts vars di Ansible con le categorie del VCENTER:")

    return current_hosts_vars

def removeOldVars(vars_dir, host_list, msg):

    static_hosts = getAnsibleStaticHosts(vars_dir)

    # Rimuovo eventuali file di variabile non più necessari
    for host in static_hosts:

        try:
            host_list.remove(host.name)
        except ValueError as e:

            vars_file = os.path.join(vars_dir, "host_vars", host.name)

            if os.path.isfile(vars_file):
                os.remove(vars_file)
                LOG.warning("VM %s rimossa o rinominata, elmino file variabili %s." % (host.name, vars_file))
                msg.append("VM %s: rimossa o rinominata, file variabili %s eliminato." % (host.name, vars_file))

def getAnsibleStaticHosts(hosts_dir):

    static_hosts_dir = os.path.join(hosts_dir, 'host_static')

    hosts_file = [ os.path.join(static_hosts_dir, f) for f in os.listdir( static_hosts_dir ) ]
    #hosts_file.append(os.path.join(hosts_dir, 'hosts'))

    host_list = []
    loader = DataLoader()
    variable_manager = VariableManager()

    for hf in hosts_file:
        inventory = Inventory( loader = loader,  variable_manager = variable_manager, host_list = hf )
        host_list.extend(inventory.get_hosts())

    return host_list


def sendMail(subj, body):

    try:
        pars = MailParams()
        mail = Mail(pars)
        mail.send(pars.SENDER, pars.RECIPIENT, subj, body)
        return True
    except Exception, e:
        LOG.warning("Attenzione: impossibile inviare il messaggio di posta (%s)" % e)
        return Falsee

def updateTagValue(vmvars, categories, names):

    try:
        stream = open(vmvars, 'r')
        data = yaml.load(stream)
        LOG.debug("Caricato file variabili %s: %s" % (vmvars, data))
    except IOError as e:
        LOG.warning("Attenzione: il file delle variabili %s non esiste" % vmvars)
        data = {}

    changed = False

    for uid in categories.iterkeys():

        cat_name = categories[uid]['category'].name.upper()

        if cat_name in names:

            cat_idx = 'TAG_' + cat_name
            cat_value = categories[uid]['tags'][0].name

            if cat_idx in data and data[cat_idx] == cat_value.lower():

                LOG.debug("File %s: categoria %s valore %s nessuna modifica" % (
                    vmvars, cat_name, cat_value))

            else:

                changed = True

                if cat_idx not in data:
                    LOG.debug("File %s: categoria %s valore %s non presente" % (vmvars, cat_name, cat_value))

                else:
                    LOG.debug("File %s: categoria %s modificata (vecchio %s nuovo %s)" % (
                        vmvars, cat_name, data[cat_idx], cat_value))

                data[cat_idx] = cat_value.lower()

        else:
            LOG.debug("File %s: ignoro categoria %s " % (vmvars, cat_name))

    if changed:
        LOG.debug("Aggiorno file %s" % (vmvars))
        with open(vmvars, 'w') as yaml_file:
            yaml_file.write( yaml.dump(data, default_flow_style=False))

    return changed

def notAvailableCategories(categories, names):

    cats = [ c['category'].name.upper() for k, c in categories.iteritems() ]
    return set(names) - set(cats)


def GetArgs():
    """
    Gestione degli argomenti
    """
    PARS=VcenterParams()
    parser = getBaseArgs(PARS)

    parser.add_argument('-f', '--folder', required=False, action='store', default='/',
                        help='Percorso assoluto della cartella sul datacenter contenente le VM per cui elencare tag e categorie.')


    subcommand = parser.add_subparsers(help='azione (help per aiuto)', dest="action")

    verify = subcommand.add_parser('verify', help='Verifica che le VM abbiano correttamente assegnati i TAG (verify help per aiuto)')
    update = subcommand.add_parser('update', help='Aggiorna i file host_vars di Ansible per ciascuna VM (update help per aiuto)')

    verify.add_argument('-t', '--tags', required=False, nargs='+', action='store', default=MANDATORY_CATEGORY, type = lambda s : s.upper(),
                        help='Elenco dei tag che devono essere assegnati a ciascuna VM (predefinito %s).' 
                            % MANDATORY_CATEGORY)

    update.add_argument('-t', '--tags', required=False, nargs='+', action='store', default=HOST_VARS_CATEGORY, type = lambda s : s.upper(),
                        help='Elenco dei tag che devono essere inseriti nel file host_vars di Ansible se presenti (predefinito %s).' 
                            % HOST_VARS_CATEGORY)

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
        LOG.error("Errore: impossibile connettersi al VCenter (%s)" % e)
        sys.exit(1)

    try:
        vms = vmdtc.getVirtualMachineList(folder = args.folder, recursive = True)
    except Exception, e:
        vms = []

    if not vms:
        subject = "ATTENZIONE: Aggiornamento/Verifica inventario VCENTER"
        LOG.error("Errore: impossibile ottenere l'elenco delle VM dal VCenter")
        msg = ["Errore: impossibile ottenere l'elenco delle VM dal VCenter"]

    elif args.action == 'verify':

        subject = "ATTENZIONE: Non conformità INVENTARIO VCenter"
        msg = verify(vmdtc, vms, args.tags)

    elif args.action == 'update':

        subject ="Sincronizzazione variabili Ansible con Categorie del VCENTER:"

        msg = []
        old_host = update(vmdtc, vms, args.tags, ANSIBLE_VARS_DIR, msg)
        removeOldVars(ANSIBLE_VARS_DIR, old_host, msg)

    if msg:
        sendMail(subject, body='\n\r'.join(msg))

    sys.exit(0)

# Avvio l'applicazione
if __name__ == "__main__":
    main()
