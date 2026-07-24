"""Escanea plataformas de empleo para verificar si son scrapeables."""
import asyncio, csv, json
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright

PLATFORMS = [
    # Colombia / Latinoamerica
    {"name": "Computrabajo", "url": "https://co.computrabajo.com/trabajo-de-python", "region": "Colombia", "type": "general"},
    {"name": "GetOnBoard", "url": "https://www.getonbrd.com/empleos-python/colombia", "region": "Colombia", "type": "tech"},
    {"name": "LinkedIn", "url": "https://www.linkedin.com/jobs/search/?keywords=python&location=Colombia", "region": "Colombia", "type": "general"},
    {"name": "Workana", "url": "https://www.workana.com/jobs?q=python&language=en", "region": "Latam", "type": "freelance"},
    {"name": "Indeed Colombia", "url": "https://co.indeed.com/ofertas?q=python", "region": "Colombia", "type": "general"},
    {"name": "El Empleo", "url": "https://www.elempleo.com/co/ofertas-empleo/python", "region": "Colombia", "type": "general"},
    {"name": "Empleo.com.co", "url": "https://www.empleo.com.co/busqueda/python", "region": "Colombia", "type": "general"},
    {"name": "Multitrabajos", "url": "https://www.multitrabajos.com/empleos-python.html", "region": "Colombia", "type": "general"},
    {"name": "Bumeran", "url": "https://www.bumeran.com.co/busqueda/python", "region": "Colombia", "type": "general"},
    {"name": "ZonaJobs", "url": "https://www.zonajobs.com.co/busqueda/python", "region": "Colombia", "type": "general"},
    {"name": "Laborum", "url": "https://www.laborum.com/empleos-python.html", "region": "Colombia", "type": "general"},
    {"name": "Jooble", "url": "https://co.jooble.org/trabajo-python", "region": "Colombia", "type": "aggregator"},
    {"name": "Talent.com", "url": "https://co.talent.com/jobs?k=python", "region": "Colombia", "type": "aggregator"},
    {"name": "Jobomas", "url": "https://www.jobomas.com/ofertas-empleo/python/colombia", "region": "Colombia", "type": "general"},
    {"name": "Trovit", "url": "https://empleo.trovit.com.co/ofertas/python", "region": "Colombia", "type": "aggregator"},
    {"name": "SimplyHired", "url": "https://www.simplyhired.com.co/search?q=python", "region": "Colombia", "type": "aggregator"},
    {"name": "InfoJobs", "url": "https://www.infojobs.com.co/ofertas/python", "region": "Colombia", "type": "general"},
    {"name": "Jobrapido", "url": "https://co.jobrapido.com/?q=python", "region": "Colombia", "type": "aggregator"},
    {"name": "Glassdoor", "url": "https://www.glassdoor.com.mx/Empleo/python-empleos-SRCH_KO0,6.htm", "region": "Latam", "type": "general"},
    {"name": "OCC Mundial", "url": "https://www.occ.com.mx/empleos/de-python/", "region": "Mexico", "type": "general"},
    {"name": "Freelancer", "url": "https://www.freelancer.com/jobs/python/", "region": "Global", "type": "freelance"},
    {"name": "Fiverr", "url": "https://www.fiverr.com/search/gigs?query=python&source=top-bar", "region": "Global", "type": "freelance"},
    {"name": "Upwork", "url": "https://www.upwork.com/search/jobs/?q=python", "region": "Global", "type": "freelance"},
    {"name": "Indeed US", "url": "https://www.indeed.com/jobs?q=python&remote=1", "region": "Global", "type": "general"},
    {"name": "CareerBuilder", "url": "https://www.careerbuilder.com/jobs-python", "region": "Global", "type": "general"},
    {"name": "ZipRecruiter", "url": "https://www.ziprecruiter.com/candidate/search?search=python", "region": "Global", "type": "general"},
    {"name": "Dice", "url": "https://www.dice.com/jobs?q=python&location=Remote", "region": "Global", "type": "tech"},
    {"name": "Wellfound", "url": "https://wellfound.com/jobs?q=python", "region": "Global", "type": "tech"},
]

CONTEXT_SIMPLE = {
    "viewport": {"width": 1280, "height": 800},
}

CONTEXT_LATAM = {
    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "viewport": {"width": 1920, "height": 1080},
    "locale": "es-CO",
}

