from abc import ABC, abstractmethod
from pathlib import Path

import pytest

from tempren.filesystem import (
    DryRunRenamer,
    FileGatherer,
    FileMover,
    FileRenamer,
    FlatFileGatherer,
    InvalidDestinationError,
    RecursiveFileGatherer,
)
from tempren.path_generator import File


def file_to_absolute_path(file: File) -> Path:
    return file.absolute_path


class FilesystemFileGathererTests(ABC):
    @abstractmethod
    def create_gatherer(self) -> FileGatherer:
        raise NotImplementedError()

    def test_empty_directory(self, tmp_path: Path):
        gatherer = self.create_gatherer()

        file_iterator = iter(gatherer.gather_in(tmp_path))

        with pytest.raises(StopIteration):
            next(file_iterator)

    def test_flat_directory(self, text_data_dir: Path):
        gatherer = self.create_gatherer()

        files = set(map(file_to_absolute_path, gatherer.gather_in(text_data_dir)))

        test_files = {
            text_data_dir / "hello.txt",
            text_data_dir / "markdown.md",
        }
        assert files == test_files

    def test_returned_files_are_relative_to_input_directory(self, text_data_dir: Path):
        gatherer = self.create_gatherer()

        files = list(gatherer.gather_in(text_data_dir))

        for file in files:
            assert file.input_directory == text_data_dir

    def test_hidden_files_are_skipped_by_default(self, hidden_data_dir: Path):
        gatherer = self.create_gatherer()

        files = set(map(file_to_absolute_path, gatherer.gather_in(hidden_data_dir)))

        test_files = {
            hidden_data_dir / "visible.txt",
        }
        assert files == test_files


class TestFlatFileGatherer(FilesystemFileGathererTests):
    def create_gatherer(self) -> FileGatherer:
        return FlatFileGatherer()

    def test_hidden_files_can_be_found_with_include_hidden(self, hidden_data_dir: Path):
        gatherer = self.create_gatherer()
        gatherer.include_hidden = True

        files = set(map(file_to_absolute_path, gatherer.gather_in(hidden_data_dir)))

        test_files = {
            hidden_data_dir / ".hidden.txt",
            hidden_data_dir / "visible.txt",
        }
        assert files == test_files

    def test_nested_files(self, nested_data_dir: Path):
        gatherer = self.create_gatherer()

        files = set(map(file_to_absolute_path, gatherer.gather_in(nested_data_dir)))

        test_files = {
            nested_data_dir / "level-1.file",
        }
        assert files == test_files


class TestRecursiveFileGatherer(FilesystemFileGathererTests):
    def create_gatherer(self) -> FileGatherer:
        return RecursiveFileGatherer()

    def test_hidden_files_can_be_found_with_include_hidden(self, hidden_data_dir: Path):
        gatherer = self.create_gatherer()
        gatherer.include_hidden = True

        files = set(map(file_to_absolute_path, gatherer.gather_in(hidden_data_dir)))

        test_files = {
            hidden_data_dir / ".hidden.txt",
            hidden_data_dir / "visible.txt",
            hidden_data_dir / ".hidden" / ".nested_hidden.txt",
            hidden_data_dir / ".hidden" / "nested_visible.txt",
        }
        assert files == test_files

    def test_nested_files(self, nested_data_dir: Path):
        gatherer = self.create_gatherer()

        files = set(map(file_to_absolute_path, gatherer.gather_in(nested_data_dir)))

        test_files = {
            nested_data_dir / "level-1.file",
            nested_data_dir / "first" / "level-2.file",
            nested_data_dir / "second" / "level-2.file",
            nested_data_dir / "second" / "third" / "level-3.file",
        }
        assert files == test_files


