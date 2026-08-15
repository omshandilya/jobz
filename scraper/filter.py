import json
import logging
import re
import time
from django.conf import settings
from groq import Groq

logger = logging.getLogger(__name__)

# Groq free tier: 30 RPM. Sleep 2.1s between calls to stay safely under limit.
_GROQ_CALL_INTERVAL = 2.1  # seconds between each API call
_GROQ_RATE_LIMIT_BACKOFF = 62  # seconds to sleep on 429 before retrying


def filter_jobs(jobs: list) -> list:
    """
    Given a list of normalized job dicts, calls Groq API (llama-3.3-70b-versatile) to score
    each job for relevancy. Keeps only jobs with score >= 0.6.

    Rate limiting: sleeps 2.1s between every API call to stay under Groq's 30 RPM limit.
    On 429: sleeps 62s and retries once. On other errors: excludes the job.
    """
    api_key = getattr(settings, 'GROQ_API_KEY', None)
    client = None
    if api_key and not api_key.startswith("gsk_your_groq_api_key"):
        try:
            client = Groq(api_key=api_key)
        except Exception as init_err:
            logger.error(f"Failed to initialize Groq client: {init_err}")
    else:
        logger.warning("GROQ_API_KEY is missing or using default placeholder.")

    filtered = []
    call_count = 0

    for job in jobs:
        title = job.get("title", "")
        jd = job.get("jd_text", "")

        if not client:
            job["relevancy_score"] = 0.5
            job["skills_extracted"] = []
            # No Groq client — exclude job (score < 0.6)
            continue

        # Rate-limit gate: sleep before each call (except the first)
        if call_count > 0:
            time.sleep(_GROQ_CALL_INTERVAL)
        call_count += 1

        prompt = f"""Score this job listing for relevance to a software/AI/backend engineering role.
Title: {title}
Description: {jd[:500]}
Return only JSON: {{"score": 0.85, "skills": ["Python", "FastAPI"]}}"""

        def _call_groq():
            """Inner helper so we can retry on 429 without code duplication."""
            return client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a strict technical job matching evaluator. "
                            "Output only valid JSON with keys: 'score' and 'skills'. "
                            "No conversational text, no wrappers, just raw JSON."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                model="llama-3.3-70b-versatile",
                temperature=0.0,
                max_tokens=200,
                response_format={"type": "json_object"},
            )

        try:
            chat_completion = _call_groq()

        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "rate_limit_exceeded" in err_str:
                logger.warning(
                    f"Groq 429 on '{title}' (call #{call_count}). "
                    f"Sleeping {_GROQ_RATE_LIMIT_BACKOFF}s then retrying..."
                )
                time.sleep(_GROQ_RATE_LIMIT_BACKOFF)
                try:
                    chat_completion = _call_groq()
                except Exception as retry_e:
                    logger.error(f"Groq retry also failed for '{title}': {retry_e}")
                    job["relevancy_score"] = 0.5
                    job["skills_extracted"] = []
                    continue
            else:
                logger.error(f"Groq API error for '{title}': {e}")
                job["relevancy_score"] = 0.5
                job["skills_extracted"] = []
                continue

        # Parse the response
        try:
            content_text = chat_completion.choices[0].message.content.strip()

            if "```" in content_text:
                json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', content_text, re.DOTALL)
                if json_match:
                    content_text = json_match.group(1)

            data = json.loads(content_text.strip())
            score = float(data.get("score", 0.5))
            skills = list(data.get("skills", []))

        except Exception as parse_err:
            logger.error(f"Failed to parse Groq response for '{title}': {parse_err}")
            score = 0.5
            skills = []

        job["relevancy_score"] = score
        job["skills_extracted"] = skills

        # Only keep jobs that genuinely scored >= 0.6
        if score >= 0.6:
            filtered.append(job)

    logger.info(
        f"filter_jobs: {len(jobs)} input → {call_count} Groq calls → {len(filtered)} passed (≥0.6)"
    )
    return filtered
