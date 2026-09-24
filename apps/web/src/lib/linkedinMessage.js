// Generate a warm LinkedIn referral-ask DM for a recruiter/connection.
// Mirrors scripts/linkedin_outreach.py so the in-app draft matches the worklist.
// Tailors by role (engineer/manager → "refer me"; recruiter → "point me to the
// hiring team") and by pipeline tier parsed from the loader's notes; falls back
// to sensible defaults for manually-added recruiters.

const SENDER_INTRO =
  "I'm finishing my MS in Applied AI at Purdue and spent ~2 years as an SDE at " +
  "AWS before this, now focused on new-grad AI/ML roles (RAG/LLM and applied ML)"

function firstName(name) {
  return (name || '').trim().split(/\s+/)[0] || 'there'
}

// engineer (peer/referrer) · manager · recruiter — from title + loader notes.
function classifyRole(recruiter) {
  const hay = `${recruiter.title || ''} ${recruiter.notes || ''}`.toLowerCase()
  if (/recruit|talent|sourc|staffing|people ops|human resources|\bhr\b/.test(hay)) return 'recruiter'
  if (/manager|director|\bhead\b|\blead\b|\bvp\b|principal|staff/.test(hay)) return 'manager'
  return 'engineer'
}

// interview · applied · other — the loader writes the tier into notes.
function pipelineTier(recruiter) {
  const n = (recruiter.notes || '').toLowerCase()
  if (n.includes('interview')) return 'interview'
  if (n.includes('applied')) return 'applied'
  return 'other'
}

export function linkedinMessage(recruiter) {
  const first = firstName(recruiter.name)
  const company = (recruiter.company || 'your team').trim()

  const tier = pipelineTier(recruiter)
  const role = classifyRole(recruiter)

  // Interviewing is worth stating; otherwise don't claim applications —
  // ask the contact which openings would be a fit.
  let ctx, ask
  if (tier === 'interview') {
    ctx = `I'm currently interviewing with ${company} for an AI/ML role`
    ask = role === 'recruiter'
      ? 'Would you be able to share any insight on the process, or who I should connect with?'
      : 'Would you be open to referring me, or putting in a good word with the team?'
  } else {
    ctx = `${company} is high on my list`
    ask = role === 'manager'
      ? 'Is your team hiring, or do you know of any openings that might be a good fit? ' +
        "I'd be grateful for a referral or a pointer to the right person."
      : role === 'recruiter'
        ? `Are there any new-grad AI/ML openings at ${company} you think I'd be a good fit for, ` +
          `or could you point me to the team that's hiring?`
        : "Do you know of any openings on your team, or ones you've heard about, that might be " +
          "a good fit? I'd be grateful for a referral if so."
  }

  return (
    `Hi ${first}, hope you've been well! ${SENDER_INTRO}. ${ctx}. ${ask} ` +
    `Happy to send over my resume — thanks so much either way!`
  )
}
