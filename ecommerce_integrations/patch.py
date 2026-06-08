import frappe

def fix():
    fields = frappe.db.sql("SELECT name, fieldname, idx FROM `tabDocField` WHERE parent='Sales Order Item' AND idx=90", as_dict=1)
    print("Found DocFields at idx=90:", fields)
    
    # Let's print all fields with duplicate names
    dups = frappe.db.sql("""
        SELECT fieldname, count(*) as c
        FROM `tabDocField`
        WHERE parent='Sales Order Item'
        GROUP BY fieldname
        HAVING c > 1
    """, as_dict=1)
    print("Duplicates in tabDocField:", dups)

    # Let's print all fields with duplicate idx
    dups_idx = frappe.db.sql("""
        SELECT idx, count(*) as c
        FROM `tabDocField`
        WHERE parent='Sales Order Item'
        GROUP BY idx
        HAVING c > 1
    """, as_dict=1)
    print("Duplicate idx in tabDocField:", dups_idx)
