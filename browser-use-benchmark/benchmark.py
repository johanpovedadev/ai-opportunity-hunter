"""Benchmark: Browser Use vs Playwright tradicional."""
import asyncio, time, csv, os, sys
from datetime import datetime as dt
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from browser_use import Agent
from browser_use.llm.litellm.chat import ChatLiteLLM
from browser_use.browser.profile import BrowserProfile

os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")


@dataclass
class BenchResult:
    approach: str
    task: str
    success: bool
    time_sec: float
    error: str = ""
    steps: int = 0
    cost_usd: float = 0.0
    details: str = ""


def _llm():
    return ChatLiteLLM(
        model="groq/llama-3.3-70b-versatile",
        api_key=os.getenv("GROQ_API_KEY"),
        temperature=0.0,
        max_tokens=4096,
    )


def _profile():
    return BrowserProfile(
        headless=True,
        viewport={"width": 1280, "height": 720},
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    )


async def bench_browser_use(task: str, url: str, label: str = "") -> BenchResult:
    start = time.time()
    agent = Agent(
        task=f"Go to {url} and {task}",
        llm=_llm(),
        browser_profile=_profile(),
        use_vision=False,
        max_failures=3,
    )
    try:
        history = await agent.run(max_steps=20)
        elapsed = time.time() - start
        n_steps = history.number_of_steps
        done = history.is_done()
        errs = history.errors
        return BenchResult(
            approach="browser_use",
            task=label or task[:50],
            success=done and not errs,
            time_sec=round(elapsed, 1),
            steps=n_steps,
            details=f"errors={errs}" if errs else f"steps={n_steps}",
        )
    except Exception as e:
        elapsed = time.time() - start
        return BenchResult(
            approach="browser_use",
            task=label or task[:50],
            success=False,
            time_sec=round(elapsed, 1),
            error=str(e)[:200],
        )


async def bench_playwright(url: str, label: str) -> BenchResult:
    from backend.application import JobApplicator
    start = time.time()
    cv = "data/hVjohan29052026.pdf"
    app = JobApplicator(cv_path=cv if Path(cv).exists() else None)
    try:
        result = await app.apply(
            offer_url=url,
            platform="computrabajo",
            profile_text="Junior Python developer with SQL, automation, scraping",
            headless=True,
        )
        elapsed = time.time() - start
        return BenchResult(
            approach="playwright",
            task=label,
            success=result.success,
            time_sec=round(elapsed, 1),
            steps=len(result.steps),
            details="; ".join(result.steps[-3:]),
        )
    except Exception as e:
        elapsed = time.time() - start
        return BenchResult(
            approach="playwright",
            task=label,
            success=False,
            time_sec=round(elapsed, 1),
            error=str(e)[:200],
        )


async def main():
    OFFER = "https://co.computrabajo.com/ofertas-de-trabajo/oferta-de-trabajo-de-analista-junior-de-automatizacion-y-aplicaciones-python-y-sql-en-bogota-dc-0EB9FA6EB7A22D6661373E686DCF3405"
    SEARCH = "https://co.computrabajo.com/trabajo-de-python"

    tests = [
        bench_browser_use(
            "search for jobs and count how many job offers are listed",
            SEARCH,
            "BU: contar ofertas",
        ),
        bench_browser_use(
            "click 'Postularme', fill the form with profile: Junior Python developer, upload CV if file input exists, and submit",
            OFFER,
            "BU: postular empleo",
        ),
        bench_playwright(OFFER, "PW: postular empleo"),
    ]

    results = await asyncio.gather(*tests, return_exceptions=True)
    results = [r for r in results if isinstance(r, BenchResult)]

    ts = dt.now().strftime("%Y%m%d_%H%M%S")
    out = Path(__file__).parent / f"benchmark_{ts}.csv"
    with open(out, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["Approach", "Task", "Success", "TimeSec", "Steps", "CostUSD", "Error", "Details"])
        for r in results:
            w.writerow([r.approach, r.task, r.success, r.time_sec, r.steps, r.cost_usd, r.error[:120], r.details])

    print(f"\n{'='*60}")
    print(f"BENCHMARK RESULTADOS")
    print(f"{'='*60}")
    for r in results:
        icon = "[OK]" if r.success else "[FAIL]"
        print(f"\n{icon} {r.approach:15s} | {r.task:30s} | {r.time_sec:6.1f}s | steps={r.steps}")
        if r.error:
            print(f"   Error: {r.error}")
        if r.details:
            print(f"   {r.details}")
    print(f"\nCSV: {out}")

    # Stats
    suc = sum(1 for r in results if r.success)
    print(f"\n{'='*60}")
    print(f"Exitosos: {suc}/{len(results)} ({suc/len(results)*100:.0f}%)")
    for approach in ["playwright", "browser_use"]:
        rs = [r for r in results if r.approach == approach and r.success]
        if rs:
            avg = sum(r.time_sec for r in rs) / len(rs)
            print(f"{approach:15s}: {avg:.1f}s avg, {len(rs)} exitosos")
        rs = [r for r in results if r.approach == approach and not r.success]
        if rs:
            print(f"{approach:15s}: {len(rs)} fallos")
    print(f"{'='*60}")


if __name__ == "__main__":
    asyncio.run(main())
