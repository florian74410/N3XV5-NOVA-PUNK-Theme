"""Canonical official public Wiki destination used by all installers."""
REPO_URL = "https://github.com/florian74410/Health-and-Perfs---Navigation-Controler-Bar"
WIKI_URL = "https://github.com/florian74410/Health-and-Perfs---Navigation-Controler-Bar/blob/main/docs/wiki/Home.md"

DOC_LINKS = {"README": REPO_URL + "/blob/main/README.md", "Wiki": WIKI_URL,
    **{name: REPO_URL + "/blob/main/docs/wiki/" + name + ".md"
       for name in ("Installation", "Configuration", "Plugins", "Depannage", "Architecture")}}
