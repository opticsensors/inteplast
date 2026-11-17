from app.ingestion.numbered_marks import proposals


def token(text, x=0.4, y=0.4):
    return {
        "text": text,
        "score": 0.99,
        "polygon": [
            [x - 0.01, y - 0.002],
            [x + 0.01, y - 0.002],
            [x + 0.01, y + 0.002],
            [x - 0.01, y + 0.002],
        ],
    }


def test_no_and_degree_prefixes_are_proposals_but_ranges_notes_and_views_are_not():
    assert not proposals([token("No.001"), token("No.002")], 1)
    assert proposals([token("N° 324")], 2)[0]["candidates"][0]["label"] == "N324"
    assert proposals([token("No. 120 Ø4")], 1)[0]["method"] == "numbered"
    assert not proposals(
        [token("VIEW No. 12"), token("ADDED No.120"), token("No.100 - No.120")], 1
    )
    assert not proposals(
        [
            token("SECTION K-K", y=0.39),
            token("No.1000", y=0.4),
            token("No.1003", y=0.408),
        ],
        1,
    )


def test_numbered_marks_keep_real_marks_elsewhere_and_deduplicate_tile_overlap():
    tokens = [
        token("VIEW M", y=0.39),
        token("No.1300", y=0.4),
        token("No.1304", y=0.408),
        token("No.1304", x=0.7, y=0.7),
        token("No.1304", x=0.7001, y=0.7001),
    ]
    found = proposals(tokens, 3)
    assert len(found) == 1
    assert found[0]["page"] == 3 and found[0]["box"][0] > 0.68
