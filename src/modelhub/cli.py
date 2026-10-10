"""The command line (contract C4).

Exit status: 0 everything asked for was done; 1 at least one item failed (the others were
still processed); 2 the command could not run (wrong options, missing input, no room, a
folder already in use).
"""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path

import typer

from modelhub import (
    __version__,
    download,
    filetypes,
    fsutil,
    hubclient,
    logsetup,
    pieces,
    progress,
    record,
    redact,
    runrecord,
    signing,
    store,
)
from modelhub import bundle as bundle_mod
from modelhub import pull as pull_mod
from modelhub import unpack as unpack_mod
from modelhub import verify as verify_mod

app = typer.Typer(
    help="Move Hugging Face models into an air-gapped environment.",
    no_args_is_help=True,
)
key_app = typer.Typer(
    help="Signing keys: create, export, show fingerprints, trust.", no_args_is_help=True
)
app.add_typer(key_app, name="key")

_STATE: dict = {"log": None}

FAILURES = (
    hubclient.HubError,
    download.ChecksumMismatch,
    bundle_mod.RecordChanged,
    bundle_mod.TooManyPieces,
    verify_mod.VerifyFailed,
    unpack_mod.UnsafeArchive,
    unpack_mod.IntegrityFailure,
    fsutil.UnsafePathError,
    record.UnsupportedFormat,
    signing.KeyError_,
)
CANNOT_RUN = (
    bundle_mod.InsufficientSpace,
    fsutil.LockedError,
    signing.NoSigningKey,
    ValueError,
)


def make_hub_client(token: str | None = None):
    return hubclient.HfHubClient(token)


@contextmanager
def _guard():
    try:
        yield
    except CANNOT_RUN as error:  # checked first: NoSigningKey is also a kind of key error
        typer.echo(redact.redact(f"Error: {error}"), err=True)
        raise typer.Exit(2)
    except FAILURES as error:
        typer.echo(redact.redact(f"Error: {error}"), err=True)
        raise typer.Exit(1)


@contextmanager
def _session(command: str, folder: Path):
    """Logging, the run record and the progress display for one command (NFR8.3, NFR8.4)."""
    logsetup.start(_STATE["log"], folder)
    run = runrecord.RunRecord(command)
    shown = progress.Reporter()
    names = {"record": "run-record.json"}
    try:
        yield shown, run, names
    finally:
        try:
            if run.items:
                run.write(Path(folder) / names["record"])
        finally:
            logsetup.stop()


def _version(value: bool) -> None:
    if value:
        typer.echo(f"modelhub {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        False, "--version", callback=_version, is_eager=True, help="Show the version."
    ),
    verbose: bool = typer.Option(
        False, "--verbose", help="Also write a log file (modelhub.log) beside the output."
    ),
    debug: bool = typer.Option(False, "--debug", help="Write a more detailed log file."),
) -> None:
    """Move Hugging Face models into an air-gapped environment."""
    _STATE["log"] = "debug" if debug else "verbose" if verbose else None


# --- pull -----------------------------------------------------------------------------


@app.command()
def pull(
    models: list[str] = typer.Argument(None, help="Model ids such as org/name."),
    list_file: Path = typer.Option(
        None, "--list", help="A file with one model id per line (# starts a comment)."
    ),
    work: Path = typer.Option(Path("pulled"), "--work", help="Folder for download records."),
    types: list[str] = typer.Option(
        None, "--type", help="File type to fetch; repeat for more, or 'all' for everything."
    ),
    revision: str = typer.Option("main", "--revision", help="Branch, tag or commit."),
    workers: int = typer.Option(
        download.DEFAULT_WORKERS, "--workers", min=1, help="Files downloaded at the same time."
    ),
    ask_token: bool = typer.Option(
        False, "--ask-token", help="Ask for a Hugging Face token (typing is hidden)."
    ),
    token: str = typer.Option(None, "--token", hidden=True),
) -> None:
    """Download models from Hugging Face into download records.

    Without --type nothing is downloaded: the file types found are shown so you can choose.
    A Hugging Face token, if needed, comes from the HF_TOKEN environment variable or --ask-token.
    """
    if token is not None:
        typer.echo(
            "Error: do not put a token on the command line; it would stay in your shell history. "
            "Set the HF_TOKEN environment variable, or use --ask-token.",
            err=True,
        )
        raise typer.Exit(2)
    with _guard():
        wanted = list(models or []) + (_read_model_list(list_file) if list_file else [])
        if not wanted:
            raise ValueError("give at least one model id, or a file with --list")
    typed = typer.prompt("Hugging Face token", hide_input=True) if ask_token else None
    redact.remember(typed)
    client = make_hub_client(typed)
    selection = set(types) if types else None
    failed = False
    with _session("pull", work) as (shown, run, _):
        for model in wanted:
            try:
                result = pull_mod.pull_model(
                    client,
                    model,
                    work,
                    revision,
                    selection,
                    workers=workers,
                    on_wait=shown.message,
                    progress=shown,
                )
            except pull_mod.PullIncomplete as error:
                _note_items(run, model, error.items)
                for item in error.failed:
                    typer.echo(
                        redact.redact(f"{model}: {item['path']}: {item['reason']}"), err=True
                    )
                failed = True
                continue
            except filetypes.UnknownFileType as error:
                typer.echo(f"{model}: {error}", err=True)
                raise typer.Exit(2)
            except fsutil.LockedError as error:
                typer.echo(f"{model}: {error}", err=True)
                raise typer.Exit(2)
            except hubclient.UnsupportedModel as error:
                run.add(model, "unsupported", reason=str(error))
                typer.echo(redact.redact(f"{model}: {error}"), err=True)
                failed = True
                continue
            except (hubclient.HubError, download.ChecksumMismatch) as error:
                run.add(model, "failed", reason=str(error))
                typer.echo(redact.redact(f"{model}: {error}"), err=True)
                failed = True
                continue
            _note_items(run, result.model_id, result.items)
            if result.name_warnings:
                typer.echo(
                    f"{model}: these file names cannot be written on Windows (kept as they are): "
                    + ", ".join(result.name_warnings),
                    err=True,
                )
            if selection is None:
                _show_types(result)
            elif result.nothing_matched:
                run.add(result.model_id, "nothing-matched")
                typer.echo(f"{model}: nothing matched the types you chose", err=True)
                _show_types(result)
                failed = True
            else:
                typer.echo(
                    f"{result.model_id} {result.commit[:12]}: {len(result.fetched)} files "
                    f"-> {result.record_dir}"
                )
    if failed:
        raise typer.Exit(1)


