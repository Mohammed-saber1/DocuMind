import os
import json
import logging
from typing import List, Dict, Any, Optional
from langchain_ollama import ChatOllama
from pydantic import BaseModel, Field

from utils.text_utils import preprocess_text, sanitize_for_json, extract_json
from core.config import get_settings

# Configure Logging
logger = logging.getLogger(__name__)

# --- Pydantic Models for Structured Output ---

class DocumentMetadata(BaseModel):
    """Schema for document analysis results."""
    language: str = Field(description="The primary language of the document")
    summary: str = Field(description="A 2-5 sentence semantic summary of the document content")

class TableAnalysis(BaseModel):
    """Schema for advanced table/excel analysis."""
    sheet_purposes: Dict[str, str] = Field(default_factory=dict, description="Mapping of sheet names to their purpose")
    insights: List[str] = Field(default_factory=list, description="Key metrics, patterns, or business implications")
    data_type: Optional[str] = Field(None, description="General category of the data")
    column_descriptions: Optional[Dict[str, str]] = Field(None, description="Meaning of specific columns")
    key_statistics: List[str] = Field(default_factory=list, description="Computed statistics or notable values")



# LLM Prompt for document parsing
PARSING_PROMPT = """
You are a professional document analyst. Analyze this document and extract key information.

IMPORTANT INSTRUCTIONS:
1. Detect the primary language (english, arabic, mixed, etc.)
2. Write a COMPREHENSIVE semantic summary that covers:
   - What is the main topic/subject of the document?
   - What are the key points, features, or capabilities discussed?
   - What is the purpose or goal of the document?
   - Any important details, metrics, or conclusions

The summary should be 2-5 sentences that capture the ESSENCE of the document.
DO NOT just copy the first paragraph. Synthesize the entire content.
DO NOT mention structural elements like "this document has X pages" or "contains Y images".

Return ONLY a valid JSON object in this exact format:
{{
  "language": "detected language here",
  "summary": "Your comprehensive semantic summary here"
}}

Document Content:
{TEXT}

JSON Response:"""




