"""
document_service.py
~~~~~~~~~~~~~~~~~~~
Rendering pipeline for resumes and cover letters.

Supported output formats: PDF (via WeasyPrint) and DOCX (via python-docx).
Both renderers target the exact single-column LaTeX-style layout specified
by the client (Times New Roman 11pt, 0.6 in margins, bold-centered name,
pipe-separated contact line, ALL-CAPS bold section headings with rule).

Public surface
--------------
render_cv_to_html()             → HTML string from StructuredCvData
render_cover_letter_to_html()   → HTML string from StructuredCvData + StructuredCoverLetter
render_pdf_bytes()              → PDF bytes from an HTML string
render_docx_bytes()             → DOCX bytes for a resume
render_cover_letter_docx_bytes()→ DOCX bytes for a cover letter
upload_to_cloudinary()          → upload helper
render_cv_documents_service()   → orchestration endpoint (admin-triggered)
"""

from __future__ import annotations

import io
import logging
import time
from pathlib import Path
from typing import List, Optional

import cloudinary
import cloudinary.uploader
import cloudinary.utils
from fastapi import status
from jinja2 import Environment, FileSystemLoader, select_autoescape
from sqlalchemy.orm import Session

from app.models.admins import Admin
from app.models.ai_generations import AiGeneration
from app.models.documents import Document
from app.models.enums import AdminRole, DocumentType
from app.models.submissions import Submission
from app.schema.ai import StructuredCoverLetter, StructuredCvData
from app.utils.custom_response import error_response, success_response
from app.utils.settings import settings

logger = logging.getLogger(__name__)

# ── Cloudinary ──────────────────────────────────────────────────────────────
cloudinary.config(
    cloud_name=settings.CLOUDINARY_CLOUD_NAME,
    api_key=settings.CLOUDINARY_API_KEY,
    api_secret=settings.CLOUDINARY_API_SECRET,
)

# ── Jinja2 template engine ──────────────────────────────────────────────────
TEMPLATES_DIR = Path(__file__).parent.parent / "templates"

_jinja_env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=select_autoescape(["html"]),
)


# ═══════════════════════════════════════════════════════════════════════════
# HTML rendering
# ═══════════════════════════════════════════════════════════════════════════

def render_cv_to_html(cv_data: StructuredCvData, template_name: Optional[str] = None) -> str:
    """Render StructuredCvData → HTML using the single-column resume template."""
    chosen = template_name or "cv_default.html"
    try:
        template = _jinja_env.get_template(chosen)
    except Exception:
        logger.warning(f"Template '{chosen}' not found — falling back to cv_default.html")
        template = _jinja_env.get_template("cv_default.html")
    return template.render(cv=cv_data)


def render_cover_letter_to_html(
    cv_data: StructuredCvData,
    letter: StructuredCoverLetter,
) -> str:
    """Render cover letter HTML (header from cv_data, body from letter)."""
    template = _jinja_env.get_template("cover_letter.html")
    return template.render(cv=cv_data, letter=letter)


# ═══════════════════════════════════════════════════════════════════════════
# PDF rendering
# ═══════════════════════════════════════════════════════════════════════════

def render_pdf_bytes(html: str) -> bytes:
    """Convert an HTML string to PDF bytes using WeasyPrint."""
    try:
        from weasyprint import HTML as WeasyprintHTML
        return WeasyprintHTML(string=html).write_pdf()
    except Exception as exc:
        logger.error(f"WeasyPrint PDF rendering failed: {exc}")
        raise RuntimeError(f"PDF rendering failed: {exc}") from exc


# ═══════════════════════════════════════════════════════════════════════════
# DOCX rendering — resume
# ═══════════════════════════════════════════════════════════════════════════

