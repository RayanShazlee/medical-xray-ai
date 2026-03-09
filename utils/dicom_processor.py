"""
DICOM (.dcm) File Processor — Tier 2 Feature

Handles real hospital-format DICOM files:
- Extracts pixel data and converts to PIL Image
- Parses metadata (patient age, sex, study date, modality, window/level)
- Applies DICOM windowing (window center/width) for optimal display
- Returns structured clinical context for the LLM
"""

import numpy as np
from PIL import Image
from typing import Dict, Any, Optional, Tuple
import os

try:
    import pydicom
    from pydicom.pixel_data_handlers.util import apply_voi_lut, apply_modality_lut
    PYDICOM_AVAILABLE = True
except ImportError:
    PYDICOM_AVAILABLE = False
    print("Warning: pydicom not installed. DICOM support disabled.")


class DICOMProcessor:
    """Process DICOM files and extract both image data and clinical metadata."""
    
    # Standard DICOM tags we care about for chest X-rays
    METADATA_TAGS = {
        'PatientAge': (0x0010, 0x1010),
        'PatientSex': (0x0010, 0x0040),
        'PatientName': (0x0010, 0x0010),
        'PatientID': (0x0010, 0x0020),
        'StudyDate': (0x0008, 0x0020),
        'StudyDescription': (0x0008, 0x1030),
        'Modality': (0x0008, 0x0060),
        'BodyPartExamined': (0x0018, 0x0015),
        'ViewPosition': (0x0018, 0x5101),
        'Manufacturer': (0x0008, 0x0070),
        'InstitutionName': (0x0008, 0x0080),
        'WindowCenter': (0x0028, 0x1050),
        'WindowWidth': (0x0028, 0x1051),
        'BitsAllocated': (0x0028, 0x0100),
        'BitsStored': (0x0028, 0x0101),
        'PhotometricInterpretation': (0x0028, 0x0004),
        'Rows': (0x0028, 0x0010),
        'Columns': (0x0028, 0x0011),
        'PixelSpacing': (0x0028, 0x0030),
        'PatientPosition': (0x0018, 0x5100),
        'KVP': (0x0018, 0x0060),
        'ExposureTime': (0x0018, 0x1150),
    }
    
    def __init__(self):
        if not PYDICOM_AVAILABLE:
            raise RuntimeError("pydicom is required for DICOM processing. Install with: pip install pydicom")
    
    def is_dicom(self, file_path: str) -> bool:
        """Check if a file is a valid DICOM file."""
        try:
            pydicom.dcmread(file_path, stop_before_pixels=True)
            return True
        except Exception:
            return file_path.lower().endswith('.dcm')
    
    def extract_metadata(self, ds: 'pydicom.Dataset') -> Dict[str, Any]:
        """Extract clinical metadata from DICOM dataset."""
        metadata = {}
        
        for name, tag in self.METADATA_TAGS.items():
            try:
                element = ds[tag]
                value = element.value
                # Handle multi-value fields
                if hasattr(value, '__iter__') and not isinstance(value, (str, bytes)):
                    value = list(value)
                    if len(value) == 1:
                        value = value[0]
                # Convert to string for JSON serialization
                if isinstance(value, bytes):
                    value = value.decode('utf-8', errors='ignore')
                metadata[name] = str(value) if value else None
            except (KeyError, IndexError):
                metadata[name] = None
        
        # Parse age properly (DICOM stores as "045Y" format)
        if metadata.get('PatientAge'):
            age_str = metadata['PatientAge'].strip()
            try:
                if age_str.endswith('Y'):
                    metadata['PatientAgeYears'] = int(age_str[:-1])
                elif age_str.endswith('M'):
                    metadata['PatientAgeYears'] = round(int(age_str[:-1]) / 12, 1)
                else:
                    metadata['PatientAgeYears'] = int(age_str)
            except ValueError:
                metadata['PatientAgeYears'] = None
        
        # Parse study date (YYYYMMDD → readable)
        if metadata.get('StudyDate'):
            try:
                d = metadata['StudyDate']
                metadata['StudyDateFormatted'] = f"{d[:4]}-{d[4:6]}-{d[6:8]}"
            except (IndexError, TypeError):
                metadata['StudyDateFormatted'] = metadata['StudyDate']
        
        return metadata
    
    def apply_windowing(self, pixel_array: np.ndarray, ds: 'pydicom.Dataset') -> np.ndarray:
        """Apply DICOM windowing (VOI LUT) for optimal display."""
        try:
            # Apply modality LUT first (Rescale Slope/Intercept)
            pixel_array = apply_modality_lut(pixel_array, ds)
            # Apply VOI LUT (Window Center/Width)
            pixel_array = apply_voi_lut(pixel_array, ds, index=0)
        except Exception:
            pass  # Fall back to raw pixels if LUT fails
        
        return pixel_array
    
    def pixel_to_image(self, pixel_array: np.ndarray, ds: 'pydicom.Dataset') -> Image.Image:
        """Convert DICOM pixel array to PIL Image with proper normalization."""
        # Apply windowing
        windowed = self.apply_windowing(pixel_array.copy(), ds)
        
        # Handle photometric interpretation (MONOCHROME1 = inverted)
        photometric = getattr(ds, 'PhotometricInterpretation', 'MONOCHROME2')
        if photometric == 'MONOCHROME1':
            windowed = windowed.max() - windowed  # Invert
        
        # Normalize to 0-255
        arr = windowed.astype(np.float64)
        arr_min, arr_max = arr.min(), arr.max()
        if arr_max > arr_min:
            arr = (arr - arr_min) / (arr_max - arr_min) * 255.0
        arr = arr.astype(np.uint8)
        
        # Convert to RGB
        if len(arr.shape) == 2:
            rgb = np.stack([arr] * 3, axis=-1)
        elif len(arr.shape) == 3 and arr.shape[2] == 1:
            rgb = np.stack([arr.squeeze()] * 3, axis=-1)
        else:
            rgb = arr
        
        return Image.fromarray(rgb, 'RGB')
    
    def process(self, file_path: str) -> Dict[str, Any]:
        """
        Full DICOM processing pipeline.
        
        Returns:
            image: PIL Image (RGB)
            metadata: Dict of clinical metadata
            clinical_context: Formatted string for LLM prompt
            pixel_spacing: Physical pixel spacing in mm (for measurements)
        """
        ds = pydicom.dcmread(file_path)
        
        # Extract metadata
        metadata = self.extract_metadata(ds)
        
        # Convert pixels to image
        pixel_array = ds.pixel_array
        image = self.pixel_to_image(pixel_array, ds)
        
        # Get pixel spacing for physical measurements
        pixel_spacing = None
        if metadata.get('PixelSpacing'):
            try:
                spacing_str = metadata['PixelSpacing']
                # Parse "[0.143, 0.143]" or "0.143\\0.143" format
                if '[' in spacing_str:
                    parts = spacing_str.strip('[]').split(',')
                else:
                    parts = spacing_str.split('\\')
                pixel_spacing = [float(p.strip()) for p in parts]
            except (ValueError, AttributeError):
                pixel_spacing = None
        
        # Build clinical context string for LLM
        clinical_context = self._build_clinical_context(metadata)
        
        return {
            'image': image,
            'metadata': metadata,
            'clinical_context': clinical_context,
            'pixel_spacing': pixel_spacing,
            'original_path': file_path
        }
    
    def _build_clinical_context(self, metadata: Dict[str, Any]) -> str:
        """Build a formatted clinical context string for the LLM."""
        lines = ["## DICOM Clinical Context:"]
        
        if metadata.get('PatientAgeYears'):
            lines.append(f"- Patient Age: {metadata['PatientAgeYears']} years")
        if metadata.get('PatientSex'):
            sex_map = {'M': 'Male', 'F': 'Female', 'O': 'Other'}
            lines.append(f"- Patient Sex: {sex_map.get(metadata['PatientSex'], metadata['PatientSex'])}")
        if metadata.get('StudyDateFormatted'):
            lines.append(f"- Study Date: {metadata['StudyDateFormatted']}")
        if metadata.get('Modality'):
            lines.append(f"- Modality: {metadata['Modality']}")
        if metadata.get('ViewPosition'):
            lines.append(f"- View: {metadata['ViewPosition']}")
        if metadata.get('BodyPartExamined'):
            lines.append(f"- Body Part: {metadata['BodyPartExamined']}")
        if metadata.get('StudyDescription'):
            lines.append(f"- Study Description: {metadata['StudyDescription']}")
        if metadata.get('InstitutionName'):
            lines.append(f"- Institution: {metadata['InstitutionName']}")
        if metadata.get('WindowCenter') and metadata.get('WindowWidth'):
            lines.append(f"- Window: C={metadata['WindowCenter']}, W={metadata['WindowWidth']}")
        if metadata.get('KVP'):
            lines.append(f"- KVP: {metadata['KVP']}")
        if metadata.get('BitsStored'):
            lines.append(f"- Bit Depth: {metadata['BitsStored']}-bit")
        
        return "\n".join(lines) if len(lines) > 1 else ""
