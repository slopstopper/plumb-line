import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import baseline as bl  # noqa: E402
from marked import mark, derive  # noqa: E402

_SCRIPT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'baseline.py')


def _run(*args):
    p = subprocess.run([sys.executable, _SCRIPT, *args], capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


def _seed(tmp_path):
    r = mark(0.04, source='real', confidence='high')
    bl.update('nightly-rate', derive([r], lambda x: x * 2), because='initial pin', dir=str(tmp_path), date='2026-09-10')


def test_list_prints_names_and_denominator(tmp_path):
    _seed(tmp_path)
    code, out = _run('list', '--dir', str(tmp_path))
    assert code == 0 and 'nightly-rate' in out and '1 baseline(s) in ' in out


def test_list_on_missing_directory_exits_zero(tmp_path):
    code, out = _run('list', '--dir', str(tmp_path / 'absent'))
    assert code == 0 and 'no baselines directory at' in out


def test_show_prints_trust_state_and_history(tmp_path):
    _seed(tmp_path)
    code, out = _run('show', 'nightly-rate', '--dir', str(tmp_path))
    assert code == 0 and 'source: "derived"' in out and '2026-09-10  initial  initial pin' in out


def test_show_unknown_exits_one(tmp_path):
    assert _run('show', 'nope', '--dir', str(tmp_path))[0] == 1


def test_validate_passes_clean_and_names_broken(tmp_path):
    _seed(tmp_path)
    assert _run('validate', '--dir', str(tmp_path))[0] == 0
    (tmp_path / 'broken.json').write_text('{ not json', encoding='utf-8')
    code, out = _run('validate', '--dir', str(tmp_path))
    assert code == 1 and 'broken.json' in out and '1 of 2 invalid' in out


def test_usage_exits_two():
    code, out = _run()
    assert code == 2 and 'usage: baseline <list|show <name>|validate> [--dir D]' in out


# Direct-call tests for coverage (coverage.py doesn't see subprocess calls)

def test_main_list_direct(tmp_path, capsys):
    _seed(tmp_path)
    code = bl.main(['list', '--dir', str(tmp_path)])
    out = capsys.readouterr().out
    assert code == 0 and 'nightly-rate' in out and '1 baseline(s) in ' in out


def test_main_list_missing_dir_direct(tmp_path, capsys):
    code = bl.main(['list', '--dir', str(tmp_path / 'absent')])
    out = capsys.readouterr().out
    assert code == 0 and 'no baselines directory at' in out


def test_main_show_direct(tmp_path, capsys):
    _seed(tmp_path)
    code = bl.main(['show', 'nightly-rate', '--dir', str(tmp_path)])
    out = capsys.readouterr().out
    assert code == 0 and 'source: "derived"' in out and '2026-09-10  initial  initial pin' in out


def test_main_show_missing_name_direct(capsys):
    code = bl.main(['show', '--dir', '/tmp'])
    err = capsys.readouterr().err
    assert code == 2 and 'usage: baseline show <name> [--dir D]' in err


def test_main_show_unknown_direct(tmp_path, capsys):
    code = bl.main(['show', 'nope', '--dir', str(tmp_path)])
    err = capsys.readouterr().err
    assert code == 1 and 'no baseline named' in err


def test_main_validate_direct(tmp_path, capsys):
    _seed(tmp_path)
    code = bl.main(['validate', '--dir', str(tmp_path)])
    out = capsys.readouterr().out
    assert code == 0 and '1 file(s) valid' in out

    (tmp_path / 'broken.json').write_text('{ not json', encoding='utf-8')
    code = bl.main(['validate', '--dir', str(tmp_path)])
    out = capsys.readouterr().out
    assert code == 1 and 'broken.json' in out and '1 of 2 invalid' in out


def test_main_validate_missing_dir_direct(tmp_path, capsys):
    code = bl.main(['validate', '--dir', str(tmp_path / 'absent')])
    out = capsys.readouterr().out
    assert code == 0 and 'no baselines directory at' in out and '0 files validated' in out


def test_main_no_command_direct(capsys):
    code = bl.main([])
    err = capsys.readouterr().err
    assert code == 2 and 'usage: baseline <list|show <name>|validate> [--dir D]' in err


# Twins of the JS CLI edge cases (primitives/js/baseline-cli.test.mjs): both
# CLIs must print identical lines for the same argv.

def test_list_on_regular_file_exits_zero(tmp_path):
    _seed(tmp_path)
    code, out = _run('list', '--dir', str(tmp_path / 'nightly-rate.json'))
    assert code == 0 and 'no baselines directory at' in out


def test_validate_on_regular_file_exits_zero(tmp_path):
    _seed(tmp_path)
    code, out = _run('validate', '--dir', str(tmp_path / 'nightly-rate.json'))
    assert code == 0 and '; 0 files validated' in out


def test_dir_with_no_value_is_a_usage_error():
    code, out = _run('list', '--dir')
    assert code == 2 and 'usage: baseline <list|show <name>|validate> [--dir D]' in out


def test_unknown_subcommand_prints_the_literal_usage_line():
    code, out = _run('bogus')
    assert code == 2 and 'usage: baseline <list|show <name>|validate> [--dir D]' in out


def test_validate_reports_name_not_matching_filename(tmp_path):
    _seed(tmp_path)
    (tmp_path / 'other-name.json').write_text(
        (tmp_path / 'nightly-rate.json').read_text(encoding='utf-8'), encoding='utf-8')
    code, out = _run('validate', '--dir', str(tmp_path))
    assert code == 1 and '✗ other-name.json' in out and 'does not match the filename' in out
