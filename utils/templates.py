"""
Template registry for the page copy production app.

Each template is a dict with:
  - name: display name shown in the UI
  - page_type: "blog" | "case_study" | "glossary"
  - description: shown in the UI to help users pick
  - sections: ordered list of section definitions

Each section definition:
  - name: internal name, used for keyword assignment and section mapping
  - label: H2 heading placeholder (AI can rename within rules)
  - purpose: one sentence, injected into the section prompt
  - word_count: [min, max]
  - keyword_slot: "primary" | "supporting" | "lsi" | "none"
  - heading_level: "h1" | "h2" | "h3" | "none" (no heading, e.g. intro body)
  - prompt_rules: section-specific instructions injected into the AI prompt
"""

TEMPLATES = {

    # ── BLOG: Standard Informational ─────────────────────────────────────────
    "blog_standard": {
        "name": "Standard Informational",
        "page_type": "blog",
        "description": "Best for: educational content, guides, and how things work. The most versatile blog format.",
        "sections": [
            {
                "name": "intro",
                "label": "Introduction",
                "purpose": "State the problem or question the reader has. Promise what this page answers. Hook without fluff.",
                "word_count": [120, 180],
                "keyword_slot": "primary",
                "heading_level": "none",
                "prompt_rules": (
                    "Open with the reader's problem or question directly. "
                    "Include the primary keyword naturally within the first two sentences. "
                    "End the intro with a clear statement of what the reader will learn. "
                    "No generic openings like 'In today's world' or 'Are you wondering'. "
                    "No em dashes."
                ),
            },
            {
                "name": "context",
                "label": "Why This Matters",
                "purpose": "Establish the stakes and why this topic is relevant now. Sets up the body sections.",
                "word_count": [150, 220],
                "keyword_slot": "supporting",
                "heading_level": "h2",
                "prompt_rules": (
                    "Explain why this topic matters to the reader's situation. "
                    "Use data, trends, or a concrete scenario to ground it. "
                    "Do not repeat the intro. Move the argument forward. "
                    "H2 must be a question or a statement readers would recognise as their own concern."
                ),
            },
            {
                "name": "body_1",
                "label": "Core Section 1",
                "purpose": "Answer the first major sub-question the reader has about this topic.",
                "word_count": [200, 300],
                "keyword_slot": "supporting",
                "heading_level": "h2",
                "prompt_rules": (
                    "H2 must reflect a real user question or search phrase. "
                    "Include the supporting keyword in the H2 or first paragraph naturally. "
                    "Use concrete examples, steps, or comparisons. Avoid vague generalisations. "
                    "No em dashes. No bullet point lists unless the content is genuinely list-like."
                ),
            },
            {
                "name": "body_2",
                "label": "Core Section 2",
                "purpose": "Answer the second major sub-question. Build on body_1 without repeating it.",
                "word_count": [200, 300],
                "keyword_slot": "supporting",
                "heading_level": "h2",
                "prompt_rules": (
                    "This section should deepen the reader's understanding, not repeat body_1. "
                    "H2 should be distinct from the previous section heading. "
                    "Use a different angle: if body_1 covered what, this covers how or why. "
                    "No em dashes."
                ),
            },
            {
                "name": "body_3",
                "label": "Core Section 3",
                "purpose": "Address a third angle, common mistake, or practical consideration.",
                "word_count": [200, 300],
                "keyword_slot": "lsi",
                "heading_level": "h2",
                "prompt_rules": (
                    "Cover a practical consideration, common mistake, or advanced angle. "
                    "This section should feel useful to someone who already read the first two body sections. "
                    "No em dashes. Can use a short numbered list if genuinely appropriate."
                ),
            },
            {
                "name": "summary",
                "label": "Key Takeaways",
                "purpose": "Summarise the core points in scannable format. Re-hits primary keyword naturally.",
                "word_count": [80, 130],
                "keyword_slot": "primary",
                "heading_level": "h2",
                "prompt_rules": (
                    "Write 3 to 5 short bullet points summarising the most actionable insights from the page. "
                    "Each bullet should be a complete sentence. No vague bullets. "
                    "Re-include the primary keyword naturally in the H2 or first bullet. "
                    "Do not introduce new information here."
                ),
            },
            {
                "name": "faq",
                "label": "Frequently Asked Questions",
                "purpose": "Answer 3 to 5 real questions readers have at this stage. Pulls from PAA data.",
                "word_count": [200, 320],
                "keyword_slot": "lsi",
                "heading_level": "h2",
                "prompt_rules": (
                    "Write 3 to 5 FAQ items using the PAA questions provided as source. "
                    "Each answer must be 2 to 4 sentences. Direct and specific. "
                    "Do not repeat information already covered in the body. "
                    "Format as: Question on its own line, then answer paragraph."
                ),
            },
            {
                "name": "cta",
                "label": "Next Steps",
                "purpose": "Soft conversion. Business-type-aware. No hard-sell language.",
                "word_count": [60, 100],
                "keyword_slot": "none",
                "heading_level": "h2",
                "prompt_rules": (
                    "Write a short closing paragraph that leads the reader to a natural next action. "
                    "B2B: contact, request a demo, or download. "
                    "Ecommerce: shop, browse, or explore. "
                    "Service/local: call, get a quote, book. "
                    "No branded consumer CTAs on B2B pages. "
                    "No exclamation marks. No em dashes."
                ),
            },
        ],
    },

    # ── BLOG: Listicle ───────────────────────────────────────────────────────
    "blog_listicle": {
        "name": "Listicle",
        "page_type": "blog",
        "description": "Best for: top X lists, roundups, collections. High CTR format for informational intent.",
        "sections": [
            {
                "name": "intro",
                "label": "Introduction",
                "purpose": "Frame what the list covers and why these items were chosen.",
                "word_count": [100, 160],
                "keyword_slot": "primary",
                "heading_level": "none",
                "prompt_rules": (
                    "State what the list covers and the selection criteria briefly. "
                    "Include primary keyword in first two sentences. "
                    "No padding. Get to the list quickly."
                ),
            },
            {
                "name": "list_items",
                "label": "The List",
                "purpose": "The numbered items. Each item gets an H3, a 2 to 4 sentence description, and one concrete example.",
                "word_count": [600, 1000],
                "keyword_slot": "supporting",
                "heading_level": "h2",
                "prompt_rules": (
                    "Write 5 to 10 numbered list items. "
                    "Each item: H3 with the item name, then 2 to 4 sentences of explanation. "
                    "Every item must include at least one concrete, specific detail. No vague generalisations. "
                    "Distribute supporting and LSI keywords naturally across the items. "
                    "No em dashes."
                ),
            },
            {
                "name": "faq",
                "label": "Frequently Asked Questions",
                "purpose": "Answer 3 PAA questions related to the list topic.",
                "word_count": [150, 250],
                "keyword_slot": "lsi",
                "heading_level": "h2",
                "prompt_rules": (
                    "Write 3 FAQ items using PAA questions provided. "
                    "Keep answers to 2 to 3 sentences each. Direct and specific."
                ),
            },
            {
                "name": "cta",
                "label": "Next Steps",
                "purpose": "Soft conversion close.",
                "word_count": [60, 100],
                "keyword_slot": "none",
                "heading_level": "h2",
                "prompt_rules": (
                    "Short closing paragraph with a natural next action. Business-type-aware. No em dashes."
                ),
            },
        ],
    },

    # ── BLOG: How-to / Guide ─────────────────────────────────────────────────
    "blog_howto": {
        "name": "How-to / Guide",
        "page_type": "blog",
        "description": "Best for: step-by-step instructions, tutorials, and process walkthroughs.",
        "sections": [
            {
                "name": "intro",
                "label": "Introduction",
                "purpose": "State the end goal the reader is trying to achieve and what this guide covers.",
                "word_count": [100, 160],
                "keyword_slot": "primary",
                "heading_level": "none",
                "prompt_rules": (
                    "Open with the outcome the reader wants. "
                    "Include primary keyword in first two sentences. "
                    "End with a brief mention of what the steps cover."
                ),
            },
            {
                "name": "prerequisites",
                "label": "What You Need Before You Start",
                "purpose": "Set expectations: tools, knowledge, or conditions needed.",
                "word_count": [80, 130],
                "keyword_slot": "none",
                "heading_level": "h2",
                "prompt_rules": (
                    "Short list of prerequisites or things the reader should have ready. "
                    "Be specific. Avoid vague items like 'a computer' unless context demands it."
                ),
            },
            {
                "name": "steps",
                "label": "Step-by-Step",
                "purpose": "The numbered steps. Each step is an H3 with clear instruction and rationale.",
                "word_count": [600, 900],
                "keyword_slot": "supporting",
                "heading_level": "h2",
                "prompt_rules": (
                    "Write 4 to 8 numbered steps. Each step: H3 with imperative verb phrase (e.g. 'Set Up Your Account'), "
                    "then 3 to 5 sentences covering what to do, how to do it, and why it matters. "
                    "Include supporting keywords naturally across the steps. "
                    "Call out common mistakes where relevant. No em dashes."
                ),
            },
            {
                "name": "tips",
                "label": "Tips and Common Mistakes",
                "purpose": "Practical tips that save the reader time or prevent failure.",
                "word_count": [150, 220],
                "keyword_slot": "lsi",
                "heading_level": "h2",
                "prompt_rules": (
                    "Write 3 to 5 tips or common mistakes to avoid. "
                    "Be specific. Each tip should be actionable, not generic advice."
                ),
            },
            {
                "name": "faq",
                "label": "Frequently Asked Questions",
                "purpose": "Answer PAA questions relevant to this how-to topic.",
                "word_count": [150, 250],
                "keyword_slot": "lsi",
                "heading_level": "h2",
                "prompt_rules": "Write 3 FAQ items from PAA questions. 2 to 3 sentences per answer.",
            },
            {
                "name": "cta",
                "label": "Next Steps",
                "purpose": "Soft conversion close.",
                "word_count": [60, 100],
                "keyword_slot": "none",
                "heading_level": "h2",
                "prompt_rules": "Short closing with natural next action. Business-type-aware. No em dashes.",
            },
        ],
    },

    # ── BLOG: Comparison ─────────────────────────────────────────────────────
    "blog_comparison": {
        "name": "Comparison / vs Post",
        "page_type": "blog",
        "description": "Best for: X vs Y, alternatives, or option-comparison content. High commercial intent.",
        "sections": [
            {
                "name": "intro",
                "label": "Introduction",
                "purpose": "Frame the comparison decision the reader is facing.",
                "word_count": [100, 160],
                "keyword_slot": "primary",
                "heading_level": "none",
                "prompt_rules": (
                    "Open by naming the decision the reader is trying to make. "
                    "Include primary keyword in first two sentences. "
                    "No 'in this article we will'. Get to the point."
                ),
            },
            {
                "name": "overview",
                "label": "Quick Overview",
                "purpose": "Brief summary of each option being compared. No verdict yet.",
                "word_count": [150, 220],
                "keyword_slot": "supporting",
                "heading_level": "h2",
                "prompt_rules": (
                    "One short paragraph per option being compared. "
                    "Describe what each one is, who it is for, and its main strength. "
                    "Do not give a verdict here. Save that for the end."
                ),
            },
            {
                "name": "criteria_1",
                "label": "Comparison Criteria 1",
                "purpose": "Compare both options on the first key dimension.",
                "word_count": [180, 260],
                "keyword_slot": "supporting",
                "heading_level": "h2",
                "prompt_rules": (
                    "H2 names the dimension being compared (e.g. 'Pricing', 'Ease of Use', 'Scalability'). "
                    "Be specific. Use concrete numbers, features, or scenarios. "
                    "Do not pad with vague statements like 'both have their pros and cons'."
                ),
            },
            {
                "name": "criteria_2",
                "label": "Comparison Criteria 2",
                "purpose": "Compare both options on the second key dimension.",
                "word_count": [180, 260],
                "keyword_slot": "supporting",
                "heading_level": "h2",
                "prompt_rules": "Same rules as criteria_1. Different dimension.",
            },
            {
                "name": "criteria_3",
                "label": "Comparison Criteria 3",
                "purpose": "Compare both options on the third key dimension.",
                "word_count": [180, 260],
                "keyword_slot": "lsi",
                "heading_level": "h2",
                "prompt_rules": "Same rules as criteria_1. Third distinct dimension.",
            },
            {
                "name": "verdict",
                "label": "Which Should You Choose?",
                "purpose": "Give a clear recommendation with conditions. No fence-sitting.",
                "word_count": [150, 200],
                "keyword_slot": "primary",
                "heading_level": "h2",
                "prompt_rules": (
                    "Give a direct recommendation. State which option is better and for whom. "
                    "Use conditional framing: 'If you need X, go with A. If you need Y, go with B.' "
                    "No vague both-sides conclusions. Readers came here to make a decision."
                ),
            },
            {
                "name": "faq",
                "label": "Frequently Asked Questions",
                "purpose": "Answer 3 PAA questions about the comparison topic.",
                "word_count": [150, 250],
                "keyword_slot": "lsi",
                "heading_level": "h2",
                "prompt_rules": "3 FAQ items from PAA questions. 2 to 3 sentences per answer.",
            },
            {
                "name": "cta",
                "label": "Next Steps",
                "purpose": "Soft conversion close.",
                "word_count": [60, 100],
                "keyword_slot": "none",
                "heading_level": "h2",
                "prompt_rules": "Short closing with natural next action. Business-type-aware. No em dashes.",
            },
        ],
    },

    # ── CASE STUDY ───────────────────────────────────────────────────────────
    "case_study_b2b": {
        "name": "B2B Case Study",
        "page_type": "case_study",
        "description": "Research-backed B2B case study structure. Situation, Trigger, Barrier, Solution, Results flow.",
        "sections": [
            {
                "name": "headline_snapshot",
                "label": "Headline and Client Snapshot",
                "purpose": "Result-first headline. Client snapshot box: industry, size, challenge tag, KPI achieved.",
                "word_count": [60, 100],
                "keyword_slot": "primary",
                "heading_level": "h1",
                "prompt_rules": (
                    "Write a headline that leads with the single most impressive measurable result. "
                    "Then write a 3 to 4 line snapshot: Client industry, company size, main challenge, key result. "
                    "Primary keyword must appear in the headline naturally. "
                    "No vague headlines like 'How We Helped Company X'. Lead with the number or outcome."
                ),
            },
            {
                "name": "situation",
                "label": "The Situation",
                "purpose": "What the client's world looked like before. Sets context. Industry keywords go here.",
                "word_count": [150, 220],
                "keyword_slot": "supporting",
                "heading_level": "h2",
                "prompt_rules": (
                    "Describe the client's situation before the engagement. "
                    "Name the industry context, the scale of their operations, and the environment they were operating in. "
                    "Pull in industry-specific keywords naturally. "
                    "Do not introduce the problem here. That comes next. This is purely context."
                ),
            },
            {
                "name": "trigger",
                "label": "What Changed",
                "purpose": "The trigger event that forced the client to act. Business and emotional logic.",
                "word_count": [100, 160],
                "keyword_slot": "supporting",
                "heading_level": "h2",
                "prompt_rules": (
                    "Name the specific event, pressure, or change that made the status quo unsustainable. "
                    "This is the 'why now' moment. It should feel real and specific. "
                    "Both business logic and human stakes should be visible."
                ),
            },
            {
                "name": "barrier",
                "label": "The Challenge",
                "purpose": "What made solving this hard. The section buyers identify with most.",
                "word_count": [120, 180],
                "keyword_slot": "lsi",
                "heading_level": "h2",
                "prompt_rules": (
                    "Describe what made the problem difficult to solve. "
                    "This is the section readers will most identify with. It should mirror their own frustrations. "
                    "Be specific about the obstacles: technical, organisational, budget, or market. "
                    "Do not mention the solution here."
                ),
            },
            {
                "name": "solution",
                "label": "The Solution",
                "purpose": "What was done and how. Product and service names go here naturally.",
                "word_count": [200, 300],
                "keyword_slot": "supporting",
                "heading_level": "h2",
                "prompt_rules": (
                    "Describe the solution in concrete terms. What was done, in what order, and why those choices were made. "
                    "Name specific products, services, or methodologies where provided. "
                    "Include implementation timeline signals (time-to-value is the most trusted B2B KPI). "
                    "No vague language like 'a comprehensive approach'. Be specific."
                ),
            },
            {
                "name": "results",
                "label": "The Results",
                "purpose": "Metrics first, then narrative. Before/after framing.",
                "word_count": [150, 220],
                "keyword_slot": "primary",
                "heading_level": "h2",
                "prompt_rules": (
                    "Lead with the most impressive metric. Then add 2 to 3 supporting metrics. "
                    "Use before/after framing where data allows. "
                    "Include time-to-value: how long until results were visible. "
                    "If placeholder metrics are provided in the brief, use them exactly. "
                    "If not, write placeholders in brackets like [X% improvement in Y]. "
                    "Do not pad with vague outcome statements."
                ),
            },
            {
                "name": "quote",
                "label": "Client Quote",
                "purpose": "Single attributed quote that names the result or removes a key objection.",
                "word_count": [30, 60],
                "keyword_slot": "none",
                "heading_level": "none",
                "prompt_rules": (
                    "If a quote is provided in the brief, use it exactly and add attribution. "
                    "If not, write a realistic placeholder in quotation marks with [Name, Title, Company] attribution. "
                    "The quote should name a result or a before/after contrast. "
                    "No generic praise quotes like 'They were great to work with'."
                ),
            },
            {
                "name": "faq",
                "label": "Frequently Asked Questions",
                "purpose": "2 to 3 questions buyers have at this stage of the funnel.",
                "word_count": [120, 200],
                "keyword_slot": "lsi",
                "heading_level": "h2",
                "prompt_rules": (
                    "Write 2 to 3 FAQ items using PAA questions or late-funnel buyer questions. "
                    "Answers should be 2 to 3 sentences. Address objections or implementation concerns."
                ),
            },
            {
                "name": "cta",
                "label": "Work With Us",
                "purpose": "Stage-aware CTA: demo, contact, or related case studies.",
                "word_count": [60, 100],
                "keyword_slot": "none",
                "heading_level": "h2",
                "prompt_rules": (
                    "Write a short CTA paragraph. "
                    "For B2B: request a demo, get in touch, or see related case studies. "
                    "No exclamation marks. No em dashes. No 'unleash your potential' language."
                ),
            },
        ],
    },

    # ── GLOSSARY ─────────────────────────────────────────────────────────────
    "glossary": {
        "name": "Glossary / Definition Page",
        "page_type": "glossary",
        "description": "Best for: defining industry terms, building topical authority, capturing definition-intent queries.",
        "sections": [
            {
                "name": "definition",
                "label": "Definition",
                "purpose": "Clear, direct definition of the term. Primary keyword in first sentence.",
                "word_count": [80, 130],
                "keyword_slot": "primary",
                "heading_level": "none",
                "prompt_rules": (
                    "Start with '[Term] is...' or '[Term] refers to...'. "
                    "Include the primary keyword in the first sentence. "
                    "Be precise. No vague openers."
                ),
            },
            {
                "name": "expanded",
                "label": "In More Detail",
                "purpose": "Expand on the definition with context, nuance, or how it is used in practice.",
                "word_count": [200, 300],
                "keyword_slot": "supporting",
                "heading_level": "h2",
                "prompt_rules": (
                    "Go deeper than the definition. Explain how the term is used in context, "
                    "common variations, or how it differs from related terms. "
                    "Include supporting keyword naturally. No em dashes."
                ),
            },
            {
                "name": "examples",
                "label": "Examples",
                "purpose": "2 to 3 concrete real-world examples of the term in use.",
                "word_count": [150, 250],
                "keyword_slot": "lsi",
                "heading_level": "h2",
                "prompt_rules": (
                    "Write 2 to 3 specific examples. Each example should show the term applied in a real scenario. "
                    "Name industries, tools, or situations where relevant. No hypothetical filler."
                ),
            },
            {
                "name": "related_terms",
                "label": "Related Terms",
                "purpose": "Brief definitions of 3 to 5 related terms. Internal link signals.",
                "word_count": [150, 220],
                "keyword_slot": "lsi",
                "heading_level": "h2",
                "prompt_rules": (
                    "List 3 to 5 related terms with a 1 to 2 sentence definition each. "
                    "Choose terms that are genuinely related, not just adjacent. "
                    "Format as: Term name then definition, one per paragraph."
                ),
            },
            {
                "name": "faq",
                "label": "Frequently Asked Questions",
                "purpose": "3 PAA questions about this term.",
                "word_count": [150, 250],
                "keyword_slot": "lsi",
                "heading_level": "h2",
                "prompt_rules": "3 FAQ items from PAA questions. 2 to 3 sentences per answer.",
            },
            {
                "name": "cta",
                "label": "Learn More",
                "purpose": "Soft CTA pointing to related content or a conversion action.",
                "word_count": [50, 80],
                "keyword_slot": "none",
                "heading_level": "h2",
                "prompt_rules": "Short closing. Business-type-aware. No em dashes.",
            },
        ],
    },
}