class TestFileRenamer:
    def test_simple_file(self, text_data_dir: Path):
        src = text_data_dir / "hello.txt"
        assert src.is_file()
        dst = text_data_dir / "hi.txt"
        assert not dst.exists()
        renamer = FileRenamer()

        renamer(src, dst)

        assert dst.exists()

    def test_simple_directory(self, nested_data_dir: Path):
        src = nested_data_dir / "first"
        assert src.is_dir()
        dst = nested_data_dir / "fourth"
        assert not dst.exists()
        renamer = FileRenamer()

        renamer(src, dst)

        assert dst.exists()

    def test_source_doesnt_exists(self, text_data_dir: Path):
        src = text_data_dir / "goodbye.txt"
        assert not src.exists()
        dst = text_data_dir / "bye.md"
        renamer = FileRenamer()

        with pytest.raises(FileNotFoundError) as exc:
            renamer(src, dst)
        assert exc.match(str(src))

    def test_destination_file_exists(self, text_data_dir: Path):
        src = text_data_dir / "hello.txt"
        dst = text_data_dir / "markdown.md"
        assert dst.exists()
        renamer = FileRenamer()

        with pytest.raises(FileExistsError) as exc:
            renamer(src, dst)
        assert exc.match(str(dst))

    def test_destination_is_directory(self, nested_data_dir: Path):
        src = nested_data_dir / "level-1.file"
        dst = nested_data_dir / "first"
        assert dst.is_dir()
        renamer = FileRenamer()

        with pytest.raises(FileExistsError) as exc:
            renamer(src, dst)
        assert exc.match(str(dst))

    def test_destination_contains_subdirectory(self, text_data_dir: Path):
        # CHECK: maybe this directory check could be done on the pipeline level?
        src = text_data_dir / "hello.txt"
        dst = text_data_dir / "first" / "markdown.md"
        renamer = FileRenamer()

        with pytest.raises(InvalidDestinationError) as exc:
            renamer(src, dst)
        assert exc.match(str(dst))

    def test_override_destination_file(self, text_data_dir: Path):
        src = text_data_dir / "hello.txt"
        dst = text_data_dir / "markdown.md"
        assert dst.exists()
        renamer = FileRenamer()

        renamer(src, dst, True)

        assert not src.exists()
        assert dst.exists()


class TestFileMover:
    def test_simple_file(self, text_data_dir: Path):
        src = text_data_dir / "hello.txt"
        assert src.is_file()
        dst = text_data_dir / "hi.txt"
        assert not dst.exists()
        mover = FileMover()

        mover(src, dst)

        assert dst.exists()
        assert not src.exists()

    def test_source_doesnt_exists(self, text_data_dir: Path):
        src = text_data_dir / "goodbye.txt"
        assert not src.exists()
        dst = text_data_dir / "bye.md"
        mover = FileMover()

        with pytest.raises(FileNotFoundError) as exc:
            mover(src, dst)
        assert exc.match(str(src))

    def test_destination_file_exists(self, text_data_dir: Path):
        src = text_data_dir / "hello.txt"
        dst = text_data_dir / "markdown.md"
        assert dst.exists()
        mover = FileMover()

        with pytest.raises(FileExistsError) as exc:
            mover(src, dst)
        assert exc.match(str(dst))

    def test_destination_is_directory(self, nested_data_dir: Path):
        src = nested_data_dir / "level-1.file"
        dst = nested_data_dir / "first"
        assert dst.is_dir()
        mover = FileMover()

        with pytest.raises(FileExistsError) as exc:
            mover(src, dst)
        assert exc.match(str(dst))

    def test_create_single_directory(self, nested_data_dir: Path):
        src = nested_data_dir / "level-1.file"
        nonexistent_dir = nested_data_dir / "nonexistent"
        dst = nonexistent_dir / "level-1.file"
        assert not nonexistent_dir.exists()
        mover = FileMover()

        mover(src, dst)

        assert nonexistent_dir.exists()
        assert dst.exists()

    def test_create_path_part_directory(self, nested_data_dir: Path):
        src = nested_data_dir / "second" / "level-2.file"
        nonexistent_dir = nested_data_dir / "second" / "nonexistent"
        dst = nonexistent_dir / "level-2.file"
        assert not nonexistent_dir.exists()
        mover = FileMover()

        mover(src, dst)

        assert nonexistent_dir.exists()
        assert dst.exists()

    def test_create_multiple_directories(self, nested_data_dir: Path):
        src = nested_data_dir / "level-1.file"
        nonexistent_dir = nested_data_dir / "a" / "b" / "c"
        dst = nonexistent_dir / "level-1.file"
        assert not nonexistent_dir.exists()
        mover = FileMover()

        mover(src, dst)

        assert nonexistent_dir.exists()
        assert dst.exists()

    def test_create_already_existing_directory(self, nested_data_dir: Path):
        src = nested_data_dir / "level-1.file"
        existing_dir = nested_data_dir / "second"
        dst = existing_dir / "level-1.file"
        assert existing_dir.exists()
        mover = FileMover()

        mover(src, dst)

        assert existing_dir.exists()
        assert dst.exists()

    def test_override_destination_file(self, text_data_dir: Path):
        src = text_data_dir / "hello.txt"
        dst = text_data_dir / "markdown.md"
        assert dst.exists()
        mover = FileMover()

        mover(src, dst, True)

        assert not src.exists()
        assert dst.exists()


