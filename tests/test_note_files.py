"""Files dropped on the notes pane: upload, extraction, serving, cleanup."""

import io
from pathlib import Path
from unittest.mock import AsyncMock, patch

import docx
import pytest
from fastapi.testclient import TestClient

from open_notebook.domain.notebook import Note
from open_notebook.exceptions import NotFoundError
from open_notebook.utils import note_files


@pytest.fixture
def client():
    from api.main import app

    return TestClient(app)


@pytest.fixture(autouse=True)
def files_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(note_files, "NOTE_FILES_FOLDER", str(tmp_path))
    return tmp_path


def _pdf() -> bytes:
    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 200] /Contents 4 0 R "
        b"/Resources << /Font << /F1 5 0 R >> >> >>",
    ]
    stream = b"BT /F1 14 Tf 20 100 Td (Hello PDF world.) Tj ET"
    objs.append(b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream")
    objs.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    out = b"%PDF-1.4\n"
    offsets = []
    for i, obj in enumerate(objs, 1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % i + obj + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1)
    for off in offsets:
        out += b"%010d 00000 n \n" % off
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (
        len(objs) + 1,
        xref,
    )
    return out


def _docx() -> bytes:
    buf = io.BytesIO()
    document = docx.Document()
    document.add_heading("Docx Heading", 1)
    document.add_paragraph("Paragraph from a docx.")
    document.save(buf)
    return buf.getvalue()


HTML = b"<html><body><script>alert(1)</script><h1>Heading</h1><p>Some html text.</p></body></html>"

CASES = [
    ("a.pdf", _pdf(), "application/pdf", "Hello PDF world"),
    ("a.html", HTML, "text/html", "Some html text"),
    ("a.docx", _docx(), note_files.ALLOWED_TYPES[".docx"], "Paragraph from a docx"),
    ("a.txt", b"plain text here", "text/plain", "plain text here"),
    ("a.md", b"# Title\n\nbody", "text/markdown", "body"),
]


def _upload(client, name, data, notebook_id="notebook:n1"):
    return client.post(
        "/api/notes/upload",
        data={"notebook_id": notebook_id},
        files={"file": (name, data, "application/octet-stream")},
    )


@pytest.fixture
def stubs():
    """Stub the database: notebook lookup, note save and linking."""
    with (
        patch("open_notebook.domain.notebook.Notebook.get", new=AsyncMock()),
        patch.object(Note, "save", new=AsyncMock(return_value=None)) as save,
        patch.object(Note, "add_to_notebook", new=AsyncMock()) as link,
    ):
        yield save, link


@pytest.mark.parametrize("name,data,mime,expected", CASES)
def test_upload_extracts_text_and_keeps_original(
    client, stubs, files_dir, name, data, mime, expected
):
    response = _upload(client, name, data)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["title"] == name
    assert expected in body["content"]
    assert body["attachment"] == {"name": name, "type": mime, "size": len(data)}
    stored = list(Path(files_dir).iterdir())
    assert len(stored) == 1
    assert stored[0].read_bytes() == data
    assert stored[0].name != name  # never stored under the user's file name
    assert "alert(1)" not in body["content"]


def test_upload_strips_directories_from_the_file_name(client, stubs):
    response = _upload(client, "../../etc/evil.txt", b"hello")
    assert response.status_code == 200
    assert response.json()["attachment"]["name"] == "evil.txt"


@pytest.mark.parametrize(
    "name,data,status",
    [
        ("run.exe", b"MZ\x90\x00", 415),
        ("noext", b"hello", 415),
        ("fake.pdf", b"not a pdf at all", 400),
        ("fake.docx", b"not a zip", 400),
        ("bin.txt", b"abc\x00def", 400),
        ("empty.txt", b"", 400),
    ],
)
def test_upload_rejects_bad_files_and_stores_nothing(
    client, stubs, files_dir, name, data, status
):
    response = _upload(client, name, data)
    assert response.status_code == status
    assert list(Path(files_dir).iterdir()) == []


def test_upload_to_missing_notebook_is_404_and_stores_nothing(client, files_dir):
    with patch(
        "open_notebook.domain.notebook.Notebook.get",
        new=AsyncMock(side_effect=NotFoundError("nope")),
    ):
        response = _upload(client, "a.txt", b"hello")
    assert response.status_code == 404
    assert list(Path(files_dir).iterdir()) == []


def test_upload_that_fails_to_link_removes_file_and_note(client, files_dir):
    with (
        patch("open_notebook.domain.notebook.Notebook.get", new=AsyncMock()),
        patch.object(Note, "save", new=AsyncMock()),
        patch.object(
            Note, "add_to_notebook", new=AsyncMock(side_effect=RuntimeError("db down"))
        ),
        patch.object(Note, "delete", new=AsyncMock()) as delete,
    ):
        response = _upload(client, "a.txt", b"hello")
    assert response.status_code == 500
    assert list(Path(files_dir).iterdir()) == []
    # The note never got an id in this stub, so nothing to delete.
    delete.assert_not_awaited()


def test_corrupt_pdf_is_a_clean_400(client, stubs, files_dir):
    response = _upload(client, "broken.pdf", b"%PDF-1.4 garbage")
    assert response.status_code == 400
    assert list(Path(files_dir).iterdir()) == []


# --- serving ----------------------------------------------------------------


def _stored_note(files_dir, name, data, mime):
    stored = note_files.write_note_file(data, Path(name).suffix)
    return Note(
        id="note:n1",
        title=name,
        content="text",
        note_type="human",
        attachment_name=name,
        attachment_file=stored,
        attachment_mime=mime,
        attachment_size=len(data),
    )


def test_serve_pdf_inline_with_forced_type(client, files_dir):
    note = _stored_note(files_dir, "a.pdf", _pdf(), "application/pdf")
    with patch("api.routers.notes.Note.get", new=AsyncMock(return_value=note)):
        response = client.get("/api/notes/note:n1/file")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["content-disposition"].startswith("inline")
    assert "content-security-policy" not in response.headers
    assert response.content.startswith(b"%PDF")


def test_serve_html_is_sandboxed(client, files_dir):
    note = _stored_note(files_dir, "a.html", HTML, "text/html")
    with patch("api.routers.notes.Note.get", new=AsyncMock(return_value=note)):
        response = client.get("/api/notes/note:n1/file")
    assert response.headers["content-security-policy"] == "sandbox"


def test_serve_type_comes_from_extension_not_the_stored_mime(client, files_dir):
    note = _stored_note(files_dir, "a.txt", b"hi", "text/html")  # tampered record
    with patch("api.routers.notes.Note.get", new=AsyncMock(return_value=note)):
        response = client.get("/api/notes/note:n1/file")
    assert response.headers["content-type"].startswith("text/plain")


def test_download_flag_sends_attachment(client, files_dir):
    note = _stored_note(files_dir, "a.txt", b"hi", "text/plain")
    with patch("api.routers.notes.Note.get", new=AsyncMock(return_value=note)):
        response = client.get("/api/notes/note:n1/file?download=true")
    assert response.headers["content-disposition"].startswith("attachment")
    assert "a.txt" in response.headers["content-disposition"]


def test_serve_note_without_file_is_404(client):
    note = Note(id="note:n1", title="t", content="c", note_type="human")
    with patch("api.routers.notes.Note.get", new=AsyncMock(return_value=note)):
        assert client.get("/api/notes/note:n1/file").status_code == 404


def test_serve_missing_file_on_disk_is_404(client, files_dir):
    note = _stored_note(files_dir, "a.txt", b"hi", "text/plain")
    Path(files_dir, note.attachment_file or "").unlink()
    with patch("api.routers.notes.Note.get", new=AsyncMock(return_value=note)):
        assert client.get("/api/notes/note:n1/file").status_code == 404


@pytest.mark.parametrize("bad", ["../../etc/passwd", "/etc/passwd", "a.txt", "x" * 32])
def test_stored_name_traversal_is_rejected(client, bad):
    note = Note(
        id="note:n1",
        title="t",
        content="c",
        note_type="human",
        attachment_name="x.txt",
        attachment_file=bad,
    )
    with patch("api.routers.notes.Note.get", new=AsyncMock(return_value=note)):
        assert client.get("/api/notes/note:n1/file").status_code == 400


# --- lifecycle --------------------------------------------------------------


@pytest.mark.asyncio
async def test_deleting_the_note_removes_the_original(files_dir):
    note = _stored_note(files_dir, "a.txt", b"hi", "text/plain")
    assert len(list(Path(files_dir).iterdir())) == 1
    with patch(
        "open_notebook.domain.base.repo_delete", new=AsyncMock(return_value=True)
    ):
        await note.delete()
    assert list(Path(files_dir).iterdir()) == []


def test_note_list_includes_attachment_only_for_file_notes(client, files_dir):
    with_file = _stored_note(files_dir, "a.pdf", _pdf(), "application/pdf")
    plain = Note(id="note:p", title="p", content="c", note_type="human")
    notebook = AsyncMock()
    notebook.get_notes = AsyncMock(return_value=[with_file, plain])
    with patch(
        "open_notebook.domain.notebook.Notebook.get",
        new=AsyncMock(return_value=notebook),
    ):
        body = client.get("/api/notes?notebook_id=notebook:n1").json()
    assert body[0]["attachment"]["name"] == "a.pdf"
    assert body[1]["attachment"] is None