def _note_items(run: runrecord.RunRecord, model: str, items: list[dict]) -> None:
    for item in items:
        run.add(
            model,
            item["status"],
            name=item["name"],
            size=item.get("size"),
            seconds=item.get("seconds"),
            retries=item.get("retries"),
            reason=item.get("reason"),
        )


def _read_model_list(path: Path) -> list[str]:
    lines = (line.strip() for line in Path(path).read_text(encoding="utf-8").splitlines())
    return [line for line in lines if line and not line.startswith("#")]


def _show_types(result: pull_mod.PullResult) -> None:
    typer.echo(f"{result.model_id} ({result.commit[:12]}) has these kinds of files:")
    for group in result.groups:
        always = " (always fetched)" if group.type.always else ""
        typer.echo(
            f"  {group.type.key:<12} {group.count:>3} file(s)  "
            f"{progress.human_bytes(group.size):>10}{always}"
        )
        typer.echo(f"      {group.type.explanation}")
    typer.echo(f"  Total: {progress.human_bytes(filetypes.total_size(result.groups))}")
    typer.echo("Choose with --type NAME (repeat for more), or --type all for everything.")


# --- bundle ---------------------------------------------------------------------------


@app.command()
def bundle(
    record_dir: Path = typer.Argument(..., help="A download record folder made by 'pull'."),
    out: Path = typer.Option(..., "--out", help="Folder for the pieces."),
    piece_size: str = typer.Option(None, "--piece-size", help="Largest piece, such as 900MB."),
    interactive: bool = typer.Option(False, "--interactive", help="Fill drives one at a time."),
    key: str = typer.Option(None, "--key", help="Key id to sign with."),
) -> None:
    """Check a download record, then cut it into signed pieces."""
    with _guard(), _session("bundle", out) as (shown, run, names):
        try:
            if interactive == (piece_size is not None):
                raise ValueError("choose exactly one of --piece-size or --interactive")
            key_id = key or signing.default_key_id()
            size = pieces.parse_size(piece_size) if piece_size else None
            if size:
                total, count = bundle_mod.plan_bundle(record_dir, size)
                typer.echo(f"About {count} pieces ({total} bytes in all) will be written to {out}.")
            else:
                typer.echo("You will be asked for each drive in turn.")
            result = bundle_mod.bundle_record(
                record_dir,
                out,
                key_id,
                piece_size=size,
                next_drive=_ask_drive(out) if interactive else None,
                progress=shown,
            )
        except Exception as error:
            run.add(str(record_dir), "failed", reason=str(error))
            names["record"] = "bundle.run-record.json"
            raise
        names["record"] = f"{result.stem}.run-record.json"
        for piece in result.pieces:
            run.add(result.stem, "written", name=piece["name"], size=piece["size"])
        typer.echo(f"Wrote {result.stem}: {len(result.pieces)} pieces, {result.stream_size} bytes.")


def _ask_drive(default: Path):
    def ask(index: int) -> tuple[Path, int]:
        typer.echo(f"Drive {index}: put the drive in place.")
        folder = typer.prompt("Folder on this drive", default=str(default))
        size = pieces.parse_size(typer.prompt("Size of this drive (for example 700MB)"))
        return Path(folder), size

    return ask


