import json
import logging
import re
from django.conf import settings
from groq import Groq

logger = logging.getLogger(__name__)

def filter_jobs(jobs: list) -> list:
    """
    Given a list of normalized job dicts, calls Groq API (using llama-3.3-70b-versatile) to evaluate relevancy,
    populates relevancy_score and skills_extracted, and filters to keep only those with score >= 0.6.
    On API error or unconfigured key: sets score=0.5, skills=[], and includes the job anyway.
    """
    api_key = getattr(settings, 'GROQ_API_KEY', None)
    client = None
    if api_key and not api_key.startswith("gsk_your_groq_api_key"):
        try:
            client = Groq(api_key=api_key)
        except Exception as init_err:
            logger.error(f"Failed to initialize Groq client: {init_err}")
            client = None
    else:
        logger.warning("GROQ_API_KEY is missing or using default placeholder.")

    filtered = []
    
    for job in jobs:
        title = job.get("title", "")
        jd = job.get("jd_text", "")
        
        prompt = f"""Score this job listing for relevance to a software/AI/backend engineering role.
Title: {title}
Description: {jd[:500]}
Return only JSON: {{"score": 0.85, "skills": ["Python", "FastAPI"]}}"""

        if client:
            try:
                chat_completion = client.chat.completions.create(
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a strict technical job matching evaluator. Output only valid JSON with keys: 'score' and 'skills'. No conversational text, no wrappers, just raw JSON."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    model="llama-3.3-70b-versatile",
                    temperature=0.0,
                    max_tokens=200,
                    response_format={"type": "json_object"}
                )
                
                content_text = chat_completion.choices[0].message.content.strip()
                
                # Clean markdown code blocks formatting if present
                if "```" in content_text:
                    json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', content_text, re.DOTALL)
                    if json_match:
                        content_text = json_match.group(1)
                
                data = json.loads(content_text.strip())
                
                score = float(data.get("score", 0.5))
                skills = list(data.get("skills", []))
                
                job["relevancy_score"] = score
                job["skills_extracted"] = skills
                
            except Exception as e:
                logger.error(f"Error calling Groq API for job '{title}': {e}")
                # On API error: set score=0.5, skills=[], include the job anyway
                job["relevancy_score"] = 0.5
                job["skills_extracted"] = []
        else:
            # On API missing / error: set score=0.5, skills=[], include the job anyway
            job["relevancy_score"] = 0.5
            job["skills_extracted"] = []
            
        # Return only jobs with score >= 0.6 OR included on API error/missing key (score=0.5)
        if job["relevancy_score"] >= 0.6 or (not client and job["relevancy_score"] == 0.5) or job.get("skills_extracted") == []:
            filtered.append(job)
            
    return filtered
