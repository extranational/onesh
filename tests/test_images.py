from onesh import images


def test_referenced_image_paths_extracts_history_refs(tmp_path):
    image = tmp_path / "clip.png"
    state = {
        "conversations": [
            {
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "describe"},
                            {
                                "type": "image_ref",
                                "image_ref": {
                                    "path": str(image),
                                    "mime_type": "image/png",
                                },
                            },
                        ],
                    }
                ]
            }
        ]
    }

    assert images.referenced_image_paths(state) == {image}


def test_prune_unreferenced_images_keeps_only_history_refs(tmp_path):
    cache = tmp_path / "tmp-images"
    cache.mkdir()
    keep = cache / "keep.png"
    remove = cache / "remove.png"
    note = cache / "note.txt"
    keep.write_bytes(b"keep")
    remove.write_bytes(b"remove")
    note.write_text("not managed", encoding="utf-8")

    images.prune_unreferenced_images(cache, {keep})

    assert keep.exists()
    assert not remove.exists()
    assert note.exists()
