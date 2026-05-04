from __future__ import annotations

import click

from halo_ssg.utils.log import setup_logging, console


@click.group()
@click.option("--config", "-c", default="config.yaml", help="Config file path.")
@click.option("--verbose", "-v", is_flag=True, help="Verbose output.")
@click.pass_context
def cli(ctx: click.Context, config: str, verbose: bool) -> None:
    ctx.ensure_object(dict)
    ctx.obj["config_path"] = config
    ctx.obj["verbose"] = verbose
    setup_logging(verbose)


@cli.command()
@click.option("--force", is_flag=True, help="Force full sync, ignore state.")
@click.pass_context
def sync(ctx: click.Context, force: bool) -> None:
    """Sync content from Halo and build static site."""
    from halo_ssg.config import load_config
    from halo_ssg.builder.site_builder import SiteBuilder

    cfg = load_config(ctx.obj["config_path"])
    builder = SiteBuilder(cfg)
    builder.run(force=force)


@cli.command()
@click.pass_context
def build(ctx: click.Context) -> None:
    """Build static site from already-crawled data."""
    from halo_ssg.config import load_config
    from halo_ssg.builder.site_builder import SiteBuilder

    cfg = load_config(ctx.obj["config_path"])
    builder = SiteBuilder(cfg)
    builder.build_only()


@cli.command()
@click.option("--port", "-p", default=8000, help="Port number.")
@click.pass_context
def serve(ctx: click.Context, port: int) -> None:
    """Start local preview server."""
    import http.server
    import functools
    from pathlib import Path
    from halo_ssg.config import load_config

    cfg = load_config(ctx.obj["config_path"])
    output_dir = cfg.output.dir.resolve()
    if not output_dir.exists():
        console.print("[red]Output directory does not exist. Run 'halo-ssg sync' first.[/red]")
        return

    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(output_dir))
    with http.server.HTTPServer(("", port), handler) as httpd:
        console.print(f"[green]Serving at http://localhost:{port}[/green]")
        console.print(f"[dim]Root: {output_dir}[/dim]")
        httpd.serve_forever()


@cli.command()
@click.pass_context
def status(ctx: click.Context) -> None:
    """Show sync status."""
    import json
    from pathlib import Path
    from halo_ssg.config import load_config

    cfg = load_config(ctx.obj["config_path"])
    state_file = cfg.sync.state_file
    if not state_file.exists():
        console.print("[yellow]No sync state found. Run 'halo-ssg sync' first.[/yellow]")
        return

    with open(state_file, encoding="utf-8") as f:
        state = json.load(f)

    console.print(f"[bold]Last sync:[/bold] {state.get('last_sync', 'unknown')}")
    console.print(f"[bold]Posts:[/bold] {len(state.get('posts', {}))}")
    console.print(f"[bold]Pages:[/bold] {len(state.get('pages', {}))}")
    console.print(f"[bold]Assets:[/bold] {len(state.get('assets', {}))}")
