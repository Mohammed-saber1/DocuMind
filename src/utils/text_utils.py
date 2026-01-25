"""Text processing and sanitization utilities."""
import re


def preprocess_text(text: str) -> str:
    """Preprocess document text for LLM processing."""
    text = re.sub(r"Page\s+\d+\s+of\s+\d+", "", text, flags=re.I)
    text = re.sub(r"\^[a-zA-Z_]+\s+.*", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def sanitize_for_json(text: str) -> str:
    """Sanitize text to prevent JSON parsing issues."""
    # Remove or replace problematic characters
    text = text.replace('\x00', '')  # null bytes
    text = text.replace('\x0b', ' ')  # vertical tab
    text = text.replace('\x0c', ' ')  # form feed
    text = text.replace('\r\n', '\n')  # normalize line endings
    text = text.replace('\r', '\n')
    # Remove other control characters except newline and tab
    text = ''.join(char for char in text if ord(char) >= 32 or char in '\n\t')
    return text


def extract_json(text: str):
    """Extract and clean JSON from LLM response."""
    # Try to find JSON in markdown code blocks first
    markdown_match = re.search(r'```(?:json)?\s*(\{[\s\S]*?\})\s*```', text)
    if markdown_match:
        json_str = markdown_match.group(1)
    else:
        # Try to find raw JSON
        match = re.search(r'\{[\s\S]*\}', text)
        if not match:
            raise ValueError("No JSON found in LLM response")
        json_str = match.group(0)
    
    # Clean up common issues
    json_str = json_str.strip()
    
    return json_str
