import os
import requests
import streamlit as st
from bs4 import BeautifulSoup
from openai import OpenAI

st.set_page_config(page_title="AI SEO Audit Assistant", page_icon="🔎", layout="wide")

st.title("🔎 AI SEO Audit Assistant")
st.caption("A practical AI-assisted website audit tool for titles, meta descriptions, headings, content, and technical SEO signals.")

def fetch_page(url):
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    headers = {"User-Agent": "AI-SEO-Audit-Assistant/1.0"}
    response = requests.get(url, headers=headers, timeout=15)
    response.raise_for_status()
    return url, response.text

def parse_page(html, url):
    soup = BeautifulSoup(html, "html.parser")
    title = soup.title.get_text(" ", strip=True) if soup.title else ""
    meta = soup.find("meta", attrs={"name": lambda x: x and x.lower() == "description"})
    description = meta.get("content", "").strip() if meta else ""
    h1s = [x.get_text(" ", strip=True) for x in soup.find_all("h1")]
    h2s = [x.get_text(" ", strip=True) for x in soup.find_all("h2")]
    canonical = soup.find("link", rel="canonical")
    canonical_url = canonical.get("href", "").strip() if canonical else ""
    robots = soup.find("meta", attrs={"name": lambda x: x and x.lower() == "robots"})
    robots_value = robots.get("content", "").strip() if robots else ""
    images = soup.find_all("img")
    missing_alt = sum(1 for img in images if not img.get("alt", "").strip())
    links = soup.find_all("a", href=True)
    text = soup.get_text(" ", strip=True)
    word_count = len(text.split())

    return {
        "url": url,
        "title": title,
        "title_length": len(title),
        "description": description,
        "description_length": len(description),
        "h1s": h1s,
        "h2s": h2s,
        "canonical": canonical_url,
        "robots": robots_value,
        "images": len(images),
        "missing_alt": missing_alt,
        "links": len(links),
        "word_count": word_count,
    }

def build_prompt(data, business_type):
    return f"""
You are a senior SEO consultant. Analyze this website page using the supplied crawl data.
Do not invent facts that are not present in the data. Clearly distinguish technical observations
from recommendations.

Business type: {business_type or "Not provided"}

PAGE DATA:
{data}

Return a concise client-ready audit with these sections:
1. Executive Summary
2. Critical Issues
3. On-Page SEO
4. Technical SEO
5. Content Opportunities
6. Recommended Title & Meta Description
7. Priority Action Plan

For every issue, explain why it matters and give a practical recommendation.
Use Priority labels: HIGH, MEDIUM, LOW.
"""

with st.sidebar:
    st.header("Audit Settings")
    url = st.text_input("Website URL", placeholder="https://example.com")
    business_type = st.text_input("Business / industry", placeholder="Golf course management")
    api_key = st.text_input("OpenAI API key", type="password", value=os.getenv("OPENAI_API_KEY", ""))
    run = st.button("Run AI Audit", type="primary", use_container_width=True)

if run:
    if not url:
        st.error("Enter a website URL first.")
        st.stop()
    if not api_key:
        st.error("Add an OpenAI API key in the sidebar or set OPENAI_API_KEY.")
        st.stop()

    with st.spinner("Fetching and analyzing the page..."):
        try:
            final_url, html = fetch_page(url)
            data = parse_page(html, final_url)
        except Exception as e:
            st.error(f"Could not fetch the page: {e}")
            st.stop()

    st.subheader("Crawl Snapshot")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Title", data["title_length"])
    c2.metric("Meta Description", data["description_length"])
    c3.metric("H1 Tags", len(data["h1s"]))
    c4.metric("Word Count", data["word_count"])

    with st.expander("Technical crawl data"):
        st.json(data)

    client = OpenAI(api_key=api_key)
    with st.spinner("Generating the AI audit..."):
        try:
            response = client.responses.create(
                model="gpt-5-mini",
                input=build_prompt(data, business_type)
            )
            audit = response.output_text
        except Exception as e:
            st.error(f"AI analysis failed: {e}")
            st.stop()

    st.subheader("AI Audit Report")
    st.markdown(audit)

    st.download_button(
        "Download Audit as Markdown",
        data=audit,
        file_name="ai-seo-audit.md",
        mime="text/markdown",
        use_container_width=True
    )

st.divider()
st.caption("Use this tool as an audit assistant. Verify recommendations manually before presenting them to clients.")
