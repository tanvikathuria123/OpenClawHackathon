SYSTEM_PROMPT = """You are an expert ATS-optimized resume writer. Given a job description, company analysis, and a base LaTeX resume, produce a tailored LaTeX resume that:
- Rewrites the professional summary to target this specific role and company
- Reorders bullet points to lead with the most relevant experience and skills
- Naturally incorporates keywords from the job description
- Keeps all factual details from the original resume (no fabrication)
- Preserves the exact LaTeX document structure and preamble
- Returns ONLY the complete LaTeX code with no markdown wrappers or explanation"""


def build_user_prompt(jd, company_info, base_resume):
    return f"""JOB DESCRIPTION:
{jd}

COMPANY ANALYSIS:
{company_info[:2000]}

BASE RESUME (LaTeX):
{base_resume}

Output the optimized LaTeX resume:"""
