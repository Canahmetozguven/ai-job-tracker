import pytest
from user_profile import load_profile
from job_loader import load_jobs, count_jobs
from telegram_notify import format_job_analysis, parse_gemini_response

def test_load_profile(tmp_path):
    """Test profile loading."""
    p = tmp_path / "profile.txt"
    p.write_text("Python developer with 5 years experience")
    assert load_profile(str(p)) == "Python developer with 5 years experience"

def test_load_profile_empty(tmp_path):
    """Test empty profile raises error? Or returns empty string?"""
    p = tmp_path / "profile.txt"
    p.write_text("")
    # Empty profile is still valid
    assert load_profile(str(p)) == ""

def test_load_jobs_single(tmp_path):
    """Test loading single job."""
    f = tmp_path / "jobs.jsonl"
    f.write_text('{"title": "Dev", "company": "Acme"}')
    jobs = list(load_jobs(str(f)))
    assert len(jobs) == 1
    assert jobs[0]['title'] == 'Dev'

def test_load_jobs_multiple(tmp_path):
    """Test loading multiple jobs."""
    f = tmp_path / "jobs.jsonl"
    f.write_text('{"title": "Dev", "company": "Acme"}\n{"title": "Eng", "company": "Beta"}')
    jobs = list(load_jobs(str(f)))
    assert len(jobs) == 2
    assert jobs[0]['title'] == 'Dev'
    assert jobs[1]['title'] == 'Eng'

def test_load_jobs_ignores_invalid_json(tmp_path):
    """Test that invalid JSON lines are skipped."""
    f = tmp_path / "jobs.jsonl"
    f.write_text('{"title": "Dev"}\ninvalid json\n{"title": "Eng"}')
    jobs = list(load_jobs(str(f)))
    assert len(jobs) == 2

def test_count_jobs(tmp_path):
    """Test job counting."""
    f = tmp_path / "jobs.jsonl"
    f.write_text('{"title": "Dev"}\n{"title": "Eng"}\n{"title": "QA"}')
    assert count_jobs(str(f)) == 3

def test_parse_gemini_response_complete():
    """Test parsing a complete Gemini response."""
    text = """1. FIT SCORE: 8/10
2. WHY GOOD: Great match for my Python skills
3. WHY BAD: Salary is below my期望
4. RECOMMENDATION: Apply"""
    result = parse_gemini_response(text)
    assert result['score'] == '8/10'
    assert 'Python skills' in result['why_good']
    assert 'Salary' in result['why_bad']
    assert result['recommendation'] == 'Apply'

def test_parse_gemini_response_partial():
    """Test parsing response with missing fields."""
    text = """1. FIT SCORE: 7/10
3. WHY BAD: Not a good fit"""
    result = parse_gemini_response(text)
    assert result['score'] == '7/10'
    assert result['why_good'] == 'N/A'
    assert 'Not a good fit' in result['why_bad']

def test_format_job_analysis():
    """Test formatting job analysis as Telegram message."""
    job = {
        'title': 'Senior Python Developer',
        'company': 'TechCorp',
        'location': 'San Francisco, CA',
        'job_url': 'https://example.com/job/123'
    }
    analysis = {
        'score': '9/10',
        'why_good': 'Perfect match for my Django and AWS experience',
        'why_bad': 'Might be too senior for my level',
        'recommendation': 'Apply'
    }
    msg = format_job_analysis(job, analysis)

    assert 'Senior Python Developer' in msg
    assert 'TechCorp' in msg
    assert 'San Francisco' in msg
    assert '9/10' in msg
    assert 'Django and AWS' in msg
    assert 'Apply' in msg