# --- verify, unpack, list -------------------------------------------------------------


@app.command()
def verify(
    paths: list[Path] = typer.Argument(..., help="Folders holding pieces, or a model store."),
) -> None:
    """Check signatures and every piece (or every file of a model store); name anything wrong."""
    with _guard():
        stores = [p for p in paths if (p / "models").is_dir()]
        bundles = [p for p in paths if p not in stores]
        failed = False
        for store_dir in stores:
            problems = verify_mod.verify_store(store_dir)
            for problem in problems:
                typer.echo(problem.message, err=True)
            failed = failed or bool(problems)
            if not problems:
                typer.echo(f"OK store {store_dir}")
        if bundles or not stores:
            reports = verify_mod.verify_bundle(bundles, progress=progress.Reporter())
            if not reports:
                raise ValueError("no bundle found in the folders given")
            for report in reports:
                if report.ok:
                    typer.echo(f"OK {report.stem}: {len(report.manifest['pieces'])} pieces")
                for problem in report.problems:
                    typer.echo(f"{report.stem}: {problem.message}", err=True)
            failed = failed or any(not r.ok for r in reports)
        if failed:
            raise typer.Exit(1)


@app.command()
def unpack(
    paths: list[Path] = typer.Argument(..., help="Folders holding the pieces."),
    store_dir: Path = typer.Option(..., "--store", help="The model store to rebuild into."),
) -> None:
    """Check a bundle and rebuild it into the model store."""
    with _guard(), _session("unpack", store_dir) as (shown, run, _):
        try:
            results = unpack_mod.unpack_bundle(paths, store_dir, progress=shown)
        except Exception as error:
            run.add(", ".join(str(p) for p in paths), "failed", reason=str(error))
            raise
        for result in results:
            status = "already-present" if result.already_present else "unpacked"
            run.add(result.model_id, status, name=result.commit)
            note = " (already present)" if result.already_present else ""
            typer.echo(f"{result.model_id} {result.commit[:12]} -> {result.path}{note}")


@app.command(name="list")
def list_(store_dir: Path = typer.Argument(..., help="The model store.")) -> None:
    """List the models in a store."""
    with _guard():
        if not store_dir.is_dir():
            raise ValueError(f"no such folder: {store_dir}")
        for item in store.list_models(store_dir):
            mark = " latest" if item.latest else ""
            size = "?" if item.size is None else str(item.size)
            typer.echo(
                f"{item.model_id}  {item.commit[:12]}  {item.captured_at or '?'}  {size} bytes  "
                f"{item.license or '-'}{mark}"
            )


# --- keys -----------------------------------------------------------------------------


@key_app.command("create")
def key_create(
    name: str = typer.Option("modelhub", "--name", help="A label for the key."),
) -> None:
    """Make a signing key pair on this computer."""
    with _guard():
        doc = signing.create_key(name)
        typer.echo(f"Created key {doc['key_id']}")
        typer.echo(f"Fingerprint: {doc['fingerprint']}")


@key_app.command("export")
def key_export(key_id: str, out: Path = typer.Option(..., "--out")) -> None:
    """Write the public half of a key to a file."""
    with _guard():
        signing.export_public(key_id, out)
        typer.echo(f"Wrote public key {key_id} to {out}")


@key_app.command("fingerprint")
def key_fingerprint(target: str) -> None:
    """Show the fingerprint of a public key file, or of a key made on this computer."""
    with _guard():
        path = Path(target)
        doc = (
            signing.read_public_doc(path)
            if path.is_file()
            else signing.read_public_doc(signing.home() / "keys" / f"{target}.pub.json")
        )
        typer.echo(f"Fingerprint: {doc['fingerprint']}")


@key_app.command("trust")
def key_trust(public_key_file: Path) -> None:
    """Trust a public key after typing its fingerprint, received by a separate route."""
    with _guard():
        doc = signing.read_public_doc(public_key_file)
        typer.echo(f"Key {doc['key_id']} ({doc['name']})")
        typed = typer.prompt("Type the fingerprint you were given for this key")
        signing.trust_key(doc, typed)
        typer.echo(f"Trusted key {doc['key_id']}")


@key_app.command("untrust")
def key_untrust(key_id: str) -> None:
    """Stop trusting a key."""
    with _guard():
        typer.echo("Removed." if signing.untrust_key(key_id) else "That key was not trusted.")


@key_app.command("list")
def key_list() -> None:
    """List keys made here and keys trusted here."""
    with _guard():
        for doc in signing.list_keys():
            typer.echo(f"own      {doc['key_id']}  {doc['fingerprint']}  {doc['name']}")
        for doc in signing.trusted_keys():
            typer.echo(f"trusted  {doc['key_id']}  {doc['fingerprint']}  {doc['name']}")
