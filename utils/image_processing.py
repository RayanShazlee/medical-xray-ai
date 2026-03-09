from PIL import Image, ImageFilter, ImageEnhance
import numpy as np
import cv2
import os
import base64
import io
from dotenv import load_dotenv

load_dotenv()


def enhance_xray(image: Image.Image) -> Image.Image:
    """Apply medical-grade X-ray image enhancement for better diagnosis.
    
    Pipeline:
    1. CLAHE (Contrast Limited Adaptive Histogram Equalization) — the gold standard
       for medical image contrast enhancement. Works on local regions.
    2. Bilateral filtering — removes noise while preserving edges (lung boundaries,
       rib edges, cardiac silhouette).
    3. Unsharp masking — sharpens fine details like nodules, infiltrates, and
       interstitial patterns.
    4. Windowing — adjusts brightness/contrast to optimize lung parenchyma visibility.
    """
    img_np = np.array(image)
    
    # Convert to grayscale for processing if RGB
    if len(img_np.shape) == 3:
        gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
    else:
        gray = img_np.copy()
    
    # --- Step 1: CLAHE (Contrast Limited Adaptive Histogram Equalization) ---
    # This is the single most important enhancement for X-rays.
    # It enhances local contrast without over-amplifying noise.
    # clipLimit=3.0 provides strong enhancement; tileGridSize=(8,8) is standard.
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    
    # --- Step 2: Bilateral Filtering (edge-preserving denoising) ---
    # Unlike Gaussian blur, bilateral filtering preserves sharp edges
    # (important for lung borders, rib margins, cardiac silhouette)
    # while smoothing out noise in uniform areas.
    denoised = cv2.bilateralFilter(enhanced, d=9, sigmaColor=75, sigmaSpace=75)
    
    # --- Step 3: Unsharp Masking (detail sharpening) ---
    # Creates a blurred version, then subtracts it to enhance fine details
    # like nodules, infiltrates, interstitial patterns, and bronchial markings.
    gaussian = cv2.GaussianBlur(denoised, (0, 0), sigmaX=2.0)
    sharpened = cv2.addWeighted(denoised, 1.5, gaussian, -0.5, 0)
    
    # --- Step 4: Lung Windowing (brightness/contrast optimization) ---
    # Optimizes the dynamic range to make lung parenchyma most visible.
    # Maps the useful intensity range (p2-p98) to full 0-255 range.
    p2, p98 = np.percentile(sharpened, (2, 98))
    windowed = np.clip((sharpened - p2) / (p98 - p2 + 1e-8) * 255, 0, 255).astype(np.uint8)
    
    # Convert back to RGB (3 channels needed for model input)
    enhanced_rgb = cv2.cvtColor(windowed, cv2.COLOR_GRAY2RGB)
    
    return Image.fromarray(enhanced_rgb)


def create_enhanced_comparison(original: Image.Image, enhanced: Image.Image) -> str:
    """Create a side-by-side comparison of original vs enhanced X-ray.
    Returns base64 encoded PNG."""
    # Ensure same size
    target_h = 400
    ratio_orig = target_h / original.size[1]
    ratio_enh = target_h / enhanced.size[1]
    
    orig_resized = original.resize(
        (int(original.size[0] * ratio_orig), target_h), Image.Resampling.LANCZOS
    )
    enh_resized = enhanced.resize(
        (int(enhanced.size[0] * ratio_enh), target_h), Image.Resampling.LANCZOS
    )
    
    # Create side-by-side canvas
    total_w = orig_resized.size[0] + enh_resized.size[0] + 20  # 20px gap
    canvas = Image.new('RGB', (total_w, target_h + 30), (255, 255, 255))
    
    canvas.paste(orig_resized, (0, 30))
    canvas.paste(enh_resized, (orig_resized.size[0] + 20, 30))
    
    # Add labels using OpenCV (simpler than PIL ImageDraw for this)
    canvas_np = np.array(canvas)
    cv2.putText(canvas_np, "Original", (10, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (100, 100, 100), 1)
    cv2.putText(canvas_np, "Enhanced (CLAHE)", (orig_resized.size[0] + 30, 22),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 120, 0), 1)
    canvas = Image.fromarray(canvas_np)
    
    buffer = io.BytesIO()
    canvas.save(buffer, format='PNG')
    buffer.seek(0)
    return base64.b64encode(buffer.read()).decode('utf-8')


def process_image(image_path):
    """Process a medical image with enhancement and return data for analysis."""
    try:
        # Open and validate the image
        image = Image.open(image_path)

        # Convert to RGB if necessary
        if image.mode != 'RGB':
            image = image.convert('RGB')

        # Resize if too large (maintain aspect ratio)
        max_size = 800
        if max(image.size) > max_size:
            ratio = max_size / max(image.size)
            new_size = tuple(int(dim * ratio) for dim in image.size)
            image = image.resize(new_size, Image.Resampling.LANCZOS)

        # Apply medical X-ray enhancement
        enhanced_image = enhance_xray(image)
        
        # Create comparison image
        comparison_b64 = create_enhanced_comparison(image, enhanced_image)

        return {
            'original_path': image_path,
            'image': image,
            'enhanced_image': enhanced_image,
            'comparison_b64': comparison_b64,
            'size': image.size
        }

    except Exception as e:
        print(f"Error processing image: {str(e)}")
        return None