#!/usr/bin/env python3
"""Check public Git content without ever printing a detected private value."""

import argparse
from pathlib import PurePosixPath
import re
import subprocess
import sys


# These are the existing public demonstration macros, not personal addresses.
PUBLIC_MACROS = {
    "personal_email": "personalemail@gmail.com",
    "spam_email": "spamemail@gmail.com",
}
EMAIL = re.compile(r"[A-Za-z0-9_.+%-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
HOME_PATH = re.compile(r"/(?:Users|home)/[A-Za-z0-9._-]+/")
TOKEN = re.compile(r"(?:github_pat_[A-Za-z0-9_]{20,}|gh[pousr]_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9_-]{24,})")
PRIVATE_KEY = re.compile(r"BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY")


def git(*args):
    return subprocess.check_output(["git", *args], stderr=subprocess.DEVNULL)


def local_patterns():
    try:
        from pathlib import Path
        path = Path(git("rev-parse", "--git-path", "privacy-patterns").decode().strip())
        return [line.strip() for line in path.read_text().splitlines() if line.strip()]
    except (OSError, subprocess.CalledProcessError):
        return []


def private_identity(name, email):
    handle = re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]*|github-actions\[bot\]", name)
    return bool(handle and email.endswith("@users.noreply.github.com"))


def text_issues(text):
    issues = []
    if any(value.casefold() in text.casefold() for value in local_patterns()):
        issues.append("locally protected personal detail")
    for email in EMAIL.findall(text):
        domain = email.rsplit("@", 1)[1].lower()
        if email not in PUBLIC_MACROS.values() and domain != "users.noreply.github.com" and domain not in {"example.com", "example.org", "example.net", "example.invalid"}:
            issues.append("non-example email address")
            break
    for pattern, message in [
        (HOME_PATH, "personal home-directory path"),
        (TOKEN, "credential-like token"),
        (PRIVATE_KEY, "private-key material"),
    ]:
        if pattern.search(text):
            issues.append(message)
    return issues


def macro_issues(text):
    clean = re.sub(r"/\*.*?\*/|//[^\n]*", "", text, flags=re.S)
    count = len(re.findall(r'compatible\s*=\s*"zmk,behavior-macro[^"]*"', clean))
    if re.search(r"\bZMK_MACRO\s*\(", clean):
        return ["unreviewed macro declaration"]
    found = 0
    for node in re.finditer(r"(\w+)\s*:\s*\w+\s*\{([^{}]*)}", clean, re.S):
        label, body = node.groups()
        if not re.search(r'compatible\s*=\s*"zmk,behavior-macro[^"]*"', body):
            continue
        found += 1
        binding = re.search(r"(?<![\w-])bindings\s*=\s*<(.*?)>\s*;", body, re.S)
        if label not in PUBLIC_MACROS or binding is None:
            return ["unreviewed text macro; keep private typing sequences outside Git"]
        values = re.findall(r"&kp\s+(\w+)", binding.group(1))
        remainder = re.sub(r"&kp\s+\w+", "", binding.group(1)).strip()
        if remainder or not values:
            return ["unreviewed macro behavior"]
        chars = []
        for value in values:
            if re.fullmatch(r"[A-Z]", value):
                chars.append(value.lower())
            elif re.fullmatch(r"N[0-9]", value):
                chars.append(value[1:])
            elif value in {"AT", "DOT", "MINUS", "UNDERSCORE"}:
                chars.append({"AT": "@", "DOT": ".", "MINUS": "-", "UNDERSCORE": "_"}[value])
            else:
                return ["unreviewed macro key sequence"]
        if "".join(chars) != PUBLIC_MACROS[label]:
            return ["private or changed text macro; only public examples may be committed"]
    if found != count:
        return ["unrecognized macro structure"]
    return []


def file_issues(path, data):
    name = PurePosixPath(path)
    path_issues = text_issues(path)
    if path_issues:
        return ["private detail in file name; rename it before publishing"]
    if any(part.startswith(".env") or re.search(r"(?:private|secret|credential)", part, re.I) for part in name.parts) or name.suffix.lower() in {".pem", ".p12", ".pfx", ".key", ".uf2", ".bin", ".elf"}:
        return ["private/configuration or compiled-binary file must stay outside Git"]
    if name.suffix.lower() in {".jpg", ".jpeg"}:
        return ["photo contains EXIF/XMP metadata"] if b"Exif\0\0" in data or b"http://ns.adobe.com/xap/1.0/" in data else []
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return ["unreviewed binary file must stay outside Git"]
    issues = text_issues(text)
    if name.suffix in {".keymap", ".dts", ".dtsi", ".overlay", ".h", ".inc"}:
        issues += macro_issues(text)
    return issues


def check_tree(ref=None, staged=False):
    paths = (git("ls-files", "-z") if staged else git("ls-tree", "-r", "--name-only", "-z", ref)).decode().split("\0")
    failures = []
    for path in filter(None, paths):
        try:
            data = git("show", f":{path}" if staged else f"{ref}:{path}")
        except subprocess.CalledProcessError:
            continue  # Staged deletions have no blob.
        # A file name can itself contain the private value. Hide it in reports.
        label = "[file name hidden]" if text_issues(path) else path
        failures += [f"{label}: {issue}" for issue in file_issues(path, data)]
    return failures


def check_commits(revision):
    failures = []
    for sha in git("rev-list", revision).decode().splitlines():
        fields = git("show", "-s", "--format=%an%x00%ae%x00%cn%x00%ce", sha).decode().strip().split("\0")
        if not private_identity(*fields[:2]) or not private_identity(*fields[2:]):
            failures.append(f"commit {sha[:8]}: use a GitHub handle and private noreply identity")
        failures += [f"commit {sha[:8]}: {issue}" for issue in text_issues(git("show", "-s", "--format=%B", sha).decode())]
        failures += check_tree(sha)
    return failures


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--staged", action="store_true")
    parser.add_argument("--ref")
    parser.add_argument("--commits")
    parser.add_argument("--outgoing", action="store_true")
    args = parser.parse_args()
    failures = []
    if args.staged:
        failures += check_tree(staged=True)
        for kind in ("GIT_AUTHOR_IDENT", "GIT_COMMITTER_IDENT"):
            identity = git("var", kind).decode()
            match = re.match(r"(.+) <([^>]+)>", identity)
            if not match or not private_identity(*match.groups()):
                failures.append("Git identity: use your GitHub handle and private noreply address")
    if args.ref:
        failures += check_tree(args.ref)
    if args.commits:
        failures += check_commits(args.commits)
    if args.outgoing:
        for line in sys.stdin:
            _, local, _, remote = line.split()
            if local == "0" * 40:
                continue
            if remote != "0" * 40:
                failures += check_commits(f"{remote}..{local}")
            else:
                for sha in git("rev-list", local, "--not", "--remotes").decode().splitlines():
                    failures += check_commits(f"{sha}^!")
    if failures:
        print("Privacy check blocked this operation. Detected values are intentionally hidden.", file=sys.stderr)
        for failure in sorted(set(failures)):
            print(f"- {failure}", file=sys.stderr)
        return 1
    print("Privacy checks passed; no private values displayed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
