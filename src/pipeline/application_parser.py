"""
Parse company + role from an application/confirmation/response email.

Recruiting emails follow a handful of recognizable shapes:

    "Your application to <ROLE> at <COMPANY>"           (LinkedIn)
    "Thank you for your interest in <COMPANY>"          (Greenhouse & co.)
    "Thanks for applying to <COMPANY>"
    "Next Steps with <COMPANY>: ..."
    "<COMPANY> Application Status Update"

When the subject doesn't yield a company, fall back to the sender's display
name, then its domain — skipping generic ATS/mail domains (greenhouse, lever,
workday, linkedin, …) that name the tooling, not the employer.

Everything is best-effort; ``company`` may be None when nothing is confident.
"""

import re

# Sender domains that are ATS/mail infrastructure, not the employer.
_ATS_DOMAINS = {
    "greenhouse-mail.io", "greenhouse.io", "us.greenhouse-mail.io",
    "lever.co", "hire.lever.co", "myworkday.com", "myworkdayjobs.com",
    "linkedin.com", "ashbyhq.com", "icims.com", "taleo.net", "jobvite.com",
    "smartrecruiters.com", "eu.greenhouse-mail.io", "workday.com",
    "mail.amazon.jobs", "amazon.jobs", "rippling.com", "paradox.ai",
}
# Domain second-level tokens that map to a well-known employer.
_DOMAIN_COMPANY = {
    "amazon": "Amazon", "microsoft": "Microsoft", "google": "Google",
    "nvidia": "NVIDIA", "apple": "Apple", "meta": "Meta",
}
# Generic mail / privacy-relay / personal domains — never name the employer.
_GENERIC_DOMAINS = {
    "eprivatemail.com", "privaterelay.appleid.com", "gmail.com", "googlemail.com",
    "outlook.com", "hotmail.com", "yahoo.com", "icloud.com", "proton.me",
    "clearcompany.com", "hire.lever.co",
}
_GENERIC_SENDERS = {
    "linkedin", "no-reply", "noreply", "no reply", "jobs-noreply", "notifications",
    "notification", "careers", "recruiting", "recruiting team", "talent",
    "talent acquisition", "hr", "hr inbox", "do-not-reply", "donotreply",
    "do not reply", "autoreply", "auto-reply", "mailer", "mailer-daemon", "team",
    "the team", "hiring", "hiring team", "system", "workday", "ds", "tal",
}
# Generic-ish tokens that, if present in a sender display name, mean it's infra
# or a role mailbox rather than the employer's clean name.
_GENERIC_NAME_TOKENS = {
    "no reply", "do not reply", "donotreply", "do-not-reply", "autoreply",
    "auto-reply", "notification", "notifications", "mailer", "inbox",
    "talent acquisition", "recruiting team", "hiring team", "via", "workday",
    "system", "donotreply", "no-reply",
}

# Subject patterns → (company_group, role_group|None). Tried in order.
_SUBJECT_PATTERNS = [
    (re.compile(r"application (?:to|for)\s+(?P<role>.+?)\s+at\s+(?P<company>.+?)\s*$", re.I), "company", "role"),
    (re.compile(r"application was sent to\s+(?P<company>.+?)\s*$", re.I), "company", None),
    (re.compile(r"applying (?:to|for a position at)\s+(?P<company>.+?)[!,:.]*\s*$", re.I), "company", None),
    (re.compile(r"(?:interest in|application to)\s+(?P<company>[A-Z0-9][\w&.\- ]+?)(?:[,!:.]| for | –|$)"),
     "company", None),
    (re.compile(r"next steps with\s+(?P<company>[\w&.\- ]+?)\s*[:!,-]", re.I), "company", None),
    # "…- Cisco Application Status Update" → grab the token(s) right before it.
    (re.compile(r"(?:[-–|]\s*)?(?P<company>[A-Z0-9][\w&.]*)\s+application status", re.I), "company", None),
    # "Tower Research Capital: Application Received", "Ripple | Update on Your Application"
    (re.compile(r"^(?P<company>[A-Z0-9][\w&.\- ]+?)\s*[:|]\s*(?:application|update)", re.I), "company", None),
    (re.compile(r"your application (?:at|with)\s+(?P<company>[\w&.\- ]+?)\s*$", re.I), "company", None),
]

