#!/usr/bin/env python3
import feedparser
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import os

FEEDS = [
    ("Topthemen",  "https://rss.sueddeutsche.de/rss/Topthemen"),
    ("Politik",    "https://rss.sueddeutsche.de/rss/Politik"),
    ("Panorama",   "https://rss.sueddeutsche.de/rss/Panorama"),
    ("Wirtschaft", "https://rss.sueddeutsche.de/rss/Wirtschaft"),
]

AUSGABE = "/home/debian/zeitung/sz_heute.html"
HEUTE   = datetime.now().strftime("%d.%m.%Y")

JAVASCRIPT = """
<script>
document.addEventListener('DOMContentLoaded', function() {

  function getArtikel() {
    return Array.from(document.querySelectorAll('h3'));
  }

  // Interner Zähler - nicht vom Scroll-Zustand abhängig
  let aktuellerIndex = 0;

  function springeZu(index) {
    const artikel = getArtikel();
    if (index < 0) index = 0;
    if (index >= artikel.length) index = artikel.length - 1;
    aktuellerIndex = index;
    const ziel = artikel[index].offsetTop - 30;
    window.scrollTo({ top: ziel, behavior: 'smooth' });
  }

  document.addEventListener('keydown', function(e) {
    switch(e.key) {
      case 'ArrowRight':
        springeZu(aktuellerIndex + 1);
        e.preventDefault();
        break;
      case 'ArrowLeft':
        springeZu(aktuellerIndex - 1);
        e.preventDefault();
        break;
      case 'ArrowDown':
        window.scrollBy({ top: 200, behavior: 'smooth' });
        e.preventDefault();
        break;
      case 'ArrowUp':
        window.scrollBy({ top: -200, behavior: 'smooth' });
        e.preventDefault();
        break;
    }
  });

});
</script>
"""

def hole_artikel(url):
    try:
        r = requests.get(url, timeout=10,
                         headers={'User-Agent': 'Mozilla/5.0'})
        soup = BeautifulSoup(r.text, 'html.parser')
        inhalt = soup.find('article') or \
                 soup.find(class_='sz-article')
        if inhalt:
            for tag in inhalt.find_all(
                    ['script','style','aside','figure']):
                tag.decompose()
            return inhalt.get_text(separator='\n', strip=True)
    except Exception:
        pass
    return None

html = f"""<!DOCTYPE html>
<html><head>
<meta charset="utf-8">
<style>
  body    {{ background:#111; color:#eee; font-family:Georgia,serif;
             font-size:22px; line-height:1.7;
             max-width:900px; margin:auto; padding:2em; }}
  h1      {{ color:#f90; font-size:2em;
             border-bottom:2px solid #f90; }}
  h2      {{ color:#fc0; font-size:1.4em; margin-top:2em; }}
  h3      {{ color:#ccc; font-size:1.1em; }}
  p       {{ margin:0.8em 0; }}
  .datum  {{ color:#888; font-size:0.8em; display:none; }}
  .trenner{{ border:none; border-top:1px solid #333; margin:2em 0; }}
  img     {{ max-width:100%; height:auto; }}
  ::-webkit-scrollbar {{ display:none; }}
</style>
{JAVASCRIPT}
</head><body>
<h1>Süddeutsche Zeitung — {HEUTE}</h1>
"""

for rubrik, feed_url in FEEDS:
    feed = feedparser.parse(feed_url)
    html += f"<h2>{rubrik}</h2>\n"
    for entry in feed.entries[:5]:
        titel    = entry.get('title', '')
        zusammen = entry.get('summary', '')
        link     = entry.get('link', '')
        html += f"<h3>{titel}</h3>\n"
        html += f"<p class='datum'>{link}</p>\n"
        html += f"<p>{zusammen}</p>\n"
        volltext = hole_artikel(link)
        if volltext:
            for absatz in volltext.split('\n'):
                absatz = absatz.strip()
                if len(absatz) > 60:
                    html += f"<p>{absatz}</p>\n"
        html += "<hr class='trenner'>\n"

html += "</body></html>"

os.makedirs(os.path.dirname(AUSGABE), exist_ok=True)
with open(AUSGABE, 'w', encoding='utf-8') as f:
    f.write(html)

print(f"Gespeichert: {AUSGABE}")
