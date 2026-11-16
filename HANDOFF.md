# Handoff: 2026-11-16 · Master résumé rewrite + profile sync

**Goal:** Land a full-time ML/AI Engineer, Research Engineer or SWE (ML) role starting May 2027. Applying is the priority, not tool work.
**Status:** Master résumé rewritten for Easy Apply (LinkedIn, Handshake) and checked: one page, clean text layer, 12 working links. `config/profile.json` synced to it. Queued résumés from 2026-11-12 are still unsent and use the old wording.

## Next step
Ishani applies to the queued jobs in the dashboard (`make local`), freshest first (24734 Apple, 25559 Nuro,
26528 Microsoft, 25558 TikTok, 23177 Oracle), and marks each applied → verify with `.venv/bin/python main.py --stats`.
Re-tailor first (`--tailor --max-age 14`) if the new wording should be in those résumés.

## Done this session
- Master résumé (iCloud `adulting/resume/Ishani-Kathuria-Resume.pdf` + .docx, edited via Claude in Word):
  header with location and full URLs; summary now full-time only (no CPT, so no "internships now");
  AWS title fixed; "Earlier Experience" block replaced by standard Deloitte and Planet E-Com entries;
  Docplus dropped; projects are now QALF, Homebase, AutoRedTeam (with numbers); skills regrouped with
  missing keywords added and model names removed; margins 0.4" top / 0.35" bottom.
- `config/profile.json` synced to the résumé: RA employer "Purdue University Northwest" and bullets
  (incl. WWS-RAG-Bench); AWS, Deloitte, Planet E-Com, QALF, Homebase, AutoRedTeam bullets; Amity location;
  added FAISS, pgvector, RAGAS, LangSmith, Bash. QALF "14%" replaced by raw scores (0.423 → 0.488 is 15.4%).
  `make test`: 256 passed.

## Decisions
- Most AWS achievements stay under the System Dev Eng title: titles and dates are what background checks verify,
  and the SDE title only covers 4 months. Rejected: moving them under SDE.
- Not stating F-1/OPT on LinkedIn, keeping "4x Published" and the India/Europe targets, keeping the AWS 30%/25% metrics.
- Old 2021 internships (Sparks ×2, ProfiVe) and the Depth Gesture project stay on LinkedIn: Ishani's call.
- Résumé: third RA bullet (trust layer) dropped for space; the profile stays a superset of the résumé
  (extra projects and skills feed the tailoring tracks).
- Don't edit résumé content or tailoring code without an explicit yes (saved as a memory).

## Open threads
- Résumé content only Ishani can fill in: a result for AutoRedTeam; how many of the "9 AI hackathons"
  were organized vs entered.
- AutoRedTeam: the old profile bullet named the attack scenarios (secret leakage, PII extraction, jailbreak,
  indirect prompt injection) and was overwritten by the vaguer résumé wording. Consider restoring it in both.
- Profile: WWS-RAG-Bench now appears under both the RA role and the TrustworthyRAG project; the four track
  summaries still differ from the résumé summary; "Claude Code" is still in the cloud/devops skills.
- Résumé cosmetics: Publications bullets render blue and smaller; Arial still embedded. No parsing impact.
- LinkedIn: RA employer still "Purdue University" (résumé and profile now say PNW); add an RA result bullet
  and a post once a paper is accepted; check SIREN's "Oct 2025 – Oct 2026" end date.
- Carried over: the scorer underrates plain SWE titles (`src/pipeline/job_filter.py`); ATS-check top picks
  (DeepMind, NVIDIA, Amazon, Apple, Nuro) before submitting.

## Gotchas
- Claude in Word: give it exact replacement text and ask it to report margins before changing layout.
  Accept all tracked changes before exporting the PDF.
- LinkedIn: use form_input or execCommand('insertText'), not typing (typing drops characters). Wait about 4 s
  before reading the page text. Language entries with a Duolingo score must be deleted and re-added to drop the score.
- Turso is the source of truth; local `data/*.db` is stale.

## Read first
- `PROJECT.md`: flow, commands, conventions
- `src/pipeline/resume_tailor.py`: tailoring + `_restore_role_facts`
- `config/profile.json`: résumé source of truth

## Uncommitted
clean (after this handoff commit)