def render_docx_bytes(cv_data: StructuredCvData) -> bytes:
    """
    Build a DOCX resume that matches the LaTeX-style single-column layout:

    - Letter page, 0.6 in margins all sides
    - Name: Times New Roman 16 pt, bold, centered, ALL-CAPS
    - Contact: 11 pt, centered, pipe-separated
    - Section headings: 11 pt, bold, ALL-CAPS, bottom border rule
    - Experience: company+location bold left / dates right; role italic left
    - Bullet points: indented 0.25 in, 11 pt, tight spacing
    - Skills: bold label + colon + comma-separated values
    - Certifications: bullet list
    - Education: pipe-separated inline lines
    """
    try:
        from docx import Document as DocxDocument
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        from docx.oxml import OxmlElement
        from docx.oxml.ns import qn
        from docx.shared import Cm, Inches, Pt, RGBColor
    except ImportError as exc:
        raise RuntimeError(f"python-docx is not installed: {exc}") from exc

    doc = DocxDocument()

    # ── Page geometry: letter, 0.6 in margins ─────────────────────────────
    for section in doc.sections:
        section.page_width  = int(8.5  * 914400)   # 8.5 in in EMU
        section.page_height = int(11.0 * 914400)   # 11  in in EMU
        section.top_margin    = int(0.6 * 914400)
        section.bottom_margin = int(0.6 * 914400)
        section.left_margin   = int(0.6 * 914400)
        section.right_margin  = int(0.6 * 914400)

    # ── Remove default paragraph spacing from Normal style ─────────────────
    normal_style = doc.styles["Normal"]
    normal_style.paragraph_format.space_before = Pt(0)
    normal_style.paragraph_format.space_after  = Pt(0)
    normal_style.font.name = "Times New Roman"
    normal_style.font.size = Pt(11)

    # ── Helper: set font on every run in a paragraph ───────────────────────
    def _apply_font(paragraph, size_pt: float, bold=False, italic=False,
                    color: Optional[tuple] = None, align=None):
        if align is not None:
            paragraph.alignment = align
        for run in paragraph.runs:
            run.font.name  = "Times New Roman"
            run.font.size  = Pt(size_pt)
            run.bold       = bold
            run.italic     = italic
            if color:
                run.font.color.rgb = RGBColor(*color)

    # ── Helper: paragraph with no extra spacing ────────────────────────────
    def _para(text: str = "", style: str = "Normal") -> object:
        p = doc.add_paragraph(text, style=style)
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after  = Pt(0)
        return p

    # ── Helper: add a bottom-border rule to a paragraph (section heading) ──
    def _add_bottom_border(paragraph):
        pPr = paragraph._p.get_or_add_pPr()
        pBdr = OxmlElement("w:pBdr")
        bottom = OxmlElement("w:bottom")
        bottom.set(qn("w:val"),   "single")
        bottom.set(qn("w:sz"),    "6")       # 0.75 pt
        bottom.set(qn("w:space"), "1")
        bottom.set(qn("w:color"), "000000")
        pBdr.append(bottom)
        pPr.append(pBdr)

    # ── Helper: right-aligned tab stop at right margin ─────────────────────
    _RIGHT_TWIPS = "8640"   # 6 in at 0.6 in margins on 8.5 in page = 7.3 in usable
                            # 7.3 in × 1440 twips/in ≈ 10512; use 8640 (6 in) for safety

    def _add_right_tab(paragraph):
        pPr = paragraph._p.get_or_add_pPr()
        tabs_el = OxmlElement("w:tabs")
        tab = OxmlElement("w:tab")
        tab.set(qn("w:val"), "right")
        tab.set(qn("w:pos"), _RIGHT_TWIPS)
        tabs_el.append(tab)
        pPr.append(tabs_el)

    # ── Helper: add a small vertical gap ──────────────────────────────────
    def _gap(pt: float = 4):
        p = _para()
        p.paragraph_format.space_after = Pt(pt)

    # ══════════════════════════════════════════════════════════════════════
    # NAME
    # ══════════════════════════════════════════════════════════════════════
    info = cv_data.personal_info

    p_name = _para()
    p_name.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p_name.add_run(info.full_name.upper())
    r.bold = True
    r.font.name = "Times New Roman"
    r.font.size = Pt(16)
    p_name.paragraph_format.space_after = Pt(2)

    # ══════════════════════════════════════════════════════════════════════
    # CONTACT LINE
    # ══════════════════════════════════════════════════════════════════════
    contact_parts = [p for p in [
        info.location, info.phone, info.email, info.linkedin, info.portfolio
    ] if p]

    if contact_parts:
        p_contact = _para()
        p_contact.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p_contact.add_run(" | ".join(contact_parts))
        r.font.name = "Times New Roman"
        r.font.size = Pt(11)
    p_name.paragraph_format.space_after = Pt(6)

    # ══════════════════════════════════════════════════════════════════════
    # SECTION HEADING helper
    # ══════════════════════════════════════════════════════════════════════
    def _section_heading(title: str):
        _gap(4)
        p = _para()
        r = p.add_run(title.upper())
        r.bold = True
        r.font.name = "Times New Roman"
        r.font.size = Pt(11)
        _add_bottom_border(p)
        p.paragraph_format.space_after = Pt(3)
        return p

    # ══════════════════════════════════════════════════════════════════════
    # PROFESSIONAL SUMMARY
    # ══════════════════════════════════════════════════════════════════════
    if cv_data.professional_summary:
        _section_heading("Professional Summary")
        p = _para(cv_data.professional_summary)
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        for r in p.runs:
            r.font.name = "Times New Roman"
            r.font.size = Pt(11)

    # ══════════════════════════════════════════════════════════════════════
    # PROFESSIONAL EXPERIENCE
    # ══════════════════════════════════════════════════════════════════════
    if cv_data.work_experience:
        _section_heading("Professional Experience")

        for job in cv_data.work_experience:
            # Company + location (bold left)
            p_co = _para()
            r_co = p_co.add_run(
                f"{job.company}, {job.location}" if job.location else job.company
            )
            r_co.bold = True
            r_co.font.name = "Times New Roman"
            r_co.font.size = Pt(11)
            p_co.paragraph_format.space_before = Pt(3)

            # Role (italic left) + dates (right-aligned via tab)
            date_str = ""
            if job.start_date:
                end = "Present" if job.is_current else (job.end_date or "")
                date_str = f"{job.start_date} \u2013 {end}"

            p_role = _para()
            _add_right_tab(p_role)
            r_role = p_role.add_run(job.job_title)
            r_role.italic = True
            r_role.font.name = "Times New Roman"
            r_role.font.size = Pt(11)
            if date_str:
                p_role.add_run("\t")
                r_date = p_role.add_run(date_str)
                r_date.font.name = "Times New Roman"
                r_date.font.size = Pt(11)

            # Bullet points
            for point in job.bullet_points:
                p_b = doc.add_paragraph(style="List Bullet")
                p_b.paragraph_format.space_before  = Pt(0)
                p_b.paragraph_format.space_after   = Pt(2)
                p_b.paragraph_format.left_indent   = Inches(0.25)
                r_b = p_b.add_run(point)
                r_b.font.name = "Times New Roman"
                r_b.font.size = Pt(11)

    # ══════════════════════════════════════════════════════════════════════
    # CORE SKILLS
    # ══════════════════════════════════════════════════════════════════════
    if cv_data.skills:
        _section_heading("Core Skills")
        for group_name, items in cv_data.skills.items():
            p_sk = _para()
            p_sk.paragraph_format.space_after = Pt(2)
            r_label = p_sk.add_run(f"{group_name}: ")
            r_label.bold = True
            r_label.font.name = "Times New Roman"
            r_label.font.size = Pt(11)
            r_val = p_sk.add_run(", ".join(items))
            r_val.font.name = "Times New Roman"
            r_val.font.size = Pt(11)

    # ══════════════════════════════════════════════════════════════════════
    # PROJECTS (optional)
    # ══════════════════════════════════════════════════════════════════════
    if cv_data.projects:
        _section_heading("Projects")
        for proj in cv_data.projects:
            p_pt = _para()
            p_pt.paragraph_format.space_before = Pt(3)
            r_pt = p_pt.add_run(proj.title)
            r_pt.bold = True
            r_pt.font.name = "Times New Roman"
            r_pt.font.size = Pt(11)
            if proj.link:
                r_lk = p_pt.add_run(f"  \u2014  {proj.link}")
                r_lk.font.name = "Times New Roman"
                r_lk.font.size = Pt(11)

            p_desc = _para(proj.description)
            p_desc.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            for r in p_desc.runs:
                r.font.name = "Times New Roman"
                r.font.size = Pt(11)

            if proj.tech_stack:
                p_st = _para()
                r_stl = p_st.add_run("Stack: ")
                r_stl.bold = True
                r_stl.font.name = "Times New Roman"
                r_stl.font.size = Pt(11)
                r_stv = p_st.add_run(", ".join(proj.tech_stack))
                r_stv.font.name = "Times New Roman"
                r_stv.font.size = Pt(11)

    # ══════════════════════════════════════════════════════════════════════
    # TECHNICAL & INDUSTRY TOOLS
    # ══════════════════════════════════════════════════════════════════════
    if cv_data.technical_tools and cv_data.technical_tools.strip():
        _section_heading("Technical & Industry Tools")
        p_tools = _para(cv_data.technical_tools.strip())
        p_tools.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        for r in p_tools.runs:
            r.font.name = "Times New Roman"
            r.font.size = Pt(11)

    # ══════════════════════════════════════════════════════════════════════
    # CERTIFICATIONS
    # ══════════════════════════════════════════════════════════════════════
    if cv_data.certifications:
        _section_heading("Certifications")
        for cert in cv_data.certifications:
            label = cert.name if hasattr(cert, "name") else str(cert)
            if hasattr(cert, "issuer") and cert.issuer:
                label += f" | {cert.issuer}"
            if hasattr(cert, "expiration_date") and cert.expiration_date:
                label += f" (exp. {cert.expiration_date})"
            elif hasattr(cert, "issue_date") and cert.issue_date:
                label += f" ({cert.issue_date})"

            p_c = doc.add_paragraph(style="List Bullet")
            p_c.paragraph_format.space_before = Pt(0)
            p_c.paragraph_format.space_after  = Pt(2)
            p_c.paragraph_format.left_indent  = Inches(0.25)
            r_c = p_c.add_run(label)
            r_c.font.name = "Times New Roman"
            r_c.font.size = Pt(11)

    # ══════════════════════════════════════════════════════════════════════
    # EDUCATION
    # ══════════════════════════════════════════════════════════════════════
    if cv_data.education:
        _section_heading("Education")
        for edu in cv_data.education:
            parts = [edu.degree, edu.institution]
            if edu.location:
                parts.append(edu.location)
            # Build date range: "Jan 2018 – May 2022" or just "May 2022"
            if edu.start_date and edu.graduation_year:
                parts.append(f"{edu.start_date} \u2013 {edu.graduation_year}")
            elif edu.graduation_year:
                parts.append(edu.graduation_year)
            elif edu.start_date:
                parts.append(edu.start_date)
            if edu.honors:
                parts.append(f"GPA: {edu.honors}")
            p_edu = _para(" | ".join(parts))
            p_edu.paragraph_format.space_after = Pt(2)
            for r in p_edu.runs:
                r.font.name = "Times New Roman"
                r.font.size = Pt(11)

    # ── Serialise ──────────────────────────────────────────────────────────
    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf.read()


