#!/usr/bin/env python3
"""AI Opportunity Hunter — CLI principal.

Uso:
    python -m backend.scripts.cli --help
    python -m backend.scripts.cli scrape --keywords "python developer"
    python -m backend.scripts.cli pipeline --keywords "python developer" --analyze
    python -m backend.scripts.cli auth login getonboard
    python -m backend.scripts.cli auth status
    python -m backend.scripts.cli apply --url <link> --cv data/cv.pdf
    python -m backend.scripts.cli doctor
"""

import asyncio
import argparse
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="AI Opportunity Hunter CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    # --- scrape ---
    scrape_p = sub.add_parser("scrape", help="Scrapeo basico sin analisis")
    scrape_p.add_argument("--keywords", "-k", type=str, help="Keywords separadas por coma")
    scrape_p.add_argument("--output", "-o", type=str, help="Ruta CSV de salida")
    scrape_p.add_argument("--platforms", "-p", type=str, help="Plataformas: getonboard,linkedin,wellfound")

    # --- pipeline ---
    pipe_p = sub.add_parser("pipeline", help="Pipeline completo: scrape + analisis + scoring + CSV")
    pipe_p.add_argument("--keywords", "-k", type=str, help="Keywords separadas por coma")
    pipe_p.add_argument("--output", "-o", type=str, help="Ruta CSV de salida")
    pipe_p.add_argument("--platforms", "-p", type=str, help="Plataformas: getonboard,linkedin,wellfound")
    pipe_p.add_argument("--analyze", action="store_true", help="Ejecutar analisis con Gemini")
    pipe_p.add_argument("--profile-tech", type=str, default="", help="Tecnologias del perfil (ej: Python, SQL, Docker)")
    pipe_p.add_argument("--profile-exp", type=int, default=0, help="Anios de experiencia")
    pipe_p.add_argument("--profile-english", type=str, default="", help="Nivel de ingles (basico/intermedio/avanzado/nativo)")
    pipe_p.add_argument("--profile-seniority", type=str, default="", help="Seniority (junior/semi-senior/senior/lead)")
    pipe_p.add_argument("--threshold", type=float, default=None, help="Score minimo para filtrar (0-10)")
    pipe_p.add_argument("--max-offers", type=int, default=None, help="Maximo de ofertas a analizar")

    # --- auth ---
    auth_p = sub.add_parser("auth", help="Gestion de autenticacion")
    auth_sub = auth_p.add_subparsers(dest="auth_command", required=True)
    auth_login = auth_sub.add_parser("login", help="Iniciar sesion en una plataforma")
    auth_login.add_argument("platform", choices=["linkedin", "wellfound", "getonboard"])
    auth_login.add_argument("--headless", action="store_true", help="Modo sin interfaz")
    auth_sub.add_parser("status", help="Ver estado de sesiones")
    auth_del = auth_sub.add_parser("delete", help="Eliminar sesion")
    auth_del.add_argument("platform", choices=["linkedin", "wellfound", "getonboard"])

    # --- apply ---
    apply_p = sub.add_parser("apply", help="Aplicar a una oferta")
    apply_p.add_argument("--url", required=True, help="URL de la oferta")
    apply_p.add_argument("--platform", default="", help="Plataforma (linkedin, getonboard, etc)")
    apply_p.add_argument("--cv", type=str, help="Ruta al archivo CV (PDF)")
    apply_p.add_argument("--profile", type=str, default="", help="Texto del perfil tecnologico")
    apply_p.add_argument("--headless", action="store_true", help="Modo sin interfaz")

    # --- doctor ---
    sub.add_parser("doctor", help="Verificar estado del sistema")

    args = parser.parse_args()

    if args.command == "scrape":
        from backend.scrapers.main import main as scrape_main
        sys.argv = [sys.argv[0], "--keywords", args.keywords or "python developer"]
        if args.output:
            sys.argv.extend(["--output", args.output])
        scrape_main()

    elif args.command == "pipeline":
        asyncio.run(_pipeline(args))

    elif args.command == "auth":
        from backend.scripts.auth_cli import main as auth_main
        if args.auth_command == "login":
            asyncio.run(_auth_login(args.platform, args.headless))
        elif args.auth_command == "status":
            _auth_status()
        elif args.auth_command == "delete":
            _auth_delete(args.platform)

    elif args.command == "apply":
        asyncio.run(_apply(
            url=args.url,
            platform=args.platform,
            cv_path=args.cv,
            profile=args.profile,
            headless=args.headless,
        ))

    elif args.command == "doctor":
        asyncio.run(_doctor())


async def _pipeline(args):
    from backend.pipeline import Pipeline
    from backend.pipeline.orchestrator import build_profile_from_args

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
        if not profile.tecnologias:
            print("  Usa --profile-tech para definir las tecnologias de tu perfil")
            return

    pipeline = Pipeline(profile=profile, threshold=args.threshold, max_offers=args.max_offers)
    result = await pipeline.run(
        keywords=keywords,
        platforms=platforms,
        output=args.output,
    )

    if result.output_path:
        print(f"\n  Resultado: {result.output_path}")
    if result.errors:
        print(f"  Errores: {len(result.errors)}")
        for e in result.errors[:3]:
            print(f"    - {e}")


