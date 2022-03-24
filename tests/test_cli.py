import io
import os
import re
import subprocess
import sys
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from typing import Optional, Tuple

import pytest

import tempren.cli

project_root_path = os.getcwd()


def run_tempren_process(*args) -> Tuple[str, str, int]:
    """Run tempren with provided arguments as separate process"""
    args = list(map(str, args))
    os.chdir(project_root_path)
    completed_process = subprocess.run(
        [sys.executable, tempren.cli.__file__] + args,
        capture_output=True,
    )

    return (
        completed_process.stdout.decode("utf-8"),
        completed_process.stderr.decode("utf-8"),
        completed_process.returncode,
    )


def run_tempren(*args) -> Tuple[str, str, int]:
    """Run tempren's main() function with provided arguments"""
    args = list(map(str, args))
    old_sys_argv = sys.argv.copy()
    sys.argv[1:] = args
    try:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(stdout):
            with redirect_stderr(stderr):
                error_code = tempren.cli.main()
    finally:
        sys.argv = old_sys_argv

    return stdout.getvalue(), stderr.getvalue(), error_code


class TestVariousFlags:
    def test_version(self):
        stdout, stderr, error_code = run_tempren("--version")

        assert error_code == 0
        assert re.match(r"\d\.\d\.\d", stdout)

    @pytest.mark.parametrize("flag", ["-d", "--dry-run"])
    def test_dry_run(self, text_data_dir: Path, flag: str):
        stdout, stderr, error_code = run_tempren(
            flag, "%Upper(){%Filename()}", text_data_dir
        )

        assert error_code == 0
        assert (text_data_dir / "hello.txt").exists()
        assert not (text_data_dir / "MARKDOWN.MD").exists()
        assert "HELLO.TXT" in stdout
        assert "MARKDOWN.MD" in stdout

    @pytest.mark.parametrize("flag", ["-h", "--help"])
    def test_help(self, flag: str):
        stdout, stderr, error_code = run_tempren(flag)

        assert error_code == 0
        assert "usage: tempren" in stdout

    def test_missing_template_and_input(self):
        stdout, stderr, error_code = run_tempren()

        assert error_code == 2
        assert "usage: tempren" in stderr

    def test_missing_input(self):
        stdout, stderr, error_code = run_tempren("%Upper(){%Filename()}")

        assert error_code == 2
        assert "usage: tempren" in stderr

    @pytest.mark.parametrize("flag", ["-l", "--list-tags"])
    def test_list_tags(self, flag: str):
        stdout, stderr, error_code = run_tempren(flag)
        stdout_lines = list(map(str.strip, stdout.split("\n")))

        assert error_code == 0
        assert any(filter(lambda line: re.match(r"^Count", line), stdout_lines))
        assert any(filter(lambda line: re.match(r"^Upper", line), stdout_lines))
        assert any(filter(lambda line: re.match(r"^Filename", line), stdout_lines))

    @pytest.mark.parametrize("flag", ["-v", "--verbose"])
    def test_verbose_output(self, flag: str):
        stdout, stderr, error_code = run_tempren_process(flag, "--list-tags")

        assert "Verbosity level set to" in stderr


@pytest.mark.parametrize("filter_flag", ["-f", "--filter"])
class TestFilterFlags:
    def test_default_glob_filter(
        self,
        text_data_dir: Path,
        filter_flag: str,
    ):
        stdout, stderr, error_code = run_tempren(
            filter_flag,
            "*.txt",
            "%Upper(){%Filename()}",
            text_data_dir,
        )

        assert error_code == 0
        assert (text_data_dir / "HELLO.TXT").exists()
        assert not (text_data_dir / "MARKDOWN.MD").exists()
        assert not (text_data_dir / "hello.txt").exists()
        assert (text_data_dir / "markdown.md").exists()

    @pytest.mark.parametrize("type_flag", ["-ft", "--filter-type"])
    @pytest.mark.parametrize(
        "filter_type,expression",
        [("glob", "*.txt"), ("regex", r".*\.txt$"), ("template", "%Size() < 50")],
    )
    @pytest.mark.parametrize("invert_flag", ["-fi", "--filter-invert", None])
    def test_filters(
        self,
        text_data_dir: Path,
        type_flag: str,
        filter_type: str,
        expression: str,
        filter_flag: str,
        invert_flag: Optional[str],
    ):
        if invert_flag is None:
            stdout, stderr, error_code = run_tempren(
                type_flag,
                filter_type,
                filter_flag,
                expression,
                "%Upper(){%Filename()}",
                text_data_dir,
            )
        else:
            stdout, stderr, error_code = run_tempren(
                type_flag,
                filter_type,
                invert_flag,
                filter_flag,
                expression,
                "%Upper(){%Filename()}",
                text_data_dir,
            )

        assert error_code == 0
        if invert_flag is None:
            assert (text_data_dir / "HELLO.TXT").exists()
            assert not (text_data_dir / "MARKDOWN.MD").exists()
            assert not (text_data_dir / "hello.txt").exists()
            assert (text_data_dir / "markdown.md").exists()
        else:
            assert not (text_data_dir / "HELLO.TXT").exists()
            assert (text_data_dir / "MARKDOWN.MD").exists()
            assert (text_data_dir / "hello.txt").exists()
            assert not (text_data_dir / "markdown.md").exists()

    @pytest.mark.parametrize("filter_expression", ["%UnknownTag()", "%Size"])
    def test_template_filter_error(
        self, text_data_dir: Path, filter_flag: str, filter_expression: str
    ):
        stdout, stderr, error_code = run_tempren(
            "-ft",
            "template",
            filter_flag,
            filter_expression,
            "%Count().%Ext()",
            text_data_dir,
        )

        assert error_code == 3
        assert "Template error" in stderr


