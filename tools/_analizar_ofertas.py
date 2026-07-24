import asyncio, sys, csv, os
from datetime import datetime
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.getcwd())

from backend.models import JobOffer, Profile
from backend.ai.openai_analyzer import OpenAIAnalyzer
from backend.ai.scoring_engine import ScoringEngine

CSV_PATH = "data/empleos_20260623_162322.csv"

profile = Profile(
    tecnologias="Python, SQL, Git, HTML, CSS, automatización, RPA",
    experiencia_anos=0,
    nivel_ingles="basico",
    seniority="junior",
    habilidades_extra=["adaptabilidad", "aprendizaje rápido", "trabajo en equipo"],
)

async def main():
    analyzer = OpenAIAnalyzer()
    engine = ScoringEngine(threshold=7.0)

    with open(CSV_PATH, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    print(f"[OK] {len(rows)} ofertas cargadas de {CSV_PATH}")

    # Dedup by link
    seen = set()
    offers = []
    for r in rows:
        key = r.get("link", "")
        if key and key not in seen:
            seen.add(key)
            offers.append(JobOffer(
                empresa=r.get("empresa", ""),
                cargo=r.get("cargo", ""),
                ubicacion=r.get("ubicacion", ""),
                salario_min=r.get("salario_min"),
                salario_max=r.get("salario_max"),
                moneda=r.get("moneda"),
                link=r.get("link", ""),
                descripcion=r.get("descripcion", ""),
                fuente=r.get("fuente", ""),
            ))

    print(f"[OK] {len(offers)} ofertas unicas para analizar")

    scored = []
    for i, offer in enumerate(offers):
        try:
            analysis = await analyzer.analyze(offer, profile)
            s = engine.score(offer, profile, analysis)
            scored.append(s)
            print(f"  [{i+1}/{len(offers)}] {offer.empresa or '?'} - {offer.cargo[:40]} -> {s.score_final}/10 [{s.clasificacion}]")
        except Exception as e:
            print(f"  [{i+1}/{len(offers)}] ERROR: {e}")

    scored.sort(key=lambda x: x.score_final, reverse=True)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = f"data/ofertas_analizadas_{ts}.csv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["fuente","empresa","cargo","ubicacion","score_ia","score_final","clasificacion","link"])
        for s in scored:
            w.writerow([s.offer.fuente, s.offer.empresa, s.offer.cargo, s.offer.ubicacion,
                        s.analysis.score, s.score_final, s.clasificacion, s.offer.link])

    print(f"\n{'='*60}")
    print(f"[OK] {len(scored)} ofertas analizadas -> {path}")
    print(f"{'='*60}")
    print(f"\n  Top 10:")
    print(f"  {'Score':<6} {'Clasif':<12} {'Empresa':<22} {'Cargo'}")
    print(f"  {'-'*5} {'-'*11} {'-'*21} {'-'*30}")
    for s in scored[:10]:
        print(f"  {s.score_final:<6} {s.clasificacion:<12} {s.offer.empresa:<22} {s.offer.cargo[:30]}")

    filtered = [s for s in scored if s.score_final >= 7.0]
    print(f"\n  Ofertas con score >= 7.0: {len(filtered)}")
    if filtered:
        path_f = path.replace(".csv", "_top7.csv")
        with open(path_f, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["fuente","empresa","cargo","ubicacion","score_ia","score_final","clasificacion","link"])
            for s in filtered:
                w.writerow([s.offer.fuente, s.offer.empresa, s.offer.cargo, s.offer.ubicacion,
                            s.analysis.score, s.score_final, s.clasificacion, s.offer.link])
        print(f"  Exportado: {path_f}")

asyncio.run(main())
