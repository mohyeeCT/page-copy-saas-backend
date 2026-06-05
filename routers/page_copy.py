import time
import uuid
import base64
import re
from datetime import datetime, timezone
from urllib.parse import urlparse
from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from pydantic import BaseModel

from auth import get_current_user, get_supabase
from utils.dfs import (
    get_search_volume, get_keyword_difficulty,
    get_ranked_keywords_for_url, get_keyword_ideas,
    get_serp_data,
)
from utils.keyword import rank_keywords, merge_keyword_pools, assign_keywords_to_sections
from utils.scraper import (
    scrape_url, infer_template_from_scrape,
    map_competitor_sections, classify_competitor_relevance,
    is_editorial_competitor,
)
from utils.templates import get_template, get_templates_for_page_type, parse_custom_template
from utils.niches import get_niche_context
from utils.copy_gen import generate_page, sanitise
from utils.docx_export import build_docx

router = APIRouter()

_RATE_LIMITS = {
    "Claude": 0.5,
    "OpenAI": 0.5,
    "Gemini (free)": 5.0,
    "Mistral (free tier)": 2.0,
    "Groq (free tier)": 2.0,
}


def _is_cancelled(sb, job_id: str) -> bool:
    try:
        res = sb.table("jobs").select("status").eq("id", job_id).execute()
        return res.data and res.data[0].get("status") == "cancelling"
    except Exception:
        return False


def _update_job(sb, job_id: str, data: dict):
    try:
        update_data = {**data, "updated_at": "now()"}
        if "current_step" in data and data["current_step"]:
            log_entry = {
                "ts": datetime.now(timezone.utc).isoformat(),
                "msg": data["current_step"],
            }
            try:
                res = sb.table("jobs").select("logs").eq("id", job_id).execute()
                current_logs = (res.data[0].get("logs") or []) if res.data else []
                current_logs.append(log_entry)
                update_data["logs"] = current_logs
            except Exception:
                pass
        sb.table("jobs").update(update_data).eq("id", job_id).execute()
    except Exception:
        pass


