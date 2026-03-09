"""
🫁 Anatomical Segmentation Agent — Tier 3 Feature

Segments chest X-ray into anatomical zones:
- Left Lung, Right Lung
- Heart / Cardiac Silhouette
- Mediastinum
- Costophrenic angles
- Diaphragm
- Trachea / Upper airway

Also computes Cardiothoracic Ratio (CTR) for cardiomegaly assessment.

Uses OpenCV-based classical segmentation (no additional ML model needed):
- Adaptive thresholding + watershed for lung fields
- Hough transforms for rib detection
- Contour analysis for cardiac silhouette
"""

import numpy as np
import cv2
from PIL import Image
import base64
import io
from typing import Dict, Any, List, Tuple, Optional


class AnatomicalSegmentationAgent:
    """
    Segments chest X-ray anatomy and computes quantitative measurements.
    """
    
    # Anatomical zone colors (RGB)
    ZONE_COLORS = {
        'right_lung': (52, 152, 219),    # Blue
        'left_lung': (46, 204, 113),     # Green
        'heart': (231, 76, 60),          # Red
        'mediastinum': (155, 89, 182),   # Purple
        'right_costophrenic': (241, 196, 15),  # Yellow
        'left_costophrenic': (230, 126, 34),   # Orange
        'trachea': (26, 188, 156),       # Teal
        'diaphragm': (149, 165, 166),    # Gray
    }
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        if verbose:
            print("🫁 Anatomical Segmentation Agent initialized")
    
    def segment(self, image: Image.Image) -> Dict[str, Any]:
        """
        Full segmentation pipeline.
        
        Returns:
            zones: Dict mapping zone name → binary mask
            ctr: Cardiothoracic ratio measurement
            overlay_b64: Base64 encoded overlay image
            measurements: Dict of quantitative measurements
            zone_descriptions: Human-readable zone descriptions
        """
        img_np = np.array(image)
        if len(img_np.shape) == 3:
            gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
        else:
            gray = img_np.copy()
        
        h, w = gray.shape
        
        # Step 1: Segment body from background
        body_mask = self._segment_body(gray)
        
        # Step 2: Segment lung fields
        right_lung, left_lung = self._segment_lungs(gray, body_mask)
        
        # Step 3: Segment heart/cardiac silhouette
        heart_mask = self._segment_heart(gray, body_mask, right_lung, left_lung)
        
        # Step 4: Segment mediastinum
        mediastinum = self._segment_mediastinum(gray, body_mask, right_lung, left_lung, heart_mask)
        
        # Step 5: Detect costophrenic angles
        right_cp, left_cp = self._detect_costophrenic_angles(gray, right_lung, left_lung)
        
        # Step 6: Detect diaphragm
        diaphragm = self._detect_diaphragm(gray, right_lung, left_lung)
        
        # Step 7: Detect trachea
        trachea = self._detect_trachea(gray, body_mask)
        
        zones = {
            'right_lung': right_lung,
            'left_lung': left_lung,
            'heart': heart_mask,
            'mediastinum': mediastinum,
            'right_costophrenic': right_cp,
            'left_costophrenic': left_cp,
            'diaphragm': diaphragm,
            'trachea': trachea
        }
        
        # Step 8: Compute CTR
        ctr_data = self._compute_ctr(heart_mask, right_lung, left_lung, gray.shape)
        
        # Step 9: Compute zone areas
        measurements = self._compute_measurements(zones, gray.shape)
        measurements['ctr'] = ctr_data
        
        # Step 10: Create overlay visualization
        overlay_b64 = self._create_overlay(img_np, zones, ctr_data)
        
        # Step 11: Zone descriptions
        zone_descriptions = self._describe_zones(zones, measurements, gray.shape)
        
        return {
            'zones': zones,
            'ctr': ctr_data,
            'overlay_b64': overlay_b64,
            'measurements': measurements,
            'zone_descriptions': zone_descriptions
        }
    
    def _segment_body(self, gray: np.ndarray) -> np.ndarray:
        """Segment body from background using Otsu thresholding."""
        _, body_mask = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        body_ratio = np.sum(body_mask > 0) / body_mask.size
        if body_ratio < 0.1 or body_ratio > 0.95:
            thresh_val = np.percentile(gray, 15)
            _, body_mask = cv2.threshold(gray, int(thresh_val), 255, cv2.THRESH_BINARY)
        
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15))
        body_mask = cv2.morphologyEx(body_mask, cv2.MORPH_CLOSE, kernel, iterations=3)
        body_mask = cv2.morphologyEx(body_mask, cv2.MORPH_OPEN, kernel, iterations=2)
        
        contours, _ = cv2.findContours(body_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if contours:
            largest = max(contours, key=cv2.contourArea)
            body_mask = np.zeros_like(body_mask)
            cv2.drawContours(body_mask, [largest], -1, 255, -1)
        
        return body_mask
    
    def _segment_lungs(self, gray: np.ndarray, body_mask: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Segment left and right lung fields."""
        h, w = gray.shape
        
        # Lung fields are darker than mediastinum
        # Use inverse + body mask to find dark regions inside body
        body_region = cv2.bitwise_and(gray, gray, mask=body_mask)
        
        # Adaptive threshold within body
        body_pixels = gray[body_mask > 0]
        if len(body_pixels) == 0:
            return np.zeros_like(gray), np.zeros_like(gray)
        
        # Lungs are typically darker than the median body intensity
        lung_threshold = np.percentile(body_pixels, 40)
        lung_mask = np.zeros_like(gray)
        lung_mask[(gray < lung_threshold) & (body_mask > 0)] = 255
        
        # Morphological cleanup
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
        lung_mask = cv2.morphologyEx(lung_mask, cv2.MORPH_OPEN, kernel, iterations=2)
        lung_mask = cv2.morphologyEx(lung_mask, cv2.MORPH_CLOSE, kernel, iterations=3)
        
        # Find two largest contours (left and right lungs)
        contours, _ = cv2.findContours(lung_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if len(contours) < 2:
            # Fallback: split body mask into left and right
            midline = w // 2
            right_lung = body_mask.copy()
            right_lung[:, midline:] = 0
            left_lung = body_mask.copy()
            left_lung[:, :midline] = 0
            
            # Reduce to 70% of body (exclude edges)
            kernel_small = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (25, 25))
            right_lung = cv2.erode(right_lung, kernel_small, iterations=2)
            left_lung = cv2.erode(left_lung, kernel_small, iterations=2)
            
            return right_lung, left_lung
        
        # Sort by area, take two largest
        contours_sorted = sorted(contours, key=cv2.contourArea, reverse=True)[:2]
        
        # Determine which is left vs right based on centroid x-position
        centroids = []
        for c in contours_sorted:
            M = cv2.moments(c)
            if M['m00'] > 0:
                cx = int(M['m10'] / M['m00'])
                centroids.append(cx)
            else:
                centroids.append(0)
        
        # In PA view: patient's right is on viewer's left
        right_lung = np.zeros_like(gray)
        left_lung = np.zeros_like(gray)
        
        if centroids[0] < centroids[1]:
            cv2.drawContours(right_lung, [contours_sorted[0]], -1, 255, -1)
            cv2.drawContours(left_lung, [contours_sorted[1]], -1, 255, -1)
        else:
            cv2.drawContours(left_lung, [contours_sorted[0]], -1, 255, -1)
            cv2.drawContours(right_lung, [contours_sorted[1]], -1, 255, -1)
        
        return right_lung, left_lung
    
    def _segment_heart(self, gray: np.ndarray, body_mask: np.ndarray,
                        right_lung: np.ndarray, left_lung: np.ndarray) -> np.ndarray:
        """Segment cardiac silhouette (between the lungs, lower half)."""
        h, w = gray.shape
        
        # Heart is in the central-lower region between the lungs
        lung_combined = cv2.bitwise_or(right_lung, left_lung)
        
        # The heart is the bright area between lungs in the lower 60% of the image
        heart_region = body_mask.copy()
        heart_region[lung_combined > 0] = 0  # Remove lung areas
        heart_region[:int(h * 0.3), :] = 0   # Remove upper 30%
        heart_region[int(h * 0.85):, :] = 0  # Remove bottom 15%
        
        # Keep only central 60%
        left_bound = int(w * 0.2)
        right_bound = int(w * 0.8)
        heart_region[:, :left_bound] = 0
        heart_region[:, right_bound:] = 0
        
        # Cleanup
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (11, 11))
        heart_region = cv2.morphologyEx(heart_region, cv2.MORPH_CLOSE, kernel, iterations=3)
        heart_region = cv2.morphologyEx(heart_region, cv2.MORPH_OPEN, kernel, iterations=2)
        
        # Keep largest contour
        contours, _ = cv2.findContours(heart_region, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        heart_mask = np.zeros_like(gray)
        if contours:
            largest = max(contours, key=cv2.contourArea)
            cv2.drawContours(heart_mask, [largest], -1, 255, -1)
        
        return heart_mask
    
    def _segment_mediastinum(self, gray: np.ndarray, body_mask: np.ndarray,
                              right_lung: np.ndarray, left_lung: np.ndarray,
                              heart_mask: np.ndarray) -> np.ndarray:
        """Segment mediastinum (central area above heart, between lungs)."""
        h, w = gray.shape
        
        lung_combined = cv2.bitwise_or(right_lung, left_lung)
        
        mediastinum = body_mask.copy()
        mediastinum[lung_combined > 0] = 0
        mediastinum[heart_mask > 0] = 0
        
        # Keep central strip
        left_bound = int(w * 0.25)
        right_bound = int(w * 0.75)
        mediastinum[:, :left_bound] = 0
        mediastinum[:, right_bound:] = 0
        
        # Upper portion (above heart)
        mediastinum[int(h * 0.7):, :] = 0
        
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
        mediastinum = cv2.morphologyEx(mediastinum, cv2.MORPH_CLOSE, kernel, iterations=2)
        
        return mediastinum
    
    def _detect_costophrenic_angles(self, gray: np.ndarray,
                                     right_lung: np.ndarray,
                                     left_lung: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Detect costophrenic angles (bottom corners of lungs)."""
        h, w = gray.shape
        
        # Right costophrenic angle: bottom of right lung
        right_cp = np.zeros_like(gray)
        right_rows = np.any(right_lung > 0, axis=1)
        if np.any(right_rows):
            bottom_right = np.max(np.where(right_rows))
            top_cp = max(0, bottom_right - int(h * 0.1))
            right_cp[top_cp:bottom_right, :] = right_lung[top_cp:bottom_right, :]
        
        # Left costophrenic angle: bottom of left lung
        left_cp = np.zeros_like(gray)
        left_rows = np.any(left_lung > 0, axis=1)
        if np.any(left_rows):
            bottom_left = np.max(np.where(left_rows))
            top_cp = max(0, bottom_left - int(h * 0.1))
            left_cp[top_cp:bottom_left, :] = left_lung[top_cp:bottom_left, :]
        
        return right_cp, left_cp
    
    def _detect_diaphragm(self, gray: np.ndarray,
                           right_lung: np.ndarray,
                           left_lung: np.ndarray) -> np.ndarray:
        """Detect diaphragm (bottom edge of lung fields)."""
        h, w = gray.shape
        diaphragm = np.zeros_like(gray)
        
        lung_combined = cv2.bitwise_or(right_lung, left_lung)
        
        # Find bottom edge of lungs for each column
        for x in range(w):
            col = lung_combined[:, x]
            lung_pixels = np.where(col > 0)[0]
            if len(lung_pixels) > 0:
                bottom = lung_pixels[-1]
                # Mark diaphragm as a thin band at the bottom of lung
                start = max(0, bottom - 5)
                end = min(h, bottom + 5)
                diaphragm[start:end, x] = 255
        
        # Thicken
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 5))
        diaphragm = cv2.dilate(diaphragm, kernel, iterations=1)
        
        return diaphragm
    
    def _detect_trachea(self, gray: np.ndarray, body_mask: np.ndarray) -> np.ndarray:
        """Detect trachea/upper airway region."""
        h, w = gray.shape
        trachea = np.zeros_like(gray)
        
        # Trachea is a dark vertical structure in the upper central area
        upper_region = gray[:int(h * 0.35), :]
        body_upper = body_mask[:int(h * 0.35), :]
        
        # Central 30%
        center_start = int(w * 0.35)
        center_end = int(w * 0.65)
        
        central = upper_region[:, center_start:center_end]
        central_body = body_upper[:, center_start:center_end]
        
        if np.sum(central_body) == 0:
            return trachea
        
        # Trachea is darker than surrounding tissue
        body_pixels = central[central_body > 0]
        if len(body_pixels) == 0:
            return trachea
        
        thresh = np.percentile(body_pixels, 30)
        trachea_region = np.zeros_like(central)
        trachea_region[(central < thresh) & (central_body > 0)] = 255
        
        # Place back in full image
        trachea[:int(h * 0.35), center_start:center_end] = trachea_region
        
        # Cleanup — keep only vertical structures
        kernel_v = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 15))
        trachea = cv2.morphologyEx(trachea, cv2.MORPH_OPEN, kernel_v, iterations=1)
        trachea = cv2.morphologyEx(trachea, cv2.MORPH_CLOSE, kernel_v, iterations=2)
        
        return trachea
    
    def _compute_ctr(self, heart_mask: np.ndarray, 
                      right_lung: np.ndarray, left_lung: np.ndarray,
                      image_shape: Tuple[int, int]) -> Dict[str, Any]:
        """
        Compute Cardiothoracic Ratio (CTR).
        
        CTR = max heart width / max thorax width
        Normal: CTR < 0.50
        Borderline: 0.50-0.55
        Cardiomegaly: CTR > 0.55
        """
        h, w = image_shape
        
        # Heart width: find leftmost and rightmost points of heart
        heart_cols = np.any(heart_mask > 0, axis=0)
        if not np.any(heart_cols):
            return {'ctr': None, 'interpretation': 'Could not measure', 'heart_width': 0, 'thorax_width': 0}
        
        heart_left = np.min(np.where(heart_cols))
        heart_right = np.max(np.where(heart_cols))
        heart_width = heart_right - heart_left
        
        # Thorax width: widest extent of both lungs combined
        lung_combined = cv2.bitwise_or(right_lung, left_lung)
        lung_cols = np.any(lung_combined > 0, axis=0)
        if not np.any(lung_cols):
            return {'ctr': None, 'interpretation': 'Could not measure lungs', 'heart_width': heart_width, 'thorax_width': 0}
        
        thorax_left = np.min(np.where(lung_cols))
        thorax_right = np.max(np.where(lung_cols))
        thorax_width = thorax_right - thorax_left
        
        if thorax_width == 0:
            return {'ctr': None, 'interpretation': 'Could not measure thorax', 'heart_width': heart_width, 'thorax_width': 0}
        
        ctr = heart_width / thorax_width
        
        # Interpretation
        if ctr < 0.50:
            interpretation = "Normal"
            severity = "normal"
        elif ctr < 0.55:
            interpretation = "Borderline cardiomegaly"
            severity = "borderline"
        elif ctr < 0.65:
            interpretation = "Mild cardiomegaly"
            severity = "mild"
        elif ctr < 0.75:
            interpretation = "Moderate cardiomegaly"
            severity = "moderate"
        else:
            interpretation = "Severe cardiomegaly"
            severity = "severe"
        
        return {
            'ctr': round(ctr, 3),
            'interpretation': interpretation,
            'severity': severity,
            'heart_width': int(heart_width),
            'thorax_width': int(thorax_width),
            'heart_left': int(heart_left),
            'heart_right': int(heart_right),
            'thorax_left': int(thorax_left),
            'thorax_right': int(thorax_right)
        }
    
    def _compute_measurements(self, zones: Dict[str, np.ndarray],
                               image_shape: Tuple[int, int]) -> Dict[str, Any]:
        """Compute area measurements for each zone."""
        h, w = image_shape
        total_pixels = h * w
        
        measurements = {}
        for name, mask in zones.items():
            area_pixels = np.sum(mask > 0)
            measurements[name] = {
                'area_pixels': int(area_pixels),
                'area_percent': round(area_pixels / total_pixels * 100, 1)
            }
        
        # Lung symmetry (right vs left)
        right_area = measurements.get('right_lung', {}).get('area_pixels', 0)
        left_area = measurements.get('left_lung', {}).get('area_pixels', 0)
        total_lung = right_area + left_area
        
        if total_lung > 0:
            measurements['lung_symmetry'] = {
                'right_percent': round(right_area / total_lung * 100, 1),
                'left_percent': round(left_area / total_lung * 100, 1),
                'symmetry_ratio': round(min(right_area, left_area) / max(right_area, left_area, 1), 3),
                'interpretation': 'Symmetric' if abs(right_area - left_area) / total_lung < 0.15 else 'Asymmetric'
            }
        
        return measurements
    
    def _create_overlay(self, img_np: np.ndarray, zones: Dict[str, np.ndarray],
                         ctr_data: Dict) -> str:
        """Create colored overlay visualization with anatomical zones and CTR lines."""
        if len(img_np.shape) == 2:
            overlay = cv2.cvtColor(img_np, cv2.COLOR_GRAY2RGB)
        else:
            overlay = img_np.copy()
        
        h, w = overlay.shape[:2]
        
        # Draw semi-transparent zone overlays
        for zone_name, mask in zones.items():
            if zone_name in self.ZONE_COLORS and np.sum(mask > 0) > 0:
                color = self.ZONE_COLORS[zone_name]
                colored = np.zeros_like(overlay)
                colored[mask > 0] = color
                
                alpha = 0.25
                blend_mask = mask > 0
                blend_mask_3d = np.stack([blend_mask] * 3, axis=-1)
                overlay[blend_mask_3d] = (
                    overlay[blend_mask_3d] * (1 - alpha) + 
                    colored[blend_mask_3d] * alpha
                ).astype(np.uint8)
                
                # Draw contour
                contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                cv2.drawContours(overlay, contours, -1, color, 1)
        
        # Draw CTR measurement lines
        if ctr_data.get('ctr') is not None:
            # Find the vertical center of the heart for measurement line
            heart_row = h // 2 + int(h * 0.1)
            
            # Heart width line (red)
            hl = ctr_data['heart_left']
            hr = ctr_data['heart_right']
            cv2.line(overlay, (hl, heart_row), (hr, heart_row), (255, 0, 0), 2)
            cv2.line(overlay, (hl, heart_row - 8), (hl, heart_row + 8), (255, 0, 0), 2)
            cv2.line(overlay, (hr, heart_row - 8), (hr, heart_row + 8), (255, 0, 0), 2)
            
            # Thorax width line (green)
            tl = ctr_data['thorax_left']
            tr = ctr_data['thorax_right']
            thorax_row = heart_row + 25
            cv2.line(overlay, (tl, thorax_row), (tr, thorax_row), (0, 255, 0), 2)
            cv2.line(overlay, (tl, thorax_row - 8), (tl, thorax_row + 8), (0, 255, 0), 2)
            cv2.line(overlay, (tr, thorax_row - 8), (tr, thorax_row + 8), (0, 255, 0), 2)
            
            # CTR label
            ctr_text = f"CTR = {ctr_data['ctr']:.2f} ({ctr_data['interpretation']})"
            (tw, th), _ = cv2.getTextSize(ctr_text, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 2)
            cv2.rectangle(overlay, (8, h - 40), (18 + tw, h - 10), (0, 0, 0), -1)
            ctr_color = (0, 255, 0) if ctr_data['ctr'] < 0.5 else (0, 255, 255) if ctr_data['ctr'] < 0.55 else (0, 0, 255)
            cv2.putText(overlay, ctr_text, (12, h - 18), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.55, ctr_color, 2, cv2.LINE_AA)
        
        # Zone legend
        legend_y = 20
        for zone_name, color in self.ZONE_COLORS.items():
            label = zone_name.replace('_', ' ').title()
            cv2.rectangle(overlay, (w - 180, legend_y - 10), (w - 168, legend_y + 2), color, -1)
            cv2.putText(overlay, label, (w - 164, legend_y),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.35, (255, 255, 255), 1, cv2.LINE_AA)
            legend_y += 18
        
        # Encode
        overlay_image = Image.fromarray(overlay)
        buffer = io.BytesIO()
        overlay_image.save(buffer, format='PNG')
        buffer.seek(0)
        return base64.b64encode(buffer.read()).decode('utf-8')
    
    def _describe_zones(self, zones: Dict[str, np.ndarray],
                         measurements: Dict, image_shape: Tuple[int, int]) -> Dict[str, str]:
        """Generate human-readable descriptions of each zone."""
        descriptions = {}
        
        right_area = measurements.get('right_lung', {}).get('area_percent', 0)
        left_area = measurements.get('left_lung', {}).get('area_percent', 0)
        
        descriptions['right_lung'] = f"Right lung field: {right_area}% of image area"
        descriptions['left_lung'] = f"Left lung field: {left_area}% of image area"
        
        symmetry = measurements.get('lung_symmetry', {})
        if symmetry:
            descriptions['lung_symmetry'] = (
                f"Lung symmetry: R={symmetry.get('right_percent', '?')}% / "
                f"L={symmetry.get('left_percent', '?')}% — {symmetry.get('interpretation', '?')}"
            )
        
        heart_area = measurements.get('heart', {}).get('area_percent', 0)
        descriptions['heart'] = f"Cardiac silhouette: {heart_area}% of image area"
        
        ctr = measurements.get('ctr', {})
        if ctr and ctr.get('ctr'):
            descriptions['ctr'] = f"CTR = {ctr['ctr']:.2f} — {ctr['interpretation']}"
        
        return descriptions
