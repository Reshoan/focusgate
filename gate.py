"""mitmproxy addon: block configured paths on YouTube/Instagram and inject a guard script for in-page (SPA) navigation."""
from mitmproxy import http

import rules


def _is_document(req: http.Request) -> bool:
    dest = req.headers.get("sec-fetch-dest")
    if dest:
        return dest == "document"
    return "text/html" in req.headers.get("accept", "")


class Gate:
    def request(self, flow: http.HTTPFlow):
        site = rules.site_of(flow.request.pretty_host)
        if not site or not _is_document(flow.request):
            return
        if not rules.is_blocked(site, flow.request.path):
            return
        flow.metadata["focusgate_blocked"] = True
        redirect = rules.RULES[site].get("redirect")
        if redirect:
            flow.response = http.Response.make(302, b"", {"Location": redirect, "Cache-Control": "no-store"})
        else:
            flow.response = http.Response.make(
                200, rules.BLOCKED_PAGE, {"Content-Type": "text/html; charset=utf-8", "Cache-Control": "no-store"}
            )

    def response(self, flow: http.HTTPFlow):
        site = rules.site_of(flow.request.pretty_host)
        if not site or not flow.response or not _is_document(flow.request):
            return
        if flow.metadata.get("focusgate_blocked"):
            return
        if "text/html" not in flow.response.headers.get("content-type", ""):
            return
        text = flow.response.text
        if not text:
            return
        for h in ("content-security-policy", "content-security-policy-report-only"):
            flow.response.headers.pop(h, None)
        tag = "<script>" + rules.guard_script(site) + "</script>"
        i = text.lower().find("<head")
        j = text.find(">", i) + 1 if i != -1 else 0
        flow.response.text = text[:j] + tag + text[j:]


addons = [Gate()]
