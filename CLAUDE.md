# page-copy-saas-backend — Repo Context

See `../CLAUDE.md` for full platform context, conventions, and working rules.

## What This Repo Is

FastAPI backend for the Page Copy workflow. Generates full-page copy
section by section using a template system.
Deployed on Railway EU West. Default branch: `main`. Current HEAD: `5cba1f6`.
Runtime: Python 3.12.

Railway URL: `https://page-copy-saas-backend-production.up.railway.app`

## File Structure

```
main.py           — App, CORS, router mounts, global exception handler
auth.py           — Supabase token validation
models.py         — Pydantic models
routers/
  page_copy.py    — POST /api/page-copy/run + _process_single_row
  jobs.py         — Shared job CRUD
  settings.py     — Shared settings CRUD
utils/
  copy_gen.py     — _build_section_prompt, generate_page, sanitise, PROVIDER_FN
  dfs.py          — Keyword volume, difficulty, SERP, LSI keywords
  gsc.py          — GSC queries
  keyword.py      — select_keyword, keyword assignment per section
  scraper.py      — Jina competitor page scraping
  niches.py       — get_niche_context (23 niches)
  templates.py    — get_template, 13 templates across 10 page types
  docx_export.py  — .docx generation
schema.sql        — Reference schema including brand_profiles
tests/
  test_cors.py
  test_dfs_error_visibility.py
```

## Endpoints

Same shared set as FAQ with POST /api/page-copy/run as the tool endpoint.

## Page Copy Pipeline (_process_single_row)

1. Select primary keyword and supporting keywords
2. Fetch LSI keywords from DFS
3. Fetch SERP: PAA + AI Overview
4. Scrape competitor pages via Jina (optional)
5. Build competitor section map (competitor excerpts per template section)
6. Select template: get_template(template_key)
7. Assign keywords per section: keyword_assignment dict
8. Generate page section by section: generate_page()
9. Rebuild full_page and word_count
10. Generate .docx: docx_export
11. Write result to Supabase

## Template System

13 templates across 10 page types (service, local, homepage, about, contact,
product, collection, blog, case study, landing page).

get_template(key) returns a dict with:
- name, page_type, sections list
- Each section: name, label, purpose, prompt_rules, word_count_range

Template key is stored in job settings and in each row for reruns.

## Key Model Fields (PageCopySettings)

```python
niche: str = ""
business_type: str = "general"
provider: str = "Claude"
brand_name: str
full_brand_name: str = ""
branded_terms_input: str = ""
include_brand: bool = True
forbidden_phrases: str = ""
brand_profile_id: str = ""
template_key: str = "service_page"
client_brief: str = ""
```

## generate_page / _build_section_prompt

Both accept forbidden_phrases. It is injected as a hard rule in every section
prompt: "Never use these phrases: {forbidden_phrases}" — only when non-empty.

include_brand controls whether brand_name reaches the prompt. When False,
effective_brand = "" is passed instead of brand_name.

previous_section_text is passed to each section for coherence. It contains
the last 600 chars of all preceding sections in template order.

## Known Gotchas

- competitor_section_map is built at runtime and is NOT stored in results.
  Section reruns (in AiO) skip competitor excerpts for this reason.
- keyword_assignment is also not stored — section reruns use primary keyword
  for all sections.
- Template key must be stored per-row (rows[i].template_key) as well as in
  settings, because settings may change between reruns.
- .docx generation uses python-docx — must be in requirements.txt.