class TestDryRunRenamer:
    def test_simple_file(self, text_data_dir: Path):
        src = text_data_dir / "hello.txt"
        assert src.is_file()
        dst = text_data_dir / "hi.txt"
        assert not dst.exists()
        renamer = DryRunRenamer()

        renamer(src, dst)

        assert not dst.exists()

    def test_simple_directory(self, nested_data_dir: Path):
        src = nested_data_dir / "first"
        assert src.is_dir()
        dst = nested_data_dir / "fourth"
        assert not dst.exists()
        renamer = DryRunRenamer()

        renamer(src, dst)

        assert not dst.exists()

    def test_source_doesnt_exists(self, text_data_dir: Path):
        src = text_data_dir / "goodbye.txt"
        assert not src.exists()
        dst = text_data_dir / "bye.md"
        renamer = DryRunRenamer()

        with pytest.raises(FileNotFoundError) as exc:
            renamer(src, dst)
        assert exc.match(str(src))

    def test_source_exists_from_previous_run(self, text_data_dir: Path):
        src = text_data_dir / "hello.txt"
        assert src.exists()
        dst = text_data_dir / "bye.md"
        renamer = DryRunRenamer()

        renamer(src, dst)

        src = dst
        dst = text_data_dir / "hi.txt"

        renamer(src, dst)

    def test_transient_state(self, text_data_dir: Path):
        src = text_data_dir / "hello.txt"
        assert src.exists()
        dst = text_data_dir / "bye.md"
        renamer = DryRunRenamer()

        renamer(src, dst)

        src = dst
        dst = text_data_dir / "hello.txt"

        renamer(src, dst)

    def test_destination_file_exists(self, text_data_dir: Path):
        src = text_data_dir / "hello.txt"
        dst = text_data_dir / "markdown.md"
        assert dst.exists()
        renamer = DryRunRenamer()

        with pytest.raises(FileExistsError) as exc:
            renamer(src, dst)
        assert exc.match(str(dst))

    def test_destination_exists_from_previous_run(self, text_data_dir: Path):
        src = text_data_dir / "hello.txt"
        dst = text_data_dir / "goodbye.txt"
        assert not dst.exists()
        renamer = DryRunRenamer()

        renamer(src, dst)
        src = text_data_dir / "markdown.md"

        with pytest.raises(FileExistsError) as exc:
            renamer(src, dst)
        assert exc.match(str(dst))

    def test_destination_is_directory(self, nested_data_dir: Path):
        src = nested_data_dir / "level-1.file"
        dst = nested_data_dir / "first"
        assert dst.is_dir()
        renamer = DryRunRenamer()

        with pytest.raises(FileExistsError) as exc:
            renamer(src, dst)
        assert exc.match(str(dst))

    def test_override_destination_file(self, text_data_dir: Path):
        src = text_data_dir / "hello.txt"
        dst = text_data_dir / "markdown.md"
        assert dst.exists()
        renamer = DryRunRenamer()

        renamer(src, dst, True)

        assert src.exists()
        assert dst.exists()