def _process_single_row(
    row: dict,
    settings: dict,
    branded_terms: list,
    used_keywords: set,
    sb,
    job_id: str,
    row_num: int,
    total_rows: int,
    brand_profile: dict = None,
) -> dict:
    def step(msg: str):
        _update_job(sb, job_id, {"current_step": f"Row {row_num}/{total_rows}: {msg}"})

    url        = (row.get("url") or "").strip()
    manual_kws = [k.strip() for k in (row.get("keyword") or "").split(",") if k.strip()]
    h1_raw     = (row.get("h1") or "").strip()
    h1         = "" if h1_raw.lower() == "none" else h1_raw
    page_type  = (row.get("page_type") or settings.get("page_type", "blog")).strip().lower()
    template_key = row.get("template_key") or settings.get("template_key", "blog_standard")

    def _empty(status: str) -> dict:
        return {
            "url": url, "primary_keyword": None, "keyword_source": status,
            "word_count": 0, "template_name": None, "competitor_urls": [],
            "docx_b64": None, "status": status,
        }

    if not url or not url.startswith("http"):
        return _empty("skipped: invalid URL")

    dfs_login    = settings["dfs_login"]
    dfs_password = settings["dfs_password"]
    provider     = settings.get("provider", "Claude")
    api_key      = settings.get("api_key", "")
    brand_name   = settings.get("brand_name", "")
    business_type = settings.get("business_type", "general")
    min_volume   = settings.get("min_volume", 10)
    location_code = settings.get("location_code", 2840)
    client_brief = settings.get("client_brief", "")
    include_brand = settings.get("include_brand", True)
    forbidden_phrases = settings.get("forbidden_phrases", "")
    effective_brand = brand_name if include_brand else ""
    _niche_ctx = get_niche_context(settings.get("niche", ""))
    if _niche_ctx:
        client_brief = (client_brief + "\n\n" + _niche_ctx).strip()

    # Inject brand profile into brief
    if brand_profile:
        parts = []
        if brand_profile.get("tone_of_voice"):
            parts.append("Tone of voice: " + brand_profile["tone_of_voice"])
        if brand_profile.get("key_messages"):
            parts.append("Key messages: " + brand_profile["key_messages"])
        if brand_profile.get("words_to_avoid"):
            parts.append("Words to avoid: " + brand_profile["words_to_avoid"])
        if brand_profile.get("guidelines"):
            parts.append(brand_profile["guidelines"])
        if parts:
            client_brief = (client_brief + "\n\n" + "\n".join(parts)).strip()

    # ── Keyword pipeline ───────────────────────────────────────────────────
    step("fetching DFS ranked keywords...")
    dfs_ranked = []
    try:
        dfs_ranked = get_ranked_keywords_for_url(url, dfs_login, dfs_password, int(location_code))
        step("DFS ranked: " + str(len(dfs_ranked)) + " keywords found")
    except Exception as e:
        step("⚠ DFS ranked keywords failed: " + str(e)[:60])

    all_kws = list({r["keyword"] for r in dfs_ranked} | set(manual_kws))
    all_kws = [k for k in all_kws if k]

    vol_map  = {}
    diff_map = {}
    if all_kws:
        step("fetching keyword volumes...")
        try:
            vol_map = get_search_volume(all_kws, dfs_login, dfs_password, int(location_code))
        except Exception as e:
            step("DataForSEO keyword volume failed: " + str(e)[:120])
        try:
            diff_map = get_keyword_difficulty(all_kws, dfs_login, dfs_password, int(location_code))
        except Exception as e:
            step("DataForSEO keyword difficulty failed: " + str(e)[:120])

    pool   = merge_keyword_pools([], dfs_ranked, manual_kws, vol_map, diff_map)
    pool   = [k for k in pool if k.get("volume", 0) >= min_volume]
    ranked = rank_keywords(pool, branded_terms, h1=h1, exclude_position_one=True)
    ranked = [k for k in ranked if not k.get("branded")]

    if not ranked and manual_kws:
        ranked = [{"keyword": k, "volume": 10, "difficulty": 1, "score": 1.0, "branded": False} for k in manual_kws]

    if not ranked:
        step("✗ no keywords found — skipping")
        return _empty("skipped: no keywords found")

    primary_keyword = ranked[0]["keyword"]
    if primary_keyword.lower() in used_keywords:
        # Use next available
        for r in ranked[1:]:
            if r["keyword"].lower() not in used_keywords:
                primary_keyword = r["keyword"]
                break
    used_keywords.add(primary_keyword.lower())

    keyword_source = "dfs+manual" if manual_kws else "dfs"
    step("keyword selected: " + primary_keyword)

    # ── SERP ───────────────────────────────────────────────────────────────
    step("fetching SERP data...")
    serp_data = {"organic": [], "paa": [], "ai_overview": ""}
    try:
        serp_data = get_serp_data(dfs_login, dfs_password, primary_keyword, int(location_code))
        if serp_data.get("error"):
            step("DataForSEO SERP failed: " + str(serp_data["error"])[:120])
        ao_present = bool(serp_data.get("ai_overview"))
        paa_count  = len(serp_data.get("paa_items") or serp_data.get("paa") or [])
        org_count  = len(serp_data.get("organic") or [])
        step("SERP: " + ("AIO ✓" if ao_present else "AIO ✗") + ", PAA: " + str(paa_count) + ", organic: " + str(org_count))
    except Exception as e:
        step("⚠ SERP failed: " + str(e)[:60])

    paa_questions = serp_data.get("paa_items") or serp_data.get("paa") or []
    ai_overview   = serp_data.get("ai_overview_raw") or serp_data.get("ai_overview") or ""
    organic_results = serp_data.get("organic") or []

    # ── Template ───────────────────────────────────────────────────────────
    custom_template_text = settings.get("custom_template_text", "").strip()
    if custom_template_text:
        template = parse_custom_template(custom_template_text, page_type)
    else:
        try:
            template = get_template(template_key)
        except ValueError:
            template = get_template("blog_standard")

    section_names   = [s["name"] for s in template["sections"]]
    kw_assignment   = assign_keywords_to_sections(ranked, section_names)

    # LSI keywords for supporting keywords
    lsi_map = {}
    supporting_kws = list({v["supporting"] for v in kw_assignment.values() if v.get("supporting")})
    for sk in supporting_kws[:3]:
        try:
            ideas = get_keyword_ideas(sk, dfs_login, dfs_password, int(location_code), limit=10)
            lsi_map[sk] = [i["keyword"] for i in ideas[:3]]
        except Exception as e:
            lsi_map[sk] = []
            step("DataForSEO keyword ideas failed: " + str(e)[:120])

    # ── Competitor scraping ────────────────────────────────────────────────
    step("scraping competitors...")
    competitor_urls_used = []
    competitor_section_map = {s["name"]: [] for s in template["sections"]}
    client_domain = urlparse(url).netloc

    if organic_results:
        try:
            scored = []
            for sr in organic_results[:8]:
                comp_url = sr.get("url") or sr.get("link") or sr.get("relative_url") or ""
                if not comp_url.startswith("http"):
                    continue
                comp_domain = urlparse(comp_url).netloc
                if client_domain and client_domain in comp_domain:
                    continue
                sc = scrape_url(comp_url)
                if not sc["success"]:
                    continue
                if not is_editorial_competitor(sc, page_type):
                    continue
                relevance = classify_competitor_relevance(sc, business_type, page_type)
                sc["relevance"] = relevance
                sc["comp_url"]  = comp_url
                scored.append(sc)

            scored.sort(key=lambda x: x["relevance"], reverse=True)
            top = scored[:3]
            competitor_urls_used = [c["comp_url"] for c in top]

            if top:
                competitor_section_map = map_competitor_sections(top, template["sections"])

            step("competitors: " + str(len(competitor_urls_used)) + " editorial pages scraped")
        except Exception as e:
            step("⚠ competitor scrape failed: " + str(e)[:60])

    # ── Client existing page ───────────────────────────────────────────────
    client_existing_content = ""
    try:
        existing = scrape_url(url)
        if existing["success"]:
            client_existing_content = existing["body_text"][:800]
    except Exception:
        pass

    if not h1 and primary_keyword:
        h1 = primary_keyword.title()

    # ── Section-by-section generation ─────────────────────────────────────
    delay = _RATE_LIMITS.get(provider, 1.0)
    step("generating with " + provider + " (" + str(len(template['sections'])) + " sections)...")

    try:
        def on_section(i: int, total: int, label: str):
            step("generating section " + str(i+1) + "/" + str(total) + ": " + label)
            # Check for cancellation between sections
            if _is_cancelled(sb, job_id):
                raise InterruptedError("job cancelled")

        section_results = generate_page(
            template=template,
            keyword_assignment=kw_assignment,
            lsi_keywords=lsi_map,
            business_type=business_type,
            brand_name=effective_brand,
            h1=h1,
            page_type=page_type,
            paa_questions=paa_questions,
            ai_overview=ai_overview,
            competitor_section_map=competitor_section_map,
            client_brief=client_brief,
            client_existing_content=client_existing_content,
            provider=provider,
            api_key=api_key,
            progress_callback=on_section,
            forbidden_phrases=forbidden_phrases,
        )
    except InterruptedError:
        raise
    except Exception as e:
        step("✗ generation failed: " + str(e)[:80])
        return {**_empty("error: " + str(e)), "primary_keyword": primary_keyword, "keyword_source": keyword_source}

    word_count = section_results.get("_word_count", 0)
    step("✓ " + str(word_count) + " words generated — building docx...")

    # ── Build docx ─────────────────────────────────────────────────────────
    try:
        docx_bytes = build_docx(
            url=url,
            page_type=page_type,
            template_name=template["name"],
            primary_keyword=primary_keyword,
            section_results=section_results,
            template_sections=template["sections"],
            keyword_assignment=kw_assignment,
            word_count=word_count,
            competitor_urls=competitor_urls_used,
            h1=h1,
        )
        docx_b64 = base64.b64encode(docx_bytes).decode("utf-8")
    except Exception as e:
        step("⚠ docx build failed: " + str(e)[:60])
        docx_b64 = None

    step("✓ done — " + str(word_count) + " words, " + str(len(template['sections'])) + " sections")

    return {
        "url":              url,
        "h1":               h1,
        "primary_keyword":  primary_keyword,
        "keyword_source":   keyword_source,
        "kw_volume":        (ranked[0].get("volume") if ranked else None),
        "template_name":    template["name"],
        "competitor_urls":  competitor_urls_used,
        "word_count":       word_count,
        "section_results":  {k: v for k, v in section_results.items() if not k.startswith("_")},
        "full_page":        section_results.get("_full_page", ""),
        "docx_b64":         docx_b64,
        "status":           "ok",
    }


