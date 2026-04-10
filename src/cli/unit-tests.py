import sys
import unittest
import click


def test_transformer():
    from tests.test_transformer import TestTransformation
    suite = unittest.TestLoader().loadTestsFromTestCase(TestTransformation)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful():
        raise Exception(f"{len(result.failures)} failure(s), {len(result.errors)} error(s)")


def test_sanity():
    from tests.test_sanity_check import test_sanity_check_relational
    test_sanity_check_relational()


def test_mapping_template():
    from tests.test_mapping_template_generator import MappingTemplateGeneratorTests
    suite = unittest.TestLoader().loadTestsFromTestCase(MappingTemplateGeneratorTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful():
        raise Exception(f"{len(result.failures)} failure(s), {len(result.errors)} error(s)")


def test_mapping_cli():
    import subprocess
    res = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/test_generate_mapping_cli.py", "-v"],
        capture_output=True, text=True
    )
    click.echo(res.stdout)
    if res.stderr:
        click.echo(res.stderr, err=True)
    if res.returncode != 0:
        raise Exception("pytest failed")


test_list = {
    "test_transformer": test_transformer,
    "test_sanity": test_sanity,
    "test_mapping_template": test_mapping_template,
    "test_mapping_cli": test_mapping_cli,
}
def resolve_tests(tests):
    if "all" in tests:
        return list(test_list.keys())

    unknown_elements = [n for n in tests if n not in test_list]
    if unknown_elements:
        raise click.BadParameter(
                    f"Unknown test(s): {', '.join(unknown_elements)}. "
                    f"Available: {', '.join(test_list)}"
                )

    return list(dict.fromkeys(tests))

@click.command()
@click.option(
    "--tests", "-t",
    multiple=True,          # allows: -t test1 -t test2
    required=True,
    help='Test name(s) or "all". Repeatable: --tests t1 --tests t2',
)
@click.option("--verbose", "-v", is_flag=True, help="Show extra output.")

def cli(tests, verbose):
    """Run one or more unit tests by name, or pass 'all' to run everything."""
    try:
        to_run = resolve_tests(tests)
    except click.BadParameter as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    click.echo(f"Running {len(to_run)} test(s): {', '.join(to_run)}\n")

    passed, failed = [], []
    for name in to_run:
        try:
            test_list[name]()
            passed.append(name)
        except Exception as exc:
            failed.append(name)
            click.echo(f"  FAIL {name}: {exc}", err=True)

    click.echo(f"\n{len(passed)} passed, {len(failed)} failed.")
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    cli()
