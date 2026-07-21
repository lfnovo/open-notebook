"""Tests for the license drift guard (scripts/check_licenses.py).

The guard is only worth having if it actually trips, so its classifier is
tested directly rather than relying on the CI run to prove it works.
"""

import importlib.util
import sys
from pathlib import Path

import pytest

# scripts/ is not a package, so load the module by path. It must be registered
# in sys.modules before exec_module, or @dataclass can't resolve its module.
_SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "check_licenses.py"
_spec = importlib.util.spec_from_file_location("check_licenses", _SCRIPT)
assert _spec and _spec.loader
check_licenses = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = check_licenses
_spec.loader.exec_module(check_licenses)

classify = check_licenses._classify


class TestPermissiveLicensesPass:
    @pytest.mark.parametrize(
        "license_text",
        [
            "MIT",
            "MIT License",
            "BSD-3-Clause",
            "Apache-2.0",
            "ISC",
            "Python Software Foundation License",
            "The Unlicense (Unlicense)",
        ],
    )
    def test_permissive_is_not_a_violation(self, license_text):
        assert classify("some-package", license_text) is None


class TestAgplIsNeverAllowed:
    @pytest.mark.parametrize(
        "license_text",
        [
            "AGPL-3.0",
            "GNU Affero General Public License v3",
            "AGPL-3.0-or-later",
        ],
    )
    def test_agpl_is_always_a_violation(self, license_text):
        reason = classify("some-package", license_text)
        assert reason is not None
        assert "AGPL is never permitted" in reason

    def test_agpl_cannot_be_rescued_by_the_allowlist(self):
        """Even an allowlisted package name is rejected if it turns AGPL."""
        reason = classify("pycountry", "AGPL-3.0")
        assert reason is not None
        assert "AGPL is never permitted" in reason

    def test_agpl_cannot_be_rescued_by_a_permissive_alternative(self):
        """A dual MIT/AGPL offer is still refused — we do not want to depend on
        electing the permissive side for network copyleft."""
        reason = classify("some-package", "MIT OR AGPL-3.0")
        assert reason is not None
        assert "AGPL is never permitted" in reason


class TestUnreviewedCopyleftFails:
    @pytest.mark.parametrize(
        "license_text",
        [
            "GPL-3.0",
            "GPLv2+",
            "GNU General Public License v2 or later (GPLv2+)",
            "LGPL-3.0-or-later",
        ],
    )
    def test_copyleft_on_an_unknown_package_is_a_violation(self, license_text):
        reason = classify("brand-new-package", license_text)
        assert reason is not None
        assert "allowlist" in reason


class TestAllowlist:
    @pytest.mark.parametrize(
        ("package", "license_text"),
        [
            ("pycountry", "LGPL-2.1-only"),
            ("chardet", "GNU Lesser General Public License v2 or later (LGPLv2+)"),
            ("asciidoc", "GNU General Public License v2 or later (GPLv2+)"),
        ],
    )
    def test_reviewed_packages_pass(self, package, license_text):
        assert classify(package, license_text) is None

    @pytest.mark.parametrize(
        "package",
        [
            "@img/sharp-win32-x64",
            "@img/sharp-linux-x64",
            "@img/sharp-darwin-arm64",
        ],
    )
    def test_sharp_platform_variants_all_match_the_prefix_entry(self, package):
        """sharp ships a different binary package per platform, so CI (linux)
        and a Windows dev box see different names for the same allowance."""
        assert classify(package, "Apache-2.0 AND LGPL-3.0-or-later") is None

    def test_every_allowlist_entry_has_a_justification(self):
        for name, allowance in check_licenses.ALLOWED.items():
            assert allowance.reason.strip(), f"{name} has no justification"
            assert len(allowance.reason) > 40, (
                f"{name}'s justification is too thin to have been reviewed"
            )


class TestMultiLicensedPackages:
    def test_permissive_alternative_is_elected(self):
        """docutils is BSD/GPL/Public-Domain — we take the BSD option."""
        assert (
            classify(
                "docutils",
                "BSD License; GNU General Public License (GPL); Public Domain",
            )
            is None
        )

    def test_gpl_only_string_is_not_rescued(self):
        assert classify("mystery-lib", "GPL-3.0-only") is not None


class TestAsciidocStaysUnused:
    """The Dockerfile purges asciidoc (GPLv2+) from the shipped image, which is
    only safe while content-core continues not to use it.

    content-core declares asciidoc as a hard dependency but never imports it.
    If a future version starts actually using it, the purge would ship a broken
    image -- so fail here, at test time, instead of at runtime in a customer's
    deployment. See the purge step in the Dockerfile.
    """

    def _content_core_root(self) -> Path:
        spec = importlib.util.find_spec("content_core")
        assert spec and spec.origin, "content_core is not installed"
        return Path(spec.origin).parent

    def test_content_core_does_not_reference_asciidoc(self):
        root = self._content_core_root()
        offenders = []
        for path in root.rglob("*.py"):
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            if "asciidoc" in text.lower():
                offenders.append(str(path.relative_to(root)))

        assert not offenders, (
            "content-core now references asciidoc in: "
            + ", ".join(offenders)
            + ". The Dockerfile purges asciidoc from the shipped image, which is "
            "no longer safe. Either drop the purge and re-add asciidoc to the "
            "licence allowlist (accepting the GPL redistribution obligation), or "
            "pin content-core to a version that does not use it."
        )

    def test_extraction_entry_points_import_without_asciidoc(self):
        """The API surface this project actually calls must not depend on it."""
        import content_core

        assert hasattr(content_core, "extract_content")
        assert hasattr(content_core, "check_file_support")


class TestNoFalsePositives:
    @pytest.mark.parametrize(
        "license_text",
        [
            "MIT",  # contains no GPL token
            "Apache Software License",
        ],
    )
    def test_unrelated_licenses_do_not_trip_the_regex(self, license_text):
        assert classify("pkg", license_text) is None
