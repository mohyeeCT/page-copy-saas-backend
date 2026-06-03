import re
import time
import json


# ── Sanitiser ─────────────────────────────────────────────────────────────────

def sanitise(text: str, brand_name: str = "") -> str:
    """Strip em dashes, fix brand casing, remove surrounding quotes."""
    if not text:
        return ""
    text = text.replace("\u2014", ",").replace("\u2013 ", ", ")
    text = text.strip().strip('"').strip("'").strip()
    if brand_name:
        text = re.sub(re.escape(brand_name), brand_name, text, flags=re.IGNORECASE)
    return text


# ── Business type context ─────────────────────────────────────────────────────

BUSINESS_TYPE_CONTEXT = {
    "b2b": (
        "This page is for a B2B business targeting other businesses. "
        "Tone: professional and direct. Focus on ROI, efficiency, and business outcomes. "
        "No consumer-facing CTAs. No exclamation marks. No lifestyle language."
    ),
    "b2c": (
        "This page is for a B2C business targeting consumers. "
        "Tone: warm, accessible, and benefit-focused. "
        "CTAs can reference product benefits and lifestyle outcomes."
    ),
    "ecommerce": (
        "This page is for an ecommerce business. "
        "Tone: direct and product-focused. "
        "Copy should support purchase decisions. Avoid vague editorial tone."
    ),
    "service": (
        "This page is for a service business. "
        "Tone: helpful and trustworthy. Focus on expertise, process, and outcomes. "
        "CTAs should invite contact or consultation."
    ),
    "local": (
        "This page is for a local service business. "
        "Tone: community-oriented and accessible. "
        "Reference the service area where natural. CTAs should invite calls or visits."
    ),
    "general": (
        "This page is for a general business. "
        "Tone: clear and professional. Adapt language to the page context."
    ),
}


# ── Prompt builder ────────────────────────────────────────────────────────────

def _build_section_prompt(
    section: dict,
    primary_keyword: str,
    supporting_keyword: str,
    lsi_keywords: list,
    business_type: str,
    brand_name: str,
    h1: str,
    page_type: str,
    paa_questions: list,
    competitor_excerpts: list,
    client_brief: str,
    previous_section_text: str,
    client_existing_content: str,
    ai_overview: str = "",
    forbidden_phrases: str = "",
) -> str:
    kw_slot = section.get("keyword_slot", "none")
    wc_min, wc_max = section.get("word_count", [150, 250])

    if kw_slot == "primary":
        keyword_instruction = f"Include this keyword naturally: {primary_keyword}" if primary_keyword else ""
    elif kw_slot == "supporting":
        keyword_instruction = f"Include this keyword naturally: {supporting_keyword}" if supporting_keyword else ""
    elif kw_slot == "lsi":
        lsi_str = ", ".join(lsi_keywords[:3]) if lsi_keywords else ""
        keyword_instruction = f"Naturally cover these related terms where relevant: {lsi_str}" if lsi_str else ""
    else:
        keyword_instruction = ""

    paa_block = ""
    if paa_questions and section["name"] == "faq":
        paa_lines = "\n".join(f"- {q['question']}" for q in paa_questions[:5])
        paa_block = f"\nPeople Also Ask questions to draw from:\n{paa_lines}"

    competitor_block = ""
    if competitor_excerpts:
        excerpts = "\n".join(f"- {e}" for e in competitor_excerpts[:3] if e.strip())
        if excerpts:
            competitor_block = f"\nWhat competitors cover in this section (use as context, not as copy):\n{excerpts}"

    existing_block = ""
    if client_existing_content and client_existing_content.strip():
        existing_block = f"\nClient's existing content on this topic (extract useful facts or claims, do not copy):\n{client_existing_content[:400]}"

    brief_block = ""
    if client_brief and client_brief.strip():
        brief_block = f"\nClient brief notes:\n{client_brief[:300]}"

    prev_block = ""
    if previous_section_text and previous_section_text.strip():
        prev_block = f"\nPrevious section (for context and coherence, do not repeat):\n{previous_section_text[-300:]}"

    heading_instruction = ""
    heading_level = section.get("heading_level", "h2")
    if heading_level == "h2":
        heading_instruction = f"Start with an H2 heading (## in markdown). The heading should reflect the section purpose."
    elif heading_level == "h3":
        heading_instruction = f"Use H3 subheadings (### in markdown) where appropriate."
    elif heading_level == "h1":
        heading_instruction = "Start with the H1 headline (# in markdown)."
    else:
        heading_instruction = "Do not add a heading. Write body copy only."

    ai_overview_block = ""
    if ai_overview and ai_overview.strip():
        ai_overview_block = f"\nGoogle AI Overview for this topic (use as reference for what topics to cover, do not copy):\n{ai_overview[:600]}"

    prompt = f"""You are writing the '{section['label']}' section of a {page_type} page.

Page H1: {h1 or 'Not provided'}
Brand name: {brand_name or 'Not specified'}
Business context: {BUSINESS_TYPE_CONTEXT.get(business_type, BUSINESS_TYPE_CONTEXT['general'])}

Section purpose: {section['purpose']}
Word count target: {wc_min} to {wc_max} words. Stay within this range.
{keyword_instruction}
{heading_instruction}

Section-specific rules:
{section['prompt_rules']}

Hard rules for all output:
- Never use em dashes (use a comma or rewrite the sentence)
- No exclamation marks
- No generic AI openings like 'In today's world' or 'Great question'
- No fluff. Every sentence must add information or move the argument forward
- Brand name must appear exactly as: {brand_name}
{f"- Never use these phrases: {forbidden_phrases}" if forbidden_phrases and forbidden_phrases.strip() else ""}
- Return only the section copy. No preamble, no notes, no explanations.
{paa_block}{ai_overview_block}{competitor_block}{existing_block}{brief_block}{prev_block}"""

    return prompt.strip()


