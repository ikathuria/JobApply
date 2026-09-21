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
  const ctx = tier === 'interview'
    ? `I'm currently interviewing with ${company} for an AI/ML role`
    : tier === 'applied'
      ? `I recently applied to a few AI/ML roles at ${company}`
      : `I'm focusing my search on AI/ML teams at ${company}`

  const role = classifyRole(recruiter)
  const ask = role === 'manager'
    ? 'Would you be open to referring me, or pointing me to the right person on your team?'
    : role === 'recruiter'
      ? `Would you be the right person to talk to about new-grad AI/ML openings at ${company}, ` +
        `or could you point me to the team that's hiring?`
      : 'Would you be open to referring me internally?'

  return (
    `Hi ${first}, hope you've been well! ${SENDER_INTRO}. ${ctx}. ${ask} ` +
    `Happy to send my resume and the exact job links to make it easy — thanks so much either way!`
  )
}
