import re
import os
import smtplib
import socket
import logging
import requests
import dns.resolver
from typing import List, Dict, Any
from django.utils import timezone
from jobs.models import Job
from .models import Contact

logger = logging.getLogger(__name__)

# Prefixes to filter out as generic/non-outreach emails
FILTER_PREFIXES = ('noreply@', 'support@', 'info@', 'help@', 'contact@', 'admin@', 'donotreply@', 'no-reply@')

def extract_from_jd(jd_text: str) -> List[Dict[str, Any]]:
    """Extract emails from job description text via regex."""
    if not jd_text:
        return []

    # Match standard email addresses
    raw_emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', jd_text)
    
    extracted = []
    seen = set()
    for e in raw_emails:
        email_clean = e.lower().strip()
        if email_clean in seen:
            continue
        if any(email_clean.startswith(prefix) for prefix in FILTER_PREFIXES):
            continue
        seen.add(email_clean)
        extracted.append({
            'email': email_clean,
            'source': 'jd_extract',
            'confidence_score': 1.0,
            'smtp_status': 'valid',
        })

    return extracted


def find_via_hunter(domain: str) -> List[Dict[str, Any]]:
    """Query Hunter.io API for HR and management contacts at domain."""
    api_key = os.getenv('HUNTER_API_KEY', '').strip()
    if not api_key or not domain:
        return []

    # Clean domain name
    domain_clean = domain.replace('http://', '').replace('https://', '').replace('www.', '').split('/')[0].strip()
    if not domain_clean:
        return []

    contacts = []
    seen = set()

    for dept in ['hr', 'management']:
        try:
            url = f"https://api.hunter.io/v2/domain-search?domain={domain_clean}&department={dept}&api_key={api_key}"
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                emails_list = data.get('data', {}).get('emails', [])
                for item in emails_list:
                    email = item.get('value', '').lower().strip()
                    if email and email not in seen:
                        seen.add(email)
                        contacts.append({
                            'email': email,
                            'first_name': item.get('first_name', '') or '',
                            'last_name': item.get('last_name', '') or '',
                            'title': item.get('position', '') or '',
                            'department': item.get('department', '') or dept,
                            'source': 'hunter',
                            'confidence_score': 0.9,
                            'smtp_status': 'valid' if item.get('verification', {}).get('status') == 'valid' else 'risky',
                        })
        except Exception as err:
            logger.error(f"Error querying Hunter.io API for domain {domain_clean} dept {dept}: {err}")

    return contacts


def generate_smtp_patterns(domain: str) -> List[str]:
    """Generate candidate HR and recruiter emails for a domain."""
    if not domain:
        return []
    
    clean_domain = domain.replace('http://', '').replace('https://', '').replace('www.', '').split('/')[0].strip()
    if not clean_domain:
        return []

    return [
        f"hr@{clean_domain}",
        f"careers@{clean_domain}",
        f"hiring@{clean_domain}",
        f"talent@{clean_domain}",
        f"recruit@{clean_domain}",
        f"jobs@{clean_domain}",
        f"people@{clean_domain}",
    ]


def verify_smtp(email: str) -> str:
    """
    Verify email via DNS MX lookup & SMTP RCPT TO check.
    Returns: 'valid', 'risky', 'catch_all', or 'not_found'.
    """
    try:
        domain = email.split('@')[1]
    except IndexError:
        return 'not_found'

    # Step 1: DNS MX Record Lookup
    try:
        answers = dns.resolver.resolve(domain, 'MX')
        mx_records = sorted(answers, key=lambda r: r.preference)
        if not mx_records:
            return 'not_found'
        mx_host = str(mx_records[0].exchange).rstrip('.')
    except Exception as err:
        logger.debug(f"DNS MX lookup failed for {domain}: {err}")
        return 'not_found'

    # Step 2 & 3: SMTP Probe
    try:
        with smtplib.SMTP(timeout=10) as smtp:
            smtp.connect(mx_host, 25)
            smtp.helo(socket.getfqdn())
            smtp.mail('verify@example.com')

            # Step 2: Probe random address to detect catch-all server
            random_probe = f"zxq9k2mhf8@{domain}"
            code_catch_all, _ = smtp.rcpt(random_probe)
            if code_catch_all == 250:
                return 'catch_all'

            # Step 3: Check candidate email
            code, _ = smtp.rcpt(email)
            if code == 250:
                return 'valid'
            elif code in (550, 551, 553):
                return 'not_found'
            else:
                return 'risky'

    except Exception as err:
        logger.debug(f"SMTP verification exception for {email} on {mx_host}: {err}")
        return 'risky'


def find_emails_for_job(job_id: str) -> List[Contact]:
    """Find contacts for a job from JD, Hunter.io, and SMTP pattern verification."""
    try:
        job = Job.objects.get(id=job_id)
    except Job.DoesNotExist:
        return []

    all_raw_contacts: Dict[str, Dict[str, Any]] = {}

    # 1. Extract from Job Description
    jd_contacts = extract_from_jd(job.jd_text)
    for item in jd_contacts:
        all_raw_contacts[item['email']] = item

    # 2. Hunter.io API lookup
    if job.company_domain:
        hunter_contacts = find_via_hunter(job.company_domain)
        for item in hunter_contacts:
            if item['email'] not in all_raw_contacts:
                all_raw_contacts[item['email']] = item

    # 3. Generate & verify SMTP patterns
    if job.company_domain:
        patterns = generate_smtp_patterns(job.company_domain)
        for candidate in patterns:
            if candidate not in all_raw_contacts:
                status = verify_smtp(candidate)
                if status in ('valid', 'risky', 'catch_all'):
                    is_catch = (status == 'catch_all')
                    score = 0.8 if status == 'valid' else (0.5 if is_catch else 0.6)
                    all_raw_contacts[candidate] = {
                        'email': candidate,
                        'source': 'smtp_pattern',
                        'smtp_status': status,
                        'is_catch_all': is_catch,
                        'confidence_score': score,
                    }

    # 4. Save to Database
    saved_contacts = []
    now = timezone.now()

    for email_key, data in all_raw_contacts.items():
        contact, _ = Contact.objects.update_or_create(
            job=job,
            email=email_key,
            defaults={
                'first_name': data.get('first_name', ''),
                'last_name': data.get('last_name', ''),
                'title': data.get('title', ''),
                'department': data.get('department', ''),
                'source': data.get('source', 'smtp_pattern'),
                'smtp_status': data.get('smtp_status', 'unverified'),
                'is_catch_all': data.get('is_catch_all', False),
                'confidence_score': data.get('confidence_score', 0.5),
                'verified_at': now,
            }
        )
        saved_contacts.append(contact)

    saved_contacts.sort(key=lambda c: c.confidence_score, reverse=True)
    return saved_contacts
