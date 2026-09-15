#!/usr/bin/env python3
import json, os, urllib.request, urllib.parse, html, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
ASSETS.mkdir(exist_ok=True)
USER = os.getenv("GITHUB_USER", "mustafa-z3hir")
TOKEN = os.getenv("GITHUB_TOKEN", "")


def esc(x): return html.escape(str(x), quote=True)

def write(name, body):
    (ASSETS / name).write_text(body, encoding="utf-8")

def card(title, lines, width=1000, height=190):
    rows = "".join(f'<text x="55" y="{105+i*30}" class="muted">{esc(k)}</text><text x="420" y="{105+i*30}" class="value">{esc(v)}</text>' for i,(k,v) in enumerate(lines))
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
<defs><linearGradient id="g" x1="0" x2="1"><stop stop-color="#0d1b2a"/><stop offset="1" stop-color="#122b45"/></linearGradient></defs>
<rect width="100%" height="100%" rx="24" fill="url(#g)" stroke="#1f4968"/>
<text x="55" y="52" class="title">{esc(title)}</text>{rows}
<style>.title{{font:700 24px Arial;fill:#eaf6ff}}.muted{{font:600 16px Arial;fill:#86a9c2}}.value{{font:700 16px Arial;fill:#62e6ff}}</style></svg>'''

def fetch_json(url, headers=None, method="GET", data=None):
    req = urllib.request.Request(url, method=method, data=data, headers=headers or {})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)

def api(path):
    return fetch_json("https://api.github.com" + path, {"Authorization": f"Bearer {TOKEN}", "Accept": "application/vnd.github+json", "User-Agent": USER})

def graphql(query, variables):
    data = json.dumps({"query": query, "variables": variables}).encode()
    return fetch_json("https://api.github.com/graphql", {"Authorization": f"Bearer {TOKEN}", "Accept": "application/json", "User-Agent": USER, "Content-Type": "application/json"}, "POST", data)

def fallback():
    write("stats.svg", card("GitHub Statistics", [("Profile", USER),("Status", "Dashboard ready — run the workflow")]))
    write("languages.svg", card("Top Languages", [("Status", "Generated from your repositories")]))
    write("streak.svg", card("Contribution Streak", [("Status", "Generated from your contribution calendar")]))
    write("activity.svg", card("Contribution Activity", [("Status", "Generated from your contribution calendar")]))
    write("highlights.svg", card("GitHub Highlights", [("Profile", USER),("Status", "Live data updates automatically")]))

try:
    user = api(f"/users/{urllib.parse.quote(USER)}")
    repos = api(f"/users/{urllib.parse.quote(USER)}/repos?per_page=100&sort=updated")
    public_repos = user.get("public_repos", 0)
    followers = user.get("followers", 0)
    stars = sum(r.get("stargazers_count", 0) for r in repos)
    forks = sum(r.get("forks_count", 0) for r in repos)
    languages = {}
    for r in repos:
        if r.get("fork"): continue
        try:
            langs = api(r["languages_url"].replace("https://api.github.com", ""))
            for k,v in langs.items(): languages[k] = languages.get(k, 0) + v
        except Exception: pass
    top = sorted(languages.items(), key=lambda x:x[1], reverse=True)[:6]

    q = '''query($login:String!){ user(login:$login){ contributionsCollection { totalCommitContributions totalIssueContributions totalPullRequestContributions totalPullRequestReviewContributions contributionCalendar { totalContributions weeks { contributionDays { contributionCount date } } } } } }'''
    gql = graphql(q, {"login": USER})
    cc = gql.get("data", {}).get("user", {}).get("contributionsCollection", {})
    cal = cc.get("contributionCalendar", {})
    total = cal.get("totalContributions", 0)
    commits = cc.get("totalCommitContributions", 0)
    prs = cc.get("totalPullRequestContributions", 0)
    issues = cc.get("totalIssueContributions", 0)
    days = [d for w in cal.get("weeks", []) for d in w.get("contributionDays", [])]
    counts = [d.get("contributionCount",0) for d in days]
    current = best = run = 0
    for c in counts:
        if c > 0: run += 1; best = max(best, run)
        else: run = 0
    for d in reversed(days):
        if d.get("contributionCount",0) > 0: current += 1
        elif current: break

    write("stats.svg", card("GitHub Statistics", [("Public repositories", public_repos),("Followers", followers),("Stars collected", stars),("Forks", forks),("Contributions (1 year)", total),("Commits", commits),("Pull requests", prs),("Issues", issues)], height=330))
    write("languages.svg", card("Top Languages", [(k, f"{v:,} bytes") for k,v in top] or [("No data", "Yet")], height=250))
    write("streak.svg", card("Contribution Streak", [("Current streak", f"{current} days"),("Best streak", f"{best} days"),("Total contributions", total)]))
    recent = days[-14:] if days else []
    bars = "".join(f'<rect x="{45+i*62}" y="110" width="40" height="{25+min(d.get("contributionCount",0),10)*7}" rx="8" fill="#16c7e8" opacity="{0.25+min(d.get("contributionCount",0),10)*0.07:.2f}"/><text x="{45+i*62}" y="165" class="muted">{esc(d.get("date","")[-5:])}</text>' for i,d in enumerate(recent))
    write("activity.svg", f'''<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="205"><rect width="100%" height="100%" rx="24" fill="#0d1b2a" stroke="#1f4968"/><text x="45" y="50" class="title">Contribution Activity</text>{bars}<style>.title{{font:700 24px Arial;fill:#eaf6ff}}.muted{{font:600 11px Arial;fill:#86a9c2}}</style></svg>''')
    write("highlights.svg", card("GitHub Highlights", [("Repositories", public_repos),("Followers", followers),("Stars", stars),("1-year contributions", total)]))
except Exception as e:
    fallback()

# Static visual assets are regenerated here so the repository always has local images.
write("header.svg", '''<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="260"><defs><linearGradient id="bg" x1="0" x2="1"><stop stop-color="#07111f"/><stop offset=".55" stop-color="#0b2239"/><stop offset="1" stop-color="#102f48"/></linearGradient></defs><rect width="1200" height="260" rx="28" fill="url(#bg)"/><circle cx="1060" cy="70" r="150" fill="#0dcaf0" opacity=".08"/><circle cx="1120" cy="220" r="110" fill="#fcbb5a" opacity=".07"/><text x="70" y="105" fill="#eaf6ff" font-family="Arial" font-size="46" font-weight="700">Mustafa Işık</text><text x="73" y="150" fill="#62e6ff" font-family="Arial" font-size="22">Software Developer • Full-Stack • AI &amp; Automation</text><text x="73" y="190" fill="#86a9c2" font-family="Arial" font-size="16">Building software, automations and reliable IT systems.</text></svg>''')
write("typing.svg", '''<svg xmlns="http://www.w3.org/2000/svg" width="900" height="58"><rect width="100%" height="100%" rx="18" fill="#0d1b2a" stroke="#1f4968"/><text x="450" y="37" text-anchor="middle" fill="#62e6ff" font-family="Arial" font-size="21" font-weight="700">Software Developer • Full-Stack Development • AI &amp; Automation</text></svg>''')
write("github-badge.svg", '''<svg xmlns="http://www.w3.org/2000/svg" width="105" height="32"><rect width="105" height="32" rx="16" fill="#172b40"/><text x="52" y="21" text-anchor="middle" fill="#fff" font-family="Arial" font-size="13" font-weight="700">GitHub</text></svg>''')
write("linkedin-badge.svg", '''<svg xmlns="http://www.w3.org/2000/svg" width="105" height="32"><rect width="105" height="32" rx="16" fill="#172b40"/><text x="52" y="21" text-anchor="middle" fill="#fff" font-family="Arial" font-size="13" font-weight="700">LinkedIn</text></svg>''')
write("devto-badge.svg", '''<svg xmlns="http://www.w3.org/2000/svg" width="105" height="32"><rect width="105" height="32" rx="16" fill="#172b40"/><text x="52" y="21" text-anchor="middle" fill="#fff" font-family="Arial" font-size="13" font-weight="700">Dev.to</text></svg>''')
write("tech-stack.svg", '''<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="220"><rect width="100%" height="100%" rx="24" fill="#0d1b2a" stroke="#1f4968"/><text x="50" y="52" fill="#eaf6ff" font-family="Arial" font-size="24" font-weight="700">Core Technologies</text><text x="50" y="105" fill="#62e6ff" font-family="Arial" font-size="18">JavaScript / TypeScript • Python • C • PHP • SQL</text><text x="50" y="145" fill="#62e6ff" font-family="Arial" font-size="18">React • Next.js • Node.js • Express • Bootstrap • Tailwind</text><text x="50" y="185" fill="#86a9c2" font-family="Arial" font-size="17">PostgreSQL • MSSQL • Git • Docker • Linux • Microsoft 365</text></svg>''')
write("ai-stack.svg", '''<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="180"><rect width="100%" height="100%" rx="24" fill="#0d1b2a" stroke="#1f4968"/><text x="50" y="52" fill="#eaf6ff" font-family="Arial" font-size="24" font-weight="700">AI &amp; Automation</text><text x="50" y="100" fill="#62e6ff" font-family="Arial" font-size="18">Prompt Engineering • AI-Assisted Development • AI Automation</text><text x="50" y="138" fill="#86a9c2" font-family="Arial" font-size="17">Multi-model evaluation • Local-first AI workflows • API integrations</text></svg>''')
write("footer.svg", '''<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="150" viewBox="0 0 1200 150"><path d="M0 75 Q150 15 300 75 T600 75 T900 75 T1200 75 V150 H0Z" fill="#0d1b2a"/><path d="M0 75 Q150 15 300 75 T600 75 T900 75 T1200 75" fill="none" stroke="#0dcaf0" stroke-width="3" opacity=".8"/><text x="600" y="122" text-anchor="middle" fill="#86a9c2" font-family="Arial" font-size="15">Built with code, curiosity and a little bit of chaos.</text></svg>''')
