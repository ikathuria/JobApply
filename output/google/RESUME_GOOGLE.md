# Ishani Kathuria — Google-tuned résumé

Built only from `config/profile.json` — nothing invented. This is the *framing*
to use for Google; your pipeline's `resume_tailor.py` will apply the same
emphasis per req (quantified impact + ATS keyword mirroring + CS-fundamentals /
research foregrounding — just updated).

**How Google screens new-grad candidates**, in priority order:
1. Coding + CS fundamentals (DS&A, complexity) — the interview loop lives here.
2. Evidence of impact at scale, quantified.
3. Role-specific depth: distributed systems (SWE) or publications/research (MLE/Research).

You have all three. The job is to put them where a 10-second scan lands.

---

Ishani Kathuria · Hammond, IN · [[phone]] · ishani@kathuria.net
linkedin.com/in/ishani-kathuria · github.com/ikathuria · ishani.kathuria.net

### Summary — pick one per req

**SWE / MLE, Early Career:**
> Ex-AWS SDE (2 yrs) and MS Applied AI candidate (4.0 GPA) who ships production
> ML systems at scale — from LLM tooling that cut root-cause time 80% to
> distributed-systems work that saved $50K/month. Strong in data structures,
> algorithms, and large-scale distributed systems across Python, Go, and Java.

**Student Researcher / Research (BS/MS):**
> Applied-AI researcher (4.0 GPA, 4 publications) working on retrieval-augmented
> generation — retrieval quality, hallucination reduction, and latency — with two
> years of production ML engineering at AWS behind it.

### Education
- **MS, Applied Artificial Intelligence**, Purdue University Northwest — GPA **4.0/4.0** — Aug 2025–May 2027
- **BTech, Artificial Intelligence**, Amity University — GPA 9.09/10 — 2019–2023

### Experience

**Software Development Engineer — Amazon Web Services** · Jul 2023–Jul 2025
*(Lead with scale + quantified impact — this is your strongest Google signal.)*
- Built and deployed production **LLM-based log-summarization** systems, cutting root-cause analysis time from 2.5 hrs to 30 min (**80% faster**).
- Optimized **distributed-system** scripts, cutting CPU/memory usage **50%** and lowering infra cost **$50K/month**.
- Automated region-build and deployment pipelines for **15+ OpenSearch services**, reducing manual intervention **80%** and accelerating launches by 3 weeks.
- Built proactive anomaly/bug-detection systems, reducing customer-reported issues **30%** pre-release.
- Designed internal AI developer-support chatbots, improving resolution efficiency **40%**.

**AI Research Assistant — Purdue University** · Sep 2025–Present
- Applied research on **RAG** systems: retrieval quality, hallucination reduction, end-to-end latency for LLM apps.
- Evaluate retrieval strategies with **Recall@K** and **nDCG** for real-world QA.

### Projects (pick 2–3 per req)
- **TrustworthyRAG** — query-adaptive learned fusion routing across vector/graph/keyword retrieval; multimodal KG for multi-hop reasoning.
- **AutoRedTeam** — multi-agent adversarial eval framework (Attacker/Target/Judge) to stress-test LLM safety; provider-agnostic (GPT-4, Gemini, Llama 3).
- **DeepFakeGuard** — client-side synthetic-audio detection with Transformers.js; sub-second in-browser inference.

### Skills
- **Languages:** Python, Go, Java, TypeScript
- **CS fundamentals:** Data Structures & Algorithms, Distributed Systems, System Design, Scalability, Concurrency
- **GenAI/ML:** LLMs, RAG, Fine-Tuning, Multi-Agent Systems, PyTorch, TensorFlow, LangChain, HuggingFace
- **Cloud/MLOps:** AWS (Bedrock, Lambda, ECS, Step Functions, CloudFormation, CloudWatch), Azure

### Publications (4) — foreground for Research/MLE reqs
- Conversational AI for Supporting Children with Autism — Springer 2025
- Temperature-Based Food Recommendation using AI — IEEE 2023
- Deep Learning in Healthcare — Springer 2023
- PM2.5 Prediction using Azure ML Studio — IEEE 2022

### Certifications
AWS Certified AI Practitioner · AWS Certified Cloud Practitioner

---

## What changed vs. your default résumé, and why

- **CS-fundamentals line added** (DS&A, distributed systems, system design). You
  have this from AWS; Google's ATS and interviewers scan for it explicitly. Added
  to `config/profile.json` so every tailored résumé now carries it.
- **Impact numbers pulled to the front of each bullet.** They were already in
  your profile — Google weights measurable outcomes heavily, so they lead now.
- **Two summary variants.** Google splits SWE/MLE from Student Researcher; your
  publications make the Research path genuinely open — don't waste it by sending
  the SWE summary to a research req.

## One honest gap to close before applying

Nothing on your résumé signals **competitive-coding / DS&A readiness**, which is
what the Google loop actually tests. It won't hurt the résumé — but budget 6–8
weeks of LeetCode-style prep (patterns, not grinding) before you accept a loop.
That, not the paper, is where new-grad Google offers are won or lost.
