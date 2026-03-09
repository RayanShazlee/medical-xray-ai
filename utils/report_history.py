"""
📊 Report History Database — Tier 4 Feature

SQLite-based storage for all analysis reports:
- Store each analysis with patient context, detections, diagnosis
- Search and retrieve past reports
- Track trends over time
- Statistics dashboard data
"""

import sqlite3
import json
import os
import datetime
from typing import Dict, Any, List, Optional


class ReportHistory:
    """SQLite-based report history for medical X-ray analyses."""
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'report_history.db')
        
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.db_path = db_path
        self._init_db()
        print(f"📊 Report History DB initialized at {db_path}")
    
    def _init_db(self):
        """Initialize database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    report_id TEXT UNIQUE NOT NULL,
                    timestamp TEXT NOT NULL,
                    image_filename TEXT,
                    image_path TEXT,
                    patient_age INTEGER,
                    patient_sex TEXT,
                    patient_symptoms TEXT,
                    dicom_metadata TEXT,
                    detections TEXT,
                    primary_finding TEXT,
                    primary_confidence REAL,
                    severity TEXT,
                    diagnosis TEXT,
                    differentials TEXT,
                    clinical_decision TEXT,
                    quality_report TEXT,
                    ctr_value REAL,
                    ctr_interpretation TEXT,
                    heatmap_b64 TEXT,
                    segmentation_b64 TEXT,
                    pdf_path TEXT,
                    language TEXT DEFAULT 'en',
                    notes TEXT
                )
            ''')
            
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_timestamp ON reports(timestamp)
            ''')
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_primary_finding ON reports(primary_finding)
            ''')
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_severity ON reports(severity)
            ''')
    
    def save_report(self, report_data: Dict[str, Any]) -> str:
        """
        Save an analysis report.
        
        Args:
            report_data: Dict with all analysis results
            
        Returns:
            report_id: Unique identifier for the report
        """
        report_id = f"RPT-{datetime.datetime.now().strftime('%Y%m%d%H%M%S%f')}"
        timestamp = datetime.datetime.now().isoformat()
        
        # Extract primary finding
        detections = report_data.get('detections', [])
        primary_finding = detections[0]['label'] if detections else 'No Finding'
        primary_confidence = detections[0]['score'] if detections else 0.0
        
        # Patient context
        patient = report_data.get('patient_context', {})
        
        # CTR
        ctr = report_data.get('ctr', {})
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT INTO reports (
                    report_id, timestamp, image_filename, image_path,
                    patient_age, patient_sex, patient_symptoms,
                    dicom_metadata, detections, primary_finding, primary_confidence,
                    severity, diagnosis, differentials, clinical_decision,
                    quality_report, ctr_value, ctr_interpretation,
                    heatmap_b64, segmentation_b64, pdf_path, language, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                report_id, timestamp,
                report_data.get('image_filename'),
                report_data.get('image_path'),
                patient.get('age'),
                patient.get('sex'),
                patient.get('symptoms'),
                json.dumps(report_data.get('dicom_metadata', {})),
                json.dumps(detections),
                primary_finding,
                primary_confidence,
                report_data.get('severity'),
                report_data.get('diagnosis'),
                json.dumps(report_data.get('differentials', [])),
                json.dumps(report_data.get('clinical_decision', {})),
                json.dumps(report_data.get('quality_report', {})),
                ctr.get('ctr'),
                ctr.get('interpretation'),
                None,  # Don't store large b64 in DB for performance
                None,
                report_data.get('pdf_path'),
                report_data.get('language', 'en'),
                report_data.get('notes')
            ))
        
        return report_id
    
    def get_report(self, report_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a single report by ID."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                'SELECT * FROM reports WHERE report_id = ?', (report_id,)
            ).fetchone()
            
            if row:
                return self._row_to_dict(row)
            return None
    
    def get_recent_reports(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get most recent reports."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                'SELECT id, report_id, timestamp, image_filename, primary_finding, '
                'primary_confidence, severity, ctr_value, ctr_interpretation, patient_age, patient_sex '
                'FROM reports ORDER BY timestamp DESC LIMIT ?', (limit,)
            ).fetchall()
            
            return [dict(row) for row in rows]
    
    def search_reports(self, query: str) -> List[Dict[str, Any]]:
        """Search reports by finding, diagnosis text, or patient info."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute('''
                SELECT id, report_id, timestamp, image_filename, primary_finding,
                primary_confidence, severity, patient_age, patient_sex
                FROM reports 
                WHERE primary_finding LIKE ? 
                   OR diagnosis LIKE ?
                   OR patient_symptoms LIKE ?
                ORDER BY timestamp DESC LIMIT 50
            ''', (f'%{query}%', f'%{query}%', f'%{query}%')).fetchall()
            
            return [dict(row) for row in rows]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get overall statistics for the dashboard."""
        with sqlite3.connect(self.db_path) as conn:
            # Total reports
            total = conn.execute('SELECT COUNT(*) FROM reports').fetchone()[0]
            
            # Finding distribution
            findings = conn.execute('''
                SELECT primary_finding, COUNT(*) as count 
                FROM reports 
                GROUP BY primary_finding 
                ORDER BY count DESC
            ''').fetchall()
            
            # Severity distribution
            severities = conn.execute('''
                SELECT severity, COUNT(*) as count 
                FROM reports 
                WHERE severity IS NOT NULL
                GROUP BY severity
            ''').fetchall()
            
            # Average confidence
            avg_confidence = conn.execute(
                'SELECT AVG(primary_confidence) FROM reports WHERE primary_confidence > 0'
            ).fetchone()[0]
            
            # Reports this week
            week_ago = (datetime.datetime.now() - datetime.timedelta(days=7)).isoformat()
            weekly = conn.execute(
                'SELECT COUNT(*) FROM reports WHERE timestamp > ?', (week_ago,)
            ).fetchone()[0]
            
            # CTR stats
            avg_ctr = conn.execute(
                'SELECT AVG(ctr_value) FROM reports WHERE ctr_value IS NOT NULL'
            ).fetchone()[0]
            
            return {
                'total_reports': total,
                'reports_this_week': weekly,
                'finding_distribution': [{'finding': f[0], 'count': f[1]} for f in findings],
                'severity_distribution': [{'severity': s[0], 'count': s[1]} for s in severities],
                'average_confidence': round(avg_confidence, 3) if avg_confidence else 0,
                'average_ctr': round(avg_ctr, 3) if avg_ctr else None
            }
    
    def delete_report(self, report_id: str) -> bool:
        """Delete a report."""
        with sqlite3.connect(self.db_path) as conn:
            result = conn.execute('DELETE FROM reports WHERE report_id = ?', (report_id,))
            return result.rowcount > 0
    
    def _row_to_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        """Convert a database row to a dict with parsed JSON fields."""
        d = dict(row)
        for key in ['dicom_metadata', 'detections', 'differentials', 
                     'clinical_decision', 'quality_report']:
            if d.get(key):
                try:
                    d[key] = json.loads(d[key])
                except (json.JSONDecodeError, TypeError):
                    pass
        return d
