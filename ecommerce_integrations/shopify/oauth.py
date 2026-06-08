import frappe
from frappe import _
import requests

@frappe.whitelist(allow_guest=True)
def callback(code=None, shop=None, hmac=None, host=None, state=None, **kwargs):
	if not code or not shop:
		frappe.throw(_("Missing authorization code or shop domain."))

	setting = frappe.get_doc("Shopify Setting", "Shopify Setting")
	if not setting.client_id or not setting.shared_secret:
		frappe.throw(_("Client ID or Client Secret is missing in Shopify Setting."))

	url = f"https://{shop}/admin/oauth/access_token"
	payload = {
		"client_id": setting.client_id,
		"client_secret": setting.get_password("shared_secret"),
		"code": code
	}

	try:
		response = requests.post(url, json=payload)
		response.raise_for_status()
		data = response.json()
		
		access_token = data.get("access_token")
		if access_token:
			setting.password = access_token
			setting.shopify_url = shop.replace("https://", "")
			setting.flags.ignore_mandatory = True
			setting.flags.ignore_validate = True
			setting.save(ignore_permissions=True)
			frappe.db.commit()
			
			frappe.local.response["type"] = "redirect"
			frappe.local.response["location"] = "/app/shopify-setting"
			frappe.msgprint(_("Shopify OAuth Authorization Successful!"))
		else:
			frappe.throw(_("Failed to retrieve access token from Shopify."))
			
	except Exception as e:
		frappe.log_error("Shopify OAuth Error", str(e))
		frappe.throw(_("OAuth Authorization Failed. Please check Error Log for details."))
