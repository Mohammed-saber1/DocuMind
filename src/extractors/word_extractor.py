"""Word/DOCX file extractor."""

import os
import zipfile
import docx

from utils.file_utils import (
    create_document_folder,
    save_text,
    save_metadata,
    save_tables,
)
from utils.table_utils import format_table_as_markdown


def extract_word(file_path):
    """Extract text, tables, and images from Word document."""
    doc_id, base, text_dir, img_dir = create_document_folder(file_path)

    document = docx.Document(file_path)
    text = ""
    tables_data = []

    # Extract paragraphs and tables in order
    for element in document.element.body:
        # Check if it's a paragraph
        if element.tag.endswith("p"):
            para = docx.text.paragraph.Paragraph(element, document)
            text += para.text + "\n"

        # Check if it's a table
        elif element.tag.endswith("tbl"):
            table = docx.table.Table(element, document)
            table_data = []
            for row in table.rows:
                table_data.append([cell.text.strip() for cell in row.cells])

            if table_data:
                tables_data.append(
                    {"table_index": len(tables_data) + 1, "data": table_data}
                )

                text += f"\n\n[TABLE {len(tables_data)}]\n"
                text += format_table_as_markdown(table_data)
                text += "\n"

    images = []
    counter = 1

    # Extract images from Word document
    with zipfile.ZipFile(file_path, "r") as z:
        for f in z.namelist():
            if f.startswith("word/media/"):
                data = z.read(f)
                ext = os.path.splitext(f)[1]
                path = os.path.join(img_dir, f"img_{counter}{ext}")
                with open(path, "wb") as out:
                    out.write(data)
                images.append(path)
                counter += 1

    # Save tables separately as JSON
    if tables_data:
        save_tables(base, tables_data)
        print(f"📊 Found {len(tables_data)} table(s) in Word document")

    save_text(text_dir, text)
    save_metadata(
        base,
        {
            "source": "word",
            "images_found": len(images),
            "tables_found": len(tables_data),
        },
    )

    return base, images, doc_id, "word"
