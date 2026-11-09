"""The in-app Wiki must resolve to complete, browseable documentation."""
import re
import unittest
from pathlib import Path
from urllib.parse import unquote
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parents[1]
WIKI = ROOT / "docs/wiki"

class WikiTests(unittest.TestCase):
    def test_required_pages_are_present(self):
        for name in ("Home","Premiers-pas","Installation","Interface","Capteurs","Holo-CPU",
                     "Plugins","Configuration","Mises-a-jour","Architecture","Depannage",
                     "FAQ","Contribuer","_Sidebar","_Footer"):
            with self.subTest(name=name):
                self.assertTrue((WIKI / (name+".md")).is_file())

    def test_local_links_images_and_svg_are_valid(self):
        for source in [ROOT/"README.md", *WIKI.glob("*.md")]:
            txt=source.read_text(encoding="utf-8")
            urls=re.findall(r"\[[^\]\n]*\]\(([^)]+)\)",txt)
            urls+=re.findall(r'<img\s+[^>]*src="([^"]+)"',txt)
            for uri in urls:
                relative=unquote(uri.split("#",1)[0])
                if not relative or re.match(r"^(?:https?://|mailto:)",relative):
                    continue
                if relative.startswith("Executable/") and relative.endswith((".deb",".flatpak")):
                    # CI generates the new versioned binary only AFTER doc unit tests.
                    # The binary assembly job verifies that the files exist.
                    continue
                with self.subTest(page=source.name,uri=relative):
                    self.assertTrue((source.parent/relative).is_file(),str(source)+": "+relative)
        for svg in WIKI.glob("assets/*.svg"):
            with self.subTest(svg=svg.name):
                ElementTree.parse(svg)

    def test_official_wiki_link_points_to_repository_main(self):
        from healthbar.help_links import WIKI_URL
        self.assertEqual(WIKI_URL,
          "https://github.com/florian74410/Health-and-Perfs---Navigation-Controler-Bar/blob/main/docs/wiki/Home.md")
