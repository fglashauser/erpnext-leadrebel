import requests
import frappe
from .tools import get_lr_date
import json

class Api:
    """Class for LeadRebel API-calls"""
    def __init__(self):
        self.config = frappe.get_single("LeadRebel Settings")
        self._page_size = 100   # Number of results per request
        
    def __enter__(self):
        self.open()
        return self
    
    def open(self):
        self.session = requests.Session()
        self.session.headers = {
            "Accept"                : "application/json",
            "Content-Type"          : "application/json",
            "auth"                  : self.config.get_password("api_key")
        }

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def close(self):
        self.session.close()

    def _request(self, endpoint: str, method: str = "POST", params: dict = None, data = None) -> dict:
        """Generic request method for LeadRebel API."""
        url = f"{self.config.get('api_url')}{endpoint}"
        try:
            response = self.session.request(method=method, url=url, params=params, data=data)
            response.raise_for_status()
        except requests.RequestException as e:
            frappe.throw(f"LeadRebel API-Error: {e}")
        return response.json()
    
    def _request_list(self, endpoint: str, method: str = "POST", data_dict: dict = None, page: int = 0) -> list:
        """Requests a list of results from LeadRebel API.
        Handles the pagination of the results.
        
        Args:
            data_dict (dict): The data to send with the request as dict,
            will be converted to JSON."""
        data_dict = data_dict or {}
        data_dict["page"] = page
        data_dict["itemsPerPage"] = self._page_size
        response = self._request(endpoint=endpoint, method=method, data=json.dumps(data_dict))
        data = list(response["data"])
        if response["total"] > (page + 1) * self._page_size:
            data.extend(self._request_list(endpoint=endpoint, method=method, data_dict=data_dict, page=page + 1))
        return data
    
    def _filter_countries(self, sessions: list) -> list:
        """Filters sessions by countries in LeadRebel Settings (if defined)."""
        filters = self.config.countries
        if not filters:
            return sessions
        countries = [frappe.get_doc("Country", filter.country).code.upper() for filter in filters]
        return [session for session in sessions if session["countryCode"] in countries]
    
    def get_company(self, company_id: str) -> dict:
        """Returns a company from LeadRebel."""
        return self._request(endpoint=f"companies/{company_id}", method="GET")["data"]
    
    def get_all_sessions(self) -> dict:
        return self._request_list(endpoint="visit/sessions/list")

    def get_new_sessions(self) -> dict:
        """Returns all sessions from LeadRebel starting from last sync date."""
        sessions = self._request_list(endpoint="visit/sessions/list", data_dict={
            "minDate": get_lr_date(self.config.last_sync)
        })
        return self._filter_countries(sessions)
    