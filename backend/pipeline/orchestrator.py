import asyncio
import csv
import json
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path

from backend.models import JobOffer, Profile, AnalysisResult
from backend.config import settings
from backend.scrapers import LinkedInScraper, WellfoundScraper, GetOnBoardScraper, ComputrabajoScraper, IndeedScraper, JobNormalizer
from backend.ai.scoring_engine import ScoringEngine, ScoredOffer
from backend.ai.base import BaseAnalyzer
from backend.ai.gemini_analyzer import GeminiAnalyzer, QuotaExceededError
from backend.ai.openai_analyzer import OpenAIAnalyzer


@dataclass
class PipelineResult:
    offers: list[JobOffer] = field(default_factory=list)
    scored: list[ScoredOffer] = field(default_factory=list)
    output_path: str = ""
    total_scraped: int = 0
    total_unique: int = 0
    total_scored: int = 0
    total_filtered: int = 0
    errors: list[str] = field(default_factory=list)


class Pipeline:
    def __init__(
        self,
        profile: Profile | None = None,
        threshold: float | None = None,
        output_dir: str = "data",
        max_offers: int | None = None,
    ):
        self.profile = profile
        self.threshold = threshold or settings.score_threshold
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.scoring_engine = ScoringEngine(threshold=self.threshold)
        self.normalizer = JobNormalizer()
        self.max_offers = max_offers

        # Init analyzer only if we have a profile
        self.analyzer: BaseAnalyzer | None = None
        if profile:
            self.analyzer = self._build_analyzer()

    def _build_analyzer(self) -> BaseAnalyzer | None:
        if settings.ai_provider == "gemini":
            if settings.gemini_api_key:
                return GeminiAnalyzer(api_key=settings.gemini_api_key)
            return None
        elif settings.ai_provider == "openai":
            return OpenAIAnalyzer()
        return None

    async def run(
        self,
        keywords: list[str] | None = None,
        platforms: list[str] | None = None,
        output: str | None = None,
    ) -> PipelineResult:
        result = PipelineResult()

        if keywords is None:
            keywords = settings.keywords_list

        # 1. Scrape
        offers = await self._scrape_all(keywords, platforms)
        result.total_scraped = len(offers)

        # 2. Normalize + dedup
        unique = self._dedup(offers)
        result.total_unique = len(unique)
        result.offers = unique

        if not unique:
            result.errors.append("No se encontraron ofertas")
            self._export_csv(unique, result, output)
            return result

        # 3. Analyze + score
        if self.analyzer and self.profile:
            to_analyze = unique[:self.max_offers] if self.max_offers else unique
            scored = await self._analyze_and_score(to_analyze, result.errors)
            result.scored = scored
            result.total_scored = len(scored)
            filtered = self.scoring_engine.filter_best(scored)
            result.total_filtered = len(filtered)

            self._print_summary(result, keywords)

            # 4. Export scored CSV
            self._export_scored_csv(scored, result, output)
            self._print_top(filtered)
        elif result.scored:
            # 4. Export scored CSV (partial — some offers may have failed)
            self._export_scored_csv(result.scored, result, output)
            self._print_top(self.scoring_engine.filter_best(result.scored))
        else:
            # 4. Export raw CSV
            if not self.analyzer or not self.profile:
                print("\n[Pipeline] Sin analisis (falta API key o --profile)")
            else:
                print("\n[Pipeline] Sin analisis (cuota Gemini agotada o errores)")
            self._export_csv(unique, result, output)

        return result

    async def _scrape_all(
        self, keywords: list[str], platforms: list[str] | None
    ) -> list[JobOffer]:
        all_offers: list[JobOffer] = []
        scrapers = []

        if platforms is None or "getonboard" in platforms:
            if settings.scrape_getonboard:
                scrapers.append(GetOnBoardScraper())
        if platforms is None or "linkedin" in platforms:
            if settings.scrape_linkedin:
                scrapers.append(LinkedInScraper())
        if platforms is None or "wellfound" in platforms:
            if settings.scrape_wellfound:
                scrapers.append(WellfoundScraper())
        if platforms is None or "computrabajo" in platforms:
            if settings.scrape_computrabajo:
                scrapers.append(ComputrabajoScraper())
        if platforms is None or "indeed" in platforms:
            if settings.scrape_indeed:
                scrapers.append(IndeedScraper())

        if not scrapers:
            print("[Pipeline] No hay scrapers habilitados. Revisa tu .env")
            return []

        for scraper in scrapers:
            try:
                print(f"[{scraper.fuente}] Scraping: {keywords}")
                offers = await scraper.scrape(keywords)
                normalized = [self.normalizer.normalizar(o) for o in offers]
                all_offers.extend(normalized)
                print(f"  -> {len(normalized)} ofertas")
            except Exception as e:
                msg = f"[{scraper.fuente}] Error: {e}"
                print(f"  -> {msg}")
                # Don't propagate — let other scrapers continue

        return all_offers

    def _dedup(self, offers: list[JobOffer]) -> list[JobOffer]:
        seen = set()
        unique = []
        for o in offers:
            key = o.link or f"{o.empresa}|{o.cargo}"
            if key not in seen:
                seen.add(key)
                unique.append(o)
        return unique

    async def _analyze_and_score(self, offers: list[JobOffer], errors: list[str]) -> list[ScoredOffer]:
        if not self.analyzer:
            return []

        scored: list[ScoredOffer] = []

        provider_name = "Gemini" if settings.ai_provider == "gemini" else settings.openai_base_url
        print(f"\n[Pipeline] Analizando {len(offers)} ofertas con {provider_name}...")
        for i, offer in enumerate(offers):
            try:
                analysis = await self._analyze_with_retry(offer, errors)
                if analysis is None:
                    continue
                s = self.scoring_engine.score(offer, self.profile, analysis)
                scored.append(s)
                print(f"  [{i+1}/{len(offers)}] {offer.empresa} - {offer.cargo[:40]} -> {s.score_final}")
            except QuotaExceededError as e:
                errors.append(f"Cuota Gemini agotada: {e}")
                print(f"  [{i+1}/{len(offers)}] CUOTA AGOTADA - deteniendo analisis")
                break

        return scored

    async def _analyze_with_retry(self, offer: JobOffer, errors: list[str]) -> AnalysisResult | None:
        import asyncio
        for attempt in range(3):
            try:
                return await self.analyzer.analyze(offer, self.profile)
            except QuotaExceededError:
                raise
            except Exception as e:
                if "503" in str(e) or "UNAVAILABLE" in str(e):
                    wait = 5 * (attempt + 1)
                    print(f"     (503, reintentando en {wait}s...)")
                    await asyncio.sleep(wait)
                    continue
                errors.append(f"{offer.cargo}@{offer.empresa}: {e}")
                print(f"     ERROR: {e}")
                return None
        errors.append(f"{offer.cargo}@{offer.empresa}: 503 agotado tras 3 intentos")
        print(f"     ERROR: 503 persistente")
        return None

        return scored

    def _export_csv(
        self, offers: list[JobOffer], result: PipelineResult, output: str | None
    ):
        if not offers:
            return
        path = output or str(self.output_dir / f"ofertas_{datetime.now():%Y%m%d_%H%M%S}.csv")
        fields = ["empresa", "cargo", "ubicacion", "salario_min", "salario_max",
                   "moneda", "link", "descripcion", "fuente", "tipo_empleo", "fecha_publicacion"]
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            for o in offers:
                w.writerow({f: getattr(o, f, "") for f in fields})
        result.output_path = path
        print(f"\n[Pipeline] Exportado: {path}")

    def _export_scored_csv(
        self, scored: list[ScoredOffer], result: PipelineResult, output: str | None
    ):
        if not scored:
            return
        path = output or str(self.output_dir / f"ofertas_scored_{datetime.now():%Y%m%d_%H%M%S}.csv")
        fields = ["empresa", "cargo", "ubicacion", "salario_min", "salario_max",
                   "moneda", "link", "fuente", "score_ia", "score_final",
                   "clasificacion", "fortalezas", "debilidades", "recomendacion"]
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            for s in scored:
                row = {f: getattr(s.offer, f, "") for f in fields if hasattr(s.offer, f)}
                row["score_ia"] = s.analysis.score
                row["score_final"] = s.score_final
                row["clasificacion"] = s.clasificacion
                row["fortalezas"] = "; ".join(s.analysis.fortalezas)
                row["debilidades"] = "; ".join(s.analysis.debilidades)
                row["recomendacion"] = s.analysis.recomendacion
                w.writerow(row)
        result.output_path = path
        print(f"\n[Pipeline] Exportado (con scores): {path}")

    def _print_summary(self, result: PipelineResult, keywords: list[str]):
        print(f"\n{'='*50}")
        print(f"  Pipeline completo")
        print(f"  Keywords: {keywords}")
        print(f"  Scraped: {result.total_scraped} -> Unicos: {result.total_unique}")
        print(f"  Analizados: {result.total_scored} | Sobre threshold ({self.threshold}): {result.total_filtered}")
        if result.errors:
            print(f"  Errores: {len(result.errors)}")
            for e in result.errors[:3]:
                print(f"    - {e}")
        print(f"{'='*50}")

    def _print_top(self, scored: list[ScoredOffer], n: int = 5):
        if not scored:
            return
        top = sorted(scored, key=lambda x: x.score_final, reverse=True)[:n]
        print(f"\n  Top {len(top)} ofertas:")
        print(f"  {'Score':<6} {'Clasificacion':<14} {'Empresa':<20} {'Cargo'}")
        print(f"  {'-'*5} {'-'*13} {'-'*19} {'-'*30}")
        for s in top:
            print(f"  {s.score_final:<6} {s.clasificacion:<14} {s.offer.empresa:<20} {s.offer.cargo[:30]}")