# ═══════════════════════════════════════════════════════════════════════════
# DOCX rendering — cover letter
# ═══════════════════════════════════════════════════════════════════════════

def render_cover_letter_docx_bytes(
    cv_data: StructuredCvData,
    letter: StructuredCoverLetter,
) -> bytes:
    """
    Build a DOCX cover letter matching the Ayobami Cover reference:

    - Same header as the resume (name bold centered 16 pt, contact line)
    - Date line
    - Salutation
    - Body paragraphs (justified, 1.15 line spacing)
    - Sign-off + signatory name
    """
    try:
        from docx import Document as DocxDocument
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        from docx.shared import Pt
    except ImportError as exc:
        raise RuntimeError(f"python-docx is not installed: {exc}") from exc

    doc = DocxDocument()

    # ── Page geometry: letter, 0.6 in margins ─────────────────────────────
    for section in doc.sections:
        section.page_width    = int(8.5  * 914400)
        section.page_height   = int(11.0 * 914400)
        section.top_margin    = int(0.6  * 914400)
        section.bottom_margin = int(0.6  * 914400)
        section.left_margin   = int(0.6  * 914400)
        section.right_margin  = int(0.6  * 914400)

    normal_style = doc.styles["Normal"]
    normal_style.paragraph_format.space_before = Pt(0)
    normal_style.paragraph_format.space_after  = Pt(0)
    normal_style.font.name = "Times New Roman"
    normal_style.font.size = Pt(11)

    def _para(text: str = "") -> object:
        p = doc.add_paragraph(text)
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after  = Pt(0)
        return p

    def _blank(pt: float = 12):
        p = _para()
        p.paragraph_format.space_after = Pt(pt)

    def _run(paragraph, text: str, size: float = 11, bold=False):
        r = paragraph.add_run(text)
        r.font.name = "Times New Roman"
        r.font.size = Pt(size)
        r.bold = bold
        return r

    # ══════════════════════════════════════════════════════════════════════
    # HEADER (identical to resume)
    # ══════════════════════════════════════════════════════════════════════
    info = cv_data.personal_info

    p_name = _para()
    p_name.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _run(p_name, info.full_name.upper(), size=16, bold=True)
    p_name.paragraph_format.space_after = Pt(2)

    contact_parts = [p for p in [
        info.location, info.phone, info.email, info.linkedin, info.portfolio
    ] if p]
    if contact_parts:
        p_contact = _para()
        p_contact.alignment = WD_ALIGN_PARAGRAPH.CENTER
        _run(p_contact, " | ".join(contact_parts))

    _blank(20)  # spacing below header

    # ══════════════════════════════════════════════════════════════════════
    # DATE
    # ══════════════════════════════════════════════════════════════════════
    if letter.date:
        p_date = _para()
        _run(p_date, letter.date)
        _blank(18)

    # ══════════════════════════════════════════════════════════════════════
    # SALUTATION
    # ══════════════════════════════════════════════════════════════════════
    p_sal = _para()
    _run(p_sal, letter.salutation or "Dear Hiring Manager,")
    _blank(12)

    # ══════════════════════════════════════════════════════════════════════
    # BODY PARAGRAPHS
    # ══════════════════════════════════════════════════════════════════════
    for para_text in letter.body_paragraphs:
        p_body = _para()
        p_body.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        _run(p_body, para_text)
        p_body.paragraph_format.line_spacing = Pt(14)  # ~1.27× at 11 pt
        p_body.paragraph_format.space_after  = Pt(12)

    # ══════════════════════════════════════════════════════════════════════
    # SIGN-OFF
    # ══════════════════════════════════════════════════════════════════════
    _blank(18)
    p_so = _para()
    _run(p_so, letter.sign_off or "Warm regards,")
    p_so.paragraph_format.space_after = Pt(4)

    p_sig = _para()
    _run(p_sig, letter.signatory_name or info.full_name)

    # ── Serialise ──────────────────────────────────────────────────────────
    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf.read()


