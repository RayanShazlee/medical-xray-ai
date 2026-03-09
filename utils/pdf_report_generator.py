"""
📄 PDF Report Generator — Professional Medical Report

Generates hospital-grade radiology PDF reports with:
- Professional letterhead with hospital branding
- Patient demographics (from DICOM or form)
- X-ray image, Grad-CAM overlay, anatomical segmentation
- CheXNet detection results with confidence indicators
- Radiological categorization
- Differential diagnosis with probabilities
- Clinical decision support (CURB-65, antibiotics, labs, follow-up)
- Severity assessment and uncertainty metrics
- Disclaimer and AI confidence assessment
- Footer with report ID, page numbers, timestamps

Uses reportlab for PDF generation.
"""

import io
import base64
import datetime
from typing import Dict, Any, Optional, List
from PIL import Image

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm, inch
    from reportlab.lib.colors import HexColor, black, white, red, green, blue, gray, Color
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        Image as RLImage, PageBreak, HRFlowable, KeepTogether, Frame
    )
    from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
    from reportlab.platypus.doctemplate import PageTemplate, BaseDocTemplate
    from reportlab.graphics.shapes import Drawing, Rect, String, Line
    from reportlab.graphics import renderPDF
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    print("Warning: reportlab not installed. PDF export disabled.")


