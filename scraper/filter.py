import json
import logging
import re
import time
from django.conf import settings
from groq import Groq

logger = logging.getLogger(__name__)

# ─── Model choice ────────────────────────────────────────────────────────────
# llama-3.1-8b-instant: 20k RPM, 500k TPD (free tier) — ideal for batch scoring
# llama-3.3-70b-versatile: 30 RPM, 100k TPD — was exhausted after ~80 jobs
_MODEL = "llama-3.1-8b-instant"

# Groq free tier for 8b-instant: 20k RPM → no need for sleep, but add a tiny
# buffer to be safe. Reduce to 0.1s — 5x faster than before.
_GROQ_CALL_INTERVAL = 0.15  # seconds between batched calls
_GROQ_RATE_LIMIT_BACKOFF = 30  # seconds to sleep on 429 before retrying
_BATCH_SIZE = 10  # jobs scored per single API call (90% reduction in calls)

# ─── Keyword pre-filter ───────────────────────────────────────────────────────
# Jobs whose titles match ANY of these patterns are immediately scored 0.0
# and excluded — no Groq call needed at all. This eliminates the biggest waste:
# Indeed returning "Sales Manager", "Retail Associate" etc for tech queries.
_IRRELEVANT_TITLE_PATTERNS = re.compile(
    r'\b('
    r'sales|retail|counter|field staff|visa|telecaller|telesales|'
    r'bpo|voice process|non.?voice|back.?office|'
    r'digital media handler|social media manager|'
    r'customer care|customer support|customer service|'
    r'logistics|e.?commerce executive|delivery|driver|'
    r'accountant|billing|finance executive|ca |'
    r'receptionist|front desk|admin assistant|'
    r'teacher|faculty|trainer|lecturer|'
    r'civil engineer|mechanical engineer|electrical engineer|'
    r'hotel|hospitality|housekeeping|chef|cook|'
    r'nursing|pharmacist|doctor|dentist'
    r')\b',
    re.IGNORECASE
)

# ─── Tech keyword boost (title must match at least one for auto-pass) ─────────
# If title clearly matches the tech domain, skip Groq and auto-score 0.85.
_TECH_TITLE_PATTERNS = re.compile(
    r'\b('
    r'engineer|developer|programmer|software|backend|frontend|full.?stack|'
    r'ai|ml|machine learning|deep learning|llm|nlp|data scien|data engineer|'
    r'scientist|researcher|'
    r'devops|sre|platform|cloud|infrastructure|'
    r'python|django|node|react|angular|java|golang|rust|'
    r'android|ios|mobile|flutter|'
    r'architect|tech lead|principal engineer|staff engineer|'
    r'analyst|data analyst|business analyst|product manager|product owner|'
    r'intern|trainee'
    r')\b',
    re.IGNORECASE
)


def _keyword_prefilter(jobs: list, user_query: str) -> tuple[list, list]:
    """
    Fast O(n) pre-filter using regex. No API calls.

    Returns:
        (jobs_for_groq, already_decided)
        - jobs_for_groq: jobs that need Groq scoring
        - already_decided: jobs with score already set (0.0 excluded or 0.85 auto-passed)
    """
    needs_groq = []
    decided = []
    query_words = set(re.findall(r'\w+', user_query.lower()))

    for job in jobs:
        title = job.get("title", "")

        # Rule 1: Irrelevant title → exclude immediately (score 0.0)
        if _IRRELEVANT_TITLE_PATTERNS.search(title):
            job["relevancy_score"] = 0.0
            job["skills_extracted"] = []
            decided.append(("excluded_keyword", job))
            continue

        # Rule 2: Title clearly matches tech domain → auto-score 0.85
        if _TECH_TITLE_PATTERNS.search(title):
            job["relevancy_score"] = 0.85
            job["skills_extracted"] = []  # Groq will fill this for passed jobs
            decided.append(("auto_passed", job))
            continue

        # Rule 3: Everything else goes to Groq
        needs_groq.append(job)

    return needs_groq, decided


