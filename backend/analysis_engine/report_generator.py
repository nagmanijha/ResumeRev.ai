# analysis_engine/report_generator.py (Unicode Font Fix)

import logging
from fpdf import FPDF
from datetime import datetime

logger = logging.getLogger(__name__)

# --- Professional Color Palette ---
COLOR_PRIMARY_TEXT = (45, 55, 72)
COLOR_SECONDARY_TEXT = (113, 128, 150)
COLOR_ACCENT = (49, 130, 206)
COLOR_BORDER = (226, 232, 240)

class PDFReport(FPDF):
    """
    Custom PDF class with a professional header, footer, and new styling methods.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.generation_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            # FIX: Add the font files for each style: Regular, Bold, and Italic
            self.add_font("DejaVu", "", "fonts/DejaVuSans.ttf")
            self.add_font("DejaVu", "B", "fonts/DejaVuSans-Bold.ttf")
            self.add_font("DejaVu", "I", "fonts/DejaVuSans-Oblique.ttf")
            self.font_family = "DejaVu"
        except RuntimeError:
            logger.error("DejaVu font files not found in /fonts folder. Falling back to Arial.")
            self.font_family = "Arial"

    def header(self):
        # This call will now work because the Bold style is registered
        self.set_font(self.font_family, 'B', 16)
        self.set_text_color(*COLOR_PRIMARY_TEXT)
        self.cell(0, 10, 'ResumeRev.ai Analysis Report', 0, 1, 'L')
        self.set_font(self.font_family, '', 8)
        self.set_text_color(*COLOR_SECONDARY_TEXT)
        self.cell(0, 5, f'Generated on: {self.generation_time}', 0, 1, 'L')
        self.set_draw_color(*COLOR_BORDER)
        self.line(10, 30, 200, 30)
        self.ln(15)

    def footer(self):
        self.set_y(-15)
        # Use Italic style
        self.set_font(self.font_family, 'I', 8)
        self.set_text_color(*COLOR_SECONDARY_TEXT)
        self.cell(0, 10, f'Page {self.page_no()}/{{nb}}', 0, 0, 'C')

    def chapter_title(self, title):
        # Use Bold style
        self.set_font(self.font_family, 'B', 12)
        self.set_text_color(*COLOR_ACCENT)
        self.cell(0, 10, title, 0, 1, 'L')
        self.ln(2)
        
    def draw_progress_bar(self, value, max_val=100, label=""):
        # Use Regular style
        self.set_font(self.font_family, '', 10)
        self.set_text_color(*COLOR_PRIMARY_TEXT)
        self.cell(50, 8, label, 0, 0)
        
        bar_width = 100
        progress = (value / max_val) * bar_width
        
        self.set_fill_color(*COLOR_BORDER)
        self.cell(bar_width, 8, '', 1, 0, 'L', fill=True)
        
        self.set_fill_color(*COLOR_ACCENT)
        if progress > 0:
            self.cell(-bar_width, 8, '', 0, 0)
            self.cell(progress, 8, '', 0, 0, 'L', fill=True)

        # Use Bold style for the score text
        self.set_font(self.font_family, 'B', 10)
        self.cell(20, 8, f' {value}/{max_val}', 0, 1, 'L')
        
    def render_pills(self, title, items, color):
        # Use Bold style for the title
        self.set_font(self.font_family, 'B', 10)
        self.set_text_color(*COLOR_PRIMARY_TEXT)
        self.cell(0, 10, title, 0, 1)
        
        # Use Regular style for the pills
        self.set_font(self.font_family, '', 9)

def generate_pdf_report(analysis_data: dict) -> bytes:
    """Generates a professionally styled, multi-section PDF report with Unicode support."""
    try:
        pdf = PDFReport()
        if pdf.font_family != "DejaVu":
             # If font failed to load, add a warning to the suggestions
             analysis_data['suggestions'].insert(0, "Warning: Unicode font not found, some characters may not render correctly.")

        pdf.alias_nb_pages()
        pdf.set_title("Resume Analysis Report")
        pdf.set_author("ResumeRev.ai")
        pdf.add_page()
        
        parsed = analysis_data.get('parsed_data', {})
        score = analysis_data.get('ats_score', {})
        suggestions = analysis_data.get('suggestions', [])
        skill_gap = score.get('skill_gap', {})
        breakdown = score.get('breakdown', {})

        # --- Candidate Info Section ---
        pdf.chapter_title('Candidate Summary')
        pdf.set_font(pdf.font_family, 'B', 11)
        pdf.set_text_color(*COLOR_PRIMARY_TEXT)
        pdf.cell(0, 8, f"Name: {parsed.get('name', 'N/A')}", 0, 1)
        
        contact = parsed.get('contact', {})
        if contact.get('email'):
            pdf.set_font(pdf.font_family, '', 10)
            pdf.cell(0, 6, f"Email: {contact.get('email', 'N/A')}", 0, 1)
        pdf.ln(5)

        # --- Overall Score Section ---
        pdf.chapter_title('Overall ATS Score')
        pdf.draw_progress_bar(score.get('total_score', 0), label="Total Score")
        pdf.ln(8)

        # --- Score Breakdown ---
        pdf.chapter_title('Score Breakdown')
        pdf.set_font(pdf.font_family, '', 10)
        pdf.set_text_color(*COLOR_PRIMARY_TEXT)
        
        breakdown_items = [
            ("Skill Match", breakdown.get('skill_match', 0)),
            ("Semantic Match", breakdown.get('semantic_match', 0)),
            ("Experience Match", breakdown.get('experience_match', 0)),
            ("Project Relevance", breakdown.get('project_match', 0)),
        ]
        
        for label, val in breakdown_items:
            pdf.cell(60, 7, f"  • {label}:", 0, 0)
            pdf.set_font(pdf.font_family, 'B', 10)
            pdf.cell(30, 7, f"{val}/100", 0, 1)
            pdf.set_font(pdf.font_family, '', 10)
        pdf.ln(5)

        # --- Skill Gap Analysis ---
        pdf.chapter_title('Skill Gap Analysis')
        pdf.set_font(pdf.font_family, '', 10)
        
        matched = skill_gap.get('matched', [])
        missing = skill_gap.get('missing', [])
        match_pct = skill_gap.get('match_percent', 0)
        
        pdf.set_text_color(*COLOR_PRIMARY_TEXT)
        pdf.cell(0, 7, f"Match Rate: {round(match_pct)}%", 0, 1)
        pdf.ln(3)
        
        # Matched Skills
        pdf.set_font(pdf.font_family, 'B', 10)
        pdf.set_text_color(34, 139, 34)  # Green
        pdf.cell(0, 7, f"Matched Skills ({len(matched)}):", 0, 1)
        pdf.set_font(pdf.font_family, '', 9)
        pdf.set_text_color(*COLOR_PRIMARY_TEXT)
        if matched:
            pdf.multi_cell(0, 5, ", ".join(matched[:15]) + ("..." if len(matched) > 15 else ""))
        else:
            pdf.cell(0, 5, "None detected", 0, 1)
        pdf.ln(3)
        
        # Missing Skills
        pdf.set_font(pdf.font_family, 'B', 10)
        pdf.set_text_color(220, 53, 69)  # Red
        pdf.cell(0, 7, f"Missing Skills ({len(missing)}):", 0, 1)
        pdf.set_font(pdf.font_family, '', 9)
        pdf.set_text_color(*COLOR_PRIMARY_TEXT)
        if missing:
            pdf.multi_cell(0, 5, ", ".join(missing[:15]) + ("..." if len(missing) > 15 else ""))
        else:
            pdf.cell(0, 5, "All required skills present!", 0, 1)
        pdf.ln(8)

        # --- AI Suggestions Section ---
        pdf.chapter_title('AI-Powered Recommendations')
        pdf.set_font(pdf.font_family, '', 10)
        pdf.set_text_color(*COLOR_PRIMARY_TEXT)
        if suggestions:
            for i, suggestion in enumerate(suggestions[:5]):  # Limit to 5 suggestions
                pdf.set_font(pdf.font_family, 'B', 10)
                pdf.cell(8, 6, f"{i+1}.", 0, 0)
                pdf.set_font(pdf.font_family, '', 10)
                pdf.multi_cell(0, 5, suggestion)
                pdf.ln(2)
        else:
            pdf.cell(0, 6, "No specific recommendations at this time.", 0, 1)
        

        return pdf.output()
    except Exception as e:
        logger.error(f"Failed to generate PDF report: {e}", exc_info=True)
        # Fallback error PDF
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(0, 10, 'Error: Could not generate the report.', 0, 1, 'C')
        return pdf.output()
