"""
DocuMind Streamlit Application 🧠
==================================

A modern document ingestion and chat interface using native Streamlit components.

Features:
- Multi-modal document upload (PDF, PPT, Word, TXT, images, audio, video)
- URL ingestion (Website, YouTube)
- Streaming chat interface
- Automatic session management

Run with:
    streamlit run app.py
"""
import streamlit as st
import uuid
import time

# Import local modules
from config import (
    ALL_EXTENSIONS,
    SUPPORTED_FILES,
    URL_TYPES,
    DEFAULT_K,
    DEFAULT_OCR_VLM
)
from api_service import (
    submit_extraction,
    send_chat_message,
    stream_chat_response
)
from components import (
    render_header,
    render_file_uploader,
    render_url_inputs,
    render_metadata_form,
    render_success_state,
    render_sidebar_session_info,
    render_empty_state
)

# --- Page Configuration ---
st.set_page_config(
    page_title="DocuMind 🧠",
    page_icon="🧠",
    layout="centered",
    initial_sidebar_state="expanded"
)


def init_session_state():
    """Initialize all session state variables."""
    defaults = {
        "session_id": str(uuid.uuid4()),
        "app_stage": "upload",  # upload, processing, chat
        "selected_modalities": [],
        "uploaded_files": [],
        "urls": [],
        "author": "",
        "description": "",
        "processing_status": "idle",  # idle, processing, ready
        "chat_history": [],
        "doc_count": 0,
        "task_id": None
    }
    
    for key, default in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default


def reset_session():
    """Reset to a new session."""
    st.session_state.session_id = str(uuid.uuid4())
    st.session_state.app_stage = "upload"
    st.session_state.selected_modalities = []
    st.session_state.uploaded_files = []
    st.session_state.urls = []
    st.session_state.author = ""
    st.session_state.description = ""
    st.session_state.processing_status = "idle"
    st.session_state.chat_history = []
    st.session_state.doc_count = 0
    st.session_state.task_id = None
    st.rerun()


def render_upload_section():
    """Render the document upload interface."""
    render_header()
    
    # --- Input Type Selection ---
    st.subheader("📤 Select Input Types")
    
    # File type toggles
    st.markdown("**Files:**")
    file_cols = st.columns(len(SUPPORTED_FILES))
    for i, (key, data) in enumerate(SUPPORTED_FILES.items()):
        with file_cols[i]:
            is_selected = key in st.session_state.selected_modalities
            if st.checkbox(f"{data['icon']}", value=is_selected, key=f"mod_{key}", help=data['label']):
                if key not in st.session_state.selected_modalities:
                    st.session_state.selected_modalities.append(key)
            else:
                if key in st.session_state.selected_modalities:
                    st.session_state.selected_modalities.remove(key)
    
    # Labels below checkboxes
    label_cols = st.columns(len(SUPPORTED_FILES))
    for i, (key, data) in enumerate(SUPPORTED_FILES.items()):
        with label_cols[i]:
            st.caption(data['label'])
    
    st.markdown("")
    
    # URL type toggles
    st.markdown("**URLs:**")
    url_cols = st.columns(2)
    for i, (key, data) in enumerate(URL_TYPES.items()):
        with url_cols[i]:
            is_selected = key in st.session_state.selected_modalities
            if st.checkbox(f"{data['icon']} {data['label']}", value=is_selected, key=f"url_{key}"):
                if key not in st.session_state.selected_modalities:
                    st.session_state.selected_modalities.append(key)
            else:
                if key in st.session_state.selected_modalities:
                    st.session_state.selected_modalities.remove(key)
    
    st.divider()
    
    # --- Upload Section ---
    has_file_modality = any(m in SUPPORTED_FILES for m in st.session_state.selected_modalities)
    has_website = "website" in st.session_state.selected_modalities
    has_youtube = "youtube" in st.session_state.selected_modalities
    
    # Get allowed extensions based on selected modalities
    allowed_extensions = []
    for mod in st.session_state.selected_modalities:
        if mod in SUPPORTED_FILES:
            allowed_extensions.extend(SUPPORTED_FILES[mod]["extensions"])
    
    # File uploader
    uploaded_files = []
    if has_file_modality:
        st.subheader("📁 Upload Files")
        uploaded_files = st.file_uploader(
            "Drop files here or click to browse",
            type=allowed_extensions if allowed_extensions else ALL_EXTENSIONS,
            accept_multiple_files=True,
            key="file_uploader",
            label_visibility="collapsed"
        )
        
        if uploaded_files:
            st.success(f"✓ {len(uploaded_files)} file(s) selected")
    
    # URL inputs
    urls = []
    if has_website:
        st.subheader("🌐 Website URL")
        website_url = st.text_input(
            "Website URL",
            placeholder="https://example.com/article",
            key="website_url_input",
            label_visibility="collapsed"
        )
        if website_url:
            urls.append(website_url)
            
    if has_youtube:
        st.subheader("▶️ YouTube URL")
        youtube_url = st.text_input(
            "YouTube URL",
            placeholder="https://youtube.com/watch?v=...",
            key="youtube_url_input",
            label_visibility="collapsed"
        )
        if youtube_url:
            urls.append(youtube_url)
    
    # Show placeholder if nothing selected
    if not st.session_state.selected_modalities:
        render_empty_state("👆", "Select input types above to get started")
    
    st.divider()
    
    # --- Metadata Section ---
    st.subheader("📋 Document Information")
    
    col1, col2 = st.columns([1, 1])
    with col1:
        author = st.text_input(
            "Author Name *",
            placeholder="Your name",
            key="author_input"
        )
    
    description = st.text_area(
        "Description (optional)",
        placeholder="Brief description of the documents...",
        height=80,
        key="description_input"
    )
    
    st.divider()
    
    # --- Submit Button ---
    can_submit = (uploaded_files or urls) and author
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button(
            "🚀 Process Documents",
            use_container_width=True,
            disabled=not can_submit,
            type="primary"
        ):
            if not author:
                st.error("Please enter your name")
            elif not (uploaded_files or urls):
                st.error("Please upload files or enter URLs")
            else:
                # Store data and transition to processing
                st.session_state.uploaded_files = uploaded_files
                st.session_state.urls = urls
                st.session_state.author = author
                st.session_state.description = description
                st.session_state.app_stage = "processing"
                st.session_state.processing_status = "processing"
                st.rerun()
    
    if not can_submit:
        st.caption("Add content and your name to continue")


