"""
Unit tests for ContactFinderTool and ScraperTool.
No network calls, no LLM.
"""
import pytest

from tools.contact_finder import ContactFinderTool
from tools.scraper import ScraperTool


class TestContactFinderTool:
    def test_extracts_vp_hr_title(self):
        text = "Our VP HR, Ravi Sharma, leads the talent team at example.com."
        contacts = ContactFinderTool().find(text, "example.com")
        titles = [c.get("title", "") for c in contacts]
        assert any("VP HR" in t or "vp hr" in t.lower() for t in titles)

    def test_extracts_chro_title(self):
        text = "Priya Mehta is the CHRO responsible for 5000 employees."
        contacts = ContactFinderTool().find(text, "company.com")
        titles = [c.get("title", "").upper() for c in contacts]
        assert any("CHRO" in t for t in titles)

    def test_empty_text_returns_empty_list(self):
        contacts = ContactFinderTool().find("", "company.com")
        assert isinstance(contacts, list)
        assert len(contacts) == 0

    def test_returns_at_most_three_contacts(self):
        text = (
            "CHRO John. VP HR Mary. HR Director Bob. HR Manager Alice. "
            "Head of HR Carol. Talent Acquisition Lead Dan."
        )
        contacts = ContactFinderTool().find(text, "corp.com")
        assert len(contacts) <= 3

    def test_contact_has_required_keys(self):
        text = "Our VP HR Ananya Kapoor can be reached at ananya@acme.com."
        contacts = ContactFinderTool().find(text, "acme.com")
        if contacts:
            c = contacts[0]
            assert "title" in c
            assert "confidence" in c


class TestScraperTool:
    def test_blocked_domain_returns_empty(self):
        result = ScraperTool().scrape("https://www.linkedin.com/company/example")
        assert isinstance(result, dict)
        assert result["text"] == ""

    def test_facebook_blocked(self):
        result = ScraperTool().scrape("https://www.facebook.com/example")
        assert isinstance(result, dict)
        assert result["text"] == ""

    def test_twitter_blocked(self):
        result = ScraperTool().scrape("https://twitter.com/example")
        assert isinstance(result, dict)
        assert result["text"] == ""

    def test_non_http_url_returns_empty(self):
        result = ScraperTool().scrape("ftp://example.com/data")
        assert isinstance(result, dict)
        assert result["text"] == ""

    def test_scrape_result_has_text_and_company_name_keys(self):
        result = ScraperTool().scrape("https://www.linkedin.com/blocked")
        assert "text" in result
        assert "company_name" in result
