#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Author: Saul Bertuccio
# Date: ven 19 luglio 2017

"""
Libreria per l'invio di mail
"""
import smtplib
from email.MIMEMultipart import MIMEMultipart
from email.MIMEText import MIMEText

class Mail(object):

	def __init__(self, params):

		self._server = smtplib.SMTP(params.HOST, params.PORT)

	def send(self, sender, recipient, subject, body):

		msg = MIMEMultipart()
		msg['From'] = sender
		msg['To'] = recipient
		msg['Subject'] = subject
		msg.attach(MIMEText(body, 'plain','utf-8'))
		self._server.sendmail(sender, recipient , msg.as_string())





