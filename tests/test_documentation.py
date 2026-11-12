"""Offline checks that repository and installed user-guide links resolve."""

from pathlib import Path
import re
import unittest
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]


def local_link_errors(root, documents):
    errors = []
    for document in documents:
        content = document.read_text(encoding="utf-8")
        # Examples inside fenced or inline code are not documentation links.
        content = re.sub(r"```.*?```", "", content, flags=re.S)
        content = re.sub(r"`[^`\n]+`", "", content)
        for link in re.findall(r"\[[^\]\n]+\]\(([^)\n]+)\)", content):
            parsed = urlsplit(link.strip().strip("<>"))
            if parsed.scheme or parsed.netloc:
                continue  # Never fetch external links during tests.
            target = (document.parent / unquote(parsed.path)).resolve() if parsed.path else document
            if not target.is_relative_to(root) or not target.exists():
                errors.append(f"{document.relative_to(root)}: missing local target {link!r}")
                continue
            if parsed.fragment and target.suffix == ".md":
                headings = []
                for heading in re.findall(r"(?m)^#{1,6}\s+(.+)$", target.read_text(encoding="utf-8")):
                    slug = re.sub(r"[^\w -]", "", heading.lower()).replace(" ", "-")
                    headings.append(slug)
                if unquote(parsed.fragment) not in headings:
                    errors.append(f"{document.relative_to(root)}: missing local heading {link!r}")
    return errors


class DocumentationTests(unittest.TestCase):
    def test_repository_navigation_and_user_guide_links(self):
        pages = [ROOT / name for name in ("README.md", "CHANGELOG.md", "ROADMAP.md", "CONTRIBUTING.md")]
        pages += [ROOT / "docs/memory/README.md"]
        pages += sorted((ROOT / "docs/memory/guides").glob("*.md"))
        self.assertEqual([], local_link_errors(ROOT, pages))


if __name__ == "__main__":
    unittest.main()
