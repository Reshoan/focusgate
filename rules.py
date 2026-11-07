"""FocusGate rules: which URL paths are blocked per site. Shared by the proxy and the injected guard script."""
import json
import re
from urllib.parse import urlsplit

# mode "block": paths matching any pattern are blocked.
# mode "allow": ONLY paths matching a pattern are allowed, everything else is blocked.
# Patterns are written to be valid in both Python `re` and JavaScript RegExp.
RULES = {
    "youtube": {
        "mode": "block",
        "patterns": [
            r"^/?$",                                              # homepage
            r"^/shorts(/|$)",                                     # Shorts
            r"^/feed/(?!history|playlists|library)",             # subscriptions, trending, explore...
            r"^/hashtag/",
            r"^/(@[^/]+|c/[^/]+|channel/[^/]+|user/[^/]+)/shorts",  # channel Shorts tab
        ],
    },
    "instagram": {
        "mode": "allow",
        "patterns": [
            r"^/direct(/|$)",                                     # messages
            r"^/accounts/",                                       # login / settings
            r"^/challenge/",
            r"^/(api|graphql|ajax|static|web|data|rsrc\.php)(/|$)",
        ],
        "redirect": "/direct/inbox/",
    },
}

_COMPILED = {k: [re.compile(p) for p in v["patterns"]] for k, v in RULES.items()}


def _host_is(host: str, base: str) -> bool:
    host = host.lower().split(":")[0]
    return host == base or host.endswith("." + base)


def site_of(host: str):
    if _host_is(host, "youtube.com") and not host.lower().startswith("music."):
        return "youtube"
    if _host_is(host, "instagram.com"):
        return "instagram"
    return None


def is_blocked(site: str, path: str) -> bool:
    p = urlsplit(path).path or "/"
    hit = any(rx.search(p) for rx in _COMPILED[site])
    return hit if RULES[site]["mode"] == "block" else not hit


BLOCKED_PAGE = """<!doctype html><html><head><meta charset="utf-8"><title>Blocked</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>body{font-family:system-ui,sans-serif;background:#111;color:#eee;display:grid;place-items:center;height:100vh;margin:0}
main{text-align:center;max-width:32rem;padding:1rem}input{font-size:1.1rem;padding:.6rem;width:70%;border-radius:6px;border:1px solid #444;background:#222;color:#eee}
button{font-size:1.1rem;padding:.6rem 1rem;border-radius:6px;border:0;background:#c33;color:#fff}</style></head>
<body><main><h1>FocusGate</h1><p>This page is blocked. You can still search for something specific:</p>
<form action="/results" method="get"><input name="search_query" placeholder="e.g. rust ownership tutorial" autofocus> <button>Search</button></form>
</main></body></html>"""

GUARD_JS = """(function(){
var R=%s;
function bad(p){var h=R.patterns.some(function(s){return new RegExp(s).test(p)});return R.mode==="block"?h:!h}
function check(){
  if(!bad(location.pathname))return;
  try{var n=+(sessionStorage.getItem("fg_n")||0);var t=+(sessionStorage.getItem("fg_t")||0);
    if(Date.now()-t>5000)n=0; if(n>3)return;
    sessionStorage.setItem("fg_n",n+1);sessionStorage.setItem("fg_t",Date.now());}catch(e){}
  location.replace(location.href);
}
["pushState","replaceState"].forEach(function(f){var o=history[f];history[f]=function(){var r=o.apply(this,arguments);check();return r}});
addEventListener("popstate",check);addEventListener("yt-navigate-start",check);
setInterval(check,400);check();
})();"""


def guard_script(site: str) -> str:
    r = RULES[site]
    return GUARD_JS % json.dumps({"mode": r["mode"], "patterns": r["patterns"]})
