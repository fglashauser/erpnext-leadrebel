import frappe
from frappe import utils
from .api import Api
from .tools import split_name, prepare_email, get_country_by_code, get_street_by_lr_full_address, get_en_date, standardize_phone_number

class Importer:
    """Class for importing LeadRebel data."""
    def __init__(self):
        self.config = frappe.get_single("LeadRebel Settings")
        self.api = Api()

    def __enter__(self):
        self.api.open()
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        self.api.close()

    def _find_lead_by_id(self, company_id: str) -> "frappe.Document":
        """Checks if a lead already exists in ERPNext and returns it.
        
        Args:
            company_id (str): The LeadRebel company ID to search for.
        """
        lead = next(iter(frappe.get_all("Lead", filters={"lr_id": company_id})), None)
        return frappe.get_doc("Lead", lead.name) if lead else None
    
    def _find_lead_by_name(self, company_name: str) -> "frappe.Document":
        """Checks if a lead already exists in ERPNext and returns it.
        
        Args:
            company_name (str): The LeadRebel company name to search for.
        """
        lead = next(iter(frappe.get_all("Lead", filters={"company_name": company_name})), None)
        return frappe.get_doc("Lead", lead.name) if lead else None

    def _find_page_view_by_id(self, pv_id: str) -> "frappe.Document":
        """Checks if a page view already exists in ERPNext and returns it."""
        pv = next(iter(frappe.get_all("Lead Page View", filters={"lr_id": pv_id})), None)
        return frappe.get_doc("Lead Page View", pv.name) if pv else None
    
    def _import_lead(self, company_id: str) -> "frappe.Document":
        """Imports a single Lead from LeadRebel."""
        company = self.api.get_company(company_id)
        salutation, first_name, last_name = split_name(self.config, company.get("contactName", None))
        street = get_street_by_lr_full_address(company.get("fullAddress", None),
                                               company.get("postal", None),
                                               company.get("city", None))
        # Lead Main-Entry
        lead = frappe.get_doc({
            "doctype"               : "Lead",
            "type"                  : "Client",
            "qualification_status"  : self.config.qualification_status if self.config.qualification_status else "Unqualified",
            "status"                : "Open",
            "source"                : self.config.lead_source,
            "lr_id"                 : company["id"],
            "salutation"            : salutation,
            "first_name"            : first_name,
            "last_name"             : last_name,
            "company_name"          : company.get("name", str()).strip(),
            "email_id"              : prepare_email(company.get("email", None)),
            "phone"                 : standardize_phone_number(company.get("phone", None)),
            "website"               : company.get("website", None),
            "lead_owner"            : self.config.lead_owner,
            "notes"                 : [frappe.get_doc({"doctype": "CRM Note", "note": company["description"]})] \
                if company.get("description", None) else None
        }).insert()
        # Address
        if street:
            frappe.get_doc({
                "doctype"               : "Address",
                "address_type"          : "Billing",
                "is_shipping_address"   : True,
                "is_primary_address"    : True,
                "address_title"         : company["name"].strip(),
                "address_line1"         : get_street_by_lr_full_address(company["fullAddress"],
                                                                        company["postal"],
                                                                        company["city"]),
                "city"                  : company["city"],
                "pincode"               : company["postal"],
                "country"               : get_country_by_code(company["countryCode"]),
                "phone"                 : standardize_phone_number(company["phone"]),
                "links"                 : [{
                    "link_doctype"      : "Lead",
                    "link_name"         : lead.name
                }]
            }).insert()
        lead.reload()
        return lead
    
    def _import_session(self, session: dict):
        """Imports a single session from LeadRebel."""
        # try to find lead, else create new one
        lead = self._find_lead_by_id(session["companyId"])
        if not lead:
            lead = self._import_lead(session["companyId"])
        # check if page views already exists, create new ones
        for page_view in session["pageViews"]:
            pv = self._find_page_view_by_id(page_view["id"])
            if not pv:
                lead.append("page_views", {
                    "lr_id"                 : page_view["id"],
                    "datetime"              : get_en_date(page_view["datetime"]),
                    "website"               : page_view["website"],
                    "path"                  : page_view["pagePath"],
                    "duration"              : page_view["timeOnPage"]
                })
                lead.save()
            
    def import_sessions(self):
        """Imports all sessions from LeadRebel."""
        sessions = self.api.get_new_sessions()
        for session in sessions:
            self._import_session(session)
        self.config.last_sync = utils.now()
        self.config.save()
        frappe.db.commit()
        frappe.msgprint(f"{len(sessions)} Sessions imported.")

    def match_existing_leads(self):
        """Matches existing leads with the LeadRebel companies.
        Sets the LeadRebel-ID (lr_id) to a matching lead."""
        sessions = self.api.get_all_sessions()
        for session in sessions:
            lead = self._find_lead_by_name(session["companyName"].strip())
            if lead:
                lead.update({"lr_id": session["companyId"]}).save()
        frappe.db.commit()
        frappe.msgprint(f"{len(sessions)} Sessions matched.")