RESULT_FILE = Path(__file__).parent.parent / "data" / "platform_scan_results.csv"

async def test_platform(platform: dict) -> dict:
    name = platform["name"]
    url = platform["url"]
    result = {"name": name, "url": url, "region": platform["region"], "type": platform["type"],
              "simple_200": False, "simple_status": 0, "simple_blocked": False,
              "latam_200": False, "latam_status": 0, "latam_blocked": False,
              "veredict": "", "details": ""}

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        contexts = [("simple", CONTEXT_SIMPLE)]
        contexts.append(("latam", CONTEXT_LATAM))

        for mode, ctx_kwargs in contexts:
            ctx = await browser.new_context(**ctx_kwargs)
            page = await ctx.new_page()
            page.set_default_timeout(15000)
            try:
                resp = await page.goto(url, wait_until="domcontentloaded", timeout=20000)
                await page.wait_for_timeout(2000)
                status = resp.status if resp else 0
                title = await page.title()
                body = (await page.text_content("body") or "")[:500].lower()
                result[f"{mode}_status"] = status

                if status in (200, 301, 302, 307, 308):
                    result[f"{mode}_200"] = True
                    # Check for blockage keywords in body
                    blocked = any(kw in body for kw in ["automated", "automation", "unusual traffic", "access denied",
                                                        "please verify", "security check", "bot"])
                    if blocked:
                        result[f"{mode}_blocked"] = True
                        result["details"] += f"[{mode}] blocked by text; "
                    else:
                        result["details"] += f"[{mode}] OK status={status} title='{title[:60]}'; "
                elif status in (403, 429):
                    result[f"{mode}_blocked"] = True
                    result["details"] += f"[{mode}] BLOCKED status={status}; "
                else:
                    result["details"] += f"[{mode}] status={status}; "
            except Exception as e:
                result[f"{mode}_200"] = False
                result[f"{mode}_blocked"] = True
                result["details"] += f"[{mode}] error={type(e).__name__}:{str(e)[:80]}; "
            finally:
                await ctx.close()

        await browser.close()

    # Veredict
    if result["latam_200"] and not result.get("latam_blocked", False):
        result["veredict"] = "INDEXABLE"
    elif result["simple_200"] and not result.get("simple_blocked", False):
        result["veredict"] = "INDEXABLE"
    elif result["latam_200"] and result.get("latam_blocked", False):
        result["veredict"] = "BLOQUEADO (falso positivo)"
    elif result["simple_200"] and result.get("simple_blocked", False):
        result["veredict"] = "BLOQUEADO (falso positivo)"
    else:
        result["veredict"] = "BLOQUEADO"

    print(f"  {result['veredict']:30s} | {name:20s} | {result['details'][:100]}")
    return result


async def main():
    results = []
    print(f"\n{'='*80}")
    print(f"ESCANEO DE PLATAFORMAS DE EMPLEO ({len(PLATFORMS)} plataformas)")
    print(f"{'='*80}\n")
    for p in PLATFORMS:
        r = await test_platform(p)
        results.append(r)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = RESULT_FILE
    with open(out, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["Plataforma", "URL", "Region", "Tipo", "Simple_200", "Simple_Status",
                     "Latam_200", "Latam_Status", "Veredicto", "Detalles"])
        for r in results:
            w.writerow([r["name"], r["url"], r["region"], r["type"],
                        r["simple_200"], r["simple_status"],
                        r["latam_200"], r["latam_status"],
                        r["veredict"], r["details"]])

    indexables = [r for r in results if r["veredict"] == "INDEXABLE"]
    bloqueados = [r for r in results if r["veredict"] != "INDEXABLE"]
    print(f"\n{'='*80}")
    print(f"RESUMEN")
    print(f"{'='*80}")
    print(f"\n✅ INDEXABLES ({len(indexables)}):")
    for r in sorted(indexables, key=lambda x: x["name"]):
        print(f"   - {r['name']:25s} | {r['url']}")
    print(f"\n❌ BLOQUEAN ({len(bloqueados)}):")
    for r in sorted(bloqueados, key=lambda x: x["name"]):
        print(f"   - {r['name']:25s} | {r['url']} | {r['details'][:80]}")
    print(f"\nCSV exportado: {out}")

if __name__ == "__main__":
    asyncio.run(main())
