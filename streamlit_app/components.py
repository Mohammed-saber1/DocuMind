"""
DocuMind UI Components 🧩
==========================

Reusable Streamlit UI components using native Streamlit elements.
"""
import streamlit as st
from typing import List, Optional
from config import SUPPORTED_FILES, URL_TYPES


def render_header():
    """Render the main header."""
    st.markdown("# DocuMind 🧠")
    st.caption("Turn unstructured data into intelligence")
    st.divider()


def render_file_uploader(accepted_extensions: List[str]):
    """
    Render the file uploader widget.
    
    Args:
        accepted_extensions: List of accepted file extensions
        
    Returns:
        List of uploaded files
    """
    return st.file_uploader(
        "📁 Drop files here or click to browse",
        type=accepted_extensions,
        accept_multiple_files=True,
        key="file_uploader"
    )


def render_url_inputs(show_website: bool = False, show_youtube: bool = False):
    """
    Render URL input fields based on selected modalities.
    
    Args:
        show_website: Whether to show website URL input
        show_youtube: Whether to show YouTube URL input
        
    Returns:
        Tuple of (website_url, youtube_url)
    """
    website_url = ""
    youtube_url = ""
    
    if show_website:
        website_url = st.text_input(
            "🌐 Website URL",
            placeholder="https://example.com/article",
            key="website_url_input"
        )
        
    if show_youtube:
        youtube_url = st.text_input(
            "▶️ YouTube URL",
            placeholder="https://youtube.com/watch?v=...",
            key="youtube_url_input"
        )
        
    return website_url, youtube_url


def render_metadata_form():
    """
    Render the metadata input form.
    
    Returns:
        Tuple of (author, description)
    """
    st.subheader("📋 Document Information")
    
    author = st.text_input(
        "Author Name *",
        placeholder="Enter your name",
        key="author_input"
    )
    
    description = st.text_area(
        "Description (optional)",
        placeholder="Brief description of the documents...",
        height=100,
        key="description_input"
    )
    
    return author, description


def render_processing_animation():
    """Render the processing state with native Streamlit spinner."""
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("### 🧠")
        st.info("Extracting intelligence...")
    st.progress(0.5)


def render_success_state():
    """Render the success completion state."""
    st.success("✨ Your knowledge base is ready!")
    st.balloons()


def render_chat_message(role: str, content: str):
    """
    Render a single chat message using native st.chat_message.
    
    Args:
        role: 'user' or 'assistant'
        content: Message content
    """
    avatar = "👤" if role == "user" else "🧠"
    with st.chat_message(role, avatar=avatar):
        st.markdown(content)


def render_thinking_indicator():
    """Render the AI thinking indicator."""
    with st.chat_message("assistant", avatar="🧠"):
        st.markdown("*Thinking...*")


def render_chat_input():
    """
    Render the chat input field.
    
    Returns:
        User's message input
    """
    return st.chat_input("Ask a question about your documents...")


def render_sidebar_session_info(
    session_id: str,
    status: str = "idle",
    doc_count: int = 0
):
    """
    Render session information in the sidebar.
    
    Args:
        session_id: Current session identifier
        status: Status ('idle', 'processing', 'ready')
        doc_count: Number of indexed documents
        
    Returns:
        True if user clicked "New Session"
    """
    with st.sidebar:
        st.header("📊 Session")
        
        # Status indicator
        status_emoji = {"idle": "⚪", "processing": "🟡", "ready": "🟢"}.get(status, "⚪")
        status_label = status.capitalize()
        st.markdown(f"**Status:** {status_emoji} {status_label}")
        
        # Session ID
        with st.expander("🔑 Session ID"):
            st.code(session_id, language=None)
        
        # Document count
        if doc_count > 0:
            st.metric("📄 Documents", doc_count)
        
        st.divider()
        
        # New session button
        if st.button("🔄 New Session", use_container_width=True):
            return True
            
    return False


def render_empty_state(icon: str = "📂", message: str = "No documents uploaded yet"):
    """
    Render an empty state placeholder.
    
    Args:
        icon: Emoji icon to display
        message: Message to display
    """
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown(f"### {icon}")
        st.caption(message)