# ═══════════════════════════════════════════════════════════════════════════
# Cloudinary upload helper
# ═══════════════════════════════════════════════════════════════════════════

def upload_to_cloudinary(
    file_bytes: bytes,
    public_id: str,
    resource_type: str = "raw",
    format: str = "pdf",
) -> dict:
    """Upload file bytes to Cloudinary and return the full response dict."""
    return cloudinary.uploader.upload(
        file_bytes,
        public_id=public_id,
        resource_type=resource_type,
        format=format,
        overwrite=True,
        access_mode="public",
    )


# ═══════════════════════════════════════════════════════════════════════════
# Orchestration service
# ═══════════════════════════════════════════════════════════════════════════

async def render_cv_documents_service(
    submission_id: str,
    payload,               # DocumentRenderRequest
    current_admin: Admin,
    db: Session,
):
    """
    Admin-triggered rendering pipeline.

    Steps:
    1. Validate submission + RBAC.
    2. Fetch AiGeneration record.
    3. Deserialise StructuredCvData (and StructuredCoverLetter if requested).
    4. Render each requested format (pdf / docx).
    5. Upload to Cloudinary.
    6. Persist Document records.
    7. Return list of DocumentResponse-compatible dicts.

    document_kind controls which document is rendered:
      'resume'       → cv resume using cv_default.html / render_docx_bytes
      'cover_letter' → cover letter using cover_letter.html / render_cover_letter_docx_bytes
    """
    # ── 1. Validate submission ─────────────────────────────────────────────
    submission = db.query(Submission).filter(Submission.id == submission_id).first()
    if not submission:
        return error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Submission not found",
        )

    if (
        current_admin.role == AdminRole.SUB_ADMIN.value
        and submission.assigned_to_id != current_admin.id
    ):
        return error_response(
            status_code=status.HTTP_403_FORBIDDEN,
            message="You are not assigned to this submission",
        )

    # ── 2. Fetch generation record ─────────────────────────────────────────
    generation = db.query(AiGeneration).filter(
        AiGeneration.id == payload.ai_generation_id,
        AiGeneration.submission_id == submission_id,
    ).first()
    if not generation:
        return error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="AI generation record not found for this submission",
        )

    # ── 3. Deserialise structured data ─────────────────────────────────────
    document_kind = getattr(payload, "document_kind", "resume")

    if not generation.structured_cv_json:
        return error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message=(
                "No structured CV data found in this generation record. "
                "Please re-generate the CV first."
            ),
        )

    try:
        cv_data = StructuredCvData.model_validate(generation.structured_cv_json)
    except Exception as exc:
        return error_response(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            message=f"Stored CV data is invalid: {exc}",
        )

    cover_letter: Optional[StructuredCoverLetter] = None
    if document_kind == "cover_letter":
        if not generation.cover_letter_json:
            return error_response(
                status_code=status.HTTP_400_BAD_REQUEST,
                message=(
                    "No cover letter data found in this generation record. "
                    "Please re-generate to include a cover letter."
                ),
            )
        try:
            cover_letter = StructuredCoverLetter.model_validate(
                generation.cover_letter_json
            )
        except Exception as exc:
            return error_response(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                message=f"Stored cover letter data is invalid: {exc}",
            )

    # ── File naming — client first name only (e.g. "Roland.pdf") ──────────
    client_first = (
        submission.client.first_name.strip()
        if submission.client and submission.client.first_name
        else f"document_{submission_id[:8]}"
    )
    # Append kind suffix so resume and cover letter coexist without collision
    kind_suffix = "" if document_kind == "resume" else "_cover_letter"

    # ── Pre-render HTML once (shared between pdf render and potential reuse)
    if document_kind == "cover_letter":
        html = render_cover_letter_to_html(cv_data, cover_letter)
    else:
        html = render_cv_to_html(cv_data)

    # ── 4-6. Render → upload → persist each requested format ──────────────
    formats = [f.lower().strip() for f in payload.formats]
    created_docs = []

    for fmt in formats:
        if fmt not in ("pdf", "docx"):
            continue

        # Version: how many docs of this kind+format already exist
        existing_count = (
            db.query(Document)
            .filter(
                Document.submission_id == submission_id,
                Document.file_type == fmt,
                Document.document_kind == document_kind,
            )
            .count()
        )
        version = existing_count + 1

        file_name = f"{client_first}{kind_suffix}.{fmt}"
        cloudinary_public_id = (
            f"ai_cv_generator/documents/{submission_id}"
            f"/{document_kind}_{fmt}_v{version}"
        )

        # ── Render ────────────────────────────────────────────────────────
        try:
            if fmt == "pdf":
                file_bytes = render_pdf_bytes(html)
            else:
                if document_kind == "cover_letter":
                    file_bytes = render_cover_letter_docx_bytes(cv_data, cover_letter)
                else:
                    file_bytes = render_docx_bytes(cv_data)
        except Exception as exc:
            logger.error(f"Rendering {fmt.upper()} ({document_kind}) failed: {exc}")
            return error_response(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=f"Failed to render {fmt.upper()} document: {exc}",
            )

        # ── Upload ────────────────────────────────────────────────────────
        try:
            cloud_resp = upload_to_cloudinary(
                file_bytes=file_bytes,
                public_id=cloudinary_public_id,
                resource_type="raw",
                format=fmt,
            )
            file_url       = cloud_resp["secure_url"]
            cloud_public_id = cloud_resp["public_id"]
        except Exception as exc:
            logger.error(f"Cloudinary upload failed: {exc}")
            return error_response(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=f"File upload failed: {exc}",
            )

        # ── Persist ───────────────────────────────────────────────────────
        doc = Document(
            submission_id=submission_id,
            ai_generation_id=generation.id,
            file_url=file_url,
            file_name=file_name,
            public_id=cloud_public_id,
            file_type=fmt,
            document_kind=document_kind,
            version=version,
        )
        db.add(doc)
        db.flush()

        created_docs.append({
            "id":               doc.id,
            "submission_id":    doc.submission_id,
            "ai_generation_id": doc.ai_generation_id,
            "file_name":        doc.file_name,
            "file_url":         doc.file_url,
            "public_id":        doc.public_id,
            "file_type":        doc.file_type,
            "document_kind":    doc.document_kind,
            "version":          doc.version,
            "created_at":       doc.created_at,
        })

    db.commit()

    return success_response(
        status_code=status.HTTP_201_CREATED,
        message=(
            f"{document_kind.replace('_', ' ').title()} rendered successfully "
            f"in {len(created_docs)} format(s)"
        ),
        data=created_docs,
    )