async def _auth_login(platform: str, headless: bool):
    from backend.auth import PLATFORMS
    auth = PLATFORMS[platform]()
    await auth.authenticate(headless=headless)


def _auth_status():
    from backend.auth.session import SessionStorage
    from backend.auth import PLATFORMS
    CHECK = "+"
    CROSS = "-"
    print()
    print("=== Estado de Sesiones ===")
    print()
    any_s = False
    for p in PLATFORMS:
        s = SessionStorage(p)
        info = s.info()
        if info["has_session"]:
            any_s = True
            print(f"  {CHECK} {p.upper()}")
            print(f"      Cookies: {info['cookies']}")
            print(f"      Archivo: {info['file_size']} bytes")
        else:
            print(f"  {CROSS} {p.upper()}  - sin sesion")
        print()
    if not any_s:
        print("  No hay sesiones. Usa: python -m backend.scripts.cli auth login <plataforma>")


def _auth_delete(platform: str):
    from backend.auth.session import SessionStorage
    s = SessionStorage(platform)
    s.delete()
    print(f"  Sesion de {platform} eliminada.")


async def _apply(url: str, platform: str, cv_path: str | None, profile: str, headless: bool):
    from backend.application import JobApplicator

    if cv_path and not Path(cv_path).exists():
        print(f"  ERROR: CV no encontrado en {cv_path}")
        return

    applicator = JobApplicator(cv_path=cv_path)
    result = await applicator.apply(
        offer_url=url,
        platform=platform,
        profile_text=profile,
        headless=headless,
    )

    print()
    print("=== Resultado de Aplicacion ===")
    for step in result.steps:
        print(f"  {step}")
    print()
    if result.success and result.applied:
        print("  [OK] Postulacion enviada correctamente")
    else:
        print(f"  [FAIL] Fallo: {result.error or 'No se pudo completar'}")
    if result.captcha and result.captcha.detected:
        print(f"  [!] CAPTCHA: {result.captcha.captcha_type.value} - {result.captcha.detail}")


async def _doctor():
    from backend.auth.session import SessionStorage
    from backend.auth import PLATFORMS
    from backend.config import settings

    print()
    print("=" * 50)
    print("  AI Opportunity Hunter — Diagnostico")
    print("=" * 50)

    print("\n[1] Configuracion")
    print(f"  AI Provider: {settings.ai_provider}")
    print(f"  Keywords: {settings.keywords_list}")
    print(f"  Threshold: {settings.score_threshold}")
    has_key = lambda v: "[OK] configurado" if v else "[FALTA]"
    if settings.ai_provider == "gemini":
        print(f"  GEMINI_API_KEY: {has_key(settings.gemini_api_key)}")
        print(f"  GEMINI_MODEL: {settings.gemini_model}")
    else:
        print(f"  OPENAI_BASE_URL: {settings.openai_base_url}")
        print(f"  OPENAI_MODEL: {settings.openai_model or '(auto-detect)'}")
    print(f"  TELEGRAM_BOT_TOKEN: {has_key(settings.telegram_bot_token)}")

    print("\n[2] Sesiones guardadas")
    for p in PLATFORMS:
        s = SessionStorage(p)
        info = s.info()
        if info["has_session"]:
            print(f"  + {p.upper()}: {info['cookies']} cookies, {info['file_size']} bytes")
        else:
            print(f"  - {p.upper()}: sin sesion")

    print("\n[3] Dependencias")
    deps = {
        "playwright": False,
        "sqlalchemy": False,
        "google.genai": False,
        "openai": False,
        "telegram": False,
    }
    for dep in deps:
        try:
            __import__(dep)
            deps[dep] = True
        except ImportError:
            pass
    for dep, ok in deps.items():
        print(f"  {'+' if ok else '-'} {dep}")

    print("\n[4] Navegador Playwright")
    playwright_path = Path.home() / "AppData/Local/ms-playwright"
    if playwright_path.exists():
        browsers = [d.name for d in playwright_path.iterdir() if d.is_dir()]
        print(f"  + Browsers instalados: {', '.join(browsers)}")
    else:
        print("  - Playwright browsers no encontrados. Ejecuta: python -m playwright install chromium")

    print("\n[5] Archivos del proyecto")
    important = [
        "requirements.txt",
        "main.py",
        ".env.example",
        "backend/scrapers/main.py",
        "backend/scripts/cli.py",
    ]
    base = Path.cwd()
    for f in important:
        exists = (base / f).exists()
        print(f"  {'+' if exists else '-'} {f}")

    print("\n[6] Datos recolectados")
    data_dir = base / "data"
    if data_dir.exists():
        csvs = list(data_dir.glob("*.csv"))
        sessions = list(data_dir.glob("sessions/*.json"))
        print(f"  Archivos CSV: {len(csvs)}")
        print(f"  Sesiones guardadas: {len(sessions)}")
        if csvs:
            latest = max(csvs, key=lambda f: f.stat().st_mtime)
            print(f"  Ultimo CSV: {latest.name} ({latest.stat().st_size} bytes)")
    else:
        print("  - data/ no existe")

    print("\n" + "=" * 50)
    print("  Diagnostico completado")
    print("=" * 50)


if __name__ == "__main__":
    main()
