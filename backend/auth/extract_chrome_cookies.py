"""Extraer cookies de LinkedIn usando browser-cookie3."""
import json
from pathlib import Path
import browser_cookie3

SESSIONS_DIR = Path("data/sessions")
SESSIONS_DIR.mkdir(parents=True, exist_ok=True)


def extract():
    print("Obteniendo cookies de LinkedIn desde Chrome...")

    # Cargar desde Chrome
    cj = browser_cookie3.chrome(domain_name="linkedin.com")

    cookies_list = []
    found = {}

    for c in cj:
        cookie = {
            "name": c.name,
            "value": c.value,
            "domain": c.domain,
            "path": c.path or "/",
            "secure": c.secure if hasattr(c, "secure") else True,
            "httpOnly": c.has_nonstandard_attr("httponly") if hasattr(c, "has_nonstandard_attr") else False,
            "sameSite": "lax",
        }
        cookies_list.append(cookie)
        found[c.name] = c.value

        if c.name in ("li_at", "JSESSIONID", "lidc", "bcookie"):
            preview = c.value[:30] + "..." if len(c.value) > 30 else c.value
            print(f"  {c.name}: [OK] ({preview})")

    storage_state = {"cookies": cookies_list, "origins": []}
    path = SESSIONS_DIR / "linkedin_session.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(storage_state, f, indent=2, ensure_ascii=False)

    print(f"\n[OK] {len(cookies_list)} cookies guardadas en {path}")

    if found.get("li_at"):
        print("[OK] li_at presente -- sesion valida!")
        return True
    else:
        print("[FAIL] li_at no encontrada -- necesitas iniciar sesion en Chrome")
        print("  Abri Chrome, ve a linkedin.com e inicia sesion. Luego cierra Chrome y ejecuta de nuevo.")
        return False


if __name__ == "__main__":
    extract()
