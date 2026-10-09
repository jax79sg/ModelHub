from pathlib import Path

import typer

from modelhub import __version__

app = typer.Typer(help="Move Hugging Face repos into an airgapped environment.", no_args_is_help=True)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(__version__)
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        False, "--version", callback=_version_callback, is_eager=True, help="Show version and exit."
    ),
) -> None:
    """Move Hugging Face repos into an airgapped environment."""


@app.command()
def pull(
    repo_id: str = typer.Argument(..., help="e.g. meta-llama/Llama-3.1-8B"),
    out: Path = typer.Option(Path("pulled"), "--out", "-o", help="Output directory."),
    repo_type: str = typer.Option("model", "--type", help="model | dataset | space"),
    revision: str = typer.Option("main", "--revision", "-r", help="Branch, tag or commit."),
    include: list[str] = typer.Option(None, "--include", help="Glob of files to fetch (repeatable)."),
    exclude: list[str] = typer.Option(None, "--exclude", help="Glob of files to skip (repeatable)."),
    token: str = typer.Option(None, envvar="HF_TOKEN", help="HF token for gated/private repos."),
) -> None:
    """Download a repo (files, README, Hub metadata) and write a hashed manifest. Needs internet."""
    from modelhub.hub import pull as _pull

    root, m = _pull(repo_id, out, repo_type, revision, include or None, exclude or None, token)
    typer.echo(f"{m.repo_id}@{m.revision[:12]}: {len(m.files)} files -> {root}")


@app.command()
def bundle(
    path: Path = typer.Argument(..., help="Directory produced by `pull`."),
    output: Path = typer.Option(None, "--output", "-o", help="Tar file (default: <name>.tar)."),
) -> None:
    """Verify a pulled repo and pack it into a single tar for transfer."""
    from modelhub.bundle import make_bundle

    output = output or Path(f"{path.name}.tar")
    make_bundle(path, output)
    typer.echo(f"wrote {output}")


@app.command()
def verify(path: Path = typer.Argument(..., help="Pulled/unpacked repo directory.")) -> None:
    """Check every file against the manifest (size + sha256)."""
    from modelhub.manifest import verify_dir

    problems = verify_dir(path)
    for p in problems:
        typer.echo(p, err=True)
    if problems:
        raise typer.Exit(1)
    typer.echo("OK")


@app.command()
def unpack(
    bundle_file: Path = typer.Argument(..., help="Tar made by `bundle`."),
    dest: Path = typer.Option(..., "--dest", "-d", help="Where to extract the verified repo."),
    hf_cache: Path = typer.Option(
        None, "--hf-cache", help="Also install into this HF hub cache dir (use with HF_HUB_CACHE)."
    ),
) -> None:
    """Extract a bundle, verify it, and optionally install it as an HF cache. Works offline."""
    from modelhub.bundle import extract_bundle, install_hf_cache

    root = extract_bundle(bundle_file, dest)
    typer.echo(f"extracted + verified -> {root}")
    if hf_cache:
        typer.echo(f"installed HF cache entry -> {install_hf_cache(root, hf_cache)}")
