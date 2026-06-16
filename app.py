

import streamlit as st
from datetime import datetime
from blog_fetcher import fetch_blogs, BLOG_SOURCES

st.set_page_config(page_title="AI Blogs Tracker", page_icon="📡", layout="wide")

if "blogs" not in st.session_state:
    st.session_state.blogs = []
if "last_updated" not in st.session_state:
    st.session_state.last_updated = None

# ── Sidebar ──
with st.sidebar:
    st.header("Sources")
    all_names = sorted(BLOG_SOURCES.keys())
    selected = st.multiselect("Companies to include:", all_names, default=all_names)

    st.divider()
    st.subheader("Add custom source")
    new_name = st.text_input("Company name:", placeholder="e.g. xAI")
    new_url = st.text_input("Blog page URL:", placeholder="e.g. https://x.ai/blog")

    st.divider()
    st.caption(f"{len(selected)} source(s) selected")

# ── Main ──
st.title("AI Blogs Tracker")
st.caption("Latest technical blogs from top AI companies & research labs")

col1, col2 = st.columns([3, 1])
with col2:
    fetch_clicked = st.button("🔄 Fetch Latest", use_container_width=True)
with col1:
    if st.session_state.last_updated:
        st.info(f"Last updated: {st.session_state.last_updated.strftime('%B %d, %Y at %I:%M %p')}")
    else:
        st.warning("Click **Fetch Latest** to load blogs.")

if fetch_clicked:
    if not selected:
        st.error("Select at least one company.")
    else:
        extra = {}
        if new_name and new_url:
            extra[new_name] = new_url

        with st.spinner(f"Fetching blogs from {len(selected)} sources... (this takes ~20s)"):
            active_sources = {k: BLOG_SOURCES[k] for k in selected}
            active_sources.update(extra)
            st.session_state.blogs = fetch_blogs(extra_sources=extra if extra else None)
            st.session_state.last_updated = datetime.now()
        st.rerun()

st.divider()

if st.session_state.blogs:
    source_list = sorted(set(b.get("source", "Unknown") for b in st.session_state.blogs))
    filter_sources = st.multiselect("Filter by source:", source_list, default=source_list)

    filtered = [b for b in st.session_state.blogs if b.get("source") in filter_sources]
    st.markdown(f"**{len(filtered)} blog(s)**")

    for blog in filtered:
        with st.container():
            c1, c2 = st.columns([4, 1])
            with c1:
                st.markdown(f"### [{blog['title']}]({blog['url']})")
            with c2:
                st.caption(f"🏢 {blog.get('source', 'Unknown')}")
                pub = blog.get("published_date", "Recent")
                st.caption(f"📅 {pub}")
            st.divider()
elif st.session_state.last_updated:
    st.info("No blogs found. Try again or add more sources.")