def _process_job(job_id: str, rows: list, settings: dict, brand_profile: dict = None):
    sb    = get_supabase()
    delay = _RATE_LIMITS.get(settings.get("provider", "Claude"), 1.0)
    total = len(rows)

    _update_job(sb, job_id, {
        "status":       "running",
        "total_rows":   total,
        "current_step": "Starting...",
    })

    branded_terms = [b.strip() for b in settings.get("brand_name", "").split() if b.strip()]
    full_brand    = settings.get("full_brand_name", "").strip()
    if full_brand:
        branded_terms = list(set(branded_terms + [w.lower() for w in re.findall(r"[a-zA-Z]+", full_brand) if len(w) >= 3]))
    branded_input = settings.get("branded_terms_input", "").strip()
    if branded_input:
        branded_terms = list(set(branded_terms + [t.strip().lower() for t in branded_input.splitlines() if t.strip()]))

    used_keywords: set = set()
    results = []

    for idx, row in enumerate(rows):
        url = (row.get("url") or "").strip()
        _update_job(sb, job_id, {"current_step": f"Row {idx+1}/{total}: starting — {url}"})

        if _is_cancelled(sb, job_id):
            _update_job(sb, job_id, {
                "status":       "cancelled",
                "current_step": f"Cancelled after {idx}/{total} rows.",
                "failed_rows":  sum(1 for r in results if r.get("status") != "ok"),
            })
            return

        try:
            result = _process_single_row(
                row=row,
                settings=settings,
                branded_terms=branded_terms,
                used_keywords=used_keywords,
                sb=sb,
                job_id=job_id,
                row_num=idx + 1,
                total_rows=total,
                brand_profile=brand_profile,
            )
        except InterruptedError:
            _update_job(sb, job_id, {
                "status":       "cancelled",
                "current_step": f"Cancelled during row {idx + 1}.",
                "failed_rows":  sum(1 for r in results if r.get("status") != "ok"),
                "results":      results,
            })
            return
        except Exception as e:
            result = {"url": url, "error": str(e), "status": "error", "word_count": 0, "docx_b64": None}

        results.append(result)
        _update_job(sb, job_id, {"completed_rows": idx + 1, "results": results})

        if _is_cancelled(sb, job_id):
            _update_job(sb, job_id, {
                "status":       "cancelled",
                "current_step": f"Cancelled after {idx + 1}/{total} rows.",
                "failed_rows":  sum(1 for r in results if r.get("status") != "ok"),
            })
            return

        if idx < total - 1:
            time.sleep(delay)

    _update_job(sb, job_id, {
        "status":        "complete",
        "current_step":  "Done.",
        "completed_rows": len(results),
        "failed_rows":   sum(1 for r in results if r.get("status") != "ok"),
        "results":       results,
    })


