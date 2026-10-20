"""
On-demand ATS score (the "ATS score" button in the job drawer).

An LLM (``llm.ats_model``, Sonnet by default) scores a tailored resume against its
job description the way an applicant-tracking system would. If the score is under
``ATS_TARGET`` the resume is re-tailored (configured tailoring model, Haiku) with the
report as feedback and re-scored, up to ``MAX_ROUNDS`` times; the best version wins.

Missing keywords are split into ``addable`` (the profile supports them, so a rewrite
may use them) and ``unsupported`` (real gaps — never stuffed into the resume). That
caps the achievable score honestly: a job asking for Kubernetes stays below 90 if the
profile has no Kubernetes.

Cost per click: 1 scoring call, plus up to MAX_ROUNDS × (1 tailor + 1 score).
"""

import json
import logging
import re

from pipeline.ats_match import build_resume_text
from pipeline.llm_client import _config, complete
from pipeline.resume_tailor import tailor_resume

logger = logging.getLogger(__name__)

ATS_TARGET = 90
MAX_ROUNDS = 2

SCORER_PROMPT = """You are an applicant tracking system (ATS) scoring a resume against a \
job description for a recruiter. Score 0-100 with this rubric:
- 40 pts hard-skill / tool keyword coverage (exact or standard variants of JD terms)
- 25 pts required qualifications met (degree, experience type, core skills)
- 15 pts role/title alignment (summary and experience read as this role)
- 10 pts preferred qualifications
- 10 pts relevant, quantified impact
Be strict and consistent; do not reward keywords that are absent.

Respond ONLY with JSON (no code fences):
{"score": int, "breakdown": {"keywords": int, "required": int, "alignment": int, \
"preferred": int, "impact": int}, "matched_keywords": [str], "missing_keywords": [str], \
"suggestions": [str]}
missing_keywords: important JD terms absent from the resume (max 15).
suggestions: up to 5 concrete edits, each under 25 words."""


def resume_text(tailored: dict) -> str:
    """Plain-text rendering of a tailored resume dict — what the ATS 'reads'."""
    lines = [tailored.get("summary", ""), "", "EXPERIENCE"]
    for e in tailored.get("experience", []):
        lines.append(f"{e.get('title')} — {e.get('company')} ({e.get('start')}–{e.get('end')})")
        lines += [f"- {b}" for b in e.get("bullets", [])]
    lines += ["", "PROJECTS"]
    for p in tailored.get("projects", []):
        lines.append(p.get("name", ""))
        lines += [f"- {b}" for b in p.get("bullets", [])]
    lines += ["", "SKILLS"]
    for cat, items in (tailored.get("skills") or {}).items():
        lines.append(f"{cat}: {', '.join(items)}")
    for edu in tailored.get("education", []):
        lines.append(f"EDUCATION: {edu.get('degree')}, {edu.get('school')}")
    if tailored.get("certifications"):
        lines.append("CERTIFICATIONS: " + ", ".join(tailored["certifications"]))
    return "\n".join(lines)


def _parse_json(raw: str) -> dict:
    start, end = raw.find("{"), raw.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"no JSON object in scorer reply: {raw[:200]!r}")
    return json.loads(raw[start:end + 1])


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9+#]+", " ", text.lower()).strip()


def split_missing(missing: list[str], profile_text: str) -> tuple[list[str], list[str]]:
    """(addable, unsupported): a missing keyword is addable only if the full
    profile already contains it, so a rewrite can claim it truthfully."""
    corpus = f" {_norm(profile_text)} "
    addable, unsupported = [], []
    for kw in missing:
        (addable if f" {_norm(kw)} " in corpus else unsupported).append(kw)
    return addable, unsupported


def score_resume(tailored: dict, jd_text: str, profile_text: str | None = None) -> dict:
    """One ATS scoring call. Returns the report with ``addable``/``unsupported``."""
    model = _config().get("ats_model", "sonnet")
    raw = complete(
        SCORER_PROMPT,
        f"JOB DESCRIPTION:\n{jd_text[:6000]}\n\nRESUME:\n{resume_text(tailored)}",
        max_tokens=1500, model=model,
    )
    report = _parse_json(raw)
    report["score"] = max(0, min(100, int(report.get("score", 0))))
    addable, unsupported = split_missing(
        report.get("missing_keywords", []),
        profile_text if profile_text is not None else build_resume_text(),
    )
    report.update(addable=addable, unsupported=unsupported, model=model)
    return report


def ats_check(job: dict, jd_text: str, tailored: dict) -> dict:
    """Score, and re-tailor until ``ATS_TARGET`` or ``MAX_ROUNDS``. Returns
    ``{"best": tailored dict, "report": best report, "history": [scores],
    "improved": bool}``. Stops early when nothing addable is left to fix."""
    profile_text = build_resume_text()
    best, report = tailored, score_resume(tailored, jd_text, profile_text)
    history = [report["score"]]
    for _ in range(MAX_ROUNDS):
        if report["score"] >= ATS_TARGET or not (report["addable"] or report.get("suggestions")):
            break
        candidate = tailor_resume(job, jd_text, feedback=report)
        if not candidate:
            break
        cand_report = score_resume(candidate, jd_text, profile_text)
        history.append(cand_report["score"])
        if cand_report["score"] > report["score"]:
            best, report = candidate, cand_report
    logger.info("ATS check %s @ %s: %s", job.get("title"), job.get("company"), history)
    return {"best": best, "report": report, "history": history,
            "improved": best is not tailored}
