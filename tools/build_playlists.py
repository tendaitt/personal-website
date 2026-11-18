#!/usr/bin/env python3
"""Build playlists/index.html from playlists.json.

For each Spotify playlist link in playlists.json, this reads the playlist's
public page for its name and description, and Spotify's oEmbed endpoint for
its cover art. It then writes the Curated playlists page: a grid of covers,
newest first, a mood filter, a "Surprise me" button and one Spotify player
pinned to the bottom of the screen.

Add new playlists to the END of playlists.json; the page shows them first.

Usage (from the repository root):
    python3 tools/build_playlists.py
"""
import html
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "playlists.json"
OUTPUT = ROOT / "playlists" / "index.html"
UA = "Mozilla/5.0 (compatible; tendaimudyiwa.com playlist builder)"
MAX_TAGS = 3
MOODS = ["dance", "focus", "reminisce", "chill", "feel things"]


def playlist_id(url):
    match = re.search(r"playlist/([A-Za-z0-9]+)", url)
    if not match:
        sys.exit(f"Not a Spotify playlist link: {url}")
    return match.group(1)


def get(url):
    """Fetch a URL, retrying a couple of times: Spotify sometimes times out."""
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=30) as resp:
                return resp.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as err:
            if err.code < 500 or attempt == 2:
                raise
        except urllib.error.URLError:
            if attempt == 2:
                raise
        time.sleep(2 * (attempt + 1))


def meta(page, attr, name):
    match = re.search(
        rf'<meta {attr}="{re.escape(name)}" content="([^"]*)"', page
    )
    if not match:
        return ""
    # Spotify double-escapes some characters (e.g. &amp;#x2F;).
    return html.unescape(html.unescape(match.group(1))).strip()


def fetch(pid):
    try:
        page = get(f"https://open.spotify.com/playlist/{pid}")
    except urllib.error.HTTPError as err:
        sys.exit(f"Could not read playlist {pid} (HTTP {err.code}): is it public?")
    title = meta(page, "property", "og:title")
    description = meta(page, "property", "og:description")
    # With no description set, Spotify fills in "Playlist · owner · N items".
    if description.startswith("Playlist ·"):
        description = ""
    if not title:
        sys.exit(f"Could not read playlist {pid}: is it public?")
    link = urllib.parse.quote(f"https://open.spotify.com/playlist/{pid}", safe="")
    cover = json.loads(get(f"https://open.spotify.com/oembed?url={link}")).get(
        "thumbnail_url", ""
    )
    return {"title": title, "description": description, "cover": cover}


