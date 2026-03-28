with open('D:/Projects/VM 3/CodeApex_2.0/embeddings/search.py', 'r', encoding='utf-8') as f:
    text = f.read()

import re

old_bank_related = '''def is_bank_related(query: str) -> bool:
    q = normalize(query)
    keywords = [
        "bank", "account", "balance", "transaction", "loan", "kyc", "atm", "card", "upi", "neft", "rtgs",'''

new_bank_related = '''def is_bank_related(query: str) -> bool:
    q = normalize(query)
    keywords = [
        "bank", "account", "balance", "transaction", "loan", "kyc", "atm", "card", "upi", "neft", "rtgs",
        "yojana", "pmay", "awas", "kisan", "pradhan mantri", "scheme", "sukanya", "samriddhi", "ppf",'''

if old_bank_related in text:
    text = text.replace(old_bank_related, new_bank_related)
    with open('D:/Projects/VM 3/CodeApex_2.0/embeddings/search.py', 'w', encoding='utf-8') as f:
        f.write(text)
    print("Patched is_bank_related successfully.")
else:
    print("Could not find is_bank_related old string.")
