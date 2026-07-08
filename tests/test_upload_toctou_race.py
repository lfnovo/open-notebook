"""
Tests for the TOCTOU race fix in generate_unique_filename()
(api/routers/sources.py).

The old implementation checked `if not resolved.exists(): return path` and
left the actual write to a *separate* open(path, "wb") call in
_write_uploaded_file() - "wb" truncates rather than failing, so two
concurrent uploads that computed the same candidate name could both pass
the check and then clobber each other, silently losing one upload.

generate_unique_filename() now atomically claims the name via
Path.touch(exist_ok=False) (O_EXCL under the hood) as part of the search
loop itself, so a losing concurrent caller gets FileExistsError and moves
on to the next candidate instead of racing.

These tests use real OS threads (not asyncio) since the race requires
actual kernel-level interleaving of filesystem syscalls, which release the
GIL - asyncio's single-threaded cooperative concurrency wouldn't exercise it.
"""

import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from api.routers.sources import generate_unique_filename


def old_racy_pattern(upload_folder, original_filename, content, delay=0.02):
    """Standalone repro of the pre-fix check-then-act pattern, with an
    injected delay to reliably widen the race window for testing (real
    concurrent uploads don't need an artificial delay to lose the race -
    this just makes the demonstration deterministic instead of flaky)."""
    file_path = Path(upload_folder)
    stem = Path(original_filename).stem
    suffix = Path(original_filename).suffix
    counter = 0
    while True:
        candidate = (
            original_filename if counter == 0 else f"{stem} ({counter}){suffix}"
        )
        full_path = file_path / candidate
        if not full_path.exists():
            break
        counter += 1
    time.sleep(delay)  # the race window
    with open(full_path, "wb") as f:
        f.write(content)
    return str(full_path)


def new_fixed_pattern(upload_folder, original_filename, content):
    file_path = generate_unique_filename(original_filename, upload_folder)
    with open(file_path, "wb") as f:
        f.write(content)
    return file_path


def run_concurrent_uploads(write_fn, upload_folder, n=8):
    with ThreadPoolExecutor(max_workers=n) as pool:
        futures = [
            pool.submit(
                write_fn, upload_folder, "report.pdf", f"content-{i}".encode()
            )
            for i in range(n)
        ]
        return [f.result() for f in futures]


def distinct_payloads_on_disk(upload_folder):
    return {f.read_bytes() for f in Path(upload_folder).iterdir()}


class TestOldPatternLosesWritesUnderRace:
    """Confirms the vulnerability this fix addresses is real, using a
    standalone repro of the old code (not the current, fixed source)."""

    def test_concurrent_uploads_to_same_name_lose_data(self, tmp_path):
        n = 8
        run_concurrent_uploads(old_racy_pattern, str(tmp_path), n=n)
        payloads = distinct_payloads_on_disk(tmp_path)
        assert len(payloads) < n, (
            "expected the old check-then-act pattern to lose at least one "
            "concurrent write to a real race"
        )


class TestFixedGenerateUniqueFilenameSurvivesRace:
    def test_concurrent_uploads_to_same_name_all_survive(self, tmp_path):
        n = 8
        run_concurrent_uploads(new_fixed_pattern, str(tmp_path), n=n)
        files = list(tmp_path.iterdir())
        payloads = distinct_payloads_on_disk(tmp_path)
        assert len(files) == n, f"expected {n} files, got {len(files)}"
        assert len(payloads) == n, (
            f"expected all {n} distinct payloads preserved, got {len(payloads)}"
        )

    def test_claimed_path_exists_and_is_empty_immediately(self, tmp_path):
        """The function itself must create the file (not just check for
        its absence) - proving the claim is atomic with the check."""
        path = generate_unique_filename("doc.txt", str(tmp_path))
        assert Path(path).exists()
        assert Path(path).stat().st_size == 0

    def test_sequential_calls_still_increment_correctly(self, tmp_path):
        path1 = generate_unique_filename("doc.txt", str(tmp_path))
        Path(path1).write_bytes(b"first")
        path2 = generate_unique_filename("doc.txt", str(tmp_path))
        Path(path2).write_bytes(b"second")
        path3 = generate_unique_filename("doc.txt", str(tmp_path))

        assert Path(path1).name == "doc.txt"
        assert Path(path2).name == "doc (1).txt"
        assert Path(path3).name == "doc (2).txt"

    def test_pre_existing_file_is_skipped(self, tmp_path):
        (tmp_path / "existing.txt").write_bytes(b"already here")
        path = generate_unique_filename("existing.txt", str(tmp_path))
        assert Path(path).name == "existing (1).txt"

    def test_directory_components_are_stripped_not_traversed(self, tmp_path):
        """os.path.basename() strips directory components from the
        original filename before the traversal check ever runs - e.g.
        "../../etc/passwd" becomes just "passwd", confined to tmp_path."""
        path = generate_unique_filename("../../etc/passwd", str(tmp_path))
        assert Path(path).parent == tmp_path.resolve()
        assert Path(path).name == "passwd"
