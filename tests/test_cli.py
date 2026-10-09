from typer.testing import CliRunner

from modelhub import __version__
from modelhub.cli import app

runner = CliRunner()


def test_version():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.output