# ═══════════════════════════════════════════════════════════════════════════
# Document listing / download services
# ═══════════════════════════════════════════════════════════════════════════

async def list_submission_documents_service(
    submission_id: str,
    current_admin: Admin,
    db: Session,
):
    """Returns all document records for a given submission."""
    submission = db.query(Submission).filter(Submission.id == submission_id).first()
    if not submission:
        return error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Submission not found",
        )

    docs = (
        db.query(Document)
        .filter(Document.submission_id == submission_id)
        .order_by(Document.document_kind, Document.file_type, Document.version)
        .all()
    )

    return success_response(
        status_code=status.HTTP_200_OK,
        message="Documents retrieved successfully",
        data=[
            {
                "id":               d.id,
                "submission_id":    d.submission_id,
                "ai_generation_id": d.ai_generation_id,
                "file_name":        d.file_name,
                "file_url":         d.file_url,
                "public_id":        d.public_id,
                "file_type":        d.file_type,
                "document_kind":    d.document_kind,
                "version":          d.version,
                "created_at":       d.created_at,
            }
            for d in docs
        ],
    )


async def download_document_service(
    submission_id: str,
    document_id: str,
    db: Session,
):
    """
    Returns the Document record and an authenticated Cloudinary private-download
    URL (via the Admin API).  The controller streams this back to the client.

    We use ``cloudinary.utils.private_download_url()`` rather than the CDN
    delivery URL (``cloudinary_url(..., sign_url=True)``).  The CDN delivery
    URL returns 401 on Cloudinary's free plan for raw assets; the Admin API
    download URL is always authenticated with the API key/secret and works
    regardless of delivery settings.
    """
    doc = db.query(Document).filter(
        Document.id == document_id,
        Document.submission_id == submission_id,
    ).first()
    if not doc:
        return None, error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Document not found",
        )

    try:
        download_url = cloudinary.utils.private_download_url(
            doc.public_id,
            doc.file_type,          # "pdf" or "docx"
            resource_type="raw",
            type="upload",
        )
    except Exception as exc:
        logger.error(f"Failed to generate Cloudinary download URL: {exc}")
        download_url = doc.file_url   # last-resort fallback

    return doc, download_url