def filter_jobs(jobs: list, user_query: str = "") -> list:
    """
    Scores jobs for relevancy using a 3-stage pipeline:

    Stage 1 — Keyword pre-filter (free, instant):
        - Clearly irrelevant titles (sales, retail, etc.) → score 0.0, excluded
        - Clearly tech titles → auto-score 0.85, passed (saves ~60% of Groq calls)

    Stage 2 — Groq batch scoring (10 jobs per API call):
        - Remaining ambiguous jobs sent to llama-3.1-8b-instant
        - 90% fewer calls vs old 1-job-per-call approach
        - 500k TPD limit (5x more headroom vs old 100k TPD model)

    Stage 3 — Score threshold (>= 0.6 passes)

    Args:
        jobs: list of normalized job dicts
        user_query: the original search query (used to improve pre-filter context)
    """
    if not jobs:
        return []

    api_key = getattr(settings, 'GROQ_API_KEY', None)
    client = None
    if api_key and not api_key.startswith("gsk_your_groq_api_key"):
        try:
            client = Groq(api_key=api_key)
        except Exception as init_err:
            logger.error(f"Failed to initialize Groq client: {init_err}")
    else:
        logger.warning("GROQ_API_KEY missing or placeholder — skipping Groq scoring.")

    # ── Stage 1: Keyword pre-filter ──────────────────────────────────────────
    needs_groq, decided = _keyword_prefilter(jobs, user_query)

    auto_passed = [j for label, j in decided if label == "auto_passed"]
    excluded_kw = [j for label, j in decided if label == "excluded_keyword"]

    logger.info(
        f"Pre-filter: {len(jobs)} input → "
        f"{len(auto_passed)} auto-passed, "
        f"{len(excluded_kw)} excluded (keywords), "
        f"{len(needs_groq)} sent to Groq"
    )

    # ── Stage 2: Groq batch scoring ──────────────────────────────────────────
    groq_passed = []
    call_count = 0

    if client and needs_groq:
        # Process in batches of _BATCH_SIZE
        for batch_start in range(0, len(needs_groq), _BATCH_SIZE):
            batch = needs_groq[batch_start: batch_start + _BATCH_SIZE]

            # Build compact batch prompt — short JD snippets to save tokens
            job_lines = []
            for i, job in enumerate(batch):
                title = job.get("title", "")
                jd_snippet = job.get("jd_text", "")[:250].replace("\n", " ")
                job_lines.append(f'{i+1}. Title: "{title}" | JD: "{jd_snippet}"')

            batch_prompt = (
                f'Rate each job\'s relevance to a "{user_query or "software/tech/AI"}" role.\n'
                f'For each job, output a JSON object with "id" (1-based), "score" (0.0-1.0), '
                f'and "skills" (array of strings).\n'
                f'Output a JSON array of objects only. No text outside the array.\n\n'
                + "\n".join(job_lines)
            )

            # Rate-limit sleep between batches (not first)
            if call_count > 0:
                time.sleep(_GROQ_CALL_INTERVAL)
            call_count += 1

            def _call_groq_batch(prompt=batch_prompt):
                return client.chat.completions.create(
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "You are a strict technical job relevancy scorer. "
                                "Output ONLY a valid JSON array. "
                                "Each element: {\"id\": <int>, \"score\": <float 0-1>, \"skills\": [<strings>]}. "
                                "Do not output anything else."
                            ),
                        },
                        {"role": "user", "content": prompt},
                    ],
                    model=_MODEL,
                    temperature=0.0,
                    max_tokens=1500,  # Ensure enough tokens for 10 jobs JSON output
                )

            # Call with retry on 429
            try:
                response = _call_groq_batch()
            except Exception as e:
                err_str = str(e)
                if "429" in err_str or "rate_limit_exceeded" in err_str:
                    logger.warning(
                        f"Groq 429 on batch #{call_count} (jobs {batch_start+1}-{batch_start+len(batch)}). "
                        f"Sleeping {_GROQ_RATE_LIMIT_BACKOFF}s then retrying..."
                    )
                    time.sleep(_GROQ_RATE_LIMIT_BACKOFF)
                    try:
                        response = _call_groq_batch()
                    except Exception as retry_e:
                        logger.error(f"Groq retry failed for batch #{call_count}: {retry_e}")
                        # Exclude all jobs in this batch
                        for job in batch:
                            job["relevancy_score"] = 0.5
                            job["skills_extracted"] = []
                        continue
                else:
                    logger.error(f"Groq API error for batch #{call_count}: {e}")
                    for job in batch:
                        job["relevancy_score"] = 0.5
                        job["skills_extracted"] = []
                    continue

            # Parse response
            try:
                content = response.choices[0].message.content.strip()

                # Strip markdown fences if present
                if "```" in content:
                    match = re.search(r'```(?:json)?\s*(\[.*?\])\s*```', content, re.DOTALL)
                    if match:
                        content = match.group(1)

                results = json.loads(content)
                if not isinstance(results, list):
                    raise ValueError(f"Expected list, got {type(results)}")

                # Map results back to jobs by 1-based id
                result_map = {r.get("id"): r for r in results if isinstance(r, dict)}

                for i, job in enumerate(batch):
                    r = result_map.get(i + 1, {})
                    score = float(r.get("score", 0.5))
                    skills = list(r.get("skills", []))
                    job["relevancy_score"] = score
                    job["skills_extracted"] = skills
                    if score >= 0.6:
                        groq_passed.append(job)

            except Exception as parse_err:
                logger.error(f"Failed to parse Groq batch response: {parse_err} | content: {content[:300]!r}")
                for job in batch:
                    job["relevancy_score"] = 0.5
                    job["skills_extracted"] = []

    elif needs_groq:
        # No Groq client — exclude all ambiguous jobs
        for job in needs_groq:
            job["relevancy_score"] = 0.5
            job["skills_extracted"] = []

    # ── Stage 3: Combine results ─────────────────────────────────────────────
    # Auto-passed (keyword matched tech titles) + Groq passed (score >= 0.6)
    final = auto_passed + groq_passed

    logger.info(
        f"filter_jobs summary: {len(jobs)} input | "
        f"pre-filter excluded={len(excluded_kw)}, auto-passed={len(auto_passed)} | "
        f"groq batches={call_count} ({len(needs_groq)} jobs) → groq_passed={len(groq_passed)} | "
        f"total saved={len(final)}"
    )
    return final
