"""Tests use synthetic private values and never print detected contents."""

import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

MODULE = Path(__file__).resolve().parents[1] / "scripts/check_privacy.py"
SPEC = importlib.util.spec_from_file_location("privacy_guard", MODULE)
GUARD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GUARD)


class PrivacyTests(unittest.TestCase):
    def test_committed_public_files_pass_the_privacy_check(self):
        self.assertFalse(GUARD.check_tree("HEAD"), "Committed public content failed privacy validation; values hidden")

    def test_public_examples_and_project_urls_are_allowed(self):
        self.assertFalse(GUARD.text_issues("https://github.com/project/repo"))
        self.assertFalse(GUARD.text_issues("demo@example.invalid"))

    def test_personal_email_is_blocked_without_echoing_it(self):
        value = "private.person" + "@" + "mail-provider.com"
        issues = GUARD.text_issues(value)
        self.assertTrue(issues)
        self.assertFalse(any(value in issue for issue in issues))

    def test_home_path_is_blocked_without_echoing_it(self):
        value = "/" + "Users" + "/" + "private-person/config"
        issues = GUARD.text_issues(value)
        self.assertTrue(issues)
        self.assertFalse(any(value in issue for issue in issues))

    def test_tokens_and_private_keys_are_blocked(self):
        self.assertTrue(GUARD.text_issues("ghp_" + "A" * 36))
        self.assertTrue(GUARD.text_issues("-----BEGIN " + "OPENSSH PRIVATE KEY-----"))

    def test_private_files_and_firmware_binaries_are_blocked(self):
        for path in ("config/private-macros.dtsi", "private/notes.txt", ".env", "backup.uf2", "signing.pem"):
            with self.subTest(path=path):
                self.assertTrue(GUARD.file_issues(path, b""))

    def test_private_file_name_is_blocked_and_hidden_in_reports(self):
        value = "private.person" + "@" + "mail-provider.com"
        path = "config/" + value + ".txt"
        with patch.object(GUARD, "local_patterns", return_value=[]), patch.object(
            GUARD, "git", side_effect=[(path + "\0").encode(), b"ordinary content"]
        ):
            issues = GUARD.check_tree("HEAD")
        self.assertTrue(issues)
        self.assertFalse(any(value in issue for issue in issues))

    def test_macro_in_header_or_devicetree_is_also_checked(self):
        value = b'example: example { compatible = "zmk,behavior-macro"; bindings = <&kp X>; };'
        for suffix in (".keymap", ".dts", ".dtsi", ".overlay", ".h", ".inc"):
            with self.subTest(suffix=suffix):
                self.assertTrue(GUARD.file_issues("config/macros" + suffix, value))

    def test_photo_metadata_is_blocked(self):
        self.assertTrue(GUARD.file_issues("photo.jpg", b"JPEG" + b"Exif\0\0"))
        self.assertFalse(GUARD.file_issues("photo.jpg", b"JPEG image bytes"))

    def test_unreviewed_binary_documents_are_blocked(self):
        self.assertTrue(GUARD.file_issues("document.pdf", b"PDF" + bytes([255, 254])))

    def test_current_public_keymap_macros_are_allowed(self):
        text = (MODULE.parents[1] / "config/eyelash_sofle.keymap").read_text()
        self.assertFalse(GUARD.macro_issues(text))

    def test_changed_typing_macro_is_blocked_without_echoing_it(self):
        text = (MODULE.parents[1] / "config/eyelash_sofle.keymap").read_text()
        # Change the first macro payload while keeping it valid ZMK syntax.
        changed = text.replace("bindings = <&kp P", "bindings = <&kp X", 1)
        self.assertNotEqual(text, changed)
        issues = GUARD.macro_issues(changed)
        self.assertTrue(issues)
        self.assertFalse(any("bindings" in issue for issue in issues))

    def test_private_git_identity_is_required(self):
        self.assertTrue(GUARD.private_identity("example-user", "123+example-user@users.noreply.github.com"))
        self.assertFalse(GUARD.private_identity("Real Person", "private" + "@" + "mail-provider.com"))


if __name__ == "__main__":
    unittest.main()
