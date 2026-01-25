"""Table processing and formatting utilities."""


def preprocess_excel_data(table_data):
    """
    Preprocess Excel table data by removing null values and cleaning the data.
    
    This function:
    1. Removes completely empty rows
    2. Removes completely empty columns
    3. Replaces None/null values with empty string
    4. Strips whitespace from cell values
    5. Removes rows where all values are null/empty (except header)
    
    Args:
        table_data: List of lists representing the table data
        
    Returns:
        Cleaned table data
    """
    if not table_data:
        return []
    
    # Step 1: Clean cell values - replace None with empty string, strip whitespace
    cleaned_data = []
    for row in table_data:
        cleaned_row = []
        for cell in row:
            if cell is None or (isinstance(cell, str) and cell.strip().lower() in ['none', 'null', 'nan', '']):
                cleaned_row.append("")
            elif isinstance(cell, float) and str(cell).lower() == 'nan':
                cleaned_row.append("")
            else:
                cleaned_row.append(str(cell).strip())
        cleaned_data.append(cleaned_row)
    
    # Step 2: Remove completely empty rows (but keep header - first row)
    if len(cleaned_data) > 1:
        header = cleaned_data[0]
        data_rows = [row for row in cleaned_data[1:] if any(cell != "" for cell in row)]
        cleaned_data = [header] + data_rows
    
    # Step 3: Identify and remove completely empty columns
    if cleaned_data:
        num_cols = len(cleaned_data[0]) if cleaned_data else 0
        cols_to_keep = []
        
        for col_idx in range(num_cols):
            # Check if column has any non-empty values
            has_data = any(
                row[col_idx] != "" 
                for row in cleaned_data 
                if col_idx < len(row)
            )
            if has_data:
                cols_to_keep.append(col_idx)
        
        # Keep only non-empty columns
        if cols_to_keep:
            cleaned_data = [
                [row[i] for i in cols_to_keep if i < len(row)]
                for row in cleaned_data
            ]
    
    return cleaned_data


def clean_numeric_values(value):
    """
    Clean numeric values - remove trailing .0 from floats that are whole numbers.
    
    Args:
        value: String value to clean
        
    Returns:
        Cleaned string value
    """
    if not value:
        return value
    
    # Check if it's a float with .0 ending (like "32.0" -> "32")
    try:
        float_val = float(value)
        if float_val.is_integer():
            return str(int(float_val))
    except (ValueError, TypeError):
        pass
    
    return value


def format_table_as_markdown(table):
    """Convert table list to markdown format."""
    if not table or len(table) < 1:
        return ""
    
    lines = []
    
    # Check if table has data
    if len(table) == 0:
        return ""
    
    # Header row
    header = table[0] if table else []
    if header:
        lines.append("| " + " | ".join(str(cell or "").strip() for cell in header) + " |")
        # Separator
        lines.append("| " + " | ".join("---" for _ in header) + " |")
    
    # Data rows
    for row in table[1:]:
        lines.append("| " + " | ".join(str(cell or "").strip() for cell in row) + " |")
    
    return "\n".join(lines)


def detect_numeric_columns(table_data):
    """Detect which columns contain primarily numeric data."""
    if not table_data or len(table_data) < 2:
        return []
    
    numeric_cols = []
    headers = table_data[0]
    
    for col_idx, header in enumerate(headers):
        numeric_count = 0
        total_count = 0
        
        # Check data rows (skip header)
        for row in table_data[1:]:
            if col_idx < len(row):
                cell = row[col_idx]
                if cell and cell.strip():
                    total_count += 1
                    try:
                        float(cell.replace(',', '').replace('$', ''))
                        numeric_count += 1
                    except:
                        pass
        
        # If >70% numeric, consider it a numeric column
        if total_count > 0 and numeric_count / total_count > 0.7:
            numeric_cols.append(header if header else f"Column {col_idx + 1}")
    
    return numeric_cols