class PDFReportGenerator:
    """Generate professional hospital-grade radiology PDF reports."""
    
    # Professional color scheme
    PRIMARY = HexColor('#0c4a6e') if REPORTLAB_AVAILABLE else None       # Dark blue
    PRIMARY_LIGHT = HexColor('#0ea5e9') if REPORTLAB_AVAILABLE else None  # Sky blue
    ACCENT = HexColor('#0369a1') if REPORTLAB_AVAILABLE else None         # Medium blue
    DANGER = HexColor('#dc2626') if REPORTLAB_AVAILABLE else None
    WARNING = HexColor('#d97706') if REPORTLAB_AVAILABLE else None
    SUCCESS = HexColor('#16a34a') if REPORTLAB_AVAILABLE else None
    DARK = HexColor('#0f172a') if REPORTLAB_AVAILABLE else None
    TEXT_DARK = HexColor('#1e293b') if REPORTLAB_AVAILABLE else None
    TEXT_BODY = HexColor('#334155') if REPORTLAB_AVAILABLE else None
    TEXT_MUTED = HexColor('#64748b') if REPORTLAB_AVAILABLE else None
    LIGHT_BG = HexColor('#f0f9ff') if REPORTLAB_AVAILABLE else None
    BORDER = HexColor('#cbd5e1') if REPORTLAB_AVAILABLE else None
    ROW_ALT = HexColor('#f8fafc') if REPORTLAB_AVAILABLE else None
    
    def __init__(self):
        if not REPORTLAB_AVAILABLE:
            raise RuntimeError("reportlab is required. Install: pip install reportlab")
        
        self.styles = getSampleStyleSheet()
        self._create_custom_styles()
        self.report_id = f"RPT-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    def _create_custom_styles(self):
        """Create custom paragraph styles for professional medical report."""
        # Main title
        self.styles.add(ParagraphStyle(
            name='ReportTitle',
            parent=self.styles['Title'],
            fontSize=20,
            textColor=self.PRIMARY,
            fontName='Helvetica-Bold',
            spaceAfter=2,
            alignment=TA_CENTER
        ))
        # Subtitle
        self.styles.add(ParagraphStyle(
            name='ReportSubtitle',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=self.TEXT_MUTED,
            fontName='Helvetica',
            alignment=TA_CENTER,
            spaceAfter=4
        ))
        # Section header with blue left border look
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading2'],
            fontSize=13,
            textColor=self.PRIMARY,
            fontName='Helvetica-Bold',
            spaceBefore=14,
            spaceAfter=6,
        ))
        self.styles.add(ParagraphStyle(
            name='SubHeader',
            parent=self.styles['Heading3'],
            fontSize=10,
            textColor=self.ACCENT,
            fontName='Helvetica-Bold',
            spaceBefore=8,
            spaceAfter=4
        ))
        self.styles.add(ParagraphStyle(
            name='BodyText2',
            parent=self.styles['BodyText'],
            fontSize=9,
            leading=14,
            textColor=self.TEXT_BODY,
            fontName='Helvetica'
        ))
        self.styles.add(ParagraphStyle(
            name='BodyBold',
            parent=self.styles['BodyText'],
            fontSize=9,
            leading=14,
            textColor=self.TEXT_DARK,
            fontName='Helvetica-Bold'
        ))
        self.styles.add(ParagraphStyle(
            name='SmallGray',
            parent=self.styles['BodyText'],
            fontSize=7,
            textColor=self.TEXT_MUTED,
            fontName='Helvetica'
        ))
        self.styles.add(ParagraphStyle(
            name='Disclaimer',
            parent=self.styles['BodyText'],
            fontSize=7.5,
            leading=11,
            textColor=self.DANGER,
            fontName='Helvetica',
            spaceBefore=8,
        ))
        self.styles.add(ParagraphStyle(
            name='FooterStyle',
            parent=self.styles['Normal'],
            fontSize=7,
            textColor=self.TEXT_MUTED,
            fontName='Helvetica',
            alignment=TA_CENTER
        ))
        self.styles.add(ParagraphStyle(
            name='FindingNormal',
            parent=self.styles['BodyText'],
            fontSize=9,
            leading=13,
            textColor=self.SUCCESS,
            fontName='Helvetica-Bold'
        ))
        self.styles.add(ParagraphStyle(
            name='FindingAbnormal',
            parent=self.styles['BodyText'],
            fontSize=9,
            leading=13,
            textColor=self.DANGER,
            fontName='Helvetica-Bold'
        ))
    
    def _section_divider(self):
        """Return a styled section divider."""
        return HRFlowable(width="100%", thickness=1, color=self.BORDER, spaceAfter=4, spaceBefore=2)
    
    def _section_header_block(self, icon, title):
        """Return a section header with icon and blue underline."""
        return [
            Spacer(1, 6),
            Paragraph(f"{icon}  {title}", self.styles['SectionHeader']),
            HRFlowable(width="100%", thickness=1.5, color=self.PRIMARY_LIGHT, spaceAfter=6),
        ]
    
    def _info_row(self, label, value, label_color=None):
        """Create a label: value pair for tables."""
        lc = label_color or self.PRIMARY
        return [
            Paragraph(f"<font color='{lc}'><b>{label}</b></font>", self.styles['BodyText2']),
            Paragraph(str(value), self.styles['BodyText2'])
        ]

    def _b64_to_rl_image(self, b64_str: str, max_width: float = 400, max_height: float = 300) -> Optional[RLImage]:
        """Convert base64 image to reportlab Image."""
        try:
            img_data = base64.b64decode(b64_str)
            img_buffer = io.BytesIO(img_data)
            pil_img = Image.open(img_buffer)
            
            w, h = pil_img.size
            ratio = min(max_width / w, max_height / h)
            new_w = w * ratio
            new_h = h * ratio
            
            img_buffer.seek(0)
            return RLImage(img_buffer, width=new_w, height=new_h)
        except Exception as e:
            print(f"Error converting image for PDF: {e}")
            return None
    
    def _add_header_footer(self, canvas, doc):
        """Add professional header and footer to every page."""
        canvas.saveState()
        width, height = A4
        
        # ─── HEADER BAR ───
        canvas.setFillColor(self.PRIMARY)
        canvas.rect(0, height - 28*mm, width, 28*mm, fill=True, stroke=False)
        
        # Hospital/System name
        canvas.setFillColor(white)
        canvas.setFont("Helvetica-Bold", 14)
        canvas.drawString(20*mm, height - 14*mm, "🏥  AI RADIOLOGY DIAGNOSTIC SYSTEM")
        
        # Subtitle
        canvas.setFont("Helvetica", 8)
        canvas.drawString(20*mm, height - 20*mm, "CheXNet DenseNet-121  •  Groq LLama-3.3-70B  •  Pinecone RAG Knowledge Base")
        
        # Report ID on right
        canvas.setFont("Helvetica-Bold", 8)
        canvas.drawRightString(width - 20*mm, height - 14*mm, self.report_id)
        canvas.setFont("Helvetica", 7)
        canvas.drawRightString(width - 20*mm, height - 20*mm, 
                               f"Generated: {datetime.datetime.now().strftime('%B %d, %Y  %H:%M')}")
        
        # Thin accent line below header
        canvas.setStrokeColor(self.PRIMARY_LIGHT)
        canvas.setLineWidth(2)
        canvas.line(0, height - 28*mm, width, height - 28*mm)
        
        # ─── FOOTER ───
        canvas.setStrokeColor(self.BORDER)
        canvas.setLineWidth(0.5)
        canvas.line(20*mm, 15*mm, width - 20*mm, 15*mm)
        
        canvas.setFillColor(self.TEXT_MUTED)
        canvas.setFont("Helvetica", 6.5)
        canvas.drawString(20*mm, 10*mm, 
                          "⚠️ AI-Generated Report — For Preliminary Screening Only — Must Be Verified By Board-Certified Radiologist")
        canvas.drawRightString(width - 20*mm, 10*mm, f"Page {doc.page}")
        
        # Confidential watermark (subtle)
        canvas.setFillColor(Color(0, 0, 0, alpha=0.03))
        canvas.setFont("Helvetica-Bold", 60)
        canvas.translate(width/2, height/2)
        canvas.rotate(45)
        canvas.drawCentredString(0, 0, "CONFIDENTIAL")
        
        canvas.restoreState()
    
    def generate(self, report_data: Dict[str, Any], output_path: str) -> str:
        """Generate a complete professional PDF report."""
        self.report_id = f"RPT-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer, pagesize=A4,
            leftMargin=20*mm, rightMargin=20*mm,
            topMargin=32*mm, bottomMargin=22*mm
        )
        
        story = []
        
        # ═══════════════════════════════════════
        # PAGE 1: PATIENT INFO + IMAGING + FINDINGS
        # ═══════════════════════════════════════
        
        # ── Patient Demographics ──
        patient = report_data.get('patient_context', {})
        dicom_meta = report_data.get('dicom_metadata', {})
        
        story.extend(self._section_header_block("👤", "PATIENT INFORMATION"))
        
        demo_data = []
        demo_data.append(self._info_row('Patient ID', self.report_id))
        demo_data.append(self._info_row('Study Date', 
            dicom_meta.get('StudyDateFormatted', datetime.datetime.now().strftime('%Y-%m-%d'))))
        if patient.get('age') or dicom_meta.get('PatientAgeYears'):
            demo_data.append(self._info_row('Age', patient.get('age') or dicom_meta.get('PatientAgeYears')))
        if patient.get('sex') or dicom_meta.get('PatientSex'):
            demo_data.append(self._info_row('Sex', patient.get('sex') or dicom_meta.get('PatientSex')))
        if patient.get('symptoms'):
            demo_data.append(self._info_row('Chief Complaint', patient['symptoms']))
        if patient.get('duration'):
            demo_data.append(self._info_row('Duration', patient['duration']))
        if patient.get('smoking'):
            demo_data.append(self._info_row('Smoking History', 'Yes'))
        if dicom_meta.get('Modality'):
            demo_data.append(self._info_row('Modality', dicom_meta['Modality']))
        if dicom_meta.get('ViewPosition'):
            demo_data.append(self._info_row('View Position', dicom_meta['ViewPosition']))
        
        if demo_data:
            table = Table(demo_data, colWidths=[120, 340])
            table.setStyle(TableStyle([
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ('TOPPADDING', (0, 0), (-1, -1), 2),
                ('LINEBELOW', (0, 0), (-1, -1), 0.3, self.BORDER),
            ]))
            story.append(table)
        
        # ── Severity Summary ──
        severity = report_data.get('severity')
        detections = report_data.get('detections', [])
        positive_findings = [d for d in detections if d.get('score', 0) > 0.2 and d.get('label') != 'No Finding']
        
        story.append(Spacer(1, 8))
        if severity:
            sev_color = self.DANGER if severity in ['Critical', 'High'] else self.WARNING if severity == 'Moderate' else self.SUCCESS
            story.append(Paragraph(
                f"<b>OVERALL SEVERITY: </b>"
                f"<font color='{sev_color}' size='12'><b>  {severity.upper()}  </b></font>"
                f"&nbsp;&nbsp;|&nbsp;&nbsp;Findings: {len(positive_findings)} pathologies detected out of {len(detections)} evaluated",
                self.styles['BodyText2']
            ))
        
        # ── Medical Images ──
        story.extend(self._section_header_block("🖼️", "DIAGNOSTIC IMAGING"))
        
        if report_data.get('enhanced_comparison'):
            story.append(Paragraph("Original vs Enhanced (CLAHE)", self.styles['SubHeader']))
            img = self._b64_to_rl_image(report_data['enhanced_comparison'], 460, 180)
            if img:
                story.append(img)
                story.append(Spacer(1, 6))
        
        # Grad-CAM and Segmentation side by side if both available
        heatmap_img = None
        seg_img = None
        if report_data.get('heatmap'):
            heatmap_img = self._b64_to_rl_image(report_data['heatmap'], 220, 200)
        if report_data.get('segmentation_overlay'):
            seg_img = self._b64_to_rl_image(report_data['segmentation_overlay'], 220, 200)
        
        if heatmap_img and seg_img:
            img_table = Table(
                [[
                    [Paragraph("Grad-CAM++ Heatmap", self.styles['SubHeader']), heatmap_img],
                    [Paragraph("Anatomical Segmentation", self.styles['SubHeader']), seg_img]
                ]],
                colWidths=[230, 230]
            )
            img_table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('LEFTPADDING', (0, 0), (-1, -1), 4),
                ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            ]))
            story.append(img_table)
        else:
            if heatmap_img:
                story.append(Paragraph("Grad-CAM++ Disease Localization", self.styles['SubHeader']))
                story.append(heatmap_img)
            if seg_img:
                story.append(Paragraph("Anatomical Segmentation", self.styles['SubHeader']))
                story.append(seg_img)
        
        story.append(Spacer(1, 4))
        
        # ── Image Quality ──
        qr = report_data.get('quality_report')
        if qr:
            q_text = qr.get('quality', 'unknown').upper()
            q_color = self.SUCCESS if qr.get('quality') == 'good' else self.WARNING
            story.append(Paragraph(
                f"<b>Image Quality:</b> <font color='{q_color}'><b>{q_text}</b></font>"
                + (f" — Issues: {', '.join(qr.get('issues', []))}" if qr.get('issues') else " — No issues detected"),
                self.styles['BodyText2']
            ))
        
        # ═══════════════════════════════════════
        # FINDINGS TABLE
        # ═══════════════════════════════════════
        
        if detections:
            story.extend(self._section_header_block("🔬", "DETECTION RESULTS"))
            
            det_data = [['#', 'Pathology', 'Confidence', 'Status']]
            for i, d in enumerate(detections, 1):
                score = d.get('score', 0)
                pct = f"{score * 100:.1f}%"
                if d.get('label') == 'No Finding':
                    status = 'BASELINE'
                    status_color = self.TEXT_MUTED
                elif score > 0.4:
                    status = '⚠️ POSITIVE'
                    status_color = self.DANGER
                elif score > 0.2:
                    status = 'SUSPICIOUS'
                    status_color = self.WARNING
                else:
                    status = 'NEGATIVE'
                    status_color = self.SUCCESS
                det_data.append([str(i), d.get('label', ''), pct, status])
            
            det_table = Table(det_data, colWidths=[25, 200, 80, 100])
            det_table.setStyle(TableStyle([
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('BACKGROUND', (0, 0), (-1, 0), self.PRIMARY),
                ('TEXTCOLOR', (0, 0), (-1, 0), white),
                ('ALIGN', (0, 0), (0, -1), 'CENTER'),
                ('ALIGN', (2, 0), (2, -1), 'CENTER'),
                ('ALIGN', (3, 0), (3, -1), 'CENTER'),
                ('GRID', (0, 0), (-1, -1), 0.5, self.BORDER),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [white, self.ROW_ALT]),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ]))
            story.append(det_table)
        
        # ── CTR ──
        ctr = report_data.get('ctr')
        if ctr and ctr.get('ctr'):
            story.append(Spacer(1, 6))
            ctr_val = ctr['ctr']
            ctr_color = self.SUCCESS if ctr_val < 0.5 else self.WARNING if ctr_val < 0.55 else self.DANGER
            story.append(Paragraph(
                f"<b>Cardiothoracic Ratio (CTR):</b> "
                f"<font color='{ctr_color}' size='11'><b>{ctr_val:.3f}</b></font> — "
                f"<font color='{ctr_color}'>{ctr.get('interpretation', '')}</font><br/>"
                f"<font size='7' color='{self.TEXT_MUTED}'>Heart width: {ctr.get('heart_width', 'N/A')}px  |  "
                f"Thorax width: {ctr.get('thorax_width', 'N/A')}px  |  Normal &lt; 0.50</font>",
                self.styles['BodyText2']
            ))
        
        # ═══════════════════════════════════════
        # PAGE 2: DIFFERENTIALS + CLINICAL + DIAGNOSIS
        # ═══════════════════════════════════════
        story.append(PageBreak())
        
        # ── Uncertainty ──
        uncertainty = report_data.get('uncertainty', {})
        if uncertainty:
            story.extend(self._section_header_block("📊", "AI CONFIDENCE ASSESSMENT"))
            unc_data = []
            
            # confidence_level OR reliability (backend sends 'reliability')
            conf_level = uncertainty.get('confidence_level') or uncertainty.get('reliability', '')
            if conf_level:
                conf_label = conf_level.split('—')[0].strip() if '—' in conf_level else conf_level
                conf_color = self.SUCCESS if conf_label.startswith('HIGH') else self.WARNING
                mean_conf = uncertainty.get('mean_confidence', 0)
                unc_data.append(self._info_row('Overall Confidence', 
                    f"{conf_label} ({mean_conf*100:.1f}%)"))
            
            # prediction_stability OR reliability description
            stability = uncertainty.get('prediction_stability')
            if not stability and '—' in (uncertainty.get('reliability') or ''):
                stability = uncertainty['reliability'].split('—', 1)[1].strip()
            if stability:
                unc_data.append(self._info_row('Prediction Stability', stability))
            
            # mc_dropout_runs OR n_forward
            n_runs = uncertainty.get('mc_dropout_runs') or uncertainty.get('n_forward') or uncertainty.get('n_forward_passes')
            if n_runs:
                unc_data.append(self._info_row('Monte Carlo Samples', str(n_runs)))
            
            # mean_std OR std_confidence
            std_val = uncertainty.get('mean_std') or uncertainty.get('std_confidence')
            if std_val:
                unc_data.append(self._info_row('Mean Uncertainty (σ)', f"{std_val:.4f}"))
            
            if unc_data:
                unc_table = Table(unc_data, colWidths=[160, 300])
                unc_table.setStyle(TableStyle([
                    ('FONTSIZE', (0, 0), (-1, -1), 9),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                    ('LINEBELOW', (0, 0), (-1, -1), 0.3, self.BORDER),
                ]))
                story.append(unc_table)
        
        # ── Differential Diagnosis ──
        differentials = report_data.get('differentials')
        if differentials:
            story.extend(self._section_header_block("🧬", "DIFFERENTIAL DIAGNOSIS"))
            
            diff_data = [['Rank', 'Diagnosis', 'Probability', 'Based On']]
            for i, d in enumerate(differentials[:8], 1):
                prob = d.get('probability', 0)
                prob_pct = f"{prob * 100:.1f}%"
                diff_data.append([
                    str(i), 
                    d.get('diagnosis', ''), 
                    prob_pct, 
                    d.get('based_on', '')
                ])
            
            diff_table = Table(diff_data, colWidths=[35, 180, 70, 170])
            diff_table.setStyle(TableStyle([
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('BACKGROUND', (0, 0), (-1, 0), self.ACCENT),
                ('TEXTCOLOR', (0, 0), (-1, 0), white),
                ('ALIGN', (0, 0), (0, -1), 'CENTER'),
                ('ALIGN', (2, 0), (2, -1), 'CENTER'),
                ('GRID', (0, 0), (-1, -1), 0.5, self.BORDER),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [white, self.ROW_ALT]),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('TOPPADDING', (0, 0), (-1, -1), 3),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ]))
            story.append(diff_table)
        
        # ── Clinical Decision Support ──
        clinical = report_data.get('clinical_decision')
        if clinical:
            story.extend(self._section_header_block("🏥", "CLINICAL DECISION SUPPORT"))
            
            # CURB-65
            curb = clinical.get('curb65')
            if curb:
                score_color = self.SUCCESS if curb['score'] <= 1 else self.WARNING if curb['score'] <= 2 else self.DANGER
                story.append(Paragraph(
                    f"<b>CURB-65 Score: </b>"
                    f"<font color='{score_color}' size='12'><b>{curb['score']}/{curb['max_score']}</b></font>"
                    f"&nbsp;&nbsp;—&nbsp;&nbsp;{curb.get('risk_level', '')}<br/>"
                    f"<b>Recommendation:</b> {curb.get('recommended_action', 'N/A')}",
                    self.styles['BodyText2']
                ))
                if curb.get('criteria_met'):
                    story.append(Paragraph(
                        f"<font color='{self.TEXT_MUTED}'>Criteria met: {', '.join(curb['criteria_met'])}</font>",
                        self.styles['SmallGray']
                    ))
                story.append(Spacer(1, 6))
            
            # Antibiotics
            abx = clinical.get('antibiotics')
            if abx:
                story.append(Paragraph("💊  Antibiotic Recommendations", self.styles['SubHeader']))
                abx_data = []
                abx_data.append(self._info_row('Setting', abx.get('setting', 'N/A')))
                abx_data.append(self._info_row('First-line', abx.get('first_line', 'N/A')))
                abx_data.append(self._info_row('Alternative', abx.get('alternative', 'N/A')))
                abx_data.append(self._info_row('Duration', abx.get('duration', 'N/A')))
                abx_data.append(self._info_row('Guideline', abx.get('guideline', 'N/A')))
                
                abx_table = Table(abx_data, colWidths=[120, 340])
                abx_table.setStyle(TableStyle([
                    ('FONTSIZE', (0, 0), (-1, -1), 8),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                    ('LINEBELOW', (0, 0), (-1, -1), 0.3, self.BORDER),
                ]))
                story.append(abx_table)
                story.append(Spacer(1, 6))
            
            # Labs
            labs = clinical.get('recommended_labs')
            if labs:
                story.append(Paragraph("🧪  Recommended Laboratory Tests", self.styles['SubHeader']))
                lab_data = [['Test', 'Reason', 'Priority']]
                for lab in labs[:10]:
                    lab_data.append([lab.get('test', ''), lab.get('reason', ''), lab.get('priority', '')])
                
                lab_table = Table(lab_data, colWidths=[150, 230, 55])
                lab_table.setStyle(TableStyle([
                    ('FONTSIZE', (0, 0), (-1, -1), 7.5),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('BACKGROUND', (0, 0), (-1, 0), self.SUCCESS),
                    ('TEXTCOLOR', (0, 0), (-1, 0), white),
                    ('GRID', (0, 0), (-1, -1), 0.5, self.BORDER),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [white, self.ROW_ALT]),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ('TOPPADDING', (0, 0), (-1, -1), 3),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                ]))
                story.append(lab_table)
                story.append(Spacer(1, 6))
            
            # Follow-up
            followup = clinical.get('imaging_followup')
            if followup:
                story.append(Paragraph("📋  Imaging Follow-up Plan", self.styles['SubHeader']))
                for f in followup:
                    priority_color = self.DANGER if f.get('priority') == 'Urgent' else self.WARNING if f.get('priority') == 'High' else self.TEXT_BODY
                    story.append(Paragraph(
                        f"<b>{f.get('imaging', '')}</b> — {f.get('timeline', '')}"
                        f"&nbsp;&nbsp;<font color='{priority_color}'>[{f.get('priority', '')}]</font><br/>"
                        f"<font color='{self.TEXT_MUTED}'><i>{f.get('reason', '')}</i></font>",
                        self.styles['BodyText2']
                    ))
                    story.append(Spacer(1, 3))
        
        # ═══════════════════════════════════════
        # PAGE 3: FULL AI DIAGNOSIS REPORT
        # ═══════════════════════════════════════
        diagnosis = report_data.get('diagnosis')
        if diagnosis:
            story.append(PageBreak())
            story.extend(self._section_header_block("📋", "AI RADIOLOGICAL REPORT"))
            
            # Clean markdown formatting
            clean_text = diagnosis
            # Convert **bold** to <b>bold</b>
            import re
            clean_text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', clean_text)
            clean_text = clean_text.replace('\n', '<br/>')
            
            if len(clean_text) > 6000:
                clean_text = clean_text[:6000] + '<br/><br/><i>[Report truncated for PDF — see full version in app]</i>'
            
            try:
                story.append(Paragraph(clean_text, self.styles['BodyText2']))
            except Exception:
                # Fallback for XML parsing issues
                safe_text = diagnosis[:4000].replace('<', '&lt;').replace('>', '&gt;').replace('\n', '<br/>')
                story.append(Paragraph(safe_text, self.styles['BodyText2']))
        
        # ═══════════════════════════════════════
        # DISCLAIMER BLOCK
        # ═══════════════════════════════════════
        story.append(Spacer(1, 20))
        story.append(HRFlowable(width="100%", thickness=1.5, color=self.DANGER, spaceAfter=6))
        
        disclaimer_data = [[
            Paragraph(
                "<b>⚠️ IMPORTANT DISCLAIMER</b><br/><br/>"
                "This report is generated by an artificial intelligence system for <b>preliminary screening "
                "purposes ONLY</b>. It does NOT constitute a medical diagnosis and is NOT a substitute for "
                "professional radiological interpretation.<br/><br/>"
                "• All findings MUST be verified by a qualified, board-certified radiologist<br/>"
                "• AI-assisted diagnosis has known limitations including false positives and false negatives<br/>"
                "• The treating physician bears full responsibility for patient care decisions<br/>"
                "• This report should be used as a supplementary tool, not a primary diagnostic resource",
                self.styles['Disclaimer']
            )
        ]]
        
        disc_table = Table(disclaimer_data, colWidths=[460])
        disc_table.setStyle(TableStyle([
            ('BOX', (0, 0), (-1, -1), 1, self.DANGER),
            ('BACKGROUND', (0, 0), (-1, -1), HexColor('#fef2f2')),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
            ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ]))
        story.append(disc_table)
        
        story.append(Spacer(1, 10))
        story.append(Paragraph(
            f"<b>Report ID:</b> {self.report_id} &nbsp;&nbsp;|&nbsp;&nbsp; "
            f"<b>AI System:</b> CheXNet DenseNet-121 + Groq LLama-3.3-70B + Pinecone RAG &nbsp;&nbsp;|&nbsp;&nbsp; "
            f"<b>Generated:</b> {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            self.styles['SmallGray']
        ))
        
        # Build PDF with header/footer
        doc.build(story, onFirstPage=self._add_header_footer, onLaterPages=self._add_header_footer)
        
        # Save to file
        pdf_bytes = buffer.getvalue()
        with open(output_path, 'wb') as f:
            f.write(pdf_bytes)
        
        return output_path
    
    def generate_to_base64(self, report_data: Dict[str, Any]) -> str:
        """Generate PDF and return as base64 string for download."""
        import tempfile, os
        tmp = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False)
        tmp_path = tmp.name
        tmp.close()
        
        self.generate(report_data, tmp_path)
        
        with open(tmp_path, 'rb') as f:
            pdf_bytes = f.read()
        
        os.unlink(tmp_path)
        
        return base64.b64encode(pdf_bytes).decode('utf-8')
