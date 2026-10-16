"""The bundle helper makes a bundle the CLI's own verification accepts."""

from modelhub_testkit.bundles import make_bundle

from modelhub import verify


def test_a_made_bundle_verifies_with_its_public_key_given(tmp_path):
    b = make_bundle(tmp_path)
    assert len(b.pieces()) > 2 and b.description_path.is_file() and b.signature_path.is_file()
    report = verify.verify_bundle([b.directory], trusted=[b.public_key])[0]
    assert report.ok
    assert report.manifest["model"]["id"] == "org/tiny"


def test_a_made_bundle_is_refused_when_its_key_is_not_in_the_list(tmp_path):
    b = make_bundle(tmp_path)
    report = verify.verify_bundle([b.directory], trusted=[])[0]
    assert [p.code for p in report.problems] == ["key-untrusted"]
