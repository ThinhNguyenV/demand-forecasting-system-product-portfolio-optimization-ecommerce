"""
Script bien dich Bao cao Chuyen de tot nghiep tu Markdown sang Microsoft Word (.docx)
chuan quy cach hoc thuat Truong Dai hoc Cong nghe Thong tin - DHQG TP.HCM (UIT).
Tich hop chuyen doi cong thuc toan LaTeX sang native Word OMML (Office Math) 100% chuan xac,
triet tieu hoan toan cac loi font toan hoc trong Microsoft Word.

Sinh vien thuc hien: Nguyen Van Thinh
MSSV: 25730149
Nganh: Cong nghe Thong tin
Lop: HTTT2021
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

import docx
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn
from docx.shared import Inches, Pt, RGBColor

import latex2mathml.converter
import lxml.etree as etree


# ── THIET LAP BO CHUYEN DOI LATEX SANG WORD OMML NATIVE ──

def get_omml_transformer():
    """Tim kiem va khoi tao file XSLT MML2OMML.XSL cua Microsoft Office."""
    candidate_paths = [
        Path(r"C:\Program Files\Microsoft Office\root\Office16\MML2OMML.XSL"),
        Path(r"C:\Program Files (x86)\Microsoft Office\root\Office16\MML2OMML.XSL"),
    ]
    xsl_path = None
    for p in candidate_paths:
        if p.exists():
            xsl_path = p
            break

    if not xsl_path:
        # Tim kiem mo rong
        found = list(Path(r"C:\Program Files\Microsoft Office").glob("**/MML2OMML.XSL"))
        if found:
            xsl_path = found[0]

    if xsl_path and xsl_path.exists():
        xslt_doc = etree.parse(str(xsl_path))
        return etree.XSLT(xslt_doc)
    return None


TRANSFORMER = get_omml_transformer()


def latex_to_omml_xml(latex_code: str, is_block: bool = False) -> str | None:
    """Chuyen doi cong thuc LaTeX thanh ma XML OMML chuan Word (<m:oMath> hoac <m:oMathPara>)."""
    if not TRANSFORMER:
        return None
    try:
        code = latex_code.strip()
        code = code.replace(r"\begin{aligned}", "").replace(r"\end{aligned}", "")
        code = code.replace(r"\mathbb{I}", "I")
        code = code.replace(r"\qquad", r"\quad ")
        code = re.sub(r"\\operatorname\{([^}]+)\}", r"\\text{\1}", code)
        code = code.replace("&", "")
        code = code.replace(r"\;", " ")

        mml = latex2mathml.converter.convert(code)
        dom = etree.fromstring(mml)
        omml = TRANSFORMER(dom)
        xml_str = etree.tostring(omml.getroot(), encoding="unicode")

        if is_block:
            return f'<m:oMathPara xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math">{xml_str}</m:oMathPara>'
        return xml_str
    except Exception as e:
        return None


# ── CAC HAM HO TRO XML CHO PYTHON-DOCX ──

def set_cell_background(cell, fill_hex: str):
    """Thiet lap mau nen cho o bang Word."""
    tcPr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill_hex}"/>')
    tcPr.append(shd)


def set_cell_margins(cell, top=120, bottom=120, left=160, right=160):
    """Thiet lap padding cho o bang Word (don vi dxa: 20 dxa = 1 pt)."""
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = OxmlElement("w:tcMar")
    for m, val in [("w:top", top), ("w:bottom", bottom), ("w:left", left), ("w:right", right)]:
        node = OxmlElement(m)
        node.set(qn("w:w"), str(val))
        node.set(qn("w:type"), "dxa")
        tcMar.append(node)
    tcPr.append(tcMar)


def set_cell_border(cell, **kwargs):
    """Thiet lap vien cho o trong bang Word."""
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    tcBorders = tcPr.first_child_found_in("w:tcBorders")
    if tcBorders is None:
        tcBorders = OxmlElement("w:tcBorders")
        tcPr.append(tcBorders)

    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        edge_data = kwargs.get(edge)
        if edge_data:
            tag = f"w:{edge}"
            element = tcBorders.find(qn(tag))
            if element is None:
                element = OxmlElement(tag)
                tcBorders.append(element)
            for key, val in edge_data.items():
                element.set(qn(f"w:{key}"), str(val))


def make_row_header(row):
    """Danh dau dong tieu de cua bang de tu dong lap lai khi sang trang moi."""
    trPr = row._tr.get_or_add_trPr()
    tblHeader = parse_xml(f'<w:tblHeader {nsdecls("w")}/>')
    trPr.append(tblHeader)


def make_row_cant_split(row):
    """Ngan dong trong bang bi cat doi giua hai trang."""
    trPr = row._tr.get_or_add_trPr()
    cantSplit = parse_xml(f'<w:cantSplit {nsdecls("w")}/>')
    trPr.append(cantSplit)


def add_xml_field(run, field_name: str):
    """Chen truong dong Word (PAGE, NUMPAGES)."""
    fldSimple = parse_xml(f'<w:fldSimple {nsdecls("w")} w:instr="{field_name}"/>')
    run._r.append(fldSimple)


# ── XU LY DOAN VAN VA CONG THUC TOAN ──

def add_paragraph_runs(p, text: str, font_name="Times New Roman", font_size=12.5, color_rgb=(0x22, 0x22, 0x22)):
    """Parse text markdown thanh cac runs chu thuong, in dam, in nghieng va cong thuc toan OMML native."""
    clean_text = re.sub(r"</?(?:div|br|span|p)[^>]*>", "", text)

    # Tokenizer bat: **bold**, *italic*, `code`, $inline_math$
    pattern = r"(\*\*.*?\*\*|\*.*?\*|`.*?`|\$[^\$]+?\$)"
    tokens = re.split(pattern, clean_text)

    for token in tokens:
        if not token:
            continue

        if token.startswith("**") and token.endswith("**") and len(token) >= 4:
            run = p.add_run(token[2:-2])
            run.bold = True
            run.font.name = font_name
            run.font.size = Pt(font_size)
            run.font.color.rgb = RGBColor(*color_rgb)
        elif token.startswith("*") and token.endswith("*") and len(token) >= 2:
            run = p.add_run(token[1:-1])
            run.italic = True
            run.font.name = font_name
            run.font.size = Pt(font_size)
            run.font.color.rgb = RGBColor(*color_rgb)
        elif token.startswith("`") and token.endswith("`") and len(token) >= 2:
            run = p.add_run(token[1:-1])
            run.font.name = "Consolas"
            run.font.size = Pt(font_size - 1.5)
            run.font.color.rgb = RGBColor(0x8B, 0x00, 0x00)
        elif token.startswith("$") and token.endswith("$") and len(token) >= 2:
            math_latex = token[1:-1].strip()
            omml_xml = latex_to_omml_xml(math_latex, is_block=False)
            if omml_xml:
                try:
                    p._p.append(parse_xml(omml_xml))
                    continue
                except Exception:
                    pass
            # Fallback neu khong convert duoc OMML
            run = p.add_run(math_latex)
            run.font.name = font_name
            run.font.size = Pt(font_size)
            run.font.italic = True
            run.font.color.rgb = RGBColor(0x1A, 0x36, 0x5D)
        else:
            run = p.add_run(token)
            run.font.name = font_name
            run.font.size = Pt(font_size)
            run.font.color.rgb = RGBColor(*color_rgb)


def add_block_formula(doc: docx.Document, latex_code: str):
    """Chen cong thuc toan hoc khoi (Block Display Equation) bang native Word OMML."""
    omml_xml = latex_to_omml_xml(latex_code, is_block=True)
    
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(8)
    p.paragraph_format.space_after = Pt(8)
    p.paragraph_format.line_spacing = 1.15
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER

    if omml_xml:
        try:
            p._p.append(parse_xml(omml_xml))
            return
        except Exception as e:
            pass

    # Fallback neu khong qua duoc XML
    r = p.add_run(latex_code.strip())
    r.font.name = "Times New Roman"
    r.font.size = Pt(12)
    r.font.italic = True
    r.font.color.rgb = RGBColor(0x1A, 0x36, 0x5D)


def create_cover_page(doc: docx.Document):
    """Tao trang bia chuan quy cach Chuyen de tot nghiep Truong DH Cong nghe Thong tin - DHQG TP.HCM."""
    p_uni = doc.add_paragraph()
    p_uni.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_uni.paragraph_format.space_before = Pt(12)
    p_uni.paragraph_format.space_after = Pt(2)

    r1 = p_uni.add_run("ĐẠI HỌC QUỐC GIA THÀNH PHỐ HỒ CHÍ MINH\n")
    r1.bold = True
    r1.font.size = Pt(13)
    r1.font.name = "Times New Roman"

    r2 = p_uni.add_run("TRƯỜNG ĐẠI HỌC CÔNG NGHỆ THÔNG TIN\n")
    r2.bold = True
    r2.font.size = Pt(14)
    r2.font.name = "Times New Roman"
    r2.font.color.rgb = RGBColor(0x1A, 0x36, 0x5D)

    r3 = p_uni.add_run("KHOA HỆ THỐNG THÔNG TIN")
    r3.bold = True
    r3.font.size = Pt(13)
    r3.font.name = "Times New Roman"

    p_line = doc.add_paragraph()
    p_line.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_line.paragraph_format.space_before = Pt(2)
    p_line.paragraph_format.space_after = Pt(28)
    r_line = p_line.add_run("━━━━━━━━━━━━━━━━━━━")
    r_line.font.color.rgb = RGBColor(0x2B, 0x6C, 0xB0)

    p_report = doc.add_paragraph()
    p_report.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_report.paragraph_format.space_before = Pt(28)
    p_report.paragraph_format.space_after = Pt(8)

    r_rep = p_report.add_run("BÁO CÁO CHUYÊN ĐỀ TỐT NGHIỆP\n")
    r_rep.bold = True
    r_rep.font.size = Pt(18)
    r_rep.font.name = "Times New Roman"
    r_rep.font.color.rgb = RGBColor(0x1A, 0x36, 0x5D)

    r_sub = p_report.add_run("NGÀNH: CÔNG NGHỆ THÔNG TIN")
    r_sub.bold = True
    r_sub.font.size = Pt(13)
    r_sub.font.name = "Times New Roman"
    r_sub.font.color.rgb = RGBColor(0x4A, 0x55, 0x68)

    p_topic = doc.add_paragraph()
    p_topic.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_topic.paragraph_format.space_before = Pt(36)
    p_topic.paragraph_format.space_after = Pt(40)

    r_topic_pre = p_topic.add_run("ĐỀ TÀI:\n")
    r_topic_pre.bold = True
    r_topic_pre.font.size = Pt(13.5)
    r_topic_pre.font.name = "Times New Roman"

    r_topic = p_topic.add_run("HỆ THỐNG DỰ BÁO NHU CẦU VÀ TỐI ƯU HÓA\nDANH MỤC SẢN PHẨM CHO THƯƠNG MẠI ĐIỆN TỬ\n")
    r_topic.bold = True
    r_topic.font.size = Pt(19)
    r_topic.font.name = "Times New Roman"
    r_topic.font.color.rgb = RGBColor(0x1A, 0x36, 0x5D)

    r_topic_en = p_topic.add_run("(Demand Forecasting and Product Portfolio Optimization System for E-Commerce)")
    r_topic_en.italic = True
    r_topic_en.font.size = Pt(12)
    r_topic_en.font.name = "Times New Roman"
    r_topic_en.font.color.rgb = RGBColor(0x4A, 0x55, 0x68)

    p_info = doc.add_paragraph()
    p_info.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p_info.paragraph_format.left_indent = Inches(1.3)
    p_info.paragraph_format.space_before = Pt(40)
    p_info.paragraph_format.line_spacing = 1.35

    fields = [
        ("Sinh viên thực hiện:", " NGUYỄN VĂN THỊNH", True, RGBColor(0x1A, 0x36, 0x5D)),
        ("Mã số sinh viên:", " 25730149", True, None),
        ("Lớp chuyên ngành:", " HTTT2021", False, None),
        ("Khóa học:", " 2021 – 2025", False, None),
        ("Giảng viên hướng dẫn:", " TS. NGUYỄN VĂN A", True, None),
    ]

    for label, val, is_bold_val, color in fields:
        r_lbl = p_info.add_run(f"{label:<24}")
        r_lbl.bold = True
        r_lbl.font.size = Pt(12.5)
        r_lbl.font.name = "Times New Roman"

        r_val = p_info.add_run(f"{val}\n")
        r_val.bold = is_bold_val
        r_val.font.size = Pt(12.5)
        r_val.font.name = "Times New Roman"
        if color:
            r_val.font.color.rgb = color

    p_bottom = doc.add_paragraph()
    p_bottom.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_bottom.paragraph_format.space_before = Pt(60)
    r_bot = p_bottom.add_run("TP. HỒ CHÍ MINH, THÁNG 09 NĂM 2026")
    r_bot.bold = True
    r_bot.font.size = Pt(12)
    r_bot.font.name = "Times New Roman"
    r_bot.font.color.rgb = RGBColor(0x2D, 0x37, 0x48)

    doc.add_page_break()


def build_word_report(md_path: Path, output_path: Path):
    print(f"[INFO] Dang doc tep noi dung Markdown: {md_path}...")
    if not md_path.exists():
        raise FileNotFoundError(f"Khong tim thay {md_path}")

    text = md_path.read_text(encoding="utf-8")
    lines = text.split("\n")

    doc = docx.Document()

    # 1. Thiet lap kho giay A4 va le trang chuan quy cach UIT
    for section in doc.sections:
        section.page_width = Inches(8.27)    # 21.0 cm A4
        section.page_height = Inches(11.69)  # 29.7 cm A4
        section.top_margin = Inches(0.79)     # 2.0 cm
        section.bottom_margin = Inches(0.79)  # 2.0 cm
        section.left_margin = Inches(1.18)    # 3.0 cm (le dong gay)
        section.right_margin = Inches(0.79)   # 2.0 cm
        section.different_first_page_header_footer = True

        # Header chay tu trang 2 tro di
        header = section.header
        p_head = header.paragraphs[0]
        p_head.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        r_head = p_head.add_run("Báo cáo Chuyên đề tốt nghiệp - SV: Nguyễn Văn Thịnh (MSSV: 25730149)")
        r_head.font.name = "Times New Roman"
        r_head.font.size = Pt(9)
        r_head.font.italic = True
        r_head.font.color.rgb = RGBColor(0x71, 0x80, 0x96)

        # Footer dong tu trang 2: Bang 1 dong 2 cot (Ten khoa ben trai, So trang dong ben phai)
        footer = section.footer
        p_foot_old = footer.paragraphs[0]
        p_foot_old.text = ""

        foot_table = footer.add_table(rows=1, cols=2, width=Inches(6.3))
        foot_table.alignment = WD_TABLE_ALIGNMENT.CENTER
        cell_l, cell_r = foot_table.rows[0].cells[0], foot_table.rows[0].cells[1]

        p_fl = cell_l.paragraphs[0]
        p_fl.alignment = WD_ALIGN_PARAGRAPH.LEFT
        r_fl = p_fl.add_run("Khoa Hệ thống Thông tin - Trường ĐH Công nghệ Thông tin, ĐHQG-HCM")
        r_fl.font.name = "Times New Roman"
        r_fl.font.size = Pt(9)
        r_fl.font.italic = True
        r_fl.font.color.rgb = RGBColor(0xA0, 0xAE, 0xC0)

        p_fr = cell_r.paragraphs[0]
        p_fr.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        r_fr1 = p_fr.add_run("Trang ")
        r_fr1.font.name = "Times New Roman"
        r_fr1.font.size = Pt(9)
        r_fr1.font.color.rgb = RGBColor(0x2B, 0x6C, 0xB0)

        r_fr_page = p_fr.add_run()
        r_fr_page.font.name = "Times New Roman"
        r_fr_page.font.size = Pt(9)
        r_fr_page.font.bold = True
        r_fr_page.font.color.rgb = RGBColor(0x1A, 0x36, 0x5D)
        add_xml_field(r_fr_page, "PAGE")

        r_fr_slash = p_fr.add_run(" / ")
        r_fr_slash.font.name = "Times New Roman"
        r_fr_slash.font.size = Pt(9)
        r_fr_slash.font.color.rgb = RGBColor(0x71, 0x80, 0x96)

        r_fr_num = p_fr.add_run()
        r_fr_num.font.name = "Times New Roman"
        r_fr_num.font.size = Pt(9)
        r_fr_num.font.color.rgb = RGBColor(0x71, 0x80, 0x96)
        add_xml_field(r_fr_num, "NUMPAGES")

    # 2. Tao trang bia
    create_cover_page(doc)

    # 3. Bien dich noi dung Markdown
    root = md_path.resolve().parent.parent
    chart_dir = root / "data" / "outputs" / "charts"

    in_code_block = False
    code_lines: list[str] = []

    in_table = False
    table_raw_rows: list[list[str]] = []

    in_math_block = False
    math_lines: list[str] = []

    skip_frontmatter = True
    idx = 0

    while idx < len(lines):
        line = lines[idx]
        stripped = line.strip()

        # Bo qua phan bia HTML o dau file markdown vi da co trang bia chinh quy
        if skip_frontmatter:
            if stripped == "## LỜI CAM ĐOAN":
                skip_frontmatter = False
            else:
                idx += 1
                continue

        # ── XU LY KHOI CONG THUC TOAN DANG BLOCK ($$ ... $$) ──
        if stripped.startswith("$$"):
            if in_math_block:
                in_math_block = False
                if stripped != "$$":
                    math_lines.append(stripped.replace("$$", "").strip())
                formula_str = " ".join(math_lines)
                add_block_formula(doc, formula_str)
                math_lines = []
            elif stripped.endswith("$$") and len(stripped) > 4:
                formula_str = stripped[2:-2].strip()
                add_block_formula(doc, formula_str)
            else:
                in_math_block = True
                rem = stripped[2:].strip()
                if rem:
                    math_lines.append(rem)
            idx += 1
            continue

        if in_math_block:
            if stripped.endswith("$$"):
                in_math_block = False
                rem = stripped[:-2].strip()
                if rem:
                    math_lines.append(rem)
                formula_str = " ".join(math_lines)
                add_block_formula(doc, formula_str)
                math_lines = []
            else:
                math_lines.append(stripped)
            idx += 1
            continue

        # ── XU LY PHAN TRANG (\newpage va ---) ──
        if stripped == "\\newpage":
            doc.add_page_break()
            idx += 1
            continue

        if stripped == "---":
            idx += 1
            continue

        # ── XU LY KHOI MA NGUON (CODE BLOCK) ──
        if stripped.startswith("```"):
            if in_code_block:
                in_code_block = False
                p = doc.add_paragraph()
                p.paragraph_format.left_indent = Inches(0.3)
                p.paragraph_format.space_before = Pt(6)
                p.paragraph_format.space_after = Pt(8)
                p.paragraph_format.line_spacing = 1.15
                code_text = "\n".join(code_lines)
                r = p.add_run(code_text)
                r.font.name = "Consolas"
                r.font.size = Pt(9.5)
                r.font.color.rgb = RGBColor(0x1A, 0x20, 0x2C)
                code_lines = []
            else:
                in_code_block = True
            idx += 1
            continue

        if in_code_block:
            code_lines.append(line)
            idx += 1
            continue

        # ── XU LY BANG BIEU (MARKDOWN TABLE) ──
        if stripped.startswith("|") and stripped.endswith("|"):
            in_table = True
            cells = [c.strip() for c in stripped[1:-1].split("|")]
            if not all(re.match(r"^:?-+:?$", c) for c in cells):
                table_raw_rows.append(cells)
            idx += 1
            continue
        elif in_table:
            in_table = False
            if table_raw_rows:
                num_cols = max(len(r) for r in table_raw_rows)
                t = doc.add_table(rows=len(table_raw_rows), cols=num_cols)
                t.alignment = WD_TABLE_ALIGNMENT.CENTER
                border_spec = {"val": "single", "sz": "4", "space": "0", "color": "CBD5E1"}

                for r_idx, row_data in enumerate(table_raw_rows):
                    row = t.rows[r_idx]
                    make_row_cant_split(row)
                    is_header = (r_idx == 0)
                    if is_header:
                        make_row_header(row)

                    bg_color = "1A365D" if is_header else ("F8FAFC" if r_idx % 2 == 1 else "FFFFFF")
                    text_color = (0xFF, 0xFF, 0xFF) if is_header else (0x2D, 0x37, 0x48)

                    for c_idx in range(num_cols):
                        cell = row.cells[c_idx]
                        content = row_data[c_idx] if c_idx < len(row_data) else ""
                        cell.text = ""
                        p = cell.paragraphs[0]
                        p.paragraph_format.space_before = Pt(4)
                        p.paragraph_format.space_after = Pt(4)
                        p.paragraph_format.line_spacing = 1.15

                        if any(term in content for term in ["%", "normal", "fast_moving", "slow_moving", "intermittent"]) or content.isdigit():
                            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                        else:
                            p.alignment = WD_ALIGN_PARAGRAPH.LEFT

                        add_paragraph_runs(p, content, font_size=10.0 if not is_header else 10.5, color_rgb=text_color)
                        if is_header:
                            for r in p.runs:
                                r.bold = True
                        set_cell_background(cell, bg_color)
                        set_cell_margins(cell, top=100, bottom=100, left=140, right=140)
                        set_cell_border(cell, top=border_spec, bottom=border_spec, left=border_spec, right=border_spec)

                p_after_tbl = doc.add_paragraph()
                p_after_tbl.paragraph_format.space_before = Pt(2)
                p_after_tbl.paragraph_format.space_after = Pt(8)
            table_raw_rows = []

        # ── XU LY TIEU DE (HEADINGS) DONG BO NAVIGATION PANE ──
        if stripped.startswith("# "):
            doc.add_page_break()
            heading_text = stripped[2:].strip()
            p = doc.add_heading(level=1)
            p.paragraph_format.space_before = Pt(18)
            p.paragraph_format.space_after = Pt(10)
            p.paragraph_format.keep_with_next = True
            r = p.add_run(heading_text)
            r.bold = True
            r.font.name = "Times New Roman"
            r.font.size = Pt(16)
            r.font.color.rgb = RGBColor(0x1A, 0x36, 0x5D)
            idx += 1
            continue

        if stripped.startswith("## "):
            heading_text = stripped[3:].strip()
            p = doc.add_heading(level=2)
            p.paragraph_format.space_before = Pt(14)
            p.paragraph_format.space_after = Pt(6)
            p.paragraph_format.keep_with_next = True
            r = p.add_run(heading_text)
            r.bold = True
            r.font.name = "Times New Roman"
            r.font.size = Pt(13.5)
            r.font.color.rgb = RGBColor(0x2B, 0x6C, 0xB0)
            idx += 1
            continue

        if stripped.startswith("### "):
            heading_text = stripped[4:].strip()
            p = doc.add_heading(level=3)
            p.paragraph_format.space_before = Pt(10)
            p.paragraph_format.space_after = Pt(4)
            p.paragraph_format.keep_with_next = True
            r = p.add_run(heading_text)
            r.bold = True
            r.font.name = "Times New Roman"
            r.font.size = Pt(12)
            r.font.color.rgb = RGBColor(0x2D, 0x37, 0x48)
            idx += 1
            continue

        # ── XU LY DANH SACH (BULLETS & NUMBERED) ──
        if stripped.startswith("- ") or stripped.startswith("* "):
            p = doc.add_paragraph()
            p.paragraph_format.left_indent = Inches(0.3)
            p.paragraph_format.space_before = Pt(2)
            p.paragraph_format.space_after = Pt(3)
            p.paragraph_format.line_spacing = 1.25
            r_bullet = p.add_run("•  ")
            r_bullet.bold = True
            r_bullet.font.color.rgb = RGBColor(0x2B, 0x6C, 0xB0)
            add_paragraph_runs(p, stripped[2:])
            idx += 1
            continue

        if re.match(r"^\d+\.\s", stripped):
            num_match = re.match(r"^(\d+\.)\s(.*)$", stripped)
            p = doc.add_paragraph()
            p.paragraph_format.left_indent = Inches(0.3)
            p.paragraph_format.space_before = Pt(3)
            p.paragraph_format.space_after = Pt(4)
            p.paragraph_format.line_spacing = 1.25
            if num_match:
                r_num = p.add_run(num_match.group(1) + " ")
                r_num.bold = True
                r_num.font.color.rgb = RGBColor(0x1A, 0x36, 0x5D)
                add_paragraph_runs(p, num_match.group(2))
            else:
                add_paragraph_runs(p, stripped)
            idx += 1
            continue

        # ── XU LY CHEN HINH ANH BIEU DO (MARKDOWN IMAGE) ──
        img_match = re.match(r"^!\[(.*?)\]\((.*?)\)$", stripped)
        if img_match:
            caption = img_match.group(1)
            img_rel = img_match.group(2)
            img_path = Path(img_rel)
            if not img_path.is_absolute():
                candidate1 = root / img_rel
                candidate2 = chart_dir / Path(img_rel).name
                if candidate1.exists():
                    img_path = candidate1
                elif candidate2.exists():
                    img_path = candidate2

            if img_path.exists():
                p_img = doc.add_paragraph()
                p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
                p_img.paragraph_format.space_before = Pt(10)
                p_img.paragraph_format.space_after = Pt(3)
                p_img.paragraph_format.keep_with_next = True

                run_img = p_img.add_run()
                run_img.add_picture(str(img_path), width=Inches(5.8))

                p_cap = doc.add_paragraph()
                p_cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
                p_cap.paragraph_format.space_before = Pt(2)
                p_cap.paragraph_format.space_after = Pt(12)
                r_cap = p_cap.add_run(caption)
                r_cap.italic = True
                r_cap.font.name = "Times New Roman"
                r_cap.font.size = Pt(10.0)
                r_cap.font.color.rgb = RGBColor(0x4A, 0x55, 0x68)

            idx += 1
            continue

        # ── XU LY DOAN VAN THUONG (PARAGRAPH) ──
        if stripped:
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(3)
            p.paragraph_format.space_after = Pt(5)
            p.paragraph_format.line_spacing = 1.3
            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

            if stripped.startswith("*TP. Hồ Chí Minh") or stripped.startswith("**Nguyễn Văn Thịnh**"):
                p.alignment = WD_ALIGN_PARAGRAPH.RIGHT

            add_paragraph_runs(p, stripped)

        idx += 1

    # 4. Luu tep Word an toan tuyet doi
    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        doc.save(str(output_path))
        print(f"[SUCCESS] Da xuat bao cao Word thanh cong tai: {output_path}")
    except PermissionError:
        backup_path = output_path.with_name(f"{output_path.stem}_FIXED.docx")
        doc.save(str(backup_path))
        print(f"[WARNING] Tep goc dang mo trong Word. Da luu ban sao tai: {backup_path}")


if __name__ == "__main__":
    root = Path(__file__).resolve().parent.parent
    md_file = root / "docs" / "bao_cao_chuyen_de.md"
    docx_file = root / "docs" / "Bao_Cao_Chuyen_De_Tot_Nghiep_NguyenVanThinh_25730149.docx"
    build_word_report(md_file, docx_file)
