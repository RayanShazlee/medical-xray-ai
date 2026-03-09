"""
🏥 Clinical Decision Support Agent — Tier 2 Feature

Provides evidence-based clinical decision support:
- CURB-65 / PSI scoring for pneumonia severity & admission criteria
- Antibiotic recommendations (CAP vs HAP guidelines)
- Differential diagnosis engine with Bayesian ranking
- Follow-up timeline recommendations
- Lab work suggestions based on findings
"""

from typing import Dict, Any, List, Optional, Tuple
import json


class ClinicalDecisionAgent:
    """
    Evidence-based clinical decision support for chest X-ray findings.
    
    Uses established clinical guidelines:
    - CURB-65 (BTS guidelines for pneumonia)
    - ATS/IDSA CAP guidelines for antibiotic selection
    - ACR Appropriateness Criteria for imaging follow-up
    """
    
    # ==================== DIFFERENTIAL DIAGNOSIS DATABASE ====================
    
    DIFFERENTIAL_DATABASE = {
        "Consolidation": {
            "differentials": [
                {"diagnosis": "Bacterial pneumonia (typical)", "probability": 0.55,
                 "key_features": ["lobar distribution", "air bronchograms", "fever", "productive cough"],
                 "supporting": ["WBC elevation", "CRP >100", "procalcitonin >0.5"]},
                {"diagnosis": "Pulmonary edema", "probability": 0.15,
                 "key_features": ["bilateral", "perihilar", "cardiomegaly", "Kerley B lines"],
                 "supporting": ["BNP elevation", "bilateral effusions", "fluid overload history"]},
                {"diagnosis": "Pulmonary hemorrhage", "probability": 0.08,
                 "key_features": ["rapid onset", "hemoptysis", "bilateral GGO"],
                 "supporting": ["dropping hemoglobin", "anticoagulation", "vasculitis"]},
                {"diagnosis": "Organizing pneumonia (COP)", "probability": 0.07,
                 "key_features": ["peripheral", "migratory", "subacute course"],
                 "supporting": ["steroid responsive", "no organism isolated"]},
                {"diagnosis": "Lung cancer (post-obstructive)", "probability": 0.05,
                 "key_features": ["persistent", "hilar mass", "atelectasis"],
                 "supporting": ["smoking history", "weight loss", "hemoptysis"]},
                {"diagnosis": "Aspiration pneumonitis", "probability": 0.10,
                 "key_features": ["dependent segments", "right lower lobe", "altered consciousness"],
                 "supporting": ["dysphagia", "recent anesthesia", "GERD"]}
            ]
        },
        "Infiltration": {
            "differentials": [
                {"diagnosis": "Viral pneumonia", "probability": 0.35,
                 "key_features": ["bilateral interstitial", "GGO", "peribronchial thickening"],
                 "supporting": ["viral prodrome", "normal WBC", "low procalcitonin"]},
                {"diagnosis": "Atypical pneumonia", "probability": 0.25,
                 "key_features": ["patchy bilateral", "interstitial pattern", "dry cough"],
                 "supporting": ["young patient", "community exposure", "Mycoplasma IgM+"]},
                {"diagnosis": "Pulmonary edema (interstitial)", "probability": 0.15,
                 "key_features": ["bilateral symmetric", "Kerley lines", "peribronchial cuffing"],
                 "supporting": ["cardiac history", "BNP elevation", "orthopnea"]},
                {"diagnosis": "Drug-induced pneumonitis", "probability": 0.05,
                 "key_features": ["bilateral GGO", "temporal drug relationship"],
                 "supporting": ["methotrexate", "amiodarone", "nitrofurantoin use"]},
                {"diagnosis": "Hypersensitivity pneumonitis", "probability": 0.05,
                 "key_features": ["upper/mid zone", "ground glass", "environmental exposure"],
                 "supporting": ["bird exposure", "moldy hay", "hot tub"]}
            ]
        },
        "Effusion": {
            "differentials": [
                {"diagnosis": "Parapneumonic effusion", "probability": 0.30,
                 "key_features": ["unilateral", "adjacent consolidation", "fever"],
                 "supporting": ["elevated WBC", "exudative on Light's criteria"]},
                {"diagnosis": "Heart failure", "probability": 0.25,
                 "key_features": ["bilateral", "cardiomegaly", "Kerley B lines"],
                 "supporting": ["BNP >400", "transudate on Light's criteria"]},
                {"diagnosis": "Malignant effusion", "probability": 0.15,
                 "key_features": ["large", "rapidly reaccumulating", "nodular pleural thickening"],
                 "supporting": ["bloody fluid", "positive cytology", "weight loss"]},
                {"diagnosis": "Empyema", "probability": 0.10,
                 "key_features": ["loculated", "split pleura sign", "high fever"],
                 "supporting": ["pH <7.2", "glucose <40", "LDH >1000"]},
                {"diagnosis": "Pulmonary embolism", "probability": 0.08,
                 "key_features": ["unilateral small", "Hampton's hump", "pleuritic pain"],
                 "supporting": ["D-dimer elevated", "Wells score high", "DVT"]},
                {"diagnosis": "Hepatic hydrothorax", "probability": 0.05,
                 "key_features": ["right-sided", "ascites present"],
                 "supporting": ["cirrhosis", "transudate"]}
            ]
        },
        "Pneumothorax": {
            "differentials": [
                {"diagnosis": "Primary spontaneous pneumothorax", "probability": 0.40,
                 "key_features": ["young tall male", "apical blebs", "sudden onset"],
                 "supporting": ["no underlying lung disease", "thin body habitus"]},
                {"diagnosis": "Secondary spontaneous pneumothorax", "probability": 0.30,
                 "key_features": ["COPD patient", "bullae", "emphysema"],
                 "supporting": ["smoking history", "known lung disease"]},
                {"diagnosis": "Traumatic pneumothorax", "probability": 0.15,
                 "key_features": ["rib fractures", "trauma history"],
                 "supporting": ["subcutaneous emphysema", "hemothorax"]},
                {"diagnosis": "Iatrogenic pneumothorax", "probability": 0.10,
                 "key_features": ["post-procedure", "central line", "thoracentesis"],
                 "supporting": ["recent procedure documented"]},
                {"diagnosis": "Tension pneumothorax", "probability": 0.05,
                 "key_features": ["mediastinal shift", "hemodynamic compromise"],
                 "supporting": ["tracheal deviation", "hypotension", "JVD"]}
            ]
        },
        "Cardiomegaly": {
            "differentials": [
                {"diagnosis": "Dilated cardiomyopathy", "probability": 0.30,
                 "key_features": ["global enlargement", "pulmonary congestion"],
                 "supporting": ["reduced EF", "BNP elevation"]},
                {"diagnosis": "Pericardial effusion", "probability": 0.20,
                 "key_features": ["water bottle sign", "enlarged silhouette"],
                 "supporting": ["low voltage ECG", "echo confirmation"]},
                {"diagnosis": "Valvular heart disease", "probability": 0.20,
                 "key_features": ["specific chamber enlargement", "valve calcification"],
                 "supporting": ["murmur on auscultation"]},
                {"diagnosis": "Hypertensive heart disease", "probability": 0.15,
                 "key_features": ["LVH pattern", "aortic unfolding"],
                 "supporting": ["hypertension history", "LVH on ECG"]},
                {"diagnosis": "Cor pulmonale", "probability": 0.10,
                 "key_features": ["right heart enlargement", "PA prominence"],
                 "supporting": ["COPD", "pulmonary hypertension"]}
            ]
        },
        "Atelectasis": {
            "differentials": [
                {"diagnosis": "Mucus plugging", "probability": 0.35,
                 "key_features": ["post-operative", "segmental collapse"],
                 "supporting": ["recent surgery", "poor cough effort"]},
                {"diagnosis": "Endobronchial lesion", "probability": 0.20,
                 "key_features": ["persistent", "lobar collapse", "hilar mass"],
                 "supporting": ["smoking history", "hemoptysis"]},
                {"diagnosis": "Compressive atelectasis", "probability": 0.25,
                 "key_features": ["adjacent to effusion", "passive collapse"],
                 "supporting": ["large effusion present"]},
                {"diagnosis": "Cicatricial (scarring)", "probability": 0.15,
                 "key_features": ["chronic", "volume loss", "traction bronchiectasis"],
                 "supporting": ["prior TB", "radiation", "fibrosis"]}
            ]
        },
        "Nodule": {
            "differentials": [
                {"diagnosis": "Lung cancer", "probability": 0.25,
                 "key_features": ["spiculated margins", "upper lobe", ">8mm"],
                 "supporting": ["smoking history", "growing on serial imaging"]},
                {"diagnosis": "Granuloma (benite)", "probability": 0.30,
                 "key_features": ["calcified", "well-defined", "stable"],
                 "supporting": ["geographic TB/histo endemic", "no growth"]},
                {"diagnosis": "Metastasis", "probability": 0.15,
                 "key_features": ["multiple", "round", "peripheral"],
                 "supporting": ["known primary malignancy"]},
                {"diagnosis": "Hamartoma", "probability": 0.10,
                 "key_features": ["popcorn calcification", "well-defined"],
                 "supporting": ["asymptomatic", "fat density on CT"]},
                {"diagnosis": "Infectious (TB/fungal)", "probability": 0.15,
                 "key_features": ["upper lobe", "cavitation possible"],
                 "supporting": ["TB exposure", "immunocompromised"]}
            ]
        },
        "Mass": {
            "differentials": [
                {"diagnosis": "Primary lung cancer", "probability": 0.45,
                 "key_features": ["spiculated", ">3cm", "hilar/mediastinal LN"],
                 "supporting": ["smoking >20 pack-years", "weight loss"]},
                {"diagnosis": "Metastatic disease", "probability": 0.20,
                 "key_features": ["multiple masses", "round well-defined"],
                 "supporting": ["known extrapulmonary malignancy"]},
                {"diagnosis": "Lung abscess", "probability": 0.15,
                 "key_features": ["air-fluid level", "thick irregular wall"],
                 "supporting": ["fever", "dental disease", "aspiration risk"]},
                {"diagnosis": "Fungal infection (aspergilloma)", "probability": 0.10,
                 "key_features": ["intracavitary mass", "air crescent sign"],
                 "supporting": ["pre-existing cavity", "immunocompromised"]}
            ]
        },
        "Pneumonia": {
            "differentials": [
                {"diagnosis": "Community-acquired bacterial pneumonia", "probability": 0.45,
                 "key_features": ["lobar consolidation", "air bronchograms", "fever", "cough"],
                 "supporting": ["WBC >12k", "CRP elevated", "procalcitonin >0.25"]},
                {"diagnosis": "Viral pneumonia", "probability": 0.20,
                 "key_features": ["bilateral interstitial", "GGO", "peribronchial"],
                 "supporting": ["viral prodrome", "normal/low WBC"]},
                {"diagnosis": "Aspiration pneumonia", "probability": 0.15,
                 "key_features": ["dependent segments", "RLL", "altered mental status"],
                 "supporting": ["dysphagia", "alcoholism", "seizures"]},
                {"diagnosis": "Mycoplasma pneumonia", "probability": 0.10,
                 "key_features": ["patchy", "peribronchial", "young adult"],
                 "supporting": ["walking pneumonia", "low-grade fever"]},
                {"diagnosis": "TB", "probability": 0.05,
                 "key_features": ["upper lobe cavitation", "miliary pattern"],
                 "supporting": ["TB exposure", "immigration", "HIV"]},
                {"diagnosis": "PCP (Pneumocystis)", "probability": 0.03,
                 "key_features": ["bilateral perihilar GGO", "apical sparing"],
                 "supporting": ["HIV/AIDS", "CD4 <200", "immunosuppression"]}
            ]
        },
        "Fibrosis": {
            "differentials": [
                {"diagnosis": "Idiopathic pulmonary fibrosis (IPF)", "probability": 0.35,
                 "key_features": ["basilar predominant", "honeycombing", "traction bronchiectasis"],
                 "supporting": ["UIP pattern on CT", "progressive dyspnea"]},
                {"diagnosis": "Connective tissue disease-related ILD", "probability": 0.20,
                 "key_features": ["bilateral fibrosis", "joint symptoms"],
                 "supporting": ["RA", "scleroderma", "dermatomyositis"]},
                {"diagnosis": "Chronic hypersensitivity pneumonitis", "probability": 0.15,
                 "key_features": ["upper/mid zone fibrosis", "mosaic attenuation"],
                 "supporting": ["environmental exposure history"]},
                {"diagnosis": "Radiation fibrosis", "probability": 0.15,
                 "key_features": ["geometric distribution", "matches radiation port"],
                 "supporting": ["prior radiation therapy"]},
                {"diagnosis": "Asbestosis", "probability": 0.10,
                 "key_features": ["bilateral basilar", "pleural plaques"],
                 "supporting": ["occupational asbestos exposure"]}
            ]
        }
    }

    # ==================== CURB-65 SCORING ====================
    
    CURB65_CRITERIA = {
        'C': 'Confusion (new onset)',
        'U': 'Urea (BUN) > 19 mg/dL (7 mmol/L)',
        'R': 'Respiratory rate ≥ 30/min',
        'B': 'Blood pressure: SBP < 90 or DBP ≤ 60 mmHg',
        '65': 'Age ≥ 65 years'
    }
    
    CURB65_MANAGEMENT = {
        0: {"risk": "Low (0.6% mortality)", "action": "Consider outpatient treatment", "class": "low"},
        1: {"risk": "Low (2.7% mortality)", "action": "Consider outpatient or short inpatient stay", "class": "low"},
        2: {"risk": "Moderate (6.8% mortality)", "action": "Hospital admission — supervised treatment", "class": "medium"},
        3: {"risk": "High (14.0% mortality)", "action": "Hospital admission — consider ICU", "class": "high"},
        4: {"risk": "Very high (27.8% mortality)", "action": "ICU admission — urgent", "class": "critical"},
        5: {"risk": "Very high (57.0% mortality)", "action": "ICU admission — critical care", "class": "critical"}
    }
    
    # ==================== ANTIBIOTIC GUIDELINES ====================
    
    ANTIBIOTIC_GUIDELINES = {
        "CAP_outpatient_healthy": {
            "setting": "Outpatient, no comorbidities",
            "first_line": "Amoxicillin 1g PO TID × 5-7 days",
            "alternative": "Doxycycline 100mg PO BID × 5 days",
            "if_atypical": "Azithromycin 500mg day 1, then 250mg × 4 days",
            "guideline": "ATS/IDSA 2019"
        },
        "CAP_outpatient_comorbid": {
            "setting": "Outpatient with comorbidities (COPD, DM, heart/liver/renal disease)",
            "first_line": "Amoxicillin/Clavulanate 875/125mg PO BID + Azithromycin (or Doxycycline)",
            "alternative": "Respiratory fluoroquinolone: Levofloxacin 750mg PO daily × 5 days",
            "guideline": "ATS/IDSA 2019"
        },
        "CAP_inpatient_nonsevere": {
            "setting": "Inpatient, non-severe (ward)",
            "first_line": "Ceftriaxone 1-2g IV daily + Azithromycin 500mg IV/PO daily",
            "alternative": "Levofloxacin 750mg IV daily (monotherapy)",
            "guideline": "ATS/IDSA 2019"
        },
        "CAP_inpatient_severe": {
            "setting": "Inpatient, severe (ICU)",
            "first_line": "Ceftriaxone 2g IV daily + Azithromycin 500mg IV daily",
            "alternative": "Ceftriaxone 2g IV + Levofloxacin 750mg IV",
            "if_MRSA_risk": "Add Vancomycin 15-20mg/kg IV q8-12h or Linezolid 600mg IV q12h",
            "if_Pseudomonas_risk": "Piperacillin/Tazobactam 4.5g IV q6h or Meropenem 1g IV q8h",
            "guideline": "ATS/IDSA 2019"
        },
        "HAP_VAP": {
            "setting": "Hospital-acquired / Ventilator-associated pneumonia",
            "first_line": "Piperacillin/Tazobactam 4.5g IV q6h",
            "alternative": "Meropenem 1g IV q8h or Cefepime 2g IV q8h",
            "if_MRSA_risk": "Add Vancomycin or Linezolid",
            "guideline": "ATS/IDSA 2016 HAP/VAP"
        },
        "aspiration": {
            "setting": "Aspiration pneumonia",
            "first_line": "Ampicillin/Sulbactam 3g IV q6h",
            "alternative": "Clindamycin 600mg IV q8h + Ceftriaxone",
            "guideline": "Expert consensus"
        }
    }
    
    def __init__(self):
        pass
    
    # ==================== DIFFERENTIAL DIAGNOSIS ====================
    
    def get_differentials(self, detected_pathologies: List[Dict], 
                          patient_context: Optional[Dict] = None) -> List[Dict]:
        """
        Generate ranked differential diagnosis based on detected pathologies.
        
        Args:
            detected_pathologies: List of {"label": str, "score": float}
            patient_context: Optional dict with age, sex, symptoms, history
            
        Returns:
            List of differential diagnoses with adjusted probabilities
        """
        all_differentials = []
        
        for pathology in detected_pathologies:
            label = pathology['label']
            confidence = pathology['score']
            
            if label in self.DIFFERENTIAL_DATABASE:
                for diff in self.DIFFERENTIAL_DATABASE[label]['differentials']:
                    # Adjust probability based on AI confidence
                    adjusted_prob = diff['probability'] * confidence
                    
                    # Adjust based on patient context
                    if patient_context:
                        adjusted_prob = self._adjust_for_context(
                            diff, adjusted_prob, patient_context
                        )
                    
                    all_differentials.append({
                        'diagnosis': diff['diagnosis'],
                        'probability': round(adjusted_prob, 3),
                        'based_on': label,
                        'ai_confidence': round(confidence, 3),
                        'key_features': diff['key_features'],
                        'supporting_evidence': diff['supporting']
                    })
        
        # Merge duplicates (same diagnosis from different pathologies)
        merged = {}
        for d in all_differentials:
            key = d['diagnosis']
            if key in merged:
                merged[key]['probability'] = max(merged[key]['probability'], d['probability'])
                merged[key]['based_on'] = f"{merged[key]['based_on']}, {d['based_on']}"
            else:
                merged[key] = d
        
        # Sort by probability
        result = sorted(merged.values(), key=lambda x: x['probability'], reverse=True)
        return result[:10]  # Top 10
    
    def _adjust_for_context(self, diff: Dict, base_prob: float, 
                            context: Dict) -> float:
        """Adjust differential probability based on patient context."""
        prob = base_prob
        
        age = context.get('age')
        sex = context.get('sex')
        smoking = context.get('smoking', False)
        immunocompromised = context.get('immunocompromised', False)
        
        diagnosis = diff['diagnosis'].lower()
        
        # Age-based adjustments
        if age:
            age = int(age)
            if age < 40 and 'cancer' in diagnosis:
                prob *= 0.3  # Cancer less likely in young
            elif age > 60 and 'cancer' in diagnosis:
                prob *= 1.5  # Cancer more likely in elderly
            if age < 30 and 'spontaneous pneumothorax' in diagnosis:
                prob *= 1.5  # More common in young tall males
            if age > 65 and 'heart failure' in diagnosis:
                prob *= 1.4
        
        # Smoking adjustments
        if smoking:
            if 'cancer' in diagnosis or 'copd' in diagnosis or 'emphysema' in diagnosis:
                prob *= 2.0
        
        # Immunocompromised adjustments
        if immunocompromised:
            if 'pcp' in diagnosis or 'fungal' in diagnosis or 'tb' in diagnosis:
                prob *= 2.5
            if 'viral' in diagnosis:
                prob *= 1.5
        
        return min(prob, 0.95)  # Cap at 95%
    
    # ==================== CURB-65 SCORING ====================
    
    def calculate_curb65(self, patient_data: Dict) -> Dict:
        """
        Calculate CURB-65 score for pneumonia severity.
        
        Args:
            patient_data: Dict with keys:
                confusion: bool
                bun: float (mg/dL) or urea: float (mmol/L)
                respiratory_rate: int
                sbp: int (systolic BP)
                dbp: int (diastolic BP)
                age: int
        """
        score = 0
        criteria_met = []
        
        if patient_data.get('confusion', False):
            score += 1
            criteria_met.append('C — Confusion')
        
        bun = patient_data.get('bun')
        urea = patient_data.get('urea')
        if bun and bun > 19:
            score += 1
            criteria_met.append(f'U — BUN {bun} mg/dL (>19)')
        elif urea and urea > 7:
            score += 1
            criteria_met.append(f'U — Urea {urea} mmol/L (>7)')
        
        rr = patient_data.get('respiratory_rate')
        if rr and rr >= 30:
            score += 1
            criteria_met.append(f'R — RR {rr}/min (≥30)')
        
        sbp = patient_data.get('sbp')
        dbp = patient_data.get('dbp')
        if (sbp and sbp < 90) or (dbp and dbp <= 60):
            score += 1
            criteria_met.append(f'B — BP {sbp}/{dbp} mmHg')
        
        age = patient_data.get('age')
        if age and age >= 65:
            score += 1
            criteria_met.append(f'65 — Age {age} (≥65)')
        
        management = self.CURB65_MANAGEMENT.get(score, self.CURB65_MANAGEMENT[5])
        
        return {
            'score': score,
            'max_score': 5,
            'criteria_met': criteria_met,
            'risk_level': management['risk'],
            'recommended_action': management['action'],
            'severity_class': management['class']
        }
    
    # ==================== ANTIBIOTIC RECOMMENDATIONS ====================
    
    def recommend_antibiotics(self, severity: str, 
                              patient_context: Optional[Dict] = None) -> Dict:
        """
        Recommend antibiotics based on pneumonia severity and patient context.
        
        Args:
            severity: "mild", "moderate", "severe", "critical"
            patient_context: Optional dict with comorbidities, allergies, etc.
        """
        has_comorbidities = False
        if patient_context:
            has_comorbidities = patient_context.get('comorbidities', False)
        
        if severity in ['mild']:
            if has_comorbidities:
                key = 'CAP_outpatient_comorbid'
            else:
                key = 'CAP_outpatient_healthy'
        elif severity in ['moderate']:
            key = 'CAP_inpatient_nonsevere'
        elif severity in ['severe', 'critical']:
            key = 'CAP_inpatient_severe'
        else:
            key = 'CAP_outpatient_healthy'
        
        guideline = self.ANTIBIOTIC_GUIDELINES[key].copy()
        
        # Check for special considerations
        if patient_context:
            if patient_context.get('aspiration_risk'):
                guideline = self.ANTIBIOTIC_GUIDELINES['aspiration'].copy()
            if patient_context.get('hospital_acquired'):
                guideline = self.ANTIBIOTIC_GUIDELINES['HAP_VAP'].copy()
            if patient_context.get('penicillin_allergy'):
                guideline['allergy_note'] = "⚠️ Penicillin allergy: use respiratory fluoroquinolone (Levofloxacin) or Azithromycin"
        
        return guideline
    
    # ==================== LAB RECOMMENDATIONS ====================
    
    def recommend_labs(self, detected_pathologies: List[Dict]) -> List[Dict]:
        """Recommend laboratory tests based on detected pathologies."""
        labs = []
        pathology_names = [p['label'] for p in detected_pathologies]
        
        # Always recommend for any significant finding
        labs.append({"test": "CBC with differential", "reason": "Assess WBC, evaluate for infection/inflammation", "priority": "STAT"})
        labs.append({"test": "CRP (C-reactive protein)", "reason": "Inflammation marker", "priority": "STAT"})
        
        if any(p in pathology_names for p in ['Pneumonia', 'Consolidation', 'Infiltration']):
            labs.extend([
                {"test": "Procalcitonin", "reason": "Distinguish bacterial vs viral infection (>0.5 = bacterial likely)", "priority": "STAT"},
                {"test": "Blood cultures × 2", "reason": "Identify causative organism before antibiotics", "priority": "STAT"},
                {"test": "Sputum culture + Gram stain", "reason": "Direct organism identification", "priority": "Urgent"},
                {"test": "Urinary Legionella antigen", "reason": "Rule out Legionella pneumophila", "priority": "Routine"},
                {"test": "Urinary Pneumococcal antigen", "reason": "Rapid S. pneumoniae detection", "priority": "Routine"},
                {"test": "BMP (electrolytes, BUN, creatinine)", "reason": "CURB-65 scoring (BUN) + renal function", "priority": "STAT"},
                {"test": "Lactate", "reason": "Assess for sepsis (>2 mmol/L concerning)", "priority": "STAT"},
                {"test": "ABG/VBG", "reason": "Oxygenation and ventilation status", "priority": "STAT"}
            ])
        
        if 'Effusion' in pathology_names:
            labs.extend([
                {"test": "Pleural fluid analysis (pH, protein, LDH, glucose, cell count)",
                 "reason": "Light's criteria: exudate vs transudate", "priority": "Urgent"},
                {"test": "Pleural fluid culture + Gram stain", "reason": "Rule out empyema", "priority": "Urgent"},
                {"test": "Pleural fluid cytology", "reason": "Rule out malignant effusion", "priority": "Routine"}
            ])
        
        if 'Cardiomegaly' in pathology_names:
            labs.extend([
                {"test": "BNP / NT-proBNP", "reason": "Heart failure assessment", "priority": "STAT"},
                {"test": "Troponin I/T", "reason": "Rule out myocardial injury", "priority": "STAT"},
                {"test": "ECG (12-lead)", "reason": "Arrhythmia, ischemia, chamber enlargement", "priority": "STAT"},
                {"test": "Echocardiogram", "reason": "EF, valvular function, pericardial effusion", "priority": "Urgent"}
            ])
        
        if any(p in pathology_names for p in ['Nodule', 'Mass']):
            labs.extend([
                {"test": "CT Chest with contrast", "reason": "Characterize nodule/mass, staging", "priority": "Urgent"},
                {"test": "Tumor markers (CEA, AFP, CA-125)", "reason": "Malignancy screening", "priority": "Routine"},
                {"test": "PET-CT", "reason": "Metabolic activity assessment if mass >8mm", "priority": "Semi-urgent"}
            ])
        
        # Deduplicate
        seen = set()
        unique_labs = []
        for lab in labs:
            if lab['test'] not in seen:
                seen.add(lab['test'])
                unique_labs.append(lab)
        
        return unique_labs
    
    # ==================== IMAGING FOLLOW-UP ====================
    
    def recommend_followup(self, detected_pathologies: List[Dict], 
                           severity: str) -> List[Dict]:
        """Recommend follow-up imaging based on findings."""
        recommendations = []
        pathology_names = [p['label'] for p in detected_pathologies]
        
        if any(p in pathology_names for p in ['Pneumonia', 'Consolidation']):
            recommendations.append({
                "imaging": "Follow-up CXR",
                "timeline": "6-8 weeks post-treatment",
                "reason": "Confirm resolution. Persistent opacity → CT to rule out underlying mass.",
                "priority": "Routine"
            })
        
        if 'Effusion' in pathology_names:
            recommendations.append({
                "imaging": "Ultrasound-guided thoracentesis",
                "timeline": "Within 24 hours if clinically significant",
                "reason": "Characterize fluid, rule out empyema",
                "priority": "Urgent"
            })
            recommendations.append({
                "imaging": "Lateral decubitus CXR",
                "timeline": "Same day",
                "reason": "Confirm mobile effusion vs loculated",
                "priority": "Urgent"
            })
        
        if any(p in pathology_names for p in ['Nodule', 'Mass']):
            recommendations.append({
                "imaging": "CT Chest (thin-section)",
                "timeline": "Within 1 week",
                "reason": "Characterize size, morphology, calcification pattern",
                "priority": "Urgent"
            })
            recommendations.append({
                "imaging": "PET-CT",
                "timeline": "If nodule >8mm and indeterminate on CT",
                "reason": "Assess metabolic activity (SUV)",
                "priority": "Semi-urgent"
            })
        
        if 'Pneumothorax' in pathology_names:
            recommendations.append({
                "imaging": "Repeat CXR",
                "timeline": "4-6 hours post-intervention",
                "reason": "Confirm resolution after chest tube/aspiration",
                "priority": "STAT"
            })
        
        if severity in ['severe', 'critical']:
            recommendations.append({
                "imaging": "CT Chest with IV contrast",
                "timeline": "Within 24 hours",
                "reason": "Detailed assessment of severe disease, complications, alternative diagnosis",
                "priority": "Urgent"
            })
        
        if 'Cardiomegaly' in pathology_names:
            recommendations.append({
                "imaging": "Echocardiogram (TTE)",
                "timeline": "Within 48 hours",
                "reason": "Assess chamber sizes, EF, valvular function, pericardial effusion",
                "priority": "Urgent"
            })
        
        return recommendations
    
    # ==================== COMPREHENSIVE CLINICAL REPORT ====================
    
    def generate_clinical_decision(self, detected_pathologies: List[Dict],
                                    severity: str,
                                    patient_context: Optional[Dict] = None) -> Dict:
        """
        Generate comprehensive clinical decision support output.
        
        Returns complete package: differentials, scoring, antibiotics, labs, follow-up.
        """
        result = {
            'differentials': self.get_differentials(detected_pathologies, patient_context),
            'recommended_labs': self.recommend_labs(detected_pathologies),
            'imaging_followup': self.recommend_followup(detected_pathologies, severity),
        }
        
        # Add CURB-65 if pneumonia is detected and patient data available
        pneumonia_detected = any(
            p['label'] in ['Pneumonia', 'Consolidation', 'Infiltration']
            for p in detected_pathologies
        )
        
        if pneumonia_detected and patient_context:
            result['curb65'] = self.calculate_curb65(patient_context)
        
        # Add antibiotic recommendations if infection detected
        if pneumonia_detected:
            result['antibiotics'] = self.recommend_antibiotics(severity, patient_context)
        
        return result