def render_processing_section():
    """Render the processing state."""
    render_header()
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("### 🧠")
        st.markdown("**Extracting intelligence...**")
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # Submit to backend
    status_text.text("Connecting to backend...")
    progress_bar.progress(20)
    
    response = submit_extraction(
        files=st.session_state.uploaded_files,
        links=st.session_state.urls,
        session_id=st.session_state.session_id,
        author=st.session_state.author,
        description=st.session_state.description
    )
    
    progress_bar.progress(80)
    
    if response.get("error"):
        progress_bar.empty()
        status_text.empty()
        st.error(f"❌ Processing failed: {response.get('message', 'Unknown error')}")
        if st.button("← Back to Upload"):
            st.session_state.app_stage = "upload"
            st.session_state.processing_status = "idle"
            st.rerun()
    else:
        progress_bar.progress(100)
        status_text.text("Processing complete!")
        
        # Store task info
        st.session_state.task_id = response.get("task_id")
        
        # Count documents
        file_count = len(st.session_state.uploaded_files)
        url_count = len(st.session_state.urls)
        st.session_state.doc_count = file_count + url_count
        
        # Show success
        render_success_state()
        
        st.toast("✅ Documents processed successfully!", icon="🎉")
        
        # Transition to chat after brief delay
        time.sleep(1.5)
        st.session_state.app_stage = "chat"
        st.session_state.processing_status = "ready"
        st.rerun()


def render_chat_section():
    """Render the chat interface."""
    # Header
    st.markdown("## 💬 Chat with Your Documents")
    st.caption("Ask questions about your uploaded content")
    st.divider()
    
    # Chat history
    if not st.session_state.chat_history:
        render_empty_state("💭", "Start a conversation by asking a question below")
    else:
        for message in st.session_state.chat_history:
            avatar = "👤" if message["role"] == "user" else "🧠"
            with st.chat_message(message["role"], avatar=avatar):
                st.markdown(message["content"])
    
    # Chat input
    if prompt := st.chat_input("Ask a question about your documents..."):
        # Add user message
        st.session_state.chat_history.append({
            "role": "user",
            "content": prompt
        })
        
        # Display user message
        with st.chat_message("user", avatar="👤"):
            st.markdown(prompt)
        
        # Get AI response with streaming
        with st.chat_message("assistant", avatar="🧠"):
            message_placeholder = st.empty()
            full_response = ""
            
            # Show thinking
            message_placeholder.markdown("*Thinking...*")
            
            # Try streaming first, fallback to regular chat
            try:
                for token in stream_chat_response(
                    message=prompt,
                    session_id=st.session_state.session_id,
                    k=DEFAULT_K,
                    use_history=True
                ):
                    full_response += token
                    message_placeholder.markdown(full_response + "▌")
                
                message_placeholder.markdown(full_response)
                
            except Exception as e:
                # Fallback to non-streaming
                response = send_chat_message(
                    message=prompt,
                    session_id=st.session_state.session_id,
                    k=DEFAULT_K,
                    use_history=True
                )
                full_response = response.get("answer", "Sorry, I couldn't generate a response.")
                message_placeholder.markdown(full_response)
        
        # Add assistant message to history
        st.session_state.chat_history.append({
            "role": "assistant",
            "content": full_response
        })
    
    # Back to upload option
    st.markdown("")
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        if st.button("📤 Upload More Documents", use_container_width=True):
            st.session_state.app_stage = "upload"
            st.session_state.processing_status = "idle"
            st.rerun()


def render_sidebar():
    """Render the sidebar with session info."""
    should_reset = render_sidebar_session_info(
        session_id=st.session_state.session_id,
        status=st.session_state.processing_status,
        doc_count=st.session_state.doc_count
    )
    
    if should_reset:
        reset_session()
    
    # About section
    with st.sidebar:
        st.divider()
        st.subheader("About DocuMind")
        st.caption(
            "Transform unstructured documents into an intelligent knowledge base "
            "you can chat with."
        )
        
        st.markdown("""
**Supported formats:**
- 📄 PDF, 📊 PPT, 📝 Word, 📃 TXT
- 🖼️ Images, 🎧 Audio, 🎬 Video
- 🌐 Websites, ▶️ YouTube
        """)


def main():
    """Main application entry point."""
    # Initialize session state
    init_session_state()
    
    # Render sidebar
    render_sidebar()
    
    # Route based on app stage
    if st.session_state.app_stage == "upload":
        render_upload_section()
    elif st.session_state.app_stage == "processing":
        render_processing_section()
    elif st.session_state.app_stage == "chat":
        render_chat_section()


if __name__ == "__main__":
    main()
