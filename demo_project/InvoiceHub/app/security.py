"""Authorization policy for InvoiceHub. Tested independently by SATRA-RV."""
def can_access_invoice(user, invoice):
    return user["role"] == "admin" or invoice["owner_id"] == user["id"]


def is_admin(user):
    return user["role"] == "admin"
