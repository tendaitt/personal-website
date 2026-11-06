#!/usr/bin/env python3
"""Build playlists/index.html from playlists.json.

For each Spotify playlist link in playlists.json, this reads the playlist's
public page for its name, description and song count, then writes the
Curated playlists page with a playable Spotify embed for each one.

Usage (from the repository root):
    python3 tools/build_playlists.py
"""
import html
import json
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "playlists.json"
OUTPUT = ROOT / "playlists" / "index.html"
UA = "Mozilla/5.0 (compatible; tendaimudyiwa.com playlist builder)"
MAX_TAGS = 3


def playlist_id(url):
    match = re.search(r"playlist/([A-Za-z0-9]+)", url)
    if not match:
        sys.exit(f"Not a Spotify playlist link: {url}")
    return match.group(1)


def meta(page, attr, name):
    match = re.search(
        rf'<meta {attr}="{re.escape(name)}" content="([^"]*)"', page
    )
    if not match:
        return ""
    # Spotify double-escapes some characters (e.g. &amp;#x2F;).
    return html.unescape(html.unescape(match.group(1))).strip()


def fetch(pid):
    req = urllib.request.Request(
        f"https://open.spotify.com/playlist/{pid}", headers={"User-Agent": UA}
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        page = resp.read().decode("utf-8", "replace")
    title = meta(page, "property", "og:title")
    description = meta(page, "property", "og:description")
    # With no description set, Spotify fills in "Playlist · owner · N items".
    if description.startswith("Playlist ·"):
        description = ""
    songs = meta(page, "name", "music:song_count")
    if not title:
        sys.exit(f"Could not read playlist {pid}: is it public?")
    return {"title": title, "description": description, "songs": songs}


def render(items):
    # Only tags shared by at least two playlists become filters; with none,
    # the filter row stays hidden. Every tag still shows on its playlist.
    counts = {}
    for item in items:
        for t in item["tags"]:
            counts[t] = counts.get(t, 0) + 1
    tags = sorted((t for t, n in counts.items() if n >= 2), key=str.lower)
    rows = []
    for item in items:
        e = html.escape
        desc = (
            f'\n          <p>{e(item["description"])}</p>' if item["description"] else ""
        )
        tag_line = (
            '\n          <ul class="tags" aria-label="Tags">'
            + "".join(f'<li class="chip">{e(t)}</li>' for t in item["tags"])
            + "</ul>"
            if item["tags"]
            else ""
        )
        rows.append(
            f"""        <li data-tags="{e("|".join(item["tags"]))}">
          <h2>{e(item["title"])}</h2>{desc}{tag_line}
          <iframe title="Spotify player: {e(item["title"])}" src="https://open.spotify.com/embed/playlist/{item["id"]}?utm_source=generator" width="100%" height="152" allow="autoplay; clipboard-write; encrypted-media; fullscreen; picture-in-picture" loading="lazy"></iframe>
        </li>"""
        )
    buttons = "\n".join(
        f'        <button type="button" class="chip" data-tag="{html.escape(t)}" aria-pressed="false">{html.escape(t)}</button>'
        for t in tags
    )
    return TEMPLATE.format(buttons=buttons, rows="\n".join(rows))


TEMPLATE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
  <title>Curated playlists · Tendai Mudyiwa</title>
  <meta name="description" content="Playlists curated by Tendai Mudyiwa, playable right on the page.">
  <link rel="canonical" href="https://www.tendaimudyiwa.com/playlists/">
  <link rel="icon" href="/favicon.svg" type="image/svg+xml">
  <meta property="og:type" content="website">
  <meta property="og:title" content="Curated playlists · Tendai Mudyiwa">
  <meta property="og:url" content="https://www.tendaimudyiwa.com/playlists/">
  <meta property="og:image" content="https://www.tendaimudyiwa.com/assets/share-wide.jpg">
  <meta property="og:image:width" content="1200">
  <meta property="og:image:height" content="630">
  <meta property="og:image:alt" content="A black vinyl record with a glowing pink label on a pale wall">
  <meta name="twitter:card" content="summary_large_image">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:ital,wght@0,400;0,700;1,400&display=swap">
  <link rel="stylesheet" href="/style.css">
</head>
<body>
  <div class="page">
    <header>
      <a class="name" href="/">Tendai Mudyiwa</a>
      <nav aria-label="Pages">
        <a href="/">About</a>
        <a href="/playlists/" aria-current="page">Curated playlists</a>
        <a href="/hello/">Say hello</a>
      </nav>
    </header>

    <main>
      <h1>Curated playlists</h1>
      <p>Playlists I've put together. Press play on any of them.</p>

      <div class="filters" role="group" aria-label="Filter by tag" hidden>
        <button type="button" class="chip" data-tag="" aria-pressed="true">all</button>
{buttons}
      </div>

      <ul class="playlists">
{rows}
      </ul>
    </main>
  </div>

  <script>
    (function () {{
      var group = document.querySelector('.filters');
      var buttons = group.querySelectorAll('button');
      var items = document.querySelectorAll('.playlists > li');
      if (buttons.length < 2) return;
      group.hidden = false;
      group.addEventListener('click', function (e) {{
        var btn = e.target.closest('button');
        if (!btn) return;
        var tag = btn.getAttribute('data-tag');
        buttons.forEach(function (b) {{ b.setAttribute('aria-pressed', String(b === btn)); }});
        items.forEach(function (li) {{
          var tags = li.getAttribute('data-tags').split('|');
          li.hidden = !(!tag || tags.indexOf(tag) !== -1);
        }});
      }});
    }})();
  </script>
</body>
</html>
"""


def main():
    entries = json.loads(SOURCE.read_text(encoding="utf-8"))
    items = []
    for entry in entries:
        if len(entry.get("tags", [])) > MAX_TAGS:
            sys.exit(f"Too many tags (max {MAX_TAGS}) for {entry['url']}: {entry['tags']}")
        pid = playlist_id(entry["url"])
        info = fetch(pid)
        # A description in playlists.json is used when Spotify has none.
        if not info["description"] and entry.get("description"):
            info["description"] = entry["description"].strip()
        items.append({"id": pid, "tags": [t.lower() for t in entry.get("tags", [])], **info})
        print(f"  {info['title']} ({info['songs']} songs)")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(render(items), encoding="utf-8")
    print(f"Wrote {OUTPUT.relative_to(ROOT)} with {len(items)} playlists.")


if __name__ == "__main__":
    main()
