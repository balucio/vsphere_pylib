#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Author: Saul Bertuccio
# Date: ven 30 giugno 2017

"""
Configurazione

"""

import os
from base64 import b64decode

class VcenterParams(object):

    @property
    def HOST(self):
        return "vcrunner.example.it"

    @property
    def PORT(self):
        return 443

    @property
    def DATACENTER(self):
        return "DATACENTER"

    @property
    def DATEFORMAT(self):
        return "%Y-%m-%d"

    @property
    def USER(self):
        """ ritorno l'utente loggato """
        return os.getlogin()


    @property
    def ADMINUSER(self):
        return "admin"

    @property
    def ADMINPASSWORD(self):
        return b64decode("base64_encoded_password")