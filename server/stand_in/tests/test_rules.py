"""Name, path and revision rules of the stand-in (rules BR1.2, BR1.4, BR1.15)."""

import pytest
from modelhub_stand_in.rules import (
    commit_hash,
    is_commit_hash,
    safe_relative_path,
    validate_names,
)


@pytest.mark.parametrize(
    "org,model,revision",
    [
        ("acme", "tiny-llama", "main"),
        ("a-b-c", "Model_1.2", "v1.0-rc1"),
        ("acme2", "m", "0123456789abcdef0123456789abcdef01234567"),
    ],
)
def test_good_names_pass(org, model, revision):
    assert validate_names(org, model, revision) is None


@pytest.mark.parametrize(
    "org",
    ["-acme", "acme-", "ac--me", "12345", "ac_me", "ac.me", ""],
)
def test_bad_organisations_name_the_field(org):
    problem = validate_names(org, "m", "main")
    assert problem is not None and "organisation" in problem


@pytest.mark.parametrize("model", ["a b", "a/b", "a@b", ""])
def test_bad_models_name_the_field(model):
    problem = validate_names("acme", model, "main")
    assert problem is not None and "model" in problem


@pytest.mark.parametrize("revision", ["a_b", "a/b", "a b", ""])
def test_bad_revisions_name_the_field(revision):
    problem = validate_names("acme", "m", revision)
    assert problem is not None and "revision" in problem


@pytest.mark.parametrize(
    "path", ["a.txt", "dir/b.bin", "d1/d2/c.json", "with space/ünï.txt", "x" * 200]
)
def test_safe_paths_pass(path):
    assert safe_relative_path(path)


@pytest.mark.parametrize(
    "path",
    ["", "/abs", "../up", "a/../b", "a\\b", "C:/x", "a//b", "./a", "a/./b", "a/", "c:\\x"],
)
def test_unsafe_paths_are_refused(path):
    assert not safe_relative_path(path)


def test_the_commit_hash_is_40_hex_and_does_not_depend_on_file_order():
    a = commit_hash([("b.txt", "11" * 32), ("a.txt", "22" * 32)])
    b = commit_hash([("a.txt", "22" * 32), ("b.txt", "11" * 32)])
    assert a == b and is_commit_hash(a) and len(a) == 40


def test_the_commit_hash_changes_with_the_content():
    assert commit_hash([("a", "11" * 32)]) != commit_hash([("a", "22" * 32)])


def test_is_commit_hash():
    assert is_commit_hash("a" * 40)
    assert not is_commit_hash("main")
    assert is_commit_hash("A" * 40)
    assert not is_commit_hash("g" * 40)
