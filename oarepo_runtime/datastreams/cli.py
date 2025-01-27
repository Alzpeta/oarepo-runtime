import click
from flask import current_app
from flask.cli import with_appcontext

from oarepo_runtime.cli import oarepo
from oarepo_runtime.datastreams.fixtures import (
    FixturesResult,
    dump_fixtures,
    load_fixtures,
)


@oarepo.group()
def fixtures():
    """Load and dump fixtures"""


@fixtures.command()
@click.argument("fixture_dir", required=False)
@click.option("--include", multiple=True)
@click.option("--exclude", multiple=True)
@with_appcontext
def load(fixture_dir=None, include=None, exclude=None):
    """Loads fixtures"""
    with current_app.wsgi_app.mounts["/api"].app_context():
        results: FixturesResult = load_fixtures(
            fixture_dir, _make_list(include), _make_list(exclude)
        )
        _show_stats(results, "Load fixtures")


@fixtures.command()
@click.option("--include", multiple=True)
@click.option("--exclude", multiple=True)
@click.argument("fixture_dir", required=True)
@with_appcontext
def dump(fixture_dir, include, exclude):
    """Dump fixtures"""
    with current_app.wsgi_app.mounts["/api"].app_context():
        results = dump_fixtures(fixture_dir, _make_list(include), _make_list(exclude))
        _show_stats(results, "Dump fixtures")


def _make_list(lst):
    return [
        item.strip() for lst_item in lst for item in lst_item.split(",") if item.strip()
    ]


def _show_stats(results: FixturesResult, title: str):
    print(f"{title} stats:")
    print(f"    ok records: {results.ok_count}")
    print(f"    failed records: {results.failed_count}")
    print(f"    skipped records: {results.skipped_count}")
    print()
    print("Details:")
    for fixture, r in results.results.items():
        print(
            f"    {fixture} - {r.ok_count} ok, {r.failed_count} failed, {r.skipped_count} skipped"
        )
        if r.failed_entries:
            for fe in r.failed_entries:
                print(f"    {fixture} failure: {fe.errors} in {fe.entry}")
