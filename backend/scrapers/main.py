import asyncio
import csv
import argparse
from datetime import datetime
from pathlib import Path
from backend.scrapers import LinkedInScraper, WellfoundScraper, GetOnBoardScraper, IndeedScraper, JobNormalizer
from backend.models import JobOffer
from backend.config import settings


async def run_pipeline(keywords: list[str] | None = None, output: str | None = None) -> list[JobOffer]:
    if keywords is None:
        keywords = settings.keywords_list

    scrapers = []
    if settings.scrape_linkedin:
        scrapers.append(LinkedInScraper())
    if settings.scrape_wellfound:
        scrapers.append(WellfoundScraper())
    if settings.scrape_getonboard:
        scrapers.append(GetOnBoardScraper())
    if settings.scrape_indeed:
        scrapers.append(IndeedScraper())

    if not scrapers:
        print("No hay scrapers habilitados. Revisa tu .env")
        return []

    all_offers: list[JobOffer] = []
    normalizer = JobNormalizer()

    for scraper in scrapers:
        print(f"[{scraper.fuente}] Scraping keywords: {keywords}")
        offers = await scraper.scrape(keywords)
        normalized = [normalizer.normalizar(o) for o in offers]
        all_offers.extend(normalized)
        print(f"[{scraper.fuente}] {len(normalized)} ofertas encontradas")

    seen = set()
    unique: list[JobOffer] = []
    for o in all_offers:
        key = o.link or o.empresa + o.cargo
        if key not in seen:
            seen.add(key)
            unique.append(o)

    print(f"\nTotal: {len(unique)} ofertas únicas de {len(scrapers)} portales")

    if output:
        _export_csv(unique, output)
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = Path("data") / f"ofertas_{timestamp}.csv"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        _export_csv(unique, str(output_path))

    return unique


def _export_csv(offers: list[JobOffer], path: str):
    if not offers:
        print("No hay ofertas para exportar")
        return

    fields = ["empresa", "cargo", "ubicacion", "salario_min", "salario_max",
              "moneda", "link", "descripcion", "fuente", "tipo_empleo", "fecha_publicacion"]

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for o in offers:
            writer.writerow({f: getattr(o, f, "") for f in fields})

    print(f"Exportado a {path}")


def main():
    parser = argparse.ArgumentParser(description="AI Opportunity Hunter - Scraper MVP")
    parser.add_argument("--keywords", "-k", type=str, help="Keywords separadas por coma")
    parser.add_argument("--output", "-o", type=str, help="Ruta del archivo CSV de salida")
    args = parser.parse_args()

    keywords = [k.strip() for k in args.keywords.split(",")] if args.keywords else None
    asyncio.run(run_pipeline(keywords=keywords, output=args.output))


if __name__ == "__main__":
    main()
