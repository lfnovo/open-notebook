from open_notebook.multimodal.detector import is_video_source


def test_detects_video_by_extension():
    assert is_video_source(url="https://example.com/demo.mp4")
    assert is_video_source(file_path="/tmp/video.MOV")


def test_detects_video_by_known_host():
    assert is_video_source(url="https://www.youtube.com/watch?v=abc123")


def test_ignores_non_video_sources():
    assert not is_video_source(url="https://example.com/doc.pdf")
    assert not is_video_source(file_path="/tmp/notes.txt")
