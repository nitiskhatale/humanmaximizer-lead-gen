"""
ContactFinderTool — extracts decision-maker names, titles, and emails
from raw scraped text using regex and keyword matching.

No third-party enrichment API required for demo.
"""
import re
from typing import Any

# Job titles that indicate HRMS buying authority
_DM_TITLE_PATTERNS = [
    r"\bCHRO\b",
    r"\bChief\s+Human\s+Resources\s+Officer\b",
    r"\bChief\s+People\s+Officer\b",
    r"\bCPO\b",
    r"\bVP\s+HR\b",
    r"\bVP\s+Human\s+Resources\b",
    r"\bHead\s+of\s+HR\b",
    r"\bHead\s+of\s+People\b",
    r"\bHR\s+Director\b",
    r"\bDirector\s+(?:of\s+)?HR\b",
    r"\bDirector\s+(?:of\s+)?Human\s+Resources\b",
    r"\bHR\s+Manager\b",
    r"\bPeople\s+Manager\b",
    r"\bTalent\s+Acquisition\s+(?:Head|Director|VP)\b",
    r"\bFounder\b",
    r"\bCo-?Founder\b",
    r"\bCEO\b",
    r"\bManaging\s+Director\b",
]

_EMAIL_PATTERN = re.compile(
    r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}"
)


class ContactFinderTool:
    def find(self, text: str, domain: str = "") -> list[dict[str, Any]]:
        """
        Scan text for decision makers and email addresses.

        Returns a list of dicts:
            {name, title, email, linkedin_url, confidence}
        """
        if not text:
            return []

        emails_found = _EMAIL_PATTERN.findall(text)
        domain_emails = [
            e for e in emails_found
            if domain and domain.lower() in e.lower()
        ] if domain else emails_found

        contacts: list[dict[str, Any]] = []
        seen_titles: set[str] = set()
        seen_names: set[str] = set()

        for pattern_str in _DM_TITLE_PATTERNS:
            title_re = re.compile(pattern_str, re.IGNORECASE)
            for match in title_re.finditer(text):
                title_text = match.group(0)
                if title_text.lower() in seen_titles:
                    continue
                seen_titles.add(title_text.lower())

                context_start = max(0, match.start() - 150)
                context = text[context_start: match.start() + len(title_text) + 50]
                name = _extract_name_near_title(context, title_text)
                if name and name != "Unknown":
                    if name.lower() in seen_names:
                        continue
                    seen_names.add(name.lower())
                email = domain_emails[0] if domain_emails else None
                confidence = _compute_confidence(name, email)

                contacts.append({
                    "name": name or "Unknown",
                    "title": title_text,
                    "email": email,
                    "linkedin_url": None,
                    "confidence": confidence,
                })

        if not contacts and domain_emails:
            contacts.append({
                "name": "Unknown",
                "title": "HR Contact",
                "email": domain_emails[0],
                "linkedin_url": None,
                "confidence": 0.3,
            })

        return contacts[:3]


def _extract_name_near_title(context: str, title: str) -> str | None:
    pattern = re.compile(
        r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})\s*[,\-–|:]\s*"
        + re.escape(title),
        re.IGNORECASE,
    )
    m = pattern.search(context)
    if m:
        return m.group(1).strip()

    words_before = context[: context.lower().find(title.lower())].strip()
    cap_pattern = re.compile(r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})$")
    m2 = cap_pattern.search(words_before)
    if m2:
        return m2.group(1).strip()

    return None


def _compute_confidence(name: str | None, email: str | None) -> float:
    score = 0.4  # base: title found
    if name and name != "Unknown":
        score += 0.4
    if email:
        score += 0.2
    return round(score, 2)
