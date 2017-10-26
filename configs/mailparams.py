#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Author: Saul Bertuccio
# Date: ven 30 giugno 2017

"""
Configurazione

"""

class MailParams(object):

    @property
    def HOST(self):
        return "mail.example.it"

    @property
    def PORT(self):
        return 25

    @property
    def SENDER(self):
        return "ansible@example.it"

    @property
    def RECIPIENT(self):
        return "admin@example.it"


