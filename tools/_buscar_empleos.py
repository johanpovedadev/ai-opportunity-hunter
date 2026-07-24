import asyncio, sys, os, csv
from datetime import datetime
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.getcwd())

from backend.scrapers.computrabajo import ComputrabajoScraper
from backend.scrapers.getonboard import GetOnBoardScraper
from backend.scrapers.indeed import IndeedScraper
from backend.scrapers.linkedin import LinkedInScraper

async def run():
    keywords = [
        "python", "desarrollador python", "programador python",
        "backend python", "automatizacion", "junior python",
        "analista desarrollador", "soporte tecnico",
    ]

    scrapers = [
        ("Computrabajo", ComputrabajoScraper()),
        ("GetOnBoard", GetOnBoardScraper()),
        ("Indeed", IndeedScraper()),
        # LinkedIn requires session
    ]

    all_offers = []

    for name, scraper in scrapers:
        print(f"\n[{name}] Scraping {len(keywords)} keywords...")
        for kw in keywords:
            try:
                results = await scraper.scrape_keyword(kw)
                seen = {r.get("link") for r in all_offers}
                new = [r for r in results if r.get("link") and r["link"] not in seen]
                all_offers.extend(new)
                seen.update(r.get("link") for r in new)
                print(f"  {kw}: {len(results)} encontrados, {len(new)} nuevos")
            except Exception as e:
                print(f"  {kw}: Error: {e}")

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = f"data/empleos_{ts}.csv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["fuente","cargo","empresa","ubicacion","salario_min","salario_max","moneda","link","descripcion"])
        w.writeheader()
        w.writerows(all_offers)

    print(f"\n[OK] {len(all_offers)} ofertas unicas exportadas a {path}")
    for r in all_offers:
        print(f"  [{r.get('fuente',''):12}] {r.get('cargo','')[:60]} @ {r.get('empresa','')[:30]}")

asyncio.run(run())
