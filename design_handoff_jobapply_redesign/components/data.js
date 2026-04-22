// Mock data for JobApply prototype
window.STATS = {
  total: 885, new: 296, ready: 58, approved: 0,
  applied: 368, oa: 4, interview: 2, offer: 0,
  rejected: 121, skipped: 36
};

window.FOCUS_ITEMS = [
  { id: "f1", type: "tailor", label: "58 jobs tailored and ready to review", cta: "Review Ready", tab: "ready", icon: "✦", color: "#22C55E" },
  { id: "f2", type: "confirm", label: "Google DeepMind application awaits your approval", cta: "Confirm & Apply", tab: "ready", jobId: 6, icon: "⚡", color: "#8B5CF6" },
  { id: "f3", type: "oa", label: "Microsoft Research sent an online assessment", cta: "View Job", tab: "all", jobId: 12, icon: "📝", color: "#F59E0B" },
  { id: "f4", type: "interview", label: "Tesla interview on April 28 — prep time!", cta: "View Details", tab: "all", jobId: 14, icon: "🎤", color: "#EC4899" },
];

const JD_LOREM = `We are looking for a motivated research intern to join our team. You will collaborate with senior researchers on cutting-edge AI/ML projects with real-world impact.

Responsibilities:
• Develop and implement ML models for production systems
• Conduct literature reviews and propose novel approaches  
• Write clean, well-documented code (Python, PyTorch/JAX)
• Present findings to cross-functional stakeholders

Requirements:
• Currently pursuing a BS/MS/PhD in CS, ML, or related field
• Strong background in deep learning, NLP, or computer vision
• Experience with PyTorch, TensorFlow, or JAX
• Solid math foundation: linear algebra, probability, optimization`;

const COVER = `Dear Hiring Team,

I am writing to express my strong interest in this role. With my background in deep learning and NLP research at [University], I am excited about the opportunity to contribute to your team's frontier AI work.

During my research, I developed novel attention mechanisms that achieved state-of-the-art performance on three NLP benchmarks. I also led a team of 4 researchers and published our work at NeurIPS 2025.

I am particularly drawn to your team's approach to scaling laws and efficient inference — areas where I have hands-on experience from my recent work on model compression.

Thank you for considering my application. I would love to discuss how my background aligns with your team's goals.

Sincerely,
Ishani Kathuria`;

