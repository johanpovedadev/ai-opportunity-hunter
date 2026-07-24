import sys, json
sys.path.insert(0, ".")
from backend.auth.session import SessionStorage

s = SessionStorage("linkedin")
info = s.info()
print(f"LinkedIn session: {info}")

data = s.load()
if data:
    cookies = data.get("cookies", [])
    li_at = [c for c in cookies if c.get("name") == "li_at"]
    print(f"  Total cookies: {len(cookies)}")
    print(f"  li_at present: {len(li_at) > 0}")
    if li_at:
        print(f"  li_at value: {li_at[0].get('value', '')[:30]}...")
    domains = set(c.get("domain", "") for c in cookies)
    print(f"  Domains: {domains}")
else:
    print("  No session data")
