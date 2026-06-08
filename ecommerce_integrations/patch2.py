import frappe

def fix():
    frappe.init(site="site1.local")
    frappe.connect()

    meta = frappe.get_meta("Sales Order Item", cached=False)
    quot_fields = [f for f in meta.fields if f.fieldname == "quotation_item"]
    print(f"Count of quotation_item in meta.fields: {len(quot_fields)}")
    for f in quot_fields:
        print(f"Field: name={f.name}, idx={f.idx}, type={f.doctype}")

if __name__ == "__main__":
    fix()
