#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Author: Saul Bertuccio
# Date: ven 30 giugno 2017

"""
funzioni di uso comune
"""

import os
import argparse

from datetime import datetime


def getPathComponents(path):

    path = os.path.abspath(os.path.normpath(path))
    path = path.lstrip(os.sep)
    folders = []

    while path:
        path, folder = os.path.split(path)
        if folder != "":
            folders.insert(0,folder)
        elif path != "" :
           folders.insert(0,path)

    return folders


def checkDate(s, f="%Y-%m-%d"):
    try:
        return datetime.strptime(s, f)
    except ValueError:
        msg = "Data '{0}' non valida.".format(s)
        raise argparse.ArgumentTypeError(msg)


def getBaseArgs(params):
    """
    Gestione degli argomenti comuni
    """

    parser = argparse.ArgumentParser(
       description='Elenco di tag e categorie per VM.')

    parser.add_argument('-s', '--host', required=False, action='store', default=params.HOST,
                       help='L\'host VMWare a cui connetersi (predefinito %s)' % params.HOST)

    parser.add_argument('-d', '--datacenter', required=False, action='store', default=params.DATACENTER,
                       help='Il nome del datacenter su cui eseguire le operazioni (predefinito %s)' % params.DATACENTER)

    parser.add_argument('-p', '--port', required=False, action='store', type=int, default=params.PORT,
                       help='Porta di connessione dell\'host VMWare (predefinita %s)' % params.PORT)

    parser.add_argument('-u', '--user', required=False, action='store', default=params.USER,
                       help='Nome utente per la connessione all\'host VMWare.')

    parser.add_argument('-w', '--password', required=False, action='store',
                       help='Password da usare per la connessione all\'host VMWare.')

    return parser