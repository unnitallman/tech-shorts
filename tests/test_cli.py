import subprocess


def test_help_shows_subcommands():
    result = subprocess.run(
        ["python3", "scripts/shorts.py", "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "new" in result.stdout
    assert "publish" in result.stdout
    assert "status" in result.stdout