def build_profile_from_args(
    tech: str = "",
    exp: int = 0,
    english: str = "",
    seniority: str = "",
) -> Profile:
    return Profile(
        tecnologias=tech or "Python, SQL, Git",
        experiencia_anos=exp or 0,
        nivel_ingles=english or "basico",
        seniority=seniority or "junior",
    )


def main():
    import argparse
    parser = argparse.ArgumentParser(description="AI Opportunity Hunter - Pipeline completo")
    parser.add_argument("--keywords", "-k", type=str, help="Keywords separadas por coma")
    parser.add_argument("--output", "-o", type=str, help="Ruta CSV de salida")
    parser.add_argument("--platforms", "-p", type=str, help="Plataformas: getonboard,linkedin,wellfound")
    parser.add_argument("--analyze", action="store_true", help="Ejecutar analisis IA")
    parser.add_argument("--profile-tech", type=str, default="", help="Tecnologias del perfil")
    parser.add_argument("--profile-exp", type=int, default=0, help="Anios de experiencia")
    parser.add_argument("--profile-english", type=str, default="", help="Nivel de ingles")
    parser.add_argument("--profile-seniority", type=str, default="", help="Seniority")
    parser.add_argument("--threshold", type=float, default=None, help="Score minimo (0-10)")
    args = parser.parse_args()

    keywords = [k.strip() for k in args.keywords.split(",")] if args.keywords else None
    platforms = [p.strip() for p in args.platforms.split(",")] if args.platforms else None

    profile = None
    if args.analyze:
        profile = build_profile_from_args(
            tech=args.profile_tech,
            exp=args.profile_exp,
            english=args.profile_english,
            seniority=args.profile_seniority,
        )

    pipeline = Pipeline(profile=profile, threshold=args.threshold)
    result = asyncio.run(pipeline.run(
        keywords=keywords,
        platforms=platforms,
        output=args.output,
    ))

    return result


if __name__ == "__main__":
    main()