@pytest.mark.parametrize("sort_flag", ["-s", "--sort"])
class TestSortingFlags:
    def test_sorting(self, text_data_dir: Path, sort_flag: str):
        stdout, stderr, error_code = run_tempren(
            sort_flag,
            "%Size()",
            "%Count().%Ext()",
            text_data_dir,
        )

        assert error_code == 0
        assert (text_data_dir / "0.txt").exists()
        assert (text_data_dir / "1.md").exists()

    @pytest.mark.parametrize("invert_flag", ["-si", "--sort-invert"])
    def test_inverted_sorting(
        self, text_data_dir: Path, invert_flag: str, sort_flag: str
    ):
        stdout, stderr, error_code = run_tempren(
            invert_flag,
            sort_flag,
            "%Size()",
            "%Count().%Ext()",
            text_data_dir,
        )

        assert error_code == 0
        assert (text_data_dir / "0.md").exists()
        assert (text_data_dir / "1.txt").exists()

    @pytest.mark.parametrize("sort_expression", ["%UnknownTag()", "%Size,"])
    def test_sort_template_error(
        self, text_data_dir: Path, sort_flag: str, sort_expression: str
    ):
        stdout, stderr, error_code = run_tempren(
            sort_flag,
            sort_expression,
            "%Count().%Ext()",
            text_data_dir,
        )

        assert error_code == 3
        assert "Template error" in stderr


@pytest.mark.parametrize("name_mode_flag", ["-n", "--name", None])
class TestNameMode:
    def test_name_mode(self, text_data_dir: Path, name_mode_flag: str):
        if name_mode_flag is None:
            stdout, stderr, error_code = run_tempren(
                "%Upper(){%Filename()}", text_data_dir
            )
        else:
            stdout, stderr, error_code = run_tempren(
                name_mode_flag, "%Upper(){%Filename()}", text_data_dir
            )

        assert error_code == 0
        assert (text_data_dir / "HELLO.TXT").exists()
        assert (text_data_dir / "MARKDOWN.MD").exists()
        assert not (text_data_dir / "hello.txt").exists()
        assert not (text_data_dir / "markdown.md").exists()

    def test_nonexistent_input(self, nonexistent_path: Path, name_mode_flag: str):
        if name_mode_flag is None:
            stdout, stderr, error_code = run_tempren(
                "%Upper(){%Filename()}", nonexistent_path
            )
        else:
            stdout, stderr, error_code = run_tempren(
                name_mode_flag, "%Upper(){%Filename()}", nonexistent_path
            )

        assert error_code != 0
        assert "doesn't exists" in stderr

    @pytest.mark.parametrize(
        "name_expression", ["%UnknownTag()", "%MissingArgStart)", "%MissingArgEnd("]
    )
    def test_name_template_error(
        self, text_data_dir: Path, name_mode_flag: str, name_expression: str
    ):
        if name_mode_flag is None:
            stdout, stderr, error_code = run_tempren(name_expression, text_data_dir)
        else:
            stdout, stderr, error_code = run_tempren(
                name_mode_flag, name_expression, text_data_dir
            )

        assert error_code == 3
        assert "Template error" in stderr


class TestPathMode:
    pass


# TODO: Test for errors