async def run_agent(base_dir, source, source_id, file_hash, author="", user_description=None):
    """Parse document content using LLM (Async) and generate structured output."""
    text_path = os.path.join(base_dir, "text", "content.txt")


    with open(text_path, "r", encoding="utf-8") as f:
        raw_text = f.read()

    clean_text = preprocess_text(raw_text)
    clean_text = sanitize_for_json(clean_text)
    
    # Check if tables exist
    tables_path = os.path.join(base_dir, "tables", "tables.json")
    tables_info = ""
    table_count = 0
    
    if os.path.exists(tables_path):
        with open(tables_path, "r", encoding="utf-8") as f:
            tables_data = json.load(f)
            table_count = len(tables_data)
            
            # Create structured table information for LLM
            tables_info = f"\n\nTABLES FOUND: {table_count}\n"
            for idx, table in enumerate(tables_data[:3], 1):
                tables_info += f"\nTable {idx}:\n"
                if "page" in table:
                    tables_info += f"Location: Page {table['page']}\n"
                elif "slide" in table:
                    tables_info += f"Location: Slide {table['slide']}\n"
                
                # Use headers field if available, otherwise fall back to first data row
                headers = table.get("headers", [])
                data = table.get("data", [])
                
                if headers:
                    tables_info += f"Columns: {len(headers)}\n"
                    tables_info += f"Rows: {len(data)}\n"
                    tables_info += f"Headers: {', '.join(str(h) for h in headers)}\n"
                elif data:
                    tables_info += f"Columns: {len(data[0]) if data else 0}\n"
                    tables_info += f"Rows: {len(data)}\n"
                    if len(data) > 0:
                        tables_info += f"Headers: {', '.join(str(h) for h in data[0])}\n"
    
    # Check for image analysis (OCR + VLM)
    images_analysis_path = os.path.join(base_dir, "images", "analysis.json")  # VLM results
    ocr_analysis_path = os.path.join(base_dir, "images", "ocr_analysis.json")  # OCR results
    images_info = ""
    all_images_data = []  # Combined OCR + VLM results

    # Load OCR analysis results
    if os.path.exists(ocr_analysis_path):
        with open(ocr_analysis_path, "r", encoding="utf-8") as f:
            ocr_data = json.load(f)
            all_images_data.extend(ocr_data)
            if ocr_data:
                images_info += f"\n\nOCR IMAGES ({len(ocr_data)}):\n"
                for img in ocr_data:
                    images_info += f"- [OCR] Image: {img['image']}\n"
                    images_info += f"  Text: {img.get('content_images', '')[:300]}...\n"

    # Load VLM analysis results
    if os.path.exists(images_analysis_path):
        with open(images_analysis_path, "r", encoding="utf-8") as f:
            vlm_data = json.load(f)
            all_images_data.extend(vlm_data)
            if vlm_data:
                images_info += f"\n\nVLM IMAGES ({len(vlm_data)}):\n"
                for img in vlm_data:
                    images_info += f"- [VLM] Image: {img['image']}\n"
                    images_info += f"  Content: {img.get('content_images', '')[:300]}...\n"
                    if img.get('is_graph'):
                        images_info += f"  Type: Graph/Chart\n"

    # Limit text for LLM to avoid token limits
    text_for_llm = clean_text[:3500] if len(clean_text) > 3500 else clean_text
    
    # 🕵️ Guardrail: Check if we have ANY meaningful content to analyze
    has_content = (len(text_for_llm.strip()) > 10) or table_count > 0 or len(all_images_data) > 0
    
    if not has_content:
        logger.warning(f"⚠️ No content found for {source_id}. Skipping LLM call to prevent hallucination.")
        # Create a basic summary from user description or filename
        basic_summary = user_description if user_description and len(user_description) > 5 else f"Image file: {source_id}"
        
        parsed = {
            "source_id": source_id,
            "source": source,
            "language": "unknown",
            "author": author,
            "user_description": user_description if user_description else "",
            "summary": f"No extractable text found. {basic_summary}",
            "tables_count": 0,
            "file_hash": file_hash,
            "clean_content": clean_text
        }
        
        # Save placeholder structured.json
        parsed_dir = os.path.join(base_dir, "parsed")
        os.makedirs(parsed_dir, exist_ok=True)
        out = os.path.join(parsed_dir, "structured.json")
        with open(out, "w", encoding="utf-8") as f:
            json.dump(parsed, f, indent=2, ensure_ascii=False)
            
        return out, parsed

    text_for_llm += tables_info
    text_for_llm += images_info

    print(f"🤖 Calling LLM for parsing... (Tables: {table_count}, Images: {len(all_images_data)})")
    
    settings = get_settings()
    llm = ChatOllama(
        model=settings.llm.model,
        temperature=settings.llm.temperature,
        base_url=settings.llm.base_url
    )
    
    # Use Async invoke
    try:
        response = await llm.ainvoke(PARSING_PROMPT.format(TEXT=text_for_llm))
        response_text = response.content if hasattr(response, "content") else response
    except Exception as e:
        logger.error(f"❌ Failed to invoke LLM: {e}")
        response_text = ""

    
    # Default values
    language = "unknown"
    summary = "Document processed successfully"
    
    # Create a better default summary for Excel files
    if source == "excel" and os.path.exists(tables_path):
        with open(tables_path, "r", encoding="utf-8") as f:
            tables_data = json.load(f)
            if tables_data:
                total_rows = sum(t.get("rows", 0) for t in tables_data)
                total_cols = tables_data[0].get("columns", 0) if tables_data else 0
                sheet_names = [t.get("sheet", "Unknown") for t in tables_data]
                
                if len(tables_data) == 1:
                    summary = f"Excel workbook with 1 sheet ({sheet_names[0]}) containing {total_rows} rows and {total_cols} columns of data"
                else:
                    summary = f"Excel workbook with {len(tables_data)} sheets ({', '.join(sheet_names[:3])}) containing {total_rows} total rows of data"
    
    # Create a better default summary for CSV files
    elif source == "csv" and os.path.exists(tables_path):
        with open(tables_path, "r", encoding="utf-8") as f:
            tables_data = json.load(f)
            if tables_data:
                csv_data = tables_data[0]
                rows = csv_data.get("rows", 0)
                cols = csv_data.get("columns", 0)
                
                data = csv_data.get("data", [])
                headers = data[0] if data else []
                
                summary = f"CSV file with {rows} rows and {cols} columns"
                if headers and len(headers) > 0:
                    header_preview = ', '.join(str(h)[:20] for h in headers[:5])
                    if len(headers) > 5:
                        header_preview += "..."
                    summary += f" (columns: {header_preview})"
    
    # Update summary with image insights if available and valid
    if all_images_data and len(summary) < 50:
         summary += f" (Contains {len(all_images_data)} analyzed images/charts)"

    try:
        json_str = extract_json(response_text)
        llm_parsed = json.loads(json_str)
        
        language = llm_parsed.get("language", "unknown")
        llm_summary = llm_parsed.get("summary", "")
        
        if llm_summary and len(llm_summary) > 20:
            summary = llm_summary
        
        print("✅ LLM parsing successful")
        
    except Exception as e:
        print(f"⚠️ LLM parsing failed: {e}")
        print(f"📄 LLM Response (first 300 chars): {response_text[:300]}")
        print("ℹ️ Using default values")
    
    # Build final structured output (author comes from endpoint input, not LLM)
    parsed = {
        "source_id": source_id,
        "source": source,
        "language": language,
        "author": author,  # Author is provided by the uploader via endpoint
        "user_description": user_description if user_description else "",
        "summary": summary,
        "tables_count": table_count,
        "file_hash": file_hash,
    }
    
    # For non-Excel files, include clean_content (with image analysis for RAG)
    if source != "excel":
        # Append image analysis content to clean_text for RAG indexing
        if all_images_data:
            images_text_parts = []
            for img in all_images_data:
                method = img.get('method', 'unknown').upper()
                image_name = img.get('image', 'unknown')
                content = img.get('content_images', '')
                if content:
                    images_text_parts.append(f"[{method} - {image_name}]: {content}")
            
            if images_text_parts:
                images_section = "\n\n--- IMAGE ANALYSIS ---\n" + "\n\n".join(images_text_parts)
                clean_text = clean_text + images_section
        
        parsed["clean_content"] = clean_text
    
    # For Excel files, include analysis.json, charts.json and tables.json data directly
    # For Excel files, include analysis.json, charts.json and tables.json data directly
    if source == "excel":
        analysis_path = os.path.join(base_dir, "tables", "analysis.json")
        if os.path.exists(analysis_path):
            with open(analysis_path, "r", encoding="utf-8") as f:
                analysis_data = json.load(f)
                parsed["analysis"] = analysis_data
                
                # OPTIMIZATION: For single-sheet workbooks, use the sheet purpose as the main summary
                # to avoid redundancy between "summary" and "sheet_purposes"
                # if "sheet_purposes" in analysis_data and len(analysis_data["sheet_purposes"]) == 1:
                #     sheet_name = list(analysis_data["sheet_purposes"].keys())[0]
                #     parsed["summary"] = analysis_data["sheet_purposes"][sheet_name]
        
        charts_path = os.path.join(base_dir, "charts", "charts.json")
        if os.path.exists(charts_path):
            with open(charts_path, "r", encoding="utf-8") as f:
                parsed["charts"] = json.load(f)
        
        if os.path.exists(tables_path):
            with open(tables_path, "r", encoding="utf-8") as f:
                parsed["tables"] = json.load(f)
    
    # Include image analysis if available (OCR + VLM combined)
    if all_images_data:
        parsed["images_analysis"] = all_images_data

    # Include OCR metadata if available
    ocr_meta_path = os.path.join(base_dir, "text", "ocr_metadata.json")
    if os.path.exists(ocr_meta_path):
        with open(ocr_meta_path, "r", encoding="utf-8") as f:
            ocr_meta = json.load(f)
            parsed["ocr_metadata"] = ocr_meta

    # Save to file
    parsed_dir = os.path.join(base_dir, "parsed")
    os.makedirs(parsed_dir, exist_ok=True)

    out = os.path.join(parsed_dir, "structured.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(parsed, f, indent=2, ensure_ascii=False)

    return out, parsed


async def analyze_tables_with_llm(base_dir):
    """
    Advanced table analysis using LLM (Async).
    This function analyzes tables and charts to provide business insights.
    """
    tables_path = os.path.join(base_dir, "tables", "tables.json")

    charts_path = os.path.join(base_dir, "charts", "charts.json")
    
    if not os.path.exists(tables_path):
        return None
    
    with open(tables_path, "r", encoding="utf-8") as f:
        tables_data = json.load(f)
    
    if not tables_data:
        return None
    
    # Load charts data if available
    charts_data = []
    if os.path.exists(charts_path):
        with open(charts_path, "r", encoding="utf-8") as f:
            charts_data = json.load(f)
    
    # Determine file type
    is_excel = any('sheet' in table for table in tables_data)
    is_csv = any('delimiter' in table for table in tables_data)
    
    # Prepare tables text for LLM
    if is_excel:
        tables_text = f"EXCEL WORKBOOK ANALYSIS:\n"
        tables_text += f"Total Sheets: {len(tables_data)}\n\n"
    elif is_csv:
        tables_text = f"CSV FILE ANALYSIS:\n\n"
    else:
        tables_text = "TABLES TO ANALYZE:\n\n"
    
    for idx, table in enumerate(tables_data, 1):
        headers = table.get("headers", [])
        data = table.get("data", [])
        
        # Skip if no data and no headers
        if not data and not headers:
            continue
        
        if is_excel:
            tables_text += f"Sheet {idx}: {table.get('sheet', 'Unknown')}\n"
            tables_text += f"Size: {table.get('rows', 0)} rows × {table.get('columns', 0)} columns\n"
        else:
            tables_text += f"Table {idx}:\n"
            if "page" in table:
                tables_text += f"Location: Page {table['page']}\n"
            elif "slide" in table:
                tables_text += f"Location: Slide {table['slide']}\n"
        
        # Show headers first
        if headers:
            tables_text += "Headers: | " + " | ".join(str(h)[:50] for h in headers) + " |\n"
        
        # Show data rows
        row_limit = 5 if is_excel and len(data) > 10 else min(len(data), 15)
        
        for row in data[:row_limit]:
            tables_text += "| " + " | ".join(str(cell)[:50] for cell in row) + " |\n"
        
        if len(data) > row_limit:
            tables_text += f"... ({len(data) - row_limit} more rows)\n"
        
        tables_text += "\n"
    
    # Add charts information
    charts_text = ""
    if charts_data:
        charts_text = f"\n\nCHARTS FOUND: {len(charts_data)} chart(s)\n"
        for chart in charts_data:
            charts_text += f"\nChart on Sheet '{chart.get('sheet', 'Unknown')}':\n"
            charts_text += f"  Type: {chart.get('chart_type_display', chart.get('chart_type', 'Unknown'))}\n"
            if chart.get('title'):
                charts_text += f"  Title: {chart['title']}\n"
            if chart.get('data_series'):
                charts_text += f"  Data Series: {len(chart['data_series'])}\n"
    
    # Create prompt based on file type
    if is_excel:
        chart_section = ""
        if charts_data:
            chart_section = '"chart_analysis": [{"chart_title": "title", "chart_type": "type", "purpose": "what it shows", "key_insights": ["insight 1", "insight 2"]}],'
        
        prompt = f"""
Analyze this Excel workbook and provide detailed insights:

1. What is the main purpose of this workbook?
2. What type of data does each sheet contain?
3. Identify key metrics, totals, or important values
4. Detect any patterns, trends, or relationships in the data
4. Detect any patterns, trends, or relationships in the data
{"5. For each chart found, explain what it visualizes and what insights it provides" if charts_data else ""}

{tables_text}
{charts_text}

Return your analysis as JSON:
{{
  "sheet_purposes": {{
    "SheetName": "Purpose/Description of this sheet"
  }},
  "insights": [
    "Metric: Value (e.g., Total Revenue: $500k)",
    "Pattern: Description (e.g., Sales peak on Fridays)",
    "Insight: Business implication (e.g., Growth is slowing)"
  ]{', ' + chart_section.rstrip(',') if charts_data else ''}
}}
"""
    elif is_csv:
        prompt = f"""
Analyze this CSV file and provide detailed insights:

1. What type of data does this CSV contain?
2. What are the column names and what do they represent?
3. Identify key metrics, totals, or ranges in the data
4. Detect any patterns, trends, or distributions
5. What could this data be used for?

{tables_text}

Return your analysis as JSON:
{{
  "data_type": "description of what data this is",
  "column_descriptions": {{"column1": "what it contains", "column2": "what it contains"}},
  "key_statistics": ["stat 1", "stat 2", ...],
  "patterns": ["pattern 1", "pattern 2", ...],
  "use_cases": ["use case 1", "use case 2", ...]
}}
"""
    else:
        prompt = f"""
Analyze these tables and provide:
1. What information do these tables contain?
2. What are the key insights or patterns?
3. What is the purpose of each table?

{tables_text}

Return your analysis as JSON:
{{
  "tables_summary": "overall summary here",
  "key_insights": ["insight 1", "insight 2", "insight 3"],
  "table_purposes": ["purpose of table 1", "purpose of table 2"]
}}
"""
    
    try:
        print("🧠 Running advanced table analysis...")
        from core.config import get_settings
        settings = get_settings()
        llm = ChatOllama(
            model=settings.llm.model,
            temperature=0.3,  # Slightly higher for creative analysis
            base_url=settings.llm.base_url
        )
            
        # Use Async invoke
        response = await llm.ainvoke(prompt)
        response_text = response.content if hasattr(response, "content") else response

        
        analysis = json.loads(extract_json(response_text))
        
        # Save analysis
        analysis_path = os.path.join(base_dir, "tables", "analysis.json")
        with open(analysis_path, "w", encoding="utf-8") as f:
            json.dump(analysis, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Table analysis saved to: {analysis_path}")
        return analysis
        
    except Exception as e:
        print(f"⚠️ Table analysis failed: {e}")
        print(f"Response preview: {response_text[:200] if 'response_text' in locals() else 'N/A'}")
        return None
