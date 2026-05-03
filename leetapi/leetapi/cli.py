from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import typer

app = typer.Typer(help="LeetCode tutor service CLI.")


@app.command()
def serve(
    host: str = "127.0.0.1",
    port: int = 4000,
    reload: bool = True,
) -> None:
    import uvicorn

    uvicorn.run("leetapi.main:app", host=host, port=port, reload=reload)


@app.command()
def migrate() -> None:
    here = Path(__file__).resolve().parent.parent
    result = subprocess.run(
        ["alembic", "upgrade", "head"],
        cwd=here,
        check=False,
    )
    sys.exit(result.returncode)


@app.command()
def ingest() -> None:
    import asyncio

    from sqlmodel.ext.asyncio.session import AsyncSession

    from .config import get_settings
    from .db import get_async_engine
    from .services.importer import ingest_csvs

    settings = get_settings()
    typer.echo(f"ingesting from {settings.problems_dir}")

    async def run() -> int:
        engine = get_async_engine()
        async with AsyncSession(engine) as session:
            agg = await ingest_csvs(session, settings.problems_dir)
        return len(agg.problems)

    n = asyncio.run(run())
    typer.secho(f"ok — upserted {n} problems", fg=typer.colors.GREEN)


@app.command("import-legacy")
def import_legacy() -> None:
    import asyncio

    from sqlmodel.ext.asyncio.session import AsyncSession

    from .config import get_settings
    from .db import get_async_engine
    from .services.legacy import import_cache_db, import_md_files

    settings = get_settings()
    leetcode_dir = settings.repo_root / "data" / "leetcode"
    cache_db = settings.repo_root / "data" / "cache.db"

    async def run() -> tuple[int, int]:
        engine = get_async_engine()
        async with AsyncSession(engine) as session:
            md_count = await import_md_files(session, leetcode_dir)
            cache_count = await import_cache_db(session, cache_db)
        return md_count, cache_count

    md_count, cache_count = asyncio.run(run())
    typer.secho(
        f"ok — imported {md_count} statement(s) and {cache_count} tutor_response(s)",
        fg=typer.colors.GREEN,
    )


@app.command("refresh-tutor")
def refresh_tutor(
    slug: str | None = None,
    persona: str | None = None,
    all_: bool = typer.Option(False, "--all"),
) -> None:
    typer.secho("not implemented yet", fg=typer.colors.YELLOW)
    raise typer.Exit(code=2)


@app.command("refresh-statement")
def refresh_statement(slug: str) -> None:
    typer.secho("not implemented yet", fg=typer.colors.YELLOW)
    raise typer.Exit(code=2)


if __name__ == "__main__":
    app()
