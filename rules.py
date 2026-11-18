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
        # Hide the watch-page recommendations/end cards and turn autoplay off.
        "css": (
            "#related,ytd-watch-next-secondary-results-renderer,.ytp-endscreen-content,.ytp-ce-element,"
            ".ytp-autonav-endscreen-countdown-overlay,.ytp-autonav-endscreen-upnext-container,"
            ".ytp-suggestion-set,.ytp-videowall-still{display:none!important}"
        ),
        "js": (
            "function fgOff(){var b=document.querySelector('.ytp-autonav-toggle-button[aria-checked=\"true\"]');if(b)b.click();}"
            "setInterval(fgOff,1000);addEventListener('yt-navigate-finish',fgOff);"
        ),
    },
    "instagram": {
        "mode": "allow",
        "patterns": [
            r"^/direct(/|$)",                                     # messages
            r"^/accounts/",                                       # login / settings
            r"^/challenge/",
            r"^/(api|graphql|ajax|static|web|data|rsrc\.php)(/|$)",
            r"^/(p|reel|tv)/[^/]+",                               # a single post / reel someone sent
            r"^/[^/]+/(p|reel)/[^/]+",                            # same, via a profile
            r"^/stories/[^/]+",                                   # stories
            # individual profiles (root only: /name/), excluding feed-like top-level pages
            r"^/(?!(?:explore|reels|reel|p|tv|direct|accounts|stories|challenge|api|graphql|ajax|static|web|data"
            r"|about|legal|privacy|developer|directory|emailsignup|oauth)(?:/|$))[A-Za-z0-9._]+/?$",
        ],
        "redirect": "/direct/inbox/",
        # non-navigation requests blocked outright (best effort; Instagram mostly uses GraphQL)
        "api_block": [r"^/api/v1/(web/search|fbsearch|discover|explore)"],
    },
    "facebook": {
        "mode": "allow",
        # Patterns are tested against both "/path" and "/path?query".
        "patterns": [
            r"^/messages(/|$)",                                   # messages
            r"^/notifications(/|$)",                              # notifications
            r"^/(login|logout|checkpoint|recover|two_step_verification|device-based|auth_platform|confirmemail|cookie)",
            r"^/(api|ajax|rsrc\.php|common|security|platform|si)(/|$)",
            r"^/permalink\.php",                                  # posts
            r"^/story\.php",
            r"^/photo(\.php|/|$)",
            r"^/media/set",
            r"^/video(\.php|s/)",                                # standalone videos
            r"^/[^/]+/reels?/[^/]+",                              # a page's single reel
            r"^/marketplace/item/",                               # a shared listing
            r"^/events/\d+",
            r"^/[^/]+/(posts|videos|photos)/[^/]+",
            r"^/groups/[^/]+/(posts|permalink)/[^/]+",
            r"^/share/",                                          # all shared-link formats
            r"^/reel/\d+",                                        # a single reel
            r"^/watch/?\?(?:.*&)?v=",                             # a single video (not the Watch feed)
            r"^/profile\.php\?(?:.*&)?id=\d+",                    # profile by numeric id
            # individual profiles (root only), excluding feed-like top-level pages
            r"^/(?!(?:home\.php|watch|reel|reels|marketplace|gaming|groups|pages|events|friends|bookmarks|search|saved"
            r"|stories|fundraisers|ads|jobs|memories|feeds|login|logout|notifications|messages|photo|permalink\.php"
            r"|story\.php|profile\.php|share|help|policies|privacy)(?:/|$))[A-Za-z0-9.]+/?$",
        ],
        "redirect": "/messages/",
    },
}

_COMPILED = {k: [re.compile(p) for p in v["patterns"]] for k, v in RULES.items()}
_API_BLOCK = {k: [re.compile(p) for p in v.get("api_block", [])] for k, v in RULES.items()}
_FB_HOSTS = {"facebook.com", "www.facebook.com", "m.facebook.com", "web.facebook.com", "mbasic.facebook.com"}


def _host_is(host: str, base: str) -> bool:
    host = host.lower().split(":")[0]
    return host == base or host.endswith("." + base)


def site_of(host: str):
    if _host_is(host, "youtube.com") and not host.lower().startswith("music."):
        return "youtube"
    if _host_is(host, "instagram.com"):
        return "instagram"
    if host.lower().split(":")[0] in _FB_HOSTS:
        return "facebook"
    return None


def _targets(path: str):
    u = urlsplit(path)
    p = u.path or "/"
    return [p, p + "?" + u.query] if u.query else [p]


def is_blocked(site: str, path: str) -> bool:
    hit = any(rx.search(t) for rx in _COMPILED[site] for t in _targets(path))
    return hit if RULES[site]["mode"] == "block" else not hit


def is_api_blocked(site: str, path: str) -> bool:
    p = urlsplit(path).path
    return any(rx.search(p) for rx in _API_BLOCK[site])


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
function bad(p){var t=[p];if(location.search)t.push(p+location.search);var h=R.patterns.some(function(s){var r=new RegExp(s);return t.some(function(x){return r.test(x)})});return R.mode==="block"?h:!h}
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


def inject_html(site: str) -> str:
    """Everything injected into the <head> of a page on this site."""
    r = RULES[site]
    out = ""
    if r.get("css"):
        out += "<style>" + r["css"] + "</style>"
    out += "<script>" + guard_script(site) + (r.get("js") or "") + "</script>"
    return out
