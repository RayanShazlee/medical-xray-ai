"""
🤖 X-Ray Enhancement Agent — Adaptive Preprocessing for Inference

This agent is used both during TRAINING (in the Kaggle notebook) and during
INFERENCE (in the Flask app). It ensures the model sees the same quality
preprocessing at prediction time as it did during training.

Pipeline:
1. Analyze image → compute brightness, contrast, noise, sharpness, dynamic range
2. Decide actions → based on calibrated thresholds, decide which filters to apply
3. Apply enhancements → CLAHE, gamma correction, denoising, sharpening, windowing
4. Return enhanced image + quality report

Usage (Flask app):
    from agents.enhancement_agent import EnhancementAgent
    
    agent = EnhancementAgent()
    enhanced_pil, report = agent.process(pil_image)
    # report = {'quality': 'poor', 'issues': ['underexposed', 'low_contrast'], 
    #           'metrics': {...}, 'actions_applied': ['gamma', 'clahe']}
"""

import numpy as np
import cv2
from PIL import Image
from typing import Dict, Any, List, Tuple, Optional


class EnhancementAgent:
    """
    Intelligent X-Ray Enhancement Agent
    
    Analyzes each X-ray image's quality metrics and dynamically applies
    the right combination of enhancements. Mimics what a radiologist does
    when adjusting window/level settings before reading a film.
    
    The thresholds are calibrated for chest X-rays and match exactly
    what was used during model training on Kaggle.
    """
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        
        # Running statistics
        self.stats = {
            'brightness_adjusted': 0,
            'clahe_applied': 0,
            'denoised': 0,
            'sharpened': 0,
            'windowed': 0,
            'total_processed': 0
        }
        
        # === Calibrated thresholds for chest X-rays ===
        # These MUST match the training notebook exactly
        self.brightness_low = 60       # Below → too dark
        self.brightness_high = 190     # Above → too bright/overexposed
        self.brightness_target = 127   # Ideal mean brightness
        
        self.contrast_low = 35         # Below → poor contrast → CLAHE
        
        self.noise_high = 800          # Above → noisy → denoise
        self.noise_low = 50            # Below → too smooth
        
        self.sharpness_low = 15        # Below → blurry → sharpen
        
        self.dynamic_range_low = 120   # If p98-p2 < this → compressed → stretch
        
        if self.verbose:
            print("🤖 Enhancement Agent initialized")
            print(f"   Brightness range: [{self.brightness_low}, {self.brightness_high}]")
            print(f"   Contrast threshold: {self.contrast_low}")
            print(f"   Noise threshold: {self.noise_high}")
            print(f"   Sharpness threshold: {self.sharpness_low}")
            print(f"   Dynamic range threshold: {self.dynamic_range_low}")
    
    # ==================== ANALYSIS ====================
    
    def analyze(self, gray: np.ndarray) -> Dict[str, float]:
        """
        Compute quality metrics for a grayscale X-ray image.
        
        Returns dict with:
            brightness: mean pixel intensity (0-255)
            contrast: std dev of pixels
            noise: Laplacian variance (high = noisy or detailed)
            sharpness: mean Sobel gradient magnitude
            dynamic_range: p98 - p2 percentile spread
            skewness: histogram skewness (negative = dark-skewed)
        """
        metrics = {}
        
        # 1. Brightness — mean pixel intensity
        metrics['brightness'] = float(np.mean(gray))
        
        # 2. Contrast — standard deviation of pixel values
        metrics['contrast'] = float(np.std(gray))
        
        # 3. Noise level — variance of Laplacian
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        metrics['noise'] = float(laplacian.var())
        
        # 4. Sharpness — high frequency energy via Sobel
        sobelx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        sobely = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
        metrics['sharpness'] = float(np.mean(np.sqrt(sobelx**2 + sobely**2)))
        
        # 5. Dynamic range — percentile spread
        p2, p98 = np.percentile(gray, (2, 98))
        metrics['dynamic_range'] = float(p98 - p2)
        metrics['p2'] = float(p2)
        metrics['p98'] = float(p98)
        
        # 6. Histogram skewness
        hist = cv2.calcHist([gray], [0], None, [256], [0, 256]).flatten()
        hist_norm = hist / hist.sum()
        bins = np.arange(256)
        mean_h = np.sum(bins * hist_norm)
        std_h = np.sqrt(np.sum((bins - mean_h)**2 * hist_norm)) + 1e-8
        metrics['skewness'] = float(np.sum((bins - mean_h)**3 * hist_norm) / std_h**3)
        
        return metrics
    
    # ==================== DECISION ====================
    
    def decide_actions(self, metrics: Dict[str, float]) -> List[Tuple[str, Any]]:
        """
        Based on quality metrics, decide which enhancements to apply.
        Returns list of (action_name, parameter) tuples.
        """
        actions = []
        
        # Brightness correction via gamma
        if metrics['brightness'] < self.brightness_low:
            gamma = max(0.4, metrics['brightness'] / self.brightness_target)
            actions.append(('gamma', gamma))
        elif metrics['brightness'] > self.brightness_high:
            gamma = min(2.5, metrics['brightness'] / self.brightness_target)
            actions.append(('gamma', gamma))
        
        # Contrast enhancement via CLAHE
        if metrics['contrast'] < self.contrast_low:
            clip_limit = min(5.0, max(2.0, 4.0 - (metrics['contrast'] / self.contrast_low) * 2.0))
            actions.append(('clahe', clip_limit))
        elif metrics['dynamic_range'] < self.dynamic_range_low:
            actions.append(('clahe', 2.5))
        
        # Denoising via non-local means
        if metrics['noise'] > self.noise_high:
            strength = min(15, int(5 + (metrics['noise'] - self.noise_high) / 200))
            actions.append(('denoise', strength))
        
        # Sharpening via unsharp mask
        if metrics['sharpness'] < self.sharpness_low:
            alpha = min(2.0, max(1.2, 1.5 + (self.sharpness_low - metrics['sharpness']) / 20))
            actions.append(('sharpen', alpha))
        
        # Histogram stretching (windowing)
        if metrics['dynamic_range'] < self.dynamic_range_low:
            actions.append(('window', (metrics['p2'], metrics['p98'])))
        
        return actions
    
    # ==================== ENHANCEMENT ====================
    
    def apply_enhancements(self, gray: np.ndarray, actions: List[Tuple[str, Any]]) -> np.ndarray:
        """Apply the decided enhancement actions to a grayscale image."""
        enhanced = gray.copy()
        
        for action, param in actions:
            if action == 'gamma':
                inv_gamma = 1.0 / param
                table = np.array([((i / 255.0) ** inv_gamma) * 255 
                                  for i in range(256)]).astype(np.uint8)
                enhanced = cv2.LUT(enhanced, table)
                self.stats['brightness_adjusted'] += 1
                
            elif action == 'clahe':
                clahe_obj = cv2.createCLAHE(clipLimit=param, tileGridSize=(8, 8))
                enhanced = clahe_obj.apply(enhanced)
                self.stats['clahe_applied'] += 1
                
            elif action == 'denoise':
                enhanced = cv2.fastNlMeansDenoising(
                    enhanced, None, h=param,
                    templateWindowSize=7, searchWindowSize=21
                )
                self.stats['denoised'] += 1
                
            elif action == 'sharpen':
                blurred = cv2.GaussianBlur(enhanced, (0, 0), sigmaX=2.0)
                enhanced = cv2.addWeighted(enhanced, param, blurred, -(param - 1.0), 0)
                self.stats['sharpened'] += 1
                
            elif action == 'window':
                p_low, p_high = param
                enhanced = np.clip(
                    (enhanced.astype(np.float32) - p_low) / (p_high - p_low + 1e-8) * 255,
                    0, 255
                ).astype(np.uint8)
                self.stats['windowed'] += 1
        
        return enhanced
    
    # ==================== MAIN ENTRY POINTS ====================
    
    def enhance(self, pil_image: Image.Image) -> Image.Image:
        """
        Enhance a PIL Image. Returns enhanced PIL Image (RGB).
        Used as a transform in training and inference pipelines.
        """
        img_np = np.array(pil_image)
        if len(img_np.shape) == 3:
            gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
        else:
            gray = img_np.copy()
        
        metrics = self.analyze(gray)
        actions = self.decide_actions(metrics)
        
        if actions:
            enhanced = self.apply_enhancements(gray, actions)
            enhanced_rgb = cv2.cvtColor(enhanced, cv2.COLOR_GRAY2RGB)
            result = Image.fromarray(enhanced_rgb)
        else:
            result = pil_image
        
        self.stats['total_processed'] += 1
        
        if self.verbose and actions:
            action_names = [a[0] for a in actions]
            print(f"   🤖 Agent: {', '.join(action_names)} | "
                  f"B={metrics['brightness']:.0f} C={metrics['contrast']:.0f} "
                  f"N={metrics['noise']:.0f} S={metrics['sharpness']:.1f}")
        
        return result
    
    def get_quality_report(self, pil_image: Image.Image) -> Dict[str, Any]:
        """
        Analyze image quality WITHOUT modifying it. Returns a quality report.
        
        Returns:
            quality: 'good' or 'poor'
            issues: list of detected issues (e.g., ['underexposed', 'low_contrast'])
            metrics: dict of raw quality metrics
            actions_applied: list of enhancement names that would be applied
        """
        img_np = np.array(pil_image)
        if len(img_np.shape) == 3:
            gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
        else:
            gray = img_np.copy()
        
        metrics = self.analyze(gray)
        actions = self.decide_actions(metrics)
        
        # Categorize issues
        issues = []
        if metrics['brightness'] < self.brightness_low:
            issues.append('underexposed')
        elif metrics['brightness'] > self.brightness_high:
            issues.append('overexposed')
        if metrics['contrast'] < self.contrast_low:
            issues.append('low_contrast')
        if metrics['noise'] > self.noise_high:
            issues.append('noisy')
        if metrics['sharpness'] < self.sharpness_low:
            issues.append('blurry')
        if metrics['dynamic_range'] < self.dynamic_range_low:
            issues.append('compressed_range')
        
        quality = 'good' if not issues else 'poor'
        
        return {
            'quality': quality,
            'issues': issues,
            'metrics': {
                'brightness': round(metrics['brightness'], 1),
                'contrast': round(metrics['contrast'], 1),
                'noise': round(metrics['noise'], 1),
                'sharpness': round(metrics['sharpness'], 1),
                'dynamic_range': round(metrics['dynamic_range'], 1),
                'skewness': round(metrics['skewness'], 2)
            },
            'actions_applied': [a[0] for a in actions]
        }
    
    def process(self, pil_image: Image.Image) -> Tuple[Image.Image, Dict[str, Any]]:
        """
        Full pipeline: enhance + quality report in one call.
        Returns (enhanced_image, quality_report).
        
        This is the recommended method for the Flask app.
        """
        report = self.get_quality_report(pil_image)
        enhanced = self.enhance(pil_image)
        return enhanced, report
    
    # ==================== UTILITIES ====================
    
    def reset_stats(self):
        """Reset running statistics."""
        self.stats = {k: 0 for k in self.stats}
    
    def print_stats(self):
        """Print summary of all enhancements applied so far."""
        print("\n🤖 Enhancement Agent Summary:")
        print(f"   Total images processed: {self.stats['total_processed']}")
        if self.stats['total_processed'] > 0:
            for key, val in self.stats.items():
                if key != 'total_processed' and val > 0:
                    pct = val / self.stats['total_processed'] * 100
                    print(f"   {key}: {val} ({pct:.1f}%)")
