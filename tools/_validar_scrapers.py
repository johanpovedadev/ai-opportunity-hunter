import asyncio, sys, os, time
sys.path.insert(0, os.getcwd())

from backend.scrapers.computrabajo import ComputrabajoScraper
from backend.scrapers.getonboard import GetOnBoardScraper
from backend.scrapers.indeed import IndeedScraper
from backend.scrapers.linkedin import LinkedInScraper

async def test_scraper(name, scraper, keyword="python"):
    print(f"\n[{name}] Probando scraping con keyword='{keyword}'...")
    try:
        t0 = time.time()
        results = await scraper.scrape_keyword(keyword)
        t = time.time() - t0
        if results:
            print(f"  [OK] {len(results)} ofertas en {t:.1f}s")
            for r in results[:3]:
                print(f"       {r.get('cargo','')[:50]} @ {r.get('empresa','')[:30]}")
            return True
        else:
            print(f"  [FAIL] 0 ofertas devueltas ({t:.1f}s)")
            return False
    except Exception as e:
        print(f"  [FAIL] Error: {e}")
        return False

async def main():
    print("=" * 50)
    print("  VALIDACION DE SCRAPERS - " + time.strftime("%Y-%m-%d %H:%M"))
    print("=" * 50)

    results = []
    results.append(await test_scraper("Computrabajo", ComputrabajoScraper()))
    results.append(await test_scraper("GetOnBoard", GetOnBoardScraper()))
    results.append(await test_scraper("Indeed", IndeedScraper()))

    print("\n" + "=" * 50)
    print("  RESUMEN")
    print("=" * 50)
    names = ["Computrabajo", "GetOnBoard", "Indeed"]
    for name, ok in zip(names, results):
        print(f"  {'[OK]' if ok else '[FAIL]'} {name}")

    if all(results):
        print("\n  [OK] Todos los scrapers funcionan correctamente")
    else:
        print(f"\n  [!] {sum(1 for r in results if not r)} scraper(s) fallaron")

asyncio.run(main())
