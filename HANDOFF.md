# Handoff: 2026-11-15 · LinkedIn overhaul + résumé title pinning

**Goal:** Land a full-time ML/AI Engineer, Research Engineer or SWE (ML) role starting May 2027. Applying is the priority, not tool work.
**Status:** LinkedIn revised and recruiter-reviewed twice (7/10, "would click in"). Résumé AWS title fixed and pinned. Queued résumés from 2026-11-12 are still unsent.

## Next step
Ishani applies to the queued jobs in the dashboard (`make local`), freshest first (24734 Apple, 25559 Nuro,
26528 Microsoft, 25558 TikTok, 23177 Oracle), and marks each applied → verify with `.venv/bin/python main.py --stats`.

## Done this session
- Résumé: AWS title is now "Software Development Engineer; System Development Engineer until Apr 2025"
  (`config/profile.json`). `_restore_role_facts` in `src/pipeline/resume_tailor.py` pins every role's title,
  company and dates to the profile after LLM tailoring (`tests/test_role_facts.py`). Commit 9458f1d.
- Committed earlier pipeline work: `make refresh` / `--refresh` (skip closed Jobright jobs, use employer URLs),
  `--tailor --max-age 14` with interns excluded, cover letters for full-time roles. Commit eab91de. `make test`: 256 passed.
- LinkedIn (done in Chrome, not in the repo): new headline/About/top skills; AWS split into System Dev Eng
  (Jul 2023–Apr 2025, 4 bullets, framed as software development) + SDE (Apr–Jul 2025, 2 bullets); 10 dated projects;
  3 honors; unverifiable metrics removed (Autbot 30%, SelfMed 30%, Docplus "40+ devs"); typos fixed;
  2020 certs (HackerRank, Django, Udemy) and the Duolingo score removed.

## Decisions
- Most AWS achievements stay under the System Dev Eng title: titles and dates are what background checks verify,
  and the SDE title only covers 4 months. Rejected: moving them under SDE.
- Not stating F-1/OPT on LinkedIn, keeping "4x Published" and the India/Europe targets, keeping the AWS 30%/25% metrics.
- Old 2021 internships (Sparks ×2, ProfiVe) and the Depth Gesture project stay: Ishani's call, they do no harm.
- Don't edit résumé content or tailoring code without an explicit yes (saved as a memory).

## Open threads
- Ishani: update the AWS title by hand in the iCloud master résumé .docx.
- LinkedIn later: add an RA result bullet and a post once a paper is accepted. Check that SIREN's
  "Oct 2025 – Oct 2026" end date is right (PROFILE.md says Ishani still runs it).
- Left for now: RA employer "Purdue University" vs PNW, degree name (AI vs Applied AI), banner.
- Carried over: the scorer underrates plain SWE titles (`src/pipeline/job_filter.py`); ATS-check top picks
  (DeepMind, NVIDIA, Amazon, Apple, Nuro) before submitting.

## Gotchas
- LinkedIn: use form_input or execCommand('insertText'), not typing (typing drops characters). Wait about 4 s
  before reading the page text. Language entries with a Duolingo score must be deleted and re-added to drop the score.
- Turso is the source of truth; local `data/*.db` is stale.

## Read first
- `PROJECT.md`: flow, commands, conventions
- `src/pipeline/resume_tailor.py`: tailoring + `_restore_role_facts`
- `config/profile.json`: résumé source of truth

## Uncommitted
clean (after this handoff commit)
