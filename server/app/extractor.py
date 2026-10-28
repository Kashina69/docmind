import fitz
from datetime import datetime, timezone

MIN_CHARS_FOR_TEXT_PAGE = 50


def read_pdf_bytes(path: str) -> bytes:
    print(f"[Storage] Reading {path}")

    with open(path, "rb") as f:
        pdf_bytes = f.read()

    file_size_kb = len(pdf_bytes) / 1024

    print(f"[Storage] Read {file_size_kb:.1f} KB")
    return pdf_bytes


def extract_text_from_pdf(
    pdf_bytes:  bytes,
    s3_key:     str,
    filename:   str,
) -> dict:
    print(f"[Extractor] Opening PDF: {filename}")

    pdf_document = fitz.open(stream=pdf_bytes, filetype="pdf")
    total_pages  = len(pdf_document)

    print(f"[Extractor] PDF has {total_pages} pages")

    extracted_pages = []
    skipped_pages   = []

    for page_index in range(total_pages):
        page        = pdf_document[page_index]
        page_number = page_index + 1

        text = page.get_text("text").strip()

        page_images = page.get_images(full=False)
        has_images  = len(page_images) > 0

        has_tables = "\t" in text or "    " in text

        if len(text) >= MIN_CHARS_FOR_TEXT_PAGE:

            extracted_pages.append({
                "page_number": page_number,
                "text":        text,
                "char_count":  len(text),

                "metadata": {
                    "filename":    filename,
                    "s3_key":      s3_key,
                    "page_number": page_number,
                    "total_pages": total_pages,
                    "has_images":  has_images,
                    "has_tables":  has_tables,
                }
            })

            print(f"[Extractor] Page {page_number:3d}: "
                  f"{len(text):5d} chars "
                  f"{'[images]' if has_images else ''}"
                  f"{'[tables]' if has_tables else ''}")

        else:
            reason = "image_only" if has_images else "no_text_layer"

            skipped_pages.append({
                "page_number": page_number,
                "reason":      reason,
                "char_count":  len(text),
            })

            print(f"[Extractor] Page {page_number:3d}: SKIPPED "
                  f"({reason}, {len(text)} chars)")

    pdf_document.close()

    if not extracted_pages:
        raise ValueError(
            f"No extractable text found in '{filename}'. "
            f"This PDF appears to be fully scanned or image-based. "
            f"Please upload a PDF with a text layer."
        )

    document_metadata = {
        "filename":          filename,
        "s3_key":            s3_key,
        "total_pages":       total_pages,
        "extracted_pages":   len(extracted_pages),
        "skipped_pages":     [p["page_number"] for p in skipped_pages],
        "skipped_count":     len(skipped_pages),
        "extraction_method": "pymupdf",
        "extracted_at":      datetime.now(timezone.utc).isoformat(),
        "file_size_bytes":   len(pdf_bytes),
    }

    print(f"[Extractor] Complete: "
          f"{len(extracted_pages)} pages extracted, "
          f"{len(skipped_pages)} skipped")

    if skipped_pages:
        skipped_nums = [p["page_number"] for p in skipped_pages]
        print(f"[Extractor] Skipped pages: {skipped_nums}")
        print(f"[Extractor] Note: skipped pages contain images/diagrams "
              f"and will not be searchable")

    return {
        "document_metadata": document_metadata,
        "pages":             extracted_pages,
        "skipped_pages":     skipped_pages,
    }
