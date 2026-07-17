"""Pack 12/14: Office output tools — DOCX, PPTX, XLSX. Tenant-scoped exports."""

from hg_core.docs.office.docx_tool import docx_create, docx_add_heading, docx_add_paragraph, docx_add_table, docx_finalize
from hg_core.docs.office.pptx_tool import pptx_create, pptx_add_slide, pptx_finalize
from hg_core.docs.office.xlsx_tool import xlsx_create, xlsx_add_sheet, xlsx_add_data, xlsx_finalize

__all__ = [
    "docx_create", "docx_add_heading", "docx_add_paragraph", "docx_add_table", "docx_finalize",
    "pptx_create", "pptx_add_slide", "pptx_finalize",
    "xlsx_create", "xlsx_add_sheet", "xlsx_add_data", "xlsx_finalize",
]
