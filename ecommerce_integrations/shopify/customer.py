from typing import Any

# pyrefly: ignore [missing-import]
import frappe
# pyrefly: ignore [missing-import]
from frappe import _
# pyrefly: ignore [missing-import]
from frappe.utils import cstr, validate_phone_number

from ecommerce_integrations.controllers.customer import EcommerceCustomer
from ecommerce_integrations.shopify.constants import (
	ADDRESS_ID_FIELD,
	CUSTOMER_ID_FIELD,
	MODULE_NAME,
	SETTING_DOCTYPE,
)


class ShopifyCustomer(EcommerceCustomer):
	def __init__(self, customer_id: str):
		self.setting = frappe.get_doc(SETTING_DOCTYPE)
		super().__init__(customer_id, CUSTOMER_ID_FIELD, MODULE_NAME)

	def sync_customer(self, customer: dict[str, Any]) -> None:
		"""Create Customer in ERPNext using shopify's Customer dict."""
		customer_name = cstr(customer.get("first_name")) + " " + cstr(customer.get("last_name"))
		if len(customer_name.strip()) == 0:
			customer_name = customer.get("email")
		
		customer_group = self.setting.customer_group
		if customer_group and frappe.db.get_value("Customer Group", customer_group, "is_group"):
			customer_group = frappe.db.get_value("Customer Group", {"is_group": 0})

		super().sync_customer(customer_name, customer_group)
		billing_address = customer.get("billing_address") or customer.get("defaultAddress") or customer.get("default_address") or {}
		shipping_address = customer.get("shipping_address") or {}

		if billing_address:
			self.create_customer_address(
				customer_name,
				billing_address,
				address_type="Billing",
				email=customer.get("email"),
			)
		if shipping_address:
			self.create_customer_address(
				customer_name,
				shipping_address,
				address_type="Shipping",
				email=customer.get("email"),
			)

		self.create_customer_contact(customer)

	def create_customer_address(
		self,
		customer_name,
		shopify_address: dict[str, Any],
		address_type: str = "Billing",
		email: str | None = None,
	) -> None:
		"""Create customer address(es) using Customer dict provided by shopify."""
		address_fields = _map_address_fields(shopify_address, customer_name, address_type, email)
		super().create_customer_address(address_fields)

	def update_existing_addresses(self, customer):
		billing_address = customer.get("billing_address") or customer.get("defaultAddress") or customer.get("default_address") or {}
		shipping_address = customer.get("shipping_address") or {}
		customer_name = cstr(customer.get("first_name")) + " " + cstr(customer.get("last_name"))
		email = customer.get("email")
		if billing_address:
			self._update_existing_address(customer_name, billing_address, "Billing", email)
		if shipping_address:
			self._update_existing_address(customer_name, shipping_address, "Shipping", email)

	def _update_existing_address(
		self,
		customer_name,
		shopify_address: dict[str, Any],
		address_type: str = "Billing",
		email: str | None = None,
	) -> None:
		old_address = self.get_customer_address_doc(address_type)

		if not old_address:
			self.create_customer_address(customer_name, shopify_address, address_type, email)

		else:
			exclude_in_update = ["address_title", "address_type"]
			new_values = _map_address_fields(shopify_address, customer_name, address_type, email)

			old_address.update({k: v for k, v in new_values.items() if k not in exclude_in_update})
			old_address.flags.ignore_mandatory = True

			old_address.save()

	def create_customer_contact(self, shopify_customer: dict[str, Any]) -> None:
		if not (shopify_customer.get("first_name") and shopify_customer.get("email")):
			return

		contact_fields = {
			"status": "Passive",
			"first_name": shopify_customer.get("first_name"),
			"last_name": shopify_customer.get("last_name"),
			"unsubscribed": not shopify_customer.get("accepts_marketing"),
		}

		if shopify_customer.get("email"):
			contact_fields["email_ids"] = [{"email_id": shopify_customer.get("email"), "is_primary": True}]

		phone_no = shopify_customer.get("phone") or shopify_customer.get("default_address", {}).get("phone")

		if validate_phone_number(phone_no, throw=False):
			contact_fields["phone_nos"] = [{"phone": phone_no, "is_primary_phone": True}]

		super().create_customer_contact(contact_fields)


def _map_address_fields(shopify_address, customer_name, address_type, email):
	"""returns dict with shopify address fields mapped to equivalent ERPNext fields"""
	state = shopify_address.get("province")
	country = shopify_address.get("country")

	# ERPNext mandates state for Indian addresses
	if country == "India" and not state:
		state = shopify_address.get("city") or "Unassigned State"

	address_fields = {
		"address_title": customer_name,
		"address_type": address_type,
		ADDRESS_ID_FIELD: shopify_address.get("id"),
		"address_line1": shopify_address.get("address1") or "Address 1",
		"address_line2": shopify_address.get("address2"),
		"city": shopify_address.get("city"),
		"state": state,
		"pincode": shopify_address.get("zip"),
		"country": country,
		"email_id": email,
	}

	phone = shopify_address.get("phone")
	if validate_phone_number(phone, throw=False):
		address_fields["phone"] = phone

	return address_fields

def sync_customer_webhook(payload, request_id=None):
	from ecommerce_integrations.shopify.utils import create_shopify_log
	frappe.set_user("Administrator")
	frappe.flags.request_id = request_id

	try:
		customer_id = payload.get("id")
		if customer_id:
			customer_id_str = str(customer_id)
			customer = ShopifyCustomer(customer_id=customer_id_str)
			if not customer.is_synced():
				customer.sync_customer(customer=payload)
			else:
				customer.update_existing_addresses(payload)
	except Exception as e:
		create_shopify_log(status="Error", exception=e, rollback=True)
	else:
		create_shopify_log(status="Success")