# ── Provider functions ────────────────────────────────────────────────────────

def _call_claude(api_key: str, prompt: str) -> str:
    import anthropic
    client = anthropic.Anthropic(api_key=api_key)
    msg = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text.strip()


def _call_openai(api_key: str, prompt: str) -> str:
    from openai import OpenAI
    client = OpenAI(api_key=api_key)
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1500,
    )
    return resp.choices[0].message.content.strip()


def _call_gemini(api_key: str, prompt: str) -> str:
    from google import genai
    client = genai.Client(api_key=api_key)
    resp = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=prompt,
    )
    return resp.text.strip()


def _call_mistral(api_key: str, prompt: str) -> str:
    from mistralai import Mistral
    client = Mistral(api_key=api_key)
    resp = client.chat.complete(
        model="mistral-small-latest",
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.choices[0].message.content.strip()


def _call_groq(api_key: str, prompt: str) -> str:
    from groq import Groq
    client = Groq(api_key=api_key)
    resp = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1500,
    )
    return resp.choices[0].message.content.strip()


PROVIDER_FN = {
    "Claude": _call_claude,
    "OpenAI": _call_openai,
    "Gemini": _call_gemini,
    "Mistral": _call_mistral,
    "Groq": _call_groq,
}

PROVIDER_DELAY = {
    "Claude": 0.5,
    "OpenAI": 0.5,
    "Gemini": 5.0,
    "Mistral": 2.0,
    "Groq": 2.0,
}


# ── Section loop ──────────────────────────────────────────────────────────────

def generate_page(
    template: dict,
    keyword_assignment: dict,
    lsi_keywords: dict,
    business_type: str,
    brand_name: str,
    h1: str,
    page_type: str,
    paa_questions: list,
    ai_overview: str,
    competitor_section_map: dict,
    client_brief: str,
    client_existing_content: str,
    provider: str,
    api_key: str,
    progress_callback=None,
    forbidden_phrases: str = "",
) -> dict:
    """
    Runs the section-by-section generation loop.
    Returns: { section_name: text, "_full_page": assembled markdown, "_word_count": int }
    """
    fn = PROVIDER_FN.get(provider)
    if not fn:
        raise ValueError(f"Unknown provider: {provider}")

    delay = PROVIDER_DELAY.get(provider, 1.0)
    sections = template.get("sections", [])
    results = {}
    previous_text = ""

    for i, section in enumerate(sections):
        if progress_callback:
            progress_callback(i, len(sections), section["label"])

        kw_slot = section.get("keyword_slot", "none")
        sec_name = section["name"]
        assignment = keyword_assignment.get(sec_name, {})
        primary_kw = assignment.get("primary", "")
        supporting_kw = assignment.get("supporting", "")
        lsi_kws = lsi_keywords.get(supporting_kw or primary_kw, [])
        comp_excerpts = competitor_section_map.get(sec_name, [])

        prompt = _build_section_prompt(
            section=section,
            primary_keyword=primary_kw,
            supporting_keyword=supporting_kw,
            lsi_keywords=lsi_kws,
            business_type=business_type,
            brand_name=brand_name,
            h1=h1,
            page_type=page_type,
            paa_questions=paa_questions if sec_name == "faq" else [],
            competitor_excerpts=comp_excerpts,
            client_brief=client_brief,
            previous_section_text=previous_text,
            client_existing_content=client_existing_content if i == 0 else "",
            forbidden_phrases=forbidden_phrases,
        )

        try:
            raw = fn(api_key, prompt)
            text = sanitise(raw, brand_name)
        except Exception as e:
            text = f"[ERROR generating section '{section['label']}': {e}]"

        results[sec_name] = text
        previous_text = text

        if i < len(sections) - 1:
            time.sleep(delay)

    full_page = "\n\n".join(results.get(s["name"], "") for s in sections)
    word_count = len(full_page.split())

    results["_full_page"] = full_page
    results["_word_count"] = word_count

    return results
