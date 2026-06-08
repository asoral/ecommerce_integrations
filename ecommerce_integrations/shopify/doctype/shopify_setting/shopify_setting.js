frappe.provide("ecommerce_integrations.shopify.shopify_setting");

frappe.ui.form.on("Shopify Setting", {
	onload: function (frm) {
		frappe.call({
			method: "ecommerce_integrations.utils.naming_series.get_series",
			callback: function (r) {
				$.each(r.message, (key, value) => {
					set_field_options(key, value);
				});
			},
		});
	},

	sync_old_orders: function (frm) {
		if (frm.doc.sync_old_orders) {
			frm.set_value("sync_old_orders", 1);
			frm.save().then(() => {
				frappe.call({
					doc: frm.doc,
					method: "sync_old_orders_in_shopify",
					freeze: true,
					freeze_message: __("Syncing old orders from Shopify..."),
					callback: function (r) {
						if (!r.exc) {
							frappe.msgprint(__("Synced Orders"));
						}
					},
				});
			});
		}
	},
	fetch_shopify_locations: function (frm) {
		frappe.call({
			doc: frm.doc,
			method: "update_location_table",
			callback: (r) => {
				if (!r.exc) refresh_field("shopify_warehouse_mapping");
			},
		});
	},

	authorize_shopify: function (frm) {
		if (!frm.doc.client_id || !frm.doc.shopify_url) {
			frappe.msgprint(__("Please enter Shop URL and Client ID first."));
			return;
		}

		frappe.run_serially([
			() => frm.save(),
			() => {
				let shop_url = frm.doc.shopify_url.replace("https://", "");
				let client_id = frm.doc.client_id;
				let base_url = window.location.origin;
				let redirect_uri = encodeURIComponent(base_url + "/api/method/ecommerce_integrations.shopify.oauth.callback");
				
				let scopes = "read_orders,write_orders,read_products,write_products,read_inventory,write_inventory,read_locations,read_fulfillments,write_fulfillments,read_customers,write_customers,read_third_party_fulfillment_orders,write_third_party_fulfillment_orders,write_shipping";

				let oauth_url = `https://${shop_url}/admin/oauth/authorize?client_id=${client_id}&scope=${scopes}&redirect_uri=${redirect_uri}`;
				
				window.location.href = oauth_url;
			}
		]).catch((err) => {
			frappe.msgprint(__("Failed to save the form before redirecting. Please check for validation errors."));
			console.error(err);
		});
	},

	refresh: function (frm) {
		frm.add_custom_button(__("Import Products"), function () {
			frappe.set_route("shopify-import-products");
		});
		frm.add_custom_button(__("View Logs"), () => {
			frappe.set_route("List", "Ecommerce Integration Log", {
				integration: "Shopify",
			});
		});
		frm.trigger("setup_queries");
	},

	setup_queries: function (frm) {
		const warehouse_query = () => {
			return {
				filters: {
					company: frm.doc.company,
					is_group: 0,
					disabled: 0,
				},
			};
		};
		frm.set_query("warehouse", warehouse_query);
		frm.set_query(
			"erpnext_warehouse",
			"shopify_warehouse_mapping",
			warehouse_query,
		);

		frm.set_query("price_list", () => {
			return {
				filters: {
					selling: 1,
				},
			};
		});

		frm.set_query("cost_center", () => {
			return {
				filters: {
					company: frm.doc.company,
					is_group: "No",
				},
			};
		});

		frm.set_query("cash_bank_account", () => {
			return {
				filters: [
					["Account", "account_type", "in", ["Cash", "Bank"]],
					["Account", "root_type", "=", "Asset"],
					["Account", "is_group", "=", 0],
					["Account", "company", "=", frm.doc.company],
				],
			};
		});

		const tax_query = () => {
			return {
				query: "erpnext.controllers.queries.tax_account_query",
				filters: {
					account_type: ["Tax", "Chargeable", "Expense Account"],
					company: frm.doc.company,
				},
			};
		};

		frm.set_query("tax_account", "taxes", tax_query);
		frm.set_query("default_sales_tax_account", tax_query);
		frm.set_query("default_shipping_charges_account", tax_query);
	},
});
