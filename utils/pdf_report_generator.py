"""
📄 PDF Report Generator — Tier 4 Feature

Generates professional radiology-style PDF reports with:
- Patient demographics (from DICOM or form)
- X-ray image, Grad-CAM overlay, anatomical segmentation
- CheXNet detection results with confidence bars
- Radiological categorization (opacity pattern, distribution, etc.)
- Differential diagnosis with probabilities
- Clinical decision support (CURB-65, antibiotics, labs, follow-up)
- Disclaimer and AI confidence assessment

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
    from reportlab.lib.colors import HexColor, black, white, red, green, blue, gray
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        Image as RLImage, PageBreak, HRFlowable
    )
    from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    print("Warning: reportlab not installed. PDF export disabled.")


class PDFReportGenerator:
    """Generate professional radiology PDF reports."""
    
    # Color scheme
    PRIMARY = HexColor('#0ea5e9') if REPORTLAB_AVAILABLE else None
    SECONDARY = HexColor('#38bdf8') if REPORTLAB_AVAILABLE else None
    DANGER = HexColor('#ef4444') if REPORTLAB_AVAILABLE else None
    WARNING = HexColor('#f59e0b') if REPORTLAB_AVAILABLE else None
    SUCCESS = HexColor('#22c55e') if REPORTLAB_AVAILABLE else None
    DARK = HexColor('#1e293b') if REPORTLAB_AVAILABLE else None
    LIGHT_GRAY = HexColor('#94a3b8') if REPORTLAB_AVAILABLE else None
    
    def __init__(self):
        if not REPORTLAB_AVAILABLE:
            raise RuntimeError("reportlab is required. Install: pip install reportlab")
        
        self.styles = getSampleStyleSheet()
        self._create_custom_styles()
    
    def _create_custom_styles(self):
        """Create custom paragraph styles for the report."""
        self.styles.add(ParagraphStyle(
            name='ReportTitle',
            parent=self.styles['Title'],
            fontSize=22,
            textColor=self.PRIMARY,
            spaceAfter=6
        ))
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading2'],
            fontSize=14,
            textColor=self.PRIMARY,
            spaceBefore=12,
            spaceAfter=6,
            borderWidth=1,
            borderColor=self.PRIMARY,
            borderPadding=4
        ))
        self.styles.add(ParagraphStyle(
            name='SubHeader',
            parent=self.styles['Heading3'],
            fontSize=11,
            textColor=self.SECONDARY,
            spaceBefore=8,
            spaceAfter=4
        ))
        self.styles.add(ParagraphStyle(
            name='BodyText2',
            parent=self.styles['BodyText'],
            fontSize=9,
            leading=13,
            textColor=black
        ))
        self.styles.add(ParagraphStyle(
            name='SmallGray',
            parent=self.styles['BodyText'],
            fontSize=7,
            textColor=self.LIGHT_GRAY
        ))
        self.styles.add(ParagraphStyle(
            name='Disclaimer',
            parent=self.styles['BodyText'],
            fontSize=8,
            textColor=self.DANGER,
            spaceBefore=12,
            borderWidth=1,
            borderColor=self.DANGER,
            borderPadding=6
        ))
    
    def _b64_to_rl_image(self, b64_str: str, max_width: float = 400, max_height: float = 300) -> Optional[RLImage]:
        """Convert base64 image to reportlab Image."""
        try:
            img_data = base64.b64decode(b64_str)
            img_buffer = io.BytesIO(img_data)
            pil_img = Image.open(img_buffer)
            
            # Calculate aspect-preserving dimensions
            w, h = pil_img.size
            ratio = min(max_width / w, max_height / h)
            new_w = w * ratio
            new_h = h * ratio
            
            img_buffer.seek(0)
            return RLImage(img_buffer, width=new_w, height=new_h)
        except Exception as e:
            print(f"Error converting image for PDF: {e}")
            return None
    
    def generate(self, report_data: Dict[str, Any], output_path: str) -> str:
        """
        Generate a complete PDF report.
        
        Args:
            report_data: Dict containing all analysis results
            output_path: File path for the PDF
            
        Returns:
            Path to the generated PDF
        """
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer, pagesize=A4,
            leftMargin=20*mm, rightMargin=20*mm,
            topMargin=15*mm, bottomMargin=15*mm
        )
        
        story = []
        
        # === HEADER ===
        story.append(Paragraph("🏥 AI Radiology Report", self.styles['ReportTitle']))
        story.append(Paragraph(
            f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
            f"System: CheXNet + Enhancement Agent + RAG",
            self.styles['SmallGray']
        ))
        story.append(HRFlowable(width="100%", thickness=2, color=self.PRIMARY))
        story.append(Spacer(1, 8))
        
        # === PATIENT DEMOGRAPHICS ===
        patient = report_data.get('patient_context', {})
        dicom_meta = report_data.get('dicom_metadata', {})
        
        if patient or dicom_meta:
            story.append(Paragraph("👤 Patient Information", self.styles['SectionHeader']))
            demo_data = []
            if patient.get('age'):
                demo_data.append(['Age', str(patient['age'])])
            elif dicom_meta.get('PatientAgeYears'):
                demo_data.append(['Age', str(dicom_meta['PatientAgeYears'])])
            if patient.get('sex'):
                demo_data.append(['Sex', patient['sex']])
            elif dicom_meta.get('PatientSex'):
                demo_data.append(['Sex', dicom_meta['PatientSex']])
            if patient.get('symptoms'):
                demo_data.append(['Symptoms', patient['symptoms']])
            if patient.get('duration'):
                demo_data.append(['Duration', patient['duration']])
            if patient.get('smoking'):
                demo_data.append(['Smoking', 'Yes' if patient['smoking'] else 'No'])
            if dicom_meta.get('StudyDateFormatted'):
                demo_data.append(['Study Date', dicom_meta['StudyDateFormatted']])
            if dicom_meta.get('Modality'):
                demo_data.append(['Modality', dicom_meta['Modality']])
            if dicom_meta.get('ViewPosition'):
                demo_data.append(['View', dicom_meta['ViewPosition']])
            
            if demo_data:
                table = Table(demo_data, colWidths=[100, 350])
                table.setStyle(TableStyle([
                    ('FONTSIZE', (0, 0), (-1, -1), 9),
                    ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                    ('TEXTCOLOR', (0, 0), (0, -1), self.PRIMARY),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                ]))
                story.append(table)
        
        # === IMAGES ===
        story.append(Paragraph("🖼️ Imaging", self.styles['SectionHeader']))
        
        images_row = []
        
        # Enhanced comparison
        if report_data.get('enhanced_comparison'):
            img = self._b64_to_rl_image(report_data['enhanced_comparison'], 450, 200)
            if img:
                story.append(Paragraph("Enhanced Comparison (Original vs CLAHE)", self.styles['SubHeader']))
                story.append(img)
                story.append(Spacer(1, 6))
        
        # Grad-CAM
        if report_data.get('heatmap'):
            img = self._b64_to_rl_image(report_data['heatmap'], 300, 250)
            if img:
                story.append(Paragraph("Grad-CAM++ Disease Localization", self.styles['SubHeader']))
                story.append(img)
                story.append(Spacer(1, 6))
        
        # Anatomical segmentation
        if report_data.get('segmentation_overlay'):
            img = self._b64_to_rl_image(report_data['segmentation_overlay'], 300, 250)
            if img:
                story.append(Paragraph("Anatomical Segmentation", self.styles['SubHeader']))
                story.append(img)
                story.append(Spacer(1, 6))
        
        # === QUALITY REPORT ===
        qr = report_data.get('quality_report')
        if qr:
            story.append(Paragraph("🤖 Enhancement Agent Quality Report", self.styles['SectionHeader']))
            quality_color = self.SUCCESS if qr['quality'] == 'good' else self.WARNING
            story.append(Paragraph(
                f"Image Quality: <b><font color='{quality_color}'>{qr['quality'].upper()}</font></b>",
                self.styles['BodyText2']
            ))
            if qr.get('issues'):
                story.append(Paragraph(f"Issues: {', '.join(qr['issues'])}", self.styles['BodyText2']))
            if qr.get('actions_applied'):
                story.append(Paragraph(f"Corrections: {', '.join(qr['actions_applied'])}", self.styles['BodyText2']))
            if qr.get('metrics'):
                m = qr['metrics']
                story.append(Paragraph(
                    f"Metrics — Brightness: {m.get('brightness', 'N/A')}, "
                    f"Contrast: {m.get('contrast', 'N/A')}, "
                    f"Noise: {m.get('noise', 'N/A')}, "
                    f"Sharpness: {m.get('sharpness', 'N/A')}",
                    self.styles['SmallGray']
                ))
        
        # === DETECTION RESULTS ===
        detections = report_data.get('detections')
        if detections:
            story.append(Paragraph("🔬 CheXNet Detection Results", self.styles['SectionHeader']))
            det_data = [['Pathology', 'Confidence', 'Level']]
            for d in detections:
                pct = f"{d['score'] * 100:.1f}%"
                level = 'HIGH' if d['score'] > 0.4 else 'MEDIUM' if d['score'] > 0.2 else 'LOW'
                det_data.append([d['label'], pct, level])
            
            det_table = Table(det_data, colWidths=[180, 100, 80])
            det_table.setStyle(TableStyle([
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('BACKGROUND', (0, 0), (-1, 0), self.PRIMARY),
                ('TEXTCOLOR', (0, 0), (-1, 0), white),
                ('GRID', (0, 0), (-1, -1), 0.5, self.LIGHT_GRAY),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [white, HexColor('#f0f4f8')]),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ]))
            story.append(det_table)
        
        # === CTR MEASUREMENT ===
        ctr = report_data.get('ctr')
        if ctr and ctr.get('ctr'):
            story.append(Paragraph("📐 Cardiothoracic Ratio", self.styles['SectionHeader']))
            ctr_color = self.SUCCESS if ctr['ctr'] < 0.5 else self.WARNING if ctr['ctr'] < 0.55 else self.DANGER
            story.append(Paragraph(
                f"CTR = <b><font color='{ctr_color}'>{ctr['ctr']:.3f}</font></b> — "
                f"<font color='{ctr_color}'>{ctr['interpretation']}</font><br/>"
                f"Heart width: {ctr['heart_width']}px | Thorax width: {ctr['thorax_width']}px",
                self.styles['BodyText2']
            ))
        
        # === DIFFERENTIAL DIAGNOSIS ===
        differentials = report_data.get('differentials')
        if differentials:
            story.append(Paragraph("🧬 Differential Diagnosis", self.styles['SectionHeader']))
            diff_data = [['#', 'Diagnosis', 'Probability', 'Based On']]
            for i, d in enumerate(differentials[:8], 1):
                prob_pct = f"{d['probability'] * 100:.1f}%"
                diff_data.append([str(i), d['diagnosis'], prob_pct, d.get('based_on', '')])
            
            diff_table = Table(diff_data, colWidths=[25, 200, 70, 120])
            diff_table.setStyle(TableStyle([
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('BACKGROUND', (0, 0), (-1, 0), HexColor('#6366f1')),
                ('TEXTCOLOR', (0, 0), (-1, 0), white),
                ('GRID', (0, 0), (-1, -1), 0.5, self.LIGHT_GRAY),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [white, HexColor('#f0f4f8')]),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ]))
            story.append(diff_table)
        
        # === CLINICAL DECISION SUPPORT ===
        clinical = report_data.get('clinical_decision')
        if clinical:
            story.append(PageBreak())
            story.append(Paragraph("🏥 Clinical Decision Support", self.styles['SectionHeader']))
            
            # CURB-65
            curb = clinical.get('curb65')
            if curb:
                story.append(Paragraph("CURB-65 Score", self.styles['SubHeader']))
                score_color = self.SUCCESS if curb['score'] <= 1 else self.WARNING if curb['score'] <= 2 else self.DANGER
                story.append(Paragraph(
                    f"Score: <b><font color='{score_color}'>{curb['score']}/{curb['max_score']}</font></b> — "
                    f"{curb['risk_level']}<br/>"
                    f"Recommendation: <b>{curb['recommended_action']}</b>",
                    self.styles['BodyText2']
                ))
                if curb.get('criteria_met'):
                    story.append(Paragraph(
                        "Criteria met: " + ", ".join(curb['criteria_met']),
                        self.styles['SmallGray']
                    ))
            
            # Antibiotics
            abx = clinical.get('antibiotics')
            if abx:
                story.append(Paragraph("💊 Antibiotic Recommendations", self.styles['SubHeader']))
                story.append(Paragraph(
                    f"Setting: {abx.get('setting', 'N/A')}<br/>"
                    f"<b>First-line:</b> {abx.get('first_line', 'N/A')}<br/>"
                    f"<b>Alternative:</b> {abx.get('alternative', 'N/A')}<br/>"
                    f"Guideline: {abx.get('guideline', 'N/A')}",
                    self.styles['BodyText2']
                ))
            
            # Labs
            labs = clinical.get('recommended_labs')
            if labs:
                story.append(Paragraph("🧪 Recommended Laboratory Tests", self.styles['SubHeader']))
                lab_data = [['Test', 'Reason', 'Priority']]
                for lab in labs[:10]:
                    lab_data.append([lab['test'], lab['reason'], lab['priority']])
                
                lab_table = Table(lab_data, colWidths=[140, 220, 50])
                lab_table.setStyle(TableStyle([
                    ('FONTSIZE', (0, 0), (-1, -1), 7),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('BACKGROUND', (0, 0), (-1, 0), HexColor('#059669')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), white),
                    ('GRID', (0, 0), (-1, -1), 0.5, self.LIGHT_GRAY),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [white, HexColor('#f0f4f8')]),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                ]))
                story.append(lab_table)
            
            # Follow-up imaging
            followup = clinical.get('imaging_followup')
            if followup:
                story.append(Paragraph("📋 Imaging Follow-up", self.styles['SubHeader']))
                for f in followup:
                    story.append(Paragraph(
                        f"<b>{f['imaging']}</b> — {f['timeline']}<br/>"
                        f"<i>{f['reason']}</i> (Priority: {f['priority']})",
                        self.styles['BodyText2']
                    ))
                    story.append(Spacer(1, 4))
        
        # === AI DIAGNOSIS ===
        diagnosis = report_data.get('diagnosis')
        if diagnosis:
            story.append(Paragraph("📋 AI Radiological Report", self.styles['SectionHeader']))
            # Clean markdown formatting
            clean_text = diagnosis.replace('**', '<b>').replace('**', '</b>')
            clean_text = clean_text.replace('\n', '<br/>')
            # Truncate if too long for PDF
            if len(clean_text) > 5000:
                clean_text = clean_text[:5000] + '...<br/>[Report truncated]'
            try:
                story.append(Paragraph(clean_text, self.styles['BodyText2']))
            except Exception:
                # Fallback for XML parsing issues
                story.append(Paragraph(diagnosis[:3000].replace('<', '&lt;').replace('>', '&gt;'), self.styles['BodyText2']))
        
        # === DISCLAIMER ===
        story.append(Spacer(1, 20))
        story.append(HRFlowable(width="100%", thickness=1, color=self.DANGER))
        story.append(Paragraph(
            "⚠️ DISCLAIMER: This report is generated by an AI system (CheXNet + LLM) for "
            "preliminary screening purposes ONLY. It is NOT a substitute for professional "
            "radiological interpretation. All findings MUST be verified by a qualified, "
            "board-certified radiologist before any clinical decisions are made. AI-assisted "
            "diagnosis has known limitations including false positives and false negatives. "
            "The treating physician bears full responsibility for patient care decisions.",
            self.styles['Disclaimer']
        ))
        story.append(Spacer(1, 8))
        story.append(Paragraph(
            f"Report ID: RPT-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')} | "
            f"AI System: CheXNet DenseNet-121 + Groq LLama-3.3-70B + Pinecone RAG | "
            f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            self.styles['SmallGray']
        ))
        
        # Build PDF
        doc.build(story)
        
        # Save to file
        pdf_bytes = buffer.getvalue()
        with open(output_path, 'wb') as f:
            f.write(pdf_bytes)
        
        return output_path
    
    def generate_to_base64(self, report_data: Dict[str, Any]) -> str:
        """Generate PDF and return as base64 string for download."""
        buffer = io.BytesIO()
        # Temporary path
        import tempfile
        tmp = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False)
        tmp_path = tmp.name
        tmp.close()
        
        self.generate(report_data, tmp_path)
        
        with open(tmp_path, 'rb') as f:
            pdf_bytes = f.read()
        
        import os
        os.unlink(tmp_path)
        
        return base64.b64encode(pdf_bytes).decode('utf-8')
