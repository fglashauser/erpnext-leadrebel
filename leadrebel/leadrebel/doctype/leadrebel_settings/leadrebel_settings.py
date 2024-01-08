# Copyright (c) 2024, PC-Giga and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from ....api import Api
import json
from ....importer import Importer

def import_sessions():
	"""Imports all sessions from LeadRebel."""
	with Importer() as importer:
		importer.import_sessions()

class LeadRebelSettings(Document):
	@frappe.whitelist()
	def import_sessions(self):
		"""Imports all sessions from LeadRebel."""
		import_sessions()

	@frappe.whitelist()
	def match_existing_leads(self):
		"""Matches existing leads with the LeadRebel companies."""
		with Importer() as importer:
			importer.match_existing_leads()