def get_templates_for_page_type(page_type: str) -> dict:
    """Returns all templates matching a given page_type."""
    return {k: v for k, v in TEMPLATES.items() if v["page_type"] == page_type}


def get_template(template_key: str) -> dict:
    """Returns a single template by key. Raises if not found."""
    if template_key not in TEMPLATES:
        raise ValueError(f"Template '{template_key}' not found.")
    return TEMPLATES[template_key]


def parse_custom_template(raw_text: str, page_type: str = "blog") -> dict:
    """
    Parses a custom template from user text input.
    Format expected (one per line):
        Section Name | min_words-max_words
    Example:
        Introduction | 100-160
        How It Works | 200-300
        Case Studies | 200-280
        FAQ | 150-250
        Next Steps | 60-100

    Returns a template dict compatible with the registry format.
    """
    sections = []
    for line in raw_text.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split("|")
        section_name = parts[0].strip()
        word_range = [150, 250]
        if len(parts) > 1:
            range_part = parts[1].strip()
            try:
                low, high = range_part.split("-")
                word_range = [int(low.strip()), int(high.strip())]
            except Exception:
                pass

        name_slug = section_name.lower().replace(" ", "_")
        is_faq = "faq" in name_slug or "question" in name_slug
        is_cta = any(x in name_slug for x in ["cta", "next step", "contact", "get in touch"])
        is_intro = name_slug in ("intro", "introduction", "overview") or sections == []

        sections.append({
            "name": name_slug,
            "label": section_name,
            "purpose": f"Cover the topic: {section_name}",
            "word_count": word_range,
            "keyword_slot": "primary" if is_intro else ("lsi" if is_faq else "supporting"),
            "heading_level": "none" if is_intro else "h2",
            "prompt_rules": (
                "Answer 3 to 5 reader questions using PAA data provided. 2 to 4 sentences each." if is_faq
                else "Short closing paragraph with a natural next action. Business-type-aware. No em dashes." if is_cta
                else f"Write the {section_name} section. Be specific and useful. No em dashes."
            ),
        })

    return {
        "name": "Custom Template",
        "page_type": page_type,
        "description": "User-defined section structure.",
        "sections": sections,
    }