def render(items):
    e = html.escape
    cards = []
    for item in items:
        url = f"https://open.spotify.com/playlist/{item['id']}"
        cards.append(
            f"""        <li data-id="{item['id']}" data-moods="{e("|".join(item["moods"]))}" data-desc="{e(item["description"])}">
          <a href="{url}" aria-label="Play {e(item["title"])}">
            <span class="cover"><img src="{e(item["cover"])}" alt="" width="300" height="300" loading="lazy"><span class="playing">Playing</span></span>
            <span class="title">{e(item["title"])}</span>
            <span class="tagline">{e(" · ".join(item["tags"]))}</span>
          </a>
        </li>"""
        )
    first = items[0]
    moods = "\n".join(
        f'        <button type="button" class="chip" data-mood="{e(m)}" aria-pressed="false">{e(m)}</button>'
        for m in MOODS
        if any(m in item["moods"] for item in items)
    )
    return TEMPLATE.format(
        moods=moods,
        cards="\n".join(cards),
        first_id=first["id"],
        first_title=e(first["title"]),
        first_desc=e(first["description"]),
    )


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
<body class="has-player">
  <div class="page wide">
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
      <p>Playlists I've put together. Press play and enjoy!</p>

      <div class="toolbar">
        <button type="button" class="surprise" hidden>
          <svg aria-hidden="true" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M16 3h5v5"/><path d="M4 20 21 3"/><path d="M21 16v5h-5"/><path d="M15 15l6 6"/><path d="M4 4l5 5"/></svg>
          Surprise me
        </button>
        <span class="divider" aria-hidden="true" hidden></span>
        <div class="filters" role="group" aria-label="Filter by mood" hidden>
        <button type="button" class="chip" data-mood="" aria-pressed="true">all</button>
{moods}
        </div>
      </div>

      <ul class="crate">
{cards}
      </ul>
    </main>
  </div>

  <aside class="player" aria-label="Player">
    <div class="player-inner">
      <p class="now"><strong>{first_title}</strong> <span>{first_desc}</span></p>
      <div class="embed"><iframe id="player-frame" title="Spotify player" src="https://open.spotify.com/embed/playlist/{first_id}?utm_source=generator" width="100%" height="80" allow="autoplay; clipboard-write; encrypted-media; fullscreen; picture-in-picture" loading="lazy"></iframe></div>
    </div>
  </aside>

  <script>
    (function () {{
      var items = [].slice.call(document.querySelectorAll('.crate > li'));
      var nowTitle = document.querySelector('.player .now strong');
      var nowDesc = document.querySelector('.player .now span');
      var frame = document.getElementById('player-frame');
      var api = null, controller = null, playWhenReady = false;

      window.onSpotifyIframeApiReady = function (IFrameAPI) {{ api = IFrameAPI; }};
      var s = document.createElement('script');
      s.src = 'https://open.spotify.com/embed/iframe-api/v1';
      s.async = true;
      document.body.appendChild(s);

      function mark(li) {{
        items.forEach(function (x) {{
          var a = x.querySelector('a');
          if (x === li) a.setAttribute('aria-current', 'true'); else a.removeAttribute('aria-current');
        }});
        nowTitle.textContent = li.querySelector('.title').textContent;
        nowDesc.textContent = li.getAttribute('data-desc');
      }}

      function play(li) {{
        mark(li);
        var id = li.getAttribute('data-id');
        var uri = 'spotify:playlist:' + id;
        if (controller) {{
          playWhenReady = true;
          controller.loadUri(uri);
          return;
        }}
        if (api) {{
          var holder = document.createElement('div');
          frame.parentNode.replaceChild(holder, frame);
          api.createController(holder, {{ uri: uri, width: '100%', height: 80 }}, function (c) {{
            controller = c;
            c.addListener('ready', function () {{
              if (playWhenReady) {{ playWhenReady = false; c.play(); }}
            }});
            playWhenReady = true;
          }});
          return;
        }}
        frame.src = 'https://open.spotify.com/embed/playlist/' + id + '?utm_source=generator';
      }}

      items.forEach(function (li) {{
        li.querySelector('a').addEventListener('click', function (e) {{
          if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
          e.preventDefault();
          play(li);
        }});
      }});
      if (items.length) mark(items[0]);

      var surprise = document.querySelector('.surprise');
      surprise.hidden = false;
      surprise.addEventListener('click', function () {{
        var current = document.querySelector('.crate a[aria-current]');
        var pool = items.filter(function (li) {{ return !li.hidden && li.querySelector('a') !== current; }});
        if (!pool.length) pool = items.filter(function (li) {{ return li.querySelector('a') !== current; }});
        var pick = pool[Math.floor(Math.random() * pool.length)];
        play(pick);
        pick.scrollIntoView({{ block: 'nearest', behavior: 'smooth' }});
      }});

      var group = document.querySelector('.filters');
      var buttons = group.querySelectorAll('button');
      if (buttons.length > 1) {{
        group.hidden = false;
        document.querySelector('.toolbar .divider').hidden = false;
        group.addEventListener('click', function (e) {{
          var btn = e.target.closest('button');
          if (!btn) return;
          var mood = btn.getAttribute('data-mood');
          buttons.forEach(function (b) {{ b.setAttribute('aria-pressed', String(b === btn)); }});
          items.forEach(function (li) {{
            li.hidden = !!mood && li.getAttribute('data-moods').split('|').indexOf(mood) === -1;
          }});
        }});
      }}
    }})();
  </script>
  <script data-goatcounter="https://tendaimudyiwa.goatcounter.com/count" async src="https://gc.zgo.at/count.js"></script>
</body>
</html>
"""


def main():
    entries = json.loads(SOURCE.read_text(encoding="utf-8"))
    items = []
    for entry in entries:
        if len(entry.get("tags", [])) > MAX_TAGS:
            sys.exit(f"Too many tags (max {MAX_TAGS}) for {entry['url']}: {entry['tags']}")
        unknown = [m for m in entry.get("moods", []) if m not in MOODS]
        if unknown:
            sys.exit(f"Unknown mood {unknown} for {entry['url']} (use: {', '.join(MOODS)})")
        pid = playlist_id(entry["url"])
        info = fetch(pid)
        # A description in playlists.json replaces Spotify's (or fills in
        # when Spotify has none).
        if entry.get("description"):
            info["description"] = entry["description"].strip()
        items.append(
            {
                "id": pid,
                "tags": [t.lower() for t in entry.get("tags", [])],
                "moods": entry.get("moods", []),
                **info,
            }
        )
        print(f"  {info['title']}")
    items.reverse()  # newest first
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(render(items), encoding="utf-8")
    print(f"Wrote {OUTPUT.relative_to(ROOT)} with {len(items)} playlists.")


if __name__ == "__main__":
    main()
