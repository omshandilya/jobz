import json
import logging
import re
from django.conf import settings
from anthropic import Anthropic

logger = logging.getLogger(__name__)

def filter_jobs(jobs: list) -> list:
    """
    Given a list of normalized job dicts, calls Anthropic Claude API to evaluate relevancy,
    populates relevancy_score and skills_extracted, and filters to keep only those with score >= 0.6.
    """
    api_key = getattr(settings, 'ANTHROPIC_API_KEY', None)
    if not api_key or api_key == "your_anthropic_api_key_here":
        logger.warning("Anthropic API key is not set or using placeholder. Defaulting all jobs to score 0.5")
        for job in jobs:
            job["relevancy_score"] = 0.5
            job["skills_extracted"] = []
        # Return empty because all jobs score 0.5 which is < 0.6.
        # But if you want to test without a valid API key, maybe allow a fallback mode or keep all.
        # Requirement: "only return jobs with score >= 0.6. Handle API errors gracefully, default score 0.5 on failure."
        return []

    try:
        client = Anthropic(api_key=api_key)
    except Exception as init_err:
        logger.error(f"Failed to initialize Anthropic client: {init_err}")
        for job in jobs:
            job["relevancy_score"] = 0.5
            job["skills_extracted"] = []
        return []

    filtered = []
    
    for job in jobs:
        title = job.get("title", "")
        jd = job.get("jd_text", "")
        
        prompt = f"""Given this job title and description, score relevance from 0.0 to 1.0 for a software engineering/AI/backend role. Return only a JSON: {{"score": 0.85, "skills": ["Python", "FastAPI", "RAG"]}}

Title: {title}
Description: {jd}
"""
        try:
            message = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=200,
                temperature=0.0,
                system="You are a strict technical job matching evaluator. Output only valid JSON with keys: 'score' and 'skills'. No conversational text, no wrappers, just raw JSON.",
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            content_text = message.content[0].text.strip()
            
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
            logger.error(f"Error calling Anthropic API for job '{title}': {e}")
            job["relevancy_score"] = 0.5
            job["skills_extracted"] = []
            
        if job["relevancy_score"] >= 0.6:
            filtered.append(job)
            
    return filtered
