import frappe
from frappe import utils
from pytz import timezone
from typing import Tuple
from datetime import datetime
import re

@staticmethod
def get_lr_date(datetime: str) -> str:
    """Returns a LeadRebel date string from a datetime string."""
    if not datetime:
        return None
    return timezone(utils.get_system_timezone()) \
            .localize(utils.get_datetime(datetime)) \
            .astimezone(timezone("UTC")) \
            .strftime("%Y-%m-%d")

@staticmethod
def get_en_date(lr_datetime: str) -> str:
    """Returns a ERPNext date string from a LeadRebel datetime string."""
    if not lr_datetime:
        return None
    return utils.get_datetime_str(
        datetime.fromisoformat(lr_datetime.replace("Z", "+00:00")) \
        .astimezone(timezone(utils.get_system_timezone())) \
    )

@staticmethod
def split_name(config: "frappe.Document", name: str) -> Tuple[str, str, str]:
    """Splits a name into salutation, first name and last name.
    
    Args:
        config (frappe.Document): The LeadRebel Settings document
        name (str): The name to split
    
    Returns:
        Tuple[str, str, str]: Salutation, First name and last name
    """
    if not name:
        return None, None, None
    salutation = None
    if name.startswith("Herr"):
        salutation = config.salutation_mr
        name = name.replace("Herr", "").strip()
    if name.startswith("Frau"):
        salutation = config.salutation_mrs
        name = name.replace("Frau", "").strip()
    return salutation, \
        re.sub(r'\s+\w+$', '', name), \
        re.sub(r'^\w+\s+', '', name).split()[-1]

@staticmethod
def prepare_email(email: str) -> str:
    """Prepares the email address for the given email.
    Replace umlauts and check if the email address is valid.
    Returns None if the email address is invalid.

    Args:
        email (str): Email address to prepare

    Returns:
        str: Prepared email address
    """
    if not email:
        return None
    email = email.lower().replace("ä", "ae") \
                            .replace("ö", "oe") \
                            .replace("ü", "ue") \
                            .replace("ß", "ss")
    return email if re.match(r"^\S+@\S+\.\S+$", email) else None

@staticmethod
def get_country_by_code(code: str) -> str:
    """Returns the country name for the given country code.

    Args:
        code (str): Country code to get the country name for

    Returns:
        str: Country name
    """
    country = frappe.get_all("Country", filters={"code": code.lower()}, fields=["name"])
    return country[0].get("name", None) if len(country) > 0 else None

@staticmethod
def get_street_by_lr_full_address(full_address: str, postal: str, city: str) -> str:
    """Returns the street from a LeadRebel full address string.

    Args:
        full_address (str): Full address string
        postal (str): Postal code
        city (str): City

    Returns:
        str: Street
    """
    if not full_address or not postal or not city:
        return None
    street = full_address.replace(postal, "").replace(city, "").strip()
    return street if street else None

@staticmethod
def standardize_phone_number(number: str) -> str:
    """Standardizes a phone number.

    Args:
        number (str): Phone number to standardize

    Returns:
        str: Standardized phone number
    """
    if not number:
        return None
    
    config = frappe.get_single("Weclapp Migration Settings")

    # Remove all non-numeric characters
    cleaned_number = re.sub(r'\D', '', number)

    # Check if there is already a country code
    # If not, add the default one
    if cleaned_number.startswith('00'):
        cleaned_number = f"+{cleaned_number[2:]}"
    elif cleaned_number.startswith('0'):
        cleaned_number = f"+{config.default_phone_country_code}{cleaned_number[1:]}"
    elif cleaned_number:
        cleaned_number = f"+{cleaned_number}"

    # Insert dash (-) after the country code
    if len(cleaned_number) > 3:
        cleaned_number = f"{cleaned_number[:3]}-{cleaned_number[3:]}"

    return cleaned_number