# ── Request models ─────────────────────────────────────────────────────────────

class PageCopyRow(BaseModel):
    url: str
    keyword: str = ""
    page_type: str = "blog"
    h1: str = ""
    template_key: str = ""


class PageCopySettings(BaseModel):
    niche: str = ""
    provider: str = "Claude"
    api_key: str = ""
    dfs_login: str = ""
    dfs_password: str = ""
    business_type: str = "general"
    brand_name: str = ""
    full_brand_name: str = ""
    branded_terms_input: str = ""
    include_brand: bool = True
    forbidden_phrases: str = ""
    location_code: int = 2840
    min_volume: int = 10
    page_type: str = "blog"
    template_key: str = "blog_standard"
    custom_template_text: str = ""
    client_brief: str = ""
    brand_profile_id: str = ""


class PageCopyJobRequest(BaseModel):
    name: str = ""
    rows: list[PageCopyRow]
    settings: PageCopySettings


@router.post("/run")
def run_page_copy_job(
    request: PageCopyJobRequest,
    background_tasks: BackgroundTasks,
    user=Depends(get_current_user),
    sb=Depends(get_supabase),
):
    job_id = str(uuid.uuid4())

    # Fetch brand profile
    brand_profile = None
    if request.settings.brand_profile_id:
        try:
            bp_res = sb.table("brand_profiles").select("data").eq("id", request.settings.brand_profile_id).eq("user_id", user.id).execute()
            if bp_res.data:
                brand_profile = bp_res.data[0].get("data") or {}
        except Exception:
            pass

    sb.table("jobs").insert({
        "id":             job_id,
        "user_id":        user.id,
        "name":           request.name or f"Page copy — {len(request.rows)} URLs",
        "tool":           "page-copy",
        "status":         "pending",
        "total_rows":     len(request.rows),
        "completed_rows": 0,
        "failed_rows":    0,
        "results":        [],
        "logs":           [],
        "rows":           [r.model_dump() for r in request.rows],
        "settings":       request.settings.model_dump(exclude={"api_key", "dfs_password"}),
        "current_step":   "Queued...",
    }).execute()

    background_tasks.add_task(
        _process_job,
        job_id=job_id,
        rows=[r.model_dump() for r in request.rows],
        settings=request.settings.model_dump(),
        brand_profile=brand_profile,
    )

    return {"job_id": job_id, "status": "running"}


@router.get("/templates")
def list_templates():
    """Return available template keys and names for each page type."""
    result = {}
    for page_type in ["blog", "case_study", "glossary"]:
        templates = get_templates_for_page_type(page_type)
        result[page_type] = [{"key": k, "name": v["name"], "description": v.get("description", "")} for k, v in templates.items()]
    return result