async def client_download_document_service(
    submission_id: str,
    document_id: str,
    client_submission,
    db: Session,
):
    """Client-facing download — confirms the submission belongs to the caller."""
    if client_submission.id != submission_id:
        return None, error_response(
            status_code=status.HTTP_403_FORBIDDEN,
            message="You do not have access to this document",
        )
    return await download_document_service(submission_id, document_id, db)


async def list_client_documents_service(
    submission_id: str,
    access_token: str,
    db: Session,
):
    """Client-facing document listing protected by submission access token."""
    submission = db.query(Submission).filter(
        Submission.id == submission_id,
        Submission.access_token == access_token,
    ).first()
    if not submission:
        return error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Submission not found or access token is invalid",
        )

    docs = (
        db.query(Document)
        .filter(Document.submission_id == submission_id)
        .order_by(Document.document_kind, Document.file_type, Document.version)
        .all()
    )

    return success_response(
        status_code=status.HTTP_200_OK,
        message="Documents retrieved successfully",
        data=[
            {
                "id":               d.id,
                "submission_id":    d.submission_id,
                "ai_generation_id": d.ai_generation_id,
                "file_name":        d.file_name,
                "file_url":         d.file_url,
                "public_id":        d.public_id,
                "file_type":        d.file_type,
                "document_kind":    d.document_kind,
                "version":          d.version,
                "created_at":       str(d.created_at),
            }
            for d in docs
        ],
    )
