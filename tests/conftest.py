import shutil
from pathlib import Path
from typing import Callable

import pytest
from _pytest.tmpdir import TempPathFactory

from tempren.path_generator import File


@pytest.fixture
def nonexistent_path() -> Path:
    return Path("nonexistent", "path")


@pytest.fixture
def nonexistent_absolute_path() -> Path:
    return Path("/nonexistent/path")


@pytest.fixture
def nonexistent_file(nonexistent_absolute_path: Path) -> File:
    return File(nonexistent_absolute_path, Path("some.file"))


@pytest.fixture
def test_data_dir(tmp_path_factory: TempPathFactory) -> Callable[[str], Path]:
    root_test_data_path = Path(__file__).parent / "test_data"

    def data_directory_generator(data_type: str) -> Path:
        """Creates a copy of one of directories under test_data root dir"""
        source_path = root_test_data_path / data_type
        if not source_path.is_dir():
            raise ValueError(f"Test data directory '{source_path}' doesn't exists")
        directory_copy = tmp_path_factory.mktemp(data_type)
        shutil.rmtree(directory_copy, ignore_errors=True)
        shutil.copytree(source_path, directory_copy)

        yield directory_copy

        shutil.rmtree(directory_copy)

    return data_directory_generator


@pytest.fixture
def hidden_data_dir(test_data_dir: Callable[[str], Path]) -> Path:
    yield from test_data_dir("hidden")


@pytest.fixture
def nested_data_dir(test_data_dir: Callable[[str], Path]) -> Path:
    yield from test_data_dir("nested")


@pytest.fixture
def tags_data_dir(test_data_dir: Callable[[str], Path]) -> Path:
    yield from test_data_dir("tags")


@pytest.fixture
def text_data_dir(test_data_dir: Callable[[str], Path]) -> Path:
    yield from test_data_dir("text")


@pytest.fixture
def audio_data_dir(test_data_dir: Callable[[str], Path]) -> Path:
    yield from test_data_dir("audio")


@pytest.fixture
def image_data_dir(test_data_dir: Callable[[str], Path]) -> Path:
    yield from test_data_dir("image")


@pytest.fixture
def video_data_dir(test_data_dir: Callable[[str], Path]) -> Path:
    yield from test_data_dir("video")