window.JOBS = [
  { id: 6,  title: "Machine Learning Engineer Intern", company: "Google DeepMind", location: "Mountain View, CA", score: 0.95, status: "ready",    source: "intern_list", url: "#", description: JD_LOREM, starred: true,  dateApplied: null,         notes: "Dream company — prioritize!", coverLetter: COVER },
  { id: 7,  title: "AI Research Intern – NLP",         company: "Apple",           location: "Cupertino, CA",     score: 0.88, status: "ready",    source: "linkedin",    url: "#", description: JD_LOREM, starred: false, dateApplied: null,         notes: "", coverLetter: COVER },
  { id: 8,  title: "Generative AI Intern",             company: "Adobe Research",  location: "San Jose, CA",      score: 0.82, status: "ready",    source: "intern_list", url: "#", description: JD_LOREM, starred: false, dateApplied: null,         notes: "", coverLetter: COVER },
  { id: 14, title: "Computer Vision Intern",           company: "Tesla",           location: "Palo Alto, CA",     score: 0.83, status: "interview", source: "intern_list", url: "#", description: JD_LOREM, starred: true,  dateApplied: "2026-02-20", notes: "Interview scheduled April 28", interviewDate: "2026-04-28" },
  { id: 12, title: "NLP Research Intern",              company: "Microsoft Research", location: "Redmond, WA",    score: 0.85, status: "oa",        source: "linkedin",    url: "#", description: JD_LOREM, starred: false, dateApplied: "2026-03-05", notes: "OA received March 25" },
  { id: 11, title: "AI Safety Research Intern",        company: "Anthropic",       location: "San Francisco, CA", score: 0.92, status: "applied",   source: "intern_list", url: "#", description: JD_LOREM, starred: true,  dateApplied: "2026-03-10", notes: "" },
  { id: 9,  title: "ML Intern – Recommendations",     company: "Spotify",         location: "New York, NY",      score: 0.78, status: "applied",   source: "linkedin",    url: "#", description: JD_LOREM, starred: false, dateApplied: "2026-03-15", notes: "Applied via LinkedIn Easy Apply" },
  { id: 10, title: "Data Science Intern",              company: "Stripe",          location: "San Francisco, CA", score: 0.72, status: "applied",   source: "intern_list", url: "#", description: JD_LOREM, starred: false, dateApplied: "2026-03-20", notes: "Referred by alumni" },
  { id: 13, title: "ML Platform Intern",               company: "Uber",            location: "San Francisco, CA", score: 0.70, status: "rejected",  source: "intern_list", url: "#", description: JD_LOREM, starred: false, dateApplied: "2026-02-28", notes: "Rejected after OA", rejectionStage: "oa" },
  { id: 1,  title: "LLM & Agentic AI Research Intern", company: "HRL Laboratories", location: "Malibu, CA",      score: 0.90, status: "new",       source: "intern_list", url: "#", description: JD_LOREM, starred: true,  dateApplied: null,         notes: "" },
  { id: 2,  title: "Internship – Applied AI Engineer", company: "Infineon Technologies", location: "San Jose, CA", score: 0.75, status: "new",     source: "linkedin",    url: "#", description: JD_LOREM, starred: false, dateApplied: null,         notes: "" },
  { id: 3,  title: "Research Scientist Intern, Gen AI – LLM (PhD)", company: "Meta", location: "Menlo Park, CA", score: 0.75, status: "new",       source: "intern_list", url: "#", description: JD_LOREM, starred: false, dateApplied: null,         notes: "" },
  { id: 4,  title: "Technical Intern, AI Software Engineer", company: "Ampere",  location: "Santa Clara, CA",    score: 0.75, status: "new",       source: "handshake",   url: "#", description: JD_LOREM, starred: false, dateApplied: null,         notes: "" },
  { id: 5,  title: "AI/ML Design Layout Intern",       company: "Analog Devices",  location: "Wilmington, MA",    score: 0.70, status: "new",       source: "linkedin",    url: "#", description: JD_LOREM, starred: false, dateApplied: null,         notes: "" },
  { id: 15, title: "Research Intern – Robotics & ML",  company: "Boston Dynamics", location: "Waltham, MA",      score: 0.67, status: "new",       source: "handshake",   url: "#", description: JD_LOREM, starred: false, dateApplied: null,         notes: "" },
  { id: 16, title: "Applied ML Intern",                company: "Waymo",           location: "Mountain View, CA", score: 0.80, status: "new",       source: "intern_list", url: "#", description: JD_LOREM, starred: false, dateApplied: null,         notes: "" },
  { id: 17, title: "AI Infrastructure Intern",         company: "OpenAI",          location: "San Francisco, CA", score: 0.87, status: "new",       source: "intern_list", url: "#", description: JD_LOREM, starred: false, dateApplied: null,         notes: "" },
  { id: 18, title: "NLP Intern",                       company: "Cohere",          location: "Toronto, ON",       score: 0.82, status: "new",       source: "linkedin",    url: "#", description: JD_LOREM, starred: false, dateApplied: null,         notes: "" },
];

window.STATUS_META = {
  new:       { label: "New",       color: "#6B7280", bg: "rgba(107,114,128,0.15)" },
  ready:     { label: "Ready",     color: "#22C55E", bg: "rgba(34,197,94,0.15)"  },
  approved:  { label: "Approved",  color: "#8B5CF6", bg: "rgba(139,92,246,0.15)" },
  applied:   { label: "Applied",   color: "#3B82F6", bg: "rgba(59,130,246,0.15)" },
  oa:        { label: "OA",        color: "#F59E0B", bg: "rgba(245,158,11,0.15)" },
  interview: { label: "Interview", color: "#EC4899", bg: "rgba(236,72,153,0.15)" },
  offer:     { label: "Offer",     color: "#10B981", bg: "rgba(16,185,129,0.15)" },
  rejected:  { label: "Rejected",  color: "#EF4444", bg: "rgba(239,68,68,0.15)"  },
  skipped:   { label: "Skipped",   color: "#9CA3AF", bg: "rgba(156,163,175,0.15)"},
};