# Noise pulled off the tail of an extracted company name.
_COMPANY_TAIL = re.compile(
    r"\b(inc|llc|ltd|corp|corporation|co|team|careers|recruiting|talent|hr|"
    r"application|update|ishani)\b\.?$", re.I)


def _clean_company(name: str) -> str:
    name = (name or "").strip().strip(".,:!-–|").strip()
    # Drop a trailing ", Ishani" style personalization or role/tooling word.
    prev = None
    while name and name != prev:
        prev = name
        name = _COMPANY_TAIL.sub("", name).strip().strip(".,:!-–|").strip()
    return name


def _from_domain(from_addr: str) -> str | None:
    """Company from the sender — used only as a last resort and deliberately
    conservative: a wrong company here would create a junk tracked application
    and merge unrelated ones, so we return a name only when confident."""
    low = (from_addr or "").lower()
    m = re.search(r"@([a-z0-9.\-]+)", low)
    if not m:
        return None
    domain = m.group(1)
    if domain in _GENERIC_DOMAINS or any(domain.endswith("." + d) or domain == d
                                         for d in _GENERIC_DOMAINS):
        return None
    # Known employer by domain token (handles amazon.jobs, careers.microsoft.com).
    for token, comp in _DOMAIN_COMPANY.items():
        if token in domain:
            return comp
    if domain in _ATS_DOMAINS or any(d in domain for d in _ATS_DOMAINS):
        # ATS infra often puts the employer in the local part: Cisco@myworkday.com
        local = re.search(r"([a-z0-9._\-]+)@", low)
        if local:
            lp = local.group(1).replace(".", " ").replace("_", " ").strip()
            if lp and lp not in _GENERIC_SENDERS and len(lp) >= 3 and not lp.isdigit():
                return lp.title()
        return None
    # A plain corporate domain: use its second-level label only if it looks like
    # a real name (not a generic mail host we already excluded).
    labels = domain.split(".")
    sld = labels[-2] if len(labels) >= 2 else labels[0]
    if sld in ("careers", "email", "mail", "jobs", "apply", "recruiting", "myworkday"):
        sld = labels[-3] if len(labels) >= 3 else sld
    if not sld or len(sld) < 3 or sld in _GENERIC_SENDERS:
        return None
    return _DOMAIN_COMPANY.get(sld, sld.capitalize())


def _from_display_name(from_addr: str) -> str | None:
    # "Microsoft <careers@...>" → "Microsoft"; skip generic senders.
    m = re.match(r"\s*\"?([^\"<]+?)\"?\s*<", from_addr or "")
    if not m:
        return None
    name = m.group(1).strip()
    low = name.lower()
    if not name or low in _GENERIC_SENDERS or "@" in name:
        return None
    if any(tok in low for tok in _GENERIC_NAME_TOKENS):
        return None
    # "NVIDIA HR" / "Acme Recruiting Team" → strip the trailing role words.
    name = re.sub(r"\s+(HR|Recruiting|Talent|Careers|Team|Hiring|Acquisition)\s*$",
                  "", name, flags=re.I).strip()
    return name or None


def parse(subject: str, from_addr: str = "") -> dict:
    """Return ``{"company": str|None, "role": str|None}`` for an email."""
    subject = subject or ""
    company = role = None

    for pattern, comp_g, role_g in _SUBJECT_PATTERNS:
        m = pattern.search(subject)
        if m:
            company = _clean_company(m.group(comp_g))
            if role_g:
                role = (m.group(role_g) or "").strip() or None
            if company:
                break
            company = None

    if not company:
        company = _from_display_name(from_addr) or _from_domain(from_addr)
        company = _clean_company(company) if company else None

    # Guard against junk (single char, or an obvious non-company word).
    if company and (len(company) < 2 or company.lower() in _GENERIC_SENDERS):
        company = None

    return {"company": company or None, "role": role}
