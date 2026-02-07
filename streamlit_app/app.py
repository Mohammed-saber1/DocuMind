"""
DocuMind 🧠 - Enterprise Document Intelligence Platform
=======================================================

Production-ready single-page Streamlit application.
"""
import streamlit as st
import uuid

from config import ALL_EXTENSIONS, SUPPORTED_FILES, DEFAULT_K
from api_service import submit_extraction, send_chat_message, stream_chat_response

# ============================================================================
# PAGE CONFIG
# ============================================================================
st.set_page_config(
    page_title="DocuMind 🧠",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ============================================================================
# SESSION STATE
# ============================================================================
def init_session():
    defaults = {
        "session_id": str(uuid.uuid4()),
        "stage": "input",
        "files": [],
        "website_url": "",
        "youtube_url": "",
        "author": "",
        "description": "",
        "selected_types": set(),
        "chat_history": [],
        "sources": [],
        "doc_count": 0,
        "processing": False,
        "all_files": set()
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def reset():
    for k in list(st.session_state.keys()):
        del st.session_state[k]
    init_session()
    st.rerun()


# ============================================================================
# UI COMPONENTS
# ============================================================================

def render_header():
    """Professional header."""
    st.title("DocuMind 🧠")
    st.markdown("### Intelligent Document Extraction & Intelligence Platform")


def render_input_types():
    """Input type selection grid."""
    st.markdown("#### 📂 Select Input Types")
    
    types = [
        ("website", "🌐", "Website"),
        ("youtube", "▶️", "YouTube"),
        ("pdf", "📄", "PDF"),
        ("ppt", "📊", "PPT"),
        ("word", "📝", "Word"),
        ("txt", "📃", "TXT"),
        ("image", "🖼️", "Images"),
        ("audio", "🎧", "Audio"),
        ("video", "🎬", "Video"),
    ]
    
    cols = st.columns(9)
    for i, (key, icon, label) in enumerate(types):
        with cols[i]:
            active = key in st.session_state.selected_types
            btn_type = "primary" if active else "secondary"
            if st.button(f"{icon}\n{label}", key=f"type_{key}", use_container_width=True, type=btn_type):
                if active:
                    st.session_state.selected_types.discard(key)
                else:
                    st.session_state.selected_types.add(key)
                st.rerun()


def render_metadata():
    """Author and description inputs."""
    st.markdown("#### 👤 Document Information")
    
    col1, col2 = st.columns([1, 2])
    with col1:
        author = st.text_input("Author Name *", placeholder="Enter your name", key="author_in", disabled=st.session_state.processing)
        st.session_state.author = author
    with col2:
        desc = st.text_area("Description (Optional)", placeholder="Brief description...", height=80, key="desc_in", disabled=st.session_state.processing)
        st.session_state.description = desc


def render_url_inputs():
    """URL input fields."""
    selected = st.session_state.selected_types
    
    if "website" in selected or "youtube" in selected:
        st.markdown("#### 🔗 URLs")
        col1, col2 = st.columns(2)
        
        if "website" in selected:
            with col1:
                url = st.text_input("🌐 Website URL", placeholder="https://example.com", key="web_in", disabled=st.session_state.processing)
                st.session_state.website_url = url
        
        if "youtube" in selected:
            with col2:
                url = st.text_input("▶️ YouTube URL", placeholder="https://youtube.com/watch?v=...", key="yt_in", disabled=st.session_state.processing)
                st.session_state.youtube_url = url


def render_file_upload():
    """File upload section."""
    file_types = {"pdf", "ppt", "word", "txt", "image", "audio", "video"}
    active_files = st.session_state.selected_types & file_types
    
    if active_files:
        st.markdown("#### 📁 Upload Files")
        
        # Build extensions
        exts = []
        for ft in active_files:
            if ft in SUPPORTED_FILES:
                exts.extend(SUPPORTED_FILES[ft]["extensions"])
        
        files = st.file_uploader(
            "Drop files here",
            type=exts or ALL_EXTENSIONS,
            accept_multiple_files=True,
            key="upload",
            label_visibility="collapsed",
            disabled=st.session_state.processing
        )
        
        if files:
            st.session_state.files = files
            with st.expander(f"✅ {len(files)} file(s) selected"):
                for f in files:
                    ext = f.name.split(".")[-1].lower()
                    icon = "📄"
                    for ft, d in SUPPORTED_FILES.items():
                        if ext in d["extensions"]:
                            icon = d["icon"]
                            break
                    st.write(f"{icon} {f.name}")


def render_submit():
    """Submit button."""
    urls = []
    if st.session_state.website_url:
        urls.append(st.session_state.website_url)
    if st.session_state.youtube_url:
        urls.append(st.session_state.youtube_url)
    
    can_submit = (st.session_state.files or urls) and st.session_state.author and not st.session_state.processing
    
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        if st.button("🚀 Submit & Process", use_container_width=True, disabled=not can_submit, type="primary"):
            st.session_state.processing = True
            st.session_state.stage = "processing"
            st.rerun()
    
    if not can_submit and st.session_state.selected_types:
        if not st.session_state.author:
            st.caption("⚠️ Enter your name to continue")
        elif not (st.session_state.files or urls):
            st.caption("⚠️ Upload files or add URLs")


def render_processing():
    """Processing screen."""
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("### ⏳ Processing Documents...")
        
        with st.spinner("Extracting intelligence..."):
            urls = []
            if st.session_state.website_url:
                urls.append(st.session_state.website_url)
            if st.session_state.youtube_url:
                urls.append(st.session_state.youtube_url)
            
            response = submit_extraction(
                files=st.session_state.files,
                links=urls,
                session_id=st.session_state.session_id,
                author=st.session_state.author,
                description=st.session_state.description
            )
        
        if response.get("error"):
            st.error(f"❌ {response.get('message', 'Failed')}")
            st.session_state.processing = False
            st.session_state.stage = "input"
            if st.button("← Try Again"):
                st.rerun()
        else:
            st.session_state.doc_count += len(st.session_state.files) + len(urls)
            
            # Track all files for sidebar
            for f in st.session_state.files:
                st.session_state.all_files.add(f.name)
            if st.session_state.website_url:
                st.session_state.all_files.add(st.session_state.website_url)
            if st.session_state.youtube_url:
                st.session_state.all_files.add(st.session_state.youtube_url)
                
            st.success(f"✅ {st.session_state.doc_count} documents indexed")
            st.session_state.stage = "chat"
            st.session_state.processing = False
            st.rerun()






def render_chat():
    """Chat interface with sources."""
    # Layout: Chat (left) | Sources (right)
    chat_col, source_col = st.columns([2, 1])
    
    with chat_col:
        st.markdown("### 💬 Chat with Your Documents")
        st.caption(f"📄 {st.session_state.doc_count} documents indexed")
        
        # Chat container
        container = st.container(height=450)
        with container:
            if not st.session_state.chat_history:
                st.markdown("")
                st.info("💡 Ask any question about your uploaded documents")
            else:
                for msg in st.session_state.chat_history:
                    avatar = "👤" if msg["role"] == "user" else "🧠"
                    with st.chat_message(msg["role"], avatar=avatar):
                        content = msg["content"]
                        st.write(content)
        
        # Input
        if prompt := st.chat_input("Ask a question..."):
            st.session_state.chat_history.append({"role": "user", "content": prompt})
            
            with container:
                with st.chat_message("user", avatar="👤"):
                    st.markdown(prompt)
                
                with st.chat_message("assistant", avatar="🧠"):
                    placeholder = st.empty()
                    response_text = ""
                    placeholder.markdown("Thinking...")
                    
                    try:
                        response_text = ""
                        placeholder.markdown("Thinking...")
                        
                        for_loop = stream_chat_response(
                            message=prompt,
                            session_id=st.session_state.session_id,
                            k=DEFAULT_K,
                            use_history=True
                        )
                        
                        for token in for_loop:
                            response_text += token
                            # Real-time formatting for better UX
                            formatted_live = response_text
                            placeholder.empty()
                            placeholder.markdown(formatted_live + "▌")
                            
                        # Final render
                        formatted_final = response_text
                        placeholder.write(formatted_final)
                        response_text = formatted_final
                        
                    except Exception:
                        resp = send_chat_message(prompt, st.session_state.session_id, DEFAULT_K, True)
                        raw_response = resp.get("answer", "Unable to respond.")
                        response_text = raw_response
                        placeholder.write(response_text)
                        if resp.get("sources"):
                            st.session_state.sources = resp["sources"]
            
            st.session_state.chat_history.append({"role": "assistant", "content": response_text})
            st.rerun()
    
    with source_col:
        st.markdown("### 📚 Sources")
        
        if st.session_state.sources:
            for i, src in enumerate(st.session_state.sources, 1):
                with st.expander(f"Source {i}"):
                    st.markdown(src.get("content", "")[:250] + "...")
        else:
            st.caption("Sources appear as you chat")
            st.markdown("---")
            st.markdown("**📁 All Documents:**")
            
            # Extract source filenames from active sources
            # Sources typically have metadata with 'source' key
            active_sources = set()
            if st.session_state.sources:
                for s in st.session_state.sources:
                    if "metadata" in s:
                        active_sources.add(s["metadata"].get("source"))
                    elif "source" in s:
                        active_sources.add(s.get("source"))

            for f_name in sorted(list(st.session_state.all_files)):
                if any(src and f_name in src for src in active_sources):
                    st.success(f"📄 {f_name}")
                else:
                    st.write(f"📄 {f_name}")
        
        
        st.markdown("---")
        if st.button("➕ Add More Documents", use_container_width=True):
            st.session_state.files = []
            st.session_state.website_url = ""
            st.session_state.youtube_url = ""
            st.session_state.stage = "input"
            if "upload" in st.session_state:
                del st.session_state["upload"]
            st.rerun()

        if st.button("🔄 New Session", use_container_width=True):
            reset()


# ============================================================================
# MAIN
# ============================================================================
def main():
    init_session()
    render_header()
    
    if st.session_state.stage == "input":
        st.markdown("---")
        
        # Section 1: Input Types
        with st.container():
            render_input_types()
        
        if st.session_state.selected_types:
            st.markdown("")
            
            # Section 2: Metadata
            with st.container():
                render_metadata()
            
            st.markdown("")
            
            # Section 3: URLs
            with st.container():
                render_url_inputs()
            
            st.markdown("")
            
            # Section 4: Files
            with st.container():
                render_file_upload()
            
            # Submit
            render_submit()
    
    elif st.session_state.stage == "processing":
        st.markdown("---")
        render_processing()
    
    elif st.session_state.stage == "chat":
        st.markdown("---")
        render_chat()


if __name__ == "__main__":
    main()
