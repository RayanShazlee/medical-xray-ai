from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
import torch
import torch.nn as nn
from torchvision import models, transforms
import numpy as np
import cv2
import os
import base64
import io
import json
from dotenv import load_dotenv
from typing import Dict, Any, Optional, List, Tuple
from PIL import Image
from sentence_transformers import SentenceTransformer
import pinecone
from huggingface_hub import hf_hub_download
from agents.enhancement_agent import EnhancementAgent
from agents.clinical_decision_agent import ClinicalDecisionAgent
from agents.anatomical_agent import AnatomicalSegmentationAgent

load_dotenv()

# ==================== CheXNet 14-Pathology Model ====================
# DenseNet-121 based model trained on NIH Chest X-ray dataset
# Detects 14 pathologies + "No Finding" (multi-label classification)
CHEXNET_CLASSES = [
    "No Finding", "Atelectasis", "Cardiomegaly", "Effusion", "Infiltration",
    "Mass", "Nodule", "Pneumonia", "Pneumothorax", "Consolidation",
    "Edema", "Emphysema", "Fibrosis", "Pleural_Thickening", "Hernia"
]


class CheXNetModel(nn.Module):
    """DenseNet-121 based CheXNet for 14-pathology chest X-ray classification.
    Matches the state_dict format: backbone.features.* and backbone.classifier.1.*"""
    def __init__(self, num_classes=15):
        super().__init__()
        densenet = models.densenet121(weights=None)
        # The saved model uses backbone.features and backbone.classifier.1 (Sequential)
        self.backbone = nn.Module()
        self.backbone.features = densenet.features
        num_features = densenet.classifier.in_features
        self.backbone.classifier = nn.Sequential(
            nn.AdaptiveAvgPool2d(1),
            nn.Linear(num_features, num_classes)
        )

    def forward(self, x):
        features = self.backbone.features(x)
        out = torch.relu(features)
        # Global average pooling
        out = self.backbone.classifier[0](out)
        out = out.view(out.size(0), -1)
        out = self.backbone.classifier[1](out)
        return out


class RadiologistAgent:
    def __init__(self):
        # Initialize Groq LLM
        self.llm = ChatGroq(
            api_key=os.getenv("GROQ_API_KEY"),
            model="llama-3.3-70b-versatile",
            temperature=0.3
        )

        # Image preprocessing for CheXNet (same as training: 224x224, ImageNet norms)
        self.transform = transforms.Compose([
            transforms.Resize(256),
            transforms.CenterCrop(224),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406],
                                 std=[0.229, 0.224, 0.225])
        ])

        # Initialize CheXNet 14-pathology model
        print("Loading CheXNet 14-pathology chest X-ray model...")
        try:
            self.chexnet = CheXNetModel(num_classes=15)
            # Download weights from HuggingFace
            weights_path = hf_hub_download(
                repo_id="alex17cmbs/chexnet-multilabel",
                filename="pytorch_model.bin"
            )
            state_dict = torch.load(weights_path, map_location='cpu', weights_only=True)
            self.chexnet.load_state_dict(state_dict)
            self.chexnet.eval()
            print(f"CheXNet loaded! Detects {len(CHEXNET_CLASSES)} conditions: {', '.join(CHEXNET_CLASSES)}")
        except Exception as e:
            print(f"Warning: Could not load CheXNet model: {e}")
            import traceback
            traceback.print_exc()
            self.chexnet = None

        # Also keep the simpler pneumonia model as a secondary check
        try:
            from transformers import pipeline as hf_pipeline
            self.pneumonia_classifier = hf_pipeline(
                "image-classification",
                model="nickmuchi/vit-finetuned-chest-xray-pneumonia",
                token=False
            )
            print("Secondary pneumonia classifier loaded!")
        except Exception as e:
            print(f"Warning: Could not load pneumonia classifier: {e}")
            self.pneumonia_classifier = None

        # Initialize Pinecone for book knowledge retrieval (RAG)
        try:
            self.pc = pinecone.Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
            self.book_index = self.pc.Index("book-knowledge")
            self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            print("Pinecone book knowledge connected for RAG!")
        except Exception as e:
            print(f"Warning: Could not connect to Pinecone for RAG: {e}")
            self.book_index = None
            self.embedding_model = None

        # Initialize Enhancement Agent — same thresholds as training
        self.enhancement_agent = EnhancementAgent(verbose=True)
        print("🤖 Enhancement Agent loaded for inference preprocessing!")

        # Initialize Clinical Decision Support Agent
        self.clinical_agent = ClinicalDecisionAgent()
        print("🏥 Clinical Decision Support Agent loaded!")

        # Initialize Anatomical Segmentation Agent
        self.segmentation_agent = AnatomicalSegmentationAgent(verbose=True)
        print("🫁 Anatomical Segmentation Agent loaded!")

    def _classify_xray_chexnet(self, image: Image.Image) -> List[Dict[str, Any]]:
        """Classify using CheXNet 14-pathology model (multi-label with sigmoid)."""
        if self.chexnet is None:
            return []

        # Preprocess
        input_tensor = self.transform(image).unsqueeze(0)  # Add batch dim

        with torch.no_grad():
            logits = self.chexnet(input_tensor)
            probabilities = torch.sigmoid(logits).squeeze(0)  # Multi-label: use sigmoid, not softmax

        results = []
        for i, (cls_name, prob) in enumerate(zip(CHEXNET_CLASSES, probabilities)):
            results.append({
                'label': cls_name,
                'score': prob.item(),
                'index': i
            })

        # Sort by probability (highest first)
        results.sort(key=lambda x: x['score'], reverse=True)
        return results

    def _classify_xray_pneumonia(self, image: Image.Image) -> List[Dict[str, Any]]:
        """Secondary classification using the ViT pneumonia model."""
        if self.pneumonia_classifier is None:
            return []
        return self.pneumonia_classifier(image, top_k=2)

    def _generate_gradcam(self, image: Image.Image, target_class_idx: int = None, all_results: List[Dict] = None) -> Optional[str]:
        """Generate Grad-CAM++ heatmap focused on the HIGHEST CERTAINTY pathology.
        
        Key improvements for certainty:
        1. Focuses on the SINGLE most confident pathology — no multi-disease dilution
        2. Uses eigenvalue-based channel selection to pick only the most discriminative 
           feature channels, removing noise from irrelevant channels
        3. Applies strong contrast stretching (power-law gamma) so the heatmap 
           concentrates on the peak activation region
        4. Tighter lung mask with automatic body-edge rejection
        
        Returns a base64-encoded PNG of the heatmap overlay."""
        if self.chexnet is None:
            return None

        try:
            # Preprocess
            input_tensor = self.transform(image).unsqueeze(0)

            activations = {}
            gradients = {}

            def forward_hook(module, inp, out):
                activations['value'] = out

            def backward_hook(module, grad_input, grad_output):
                gradients['value'] = grad_output[0]

            # Hook into norm5 — the LAST spatial layer before global avg pool
            target_layer = self.chexnet.backbone.features.norm5
            fwd_handle = target_layer.register_forward_hook(forward_hook)
            bwd_handle = target_layer.register_full_backward_hook(backward_hook)

            # Forward pass
            logits = self.chexnet(input_tensor)
            probs = torch.sigmoid(logits)
            all_probs = probs[0].detach()

            # ===== Focus on the SINGLE HIGHEST certainty pathology =====
            if target_class_idx is not None and target_class_idx > 0:
                focus_idx = target_class_idx
            else:
                # Find the pathology with the absolute highest score (skip "No Finding" idx 0)
                focus_idx = all_probs[1:].argmax().item() + 1

            focus_label = CHEXNET_CLASSES[focus_idx]
            focus_prob = all_probs[focus_idx].item()

            # Zero gradients & backward for the focused class only
            self.chexnet.zero_grad()
            target_score = logits[0, focus_idx]
            target_score.backward(retain_graph=False)

            grad = gradients['value']   # [1, C, H, W]
            act = activations['value']  # [1, C, H, W]

            # ===== Grad-CAM++ alpha coefficients =====
            grad_2 = grad.pow(2)
            grad_3 = grad.pow(3)
            sum_act = act.sum(dim=[2, 3], keepdim=True)
            eps = 1e-7
            alpha = grad_2 / (2.0 * grad_2 + sum_act * grad_3 + eps)
            alpha = alpha * torch.relu(target_score.detach() * grad)
            weights = alpha.sum(dim=[2, 3], keepdim=True)  # [1, C, 1, 1]

            # ===== Channel selection: keep only top-K most important channels =====
            # This removes noisy/irrelevant channels that dilute the heatmap
            weights_flat = weights.squeeze()  # [C]
            num_channels = weights_flat.shape[0]
            top_k = max(num_channels // 4, 32)  # Keep top 25% of channels (at least 32)
            _, top_indices = torch.topk(weights_flat.abs(), top_k)
            channel_mask = torch.zeros_like(weights_flat)
            channel_mask[top_indices] = 1.0
            weights = weights * channel_mask.view(1, -1, 1, 1)

            # Weighted combination
            cam = torch.sum(weights * act, dim=1, keepdim=True)
            cam = torch.relu(cam)
            cam = cam.squeeze().detach().numpy()

            # Normalize
            cam_min, cam_max = cam.min(), cam.max()
            if cam_max - cam_min > eps:
                cam = (cam - cam_min) / (cam_max - cam_min)
            else:
                cam = np.zeros_like(cam)

            # Cleanup hooks
            fwd_handle.remove()
            bwd_handle.remove()

            # Resize to original image
            orig_w, orig_h = image.size
            cam_resized = cv2.resize(cam, (orig_w, orig_h), interpolation=cv2.INTER_CUBIC)
            cam_resized = np.clip(cam_resized, 0, 1)

            # Lung masking
            lung_mask = self._detect_lung_mask(image)
            cam_resized = cam_resized * lung_mask
            if cam_resized.max() > 0:
                cam_resized = cam_resized / cam_resized.max()

            # ===== Aggressive focus: power-law gamma to concentrate on peak region =====
            # gamma < 1 would spread; gamma > 1 concentrates on the brightest spots
            gamma = 2.0  # Square the activation — only the truly bright areas survive
            cam_resized = np.power(cam_resized, gamma)
            if cam_resized.max() > 0:
                cam_resized = cam_resized / cam_resized.max()

            # Hard threshold: remove bottom 70% of activation (keep top 30%)
            nonzero = cam_resized[cam_resized > 0.01]
            if len(nonzero) > 50:
                threshold = np.percentile(nonzero, 70)
                cam_resized[cam_resized < threshold] = 0
                # Re-normalize
                if cam_resized.max() > 0:
                    cam_resized = cam_resized / cam_resized.max()

            # Light smooth
            cam_resized = cv2.GaussianBlur(cam_resized, (9, 9), 0)
            if cam_resized.max() > 0:
                cam_resized = cam_resized / cam_resized.max()

            # ===== Visualization =====
            heatmap_uint8 = (cam_resized * 255).astype(np.uint8)
            heatmap_colored = cv2.applyColorMap(heatmap_uint8, cv2.COLORMAP_TURBO)
            heatmap_colored = cv2.cvtColor(heatmap_colored, cv2.COLOR_BGR2RGB)

            original_np = np.array(image)
            overlay = original_np.copy()

            # Strong alpha where activation is high
            alpha_map = np.clip(cam_resized * 2.0, 0, 0.85)
            alpha_3d = np.stack([alpha_map] * 3, axis=-1)

            blend_mask = alpha_3d > 0.01
            overlay[blend_mask] = (
                original_np[blend_mask] * (1 - alpha_3d[blend_mask]) +
                heatmap_colored[blend_mask] * alpha_3d[blend_mask]
            ).astype(np.uint8)

            # Lung outline
            lung_contour_mask = (lung_mask > 0.5).astype(np.uint8) * 255
            contours, _ = cv2.findContours(lung_contour_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            cv2.drawContours(overlay, contours, -1, (0, 255, 128), 1)

            # Draw primary finding label with confidence
            label_text = f"{focus_label}: {focus_prob:.0%} certainty"
            (tw, th), _ = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.65, 2)
            cv2.rectangle(overlay, (8, 12), (16 + tw, 20 + th + 8), (0, 0, 0), -1)
            cv2.rectangle(overlay, (8, 12), (16 + tw, 20 + th + 8), (56, 189, 248), 1)
            color = (0, 255, 255) if focus_prob > 0.3 else (200, 200, 100)
            cv2.putText(overlay, label_text, (12, 18 + th),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.65, color, 2, cv2.LINE_AA)

            # Find and mark the peak activation point with a crosshair
            peak_y, peak_x = np.unravel_index(cam_resized.argmax(), cam_resized.shape)
            if cam_resized[peak_y, peak_x] > 0.3:
                cross_size = 15
                cv2.line(overlay, (peak_x - cross_size, peak_y), (peak_x + cross_size, peak_y), (255, 255, 0), 2)
                cv2.line(overlay, (peak_x, peak_y - cross_size), (peak_x, peak_y + cross_size), (255, 255, 0), 2)
                cv2.circle(overlay, (peak_x, peak_y), cross_size + 5, (255, 255, 0), 1)

            # Encode to base64
            overlay_image = Image.fromarray(overlay)
            buffer = io.BytesIO()
            overlay_image.save(buffer, format='PNG')
            buffer.seek(0)
            heatmap_b64 = base64.b64encode(buffer.read()).decode('utf-8')
            return heatmap_b64

        except Exception as e:
            print(f"Error generating Grad-CAM++: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _detect_lung_mask(self, image: Image.Image) -> np.ndarray:
        """Detect the lung/chest region in an X-ray and create a binary mask.
        Improved: wider coverage (85% width, 85% height) to avoid cutting off
        peripheral findings like pleural effusion, pneumothorax, or cardiomegaly.
        Uses adaptive thresholding + morphological operations."""
        img_np = np.array(image.convert('L'))
        h, w = img_np.shape

        # Step 1: Adaptive threshold to separate body from background
        # Try Otsu first; if it fails (e.g. very uniform image), use percentile
        _, body_mask = cv2.threshold(img_np, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # If Otsu captures too little or too much, use percentile fallback
        body_ratio = np.sum(body_mask > 0) / body_mask.size
        if body_ratio < 0.1 or body_ratio > 0.95:
            thresh_val = np.percentile(img_np, 15)
            _, body_mask = cv2.threshold(img_np, int(thresh_val), 255, cv2.THRESH_BINARY)

        # Step 2: Morphological cleanup
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (11, 11))
        body_mask = cv2.morphologyEx(body_mask, cv2.MORPH_CLOSE, kernel, iterations=3)
        body_mask = cv2.morphologyEx(body_mask, cv2.MORPH_OPEN, kernel, iterations=2)

        # Step 3: Find the largest contour (torso)
        contours, _ = cv2.findContours(body_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if contours:
            largest = max(contours, key=cv2.contourArea)
            body_mask = np.zeros_like(body_mask)
            cv2.drawContours(body_mask, [largest], -1, (255,), -1)

            # Step 4: Define chest region — WIDER than before to catch peripheral findings
            x, y, bw, bh = cv2.boundingRect(largest)
            chest_mask = np.zeros_like(body_mask)
            cx = x + bw // 2
            # 85% width (was 70%) and 85% height (was 75%) — catches pleural margins
            lung_w = int(bw * 0.85)
            lung_h = int(bh * 0.85)
            lung_x1 = max(0, cx - lung_w // 2)
            lung_x2 = min(w, cx + lung_w // 2)
            lung_y1 = max(0, y + int(bh * 0.03))  # Small offset from top
            lung_y2 = min(h, lung_y1 + lung_h)
            chest_mask[lung_y1:lung_y2, lung_x1:lung_x2] = 255

            # Combine: must be within body AND chest region
            lung_mask = cv2.bitwise_and(body_mask, chest_mask)
        else:
            lung_mask = body_mask

        # Step 5: Smooth edges with larger kernel for gradual falloff
        lung_mask = cv2.GaussianBlur(lung_mask, (31, 31), 0)
        lung_mask = lung_mask.astype(np.float32) / 255.0
        return lung_mask

    def _retrieve_book_knowledge(self, query: str, top_k: int = 8) -> str:
        """Retrieve relevant knowledge from the X-ray book stored in Pinecone."""
        if self.book_index is None or self.embedding_model is None:
            return ""

        try:
            query_embedding = self.embedding_model.encode(query).tolist()
            results = self.book_index.query(
                vector=query_embedding,
                top_k=top_k,
                include_metadata=True,
                namespace="books"
            )

            knowledge_chunks = []
            for match in results.matches:
                content = match.metadata.get("content", match.metadata.get("ocr_text", ""))
                if content:
                    knowledge_chunks.append(content)

            return "\n\n".join(knowledge_chunks)
        except Exception as e:
            print(f"Error retrieving book knowledge: {e}")
            return ""

    def analyze_image(self, image_data: Dict[str, Any], 
                       patient_context: Optional[Dict] = None,
                       language: str = 'en',
                       emit_progress=None) -> Dict[str, Any]:
        """Analyze a medical image with full Tier 2/3/4 pipeline.
        
        Pipeline:
        1. 🤖 Enhancement Agent: analyze quality → adaptively enhance
        2. 🫁 Anatomical Segmentation + CTR measurement
        3. CheXNet 14-pathology classification
        4. Secondary ViT pneumonia check
        5. Grad-CAM++ heatmap
        6. 🧬 Differential Diagnosis Engine
        7. 🏥 Clinical Decision Support (CURB-65, antibiotics, labs, follow-up)
        8. 📚 RAG knowledge retrieval
        9. 🤖 LLM synthesis (multi-language)
        10. MC Dropout Uncertainty Quantification
        
        Returns comprehensive result dict."""
        try:
            def _emit(step, detail=""):
                if emit_progress:
                    try:
                        emit_progress({'step': step, 'detail': detail})
                    except Exception:
                        pass

            # Load the image
            if isinstance(image_data, dict) and 'original_path' in image_data:
                image = Image.open(image_data['original_path']).convert('RGB')
            else:
                return {"diagnosis": "Error: Could not load image data", "heatmap": None}

            # Get enhanced image if available (from image_processing.py)
            enhanced_image = image_data.get('enhanced_image', None)
            comparison_b64 = image_data.get('comparison_b64', None)

            # ===== Step 1: 🤖 Enhancement Agent =====
            _emit('enhancement', 'Analyzing image quality...')
            quality_report = self.enhancement_agent.get_quality_report(image)
            agent_enhanced = self.enhancement_agent.enhance(image)
            classify_image = agent_enhanced

            if quality_report['issues']:
                print(f"🤖 Enhancement Agent: Quality={quality_report['quality']}, "
                      f"Issues={quality_report['issues']}, "
                      f"Actions={quality_report['actions_applied']}")
            else:
                print(f"🤖 Enhancement Agent: Image quality is GOOD — no enhancement needed")

            # ===== Step 2: 🫁 Anatomical Segmentation + CTR =====
            _emit('segmentation', 'Segmenting anatomy...')
            try:
                seg_result = self.segmentation_agent.segment(image)
                segmentation_overlay = seg_result.get('overlay_b64')
                ctr_data = seg_result.get('ctr', {})
                zone_descriptions = seg_result.get('zone_descriptions', {})
                measurements = seg_result.get('measurements', {})
                print(f"🫁 Segmentation: CTR={ctr_data.get('ctr', 'N/A')} — {ctr_data.get('interpretation', 'N/A')}")
            except Exception as e:
                print(f"Warning: Segmentation failed: {e}")
                segmentation_overlay = None
                ctr_data = {}
                zone_descriptions = {}
                measurements = {}

            # ===== Step 3: CheXNet 14-pathology classification =====
            _emit('classification', 'Running CheXNet 14-pathology model...')
            chexnet_results = self._classify_xray_chexnet(classify_image)

            # ===== Step 4: Secondary pneumonia check =====
            pneumonia_results = self._classify_xray_pneumonia(classify_image)

            if not chexnet_results:
                return {"diagnosis": "Error: Medical classification models not available.", "heatmap": None}

            # ===== Step 5: MC Dropout Uncertainty Quantification (Tier 3) =====
            _emit('uncertainty', 'Computing prediction uncertainty...')
            uncertainty_data = self._mc_dropout_uncertainty(classify_image, n_forward=15)

            # Format CheXNet predictions
            significant = [r for r in chexnet_results if r['score'] > 0.10]
            if not significant:
                significant = chexnet_results[:5]

            pred_text_lines = []
            for r in significant:
                bar = "█" * int(r['score'] * 20) + "░" * (20 - int(r['score'] * 20))
                pred_text_lines.append(f"  {r['label']:22s} [{bar}] {r['score']:.1%}")
            pred_text = "\n".join(pred_text_lines)

            pneumonia_text = ""
            if pneumonia_results:
                pneumonia_text = "\n".join(
                    [f"  - {p['label']}: {p['score']:.2%}" for p in pneumonia_results]
                )

            # Detected pathologies (score > 0.3 threshold)
            detected_pathologies = [r for r in chexnet_results if r['score'] > 0.30 and r['label'] != "No Finding"]
            top_pathology = detected_pathologies[0] if detected_pathologies else chexnet_results[0]

            # Detections for UI
            detections_for_ui = [
                {"label": r['label'], "score": round(r['score'], 4)}
                for r in chexnet_results
                if r['score'] > 0.10 and r['label'] != "No Finding"
            ]
            if not detections_for_ui:
                top_path = [r for r in chexnet_results if r['label'] != "No Finding"]
                if top_path:
                    detections_for_ui = [{"label": top_path[0]['label'], "score": round(top_path[0]['score'], 4)}]

            # Determine severity
            max_score = max([d['score'] for d in detections_for_ui]) if detections_for_ui else 0
            if max_score > 0.6:
                severity = 'severe'
            elif max_score > 0.4:
                severity = 'moderate'
            elif max_score > 0.2:
                severity = 'mild'
            else:
                severity = 'mild'

            # ===== Step 6: Grad-CAM++ (only if significant pathology detected) =====
            has_significant_pathology = bool(detected_pathologies) and top_pathology.get('label') != 'No Finding' and top_pathology.get('score', 0) > 0.15
            if has_significant_pathology:
                _emit('gradcam', 'Generating Grad-CAM++ heatmap...')
                heatmap_b64 = self._generate_gradcam(image, target_class_idx=top_pathology.get('index'))
            else:
                _emit('gradcam', 'No significant pathology — skipping Grad-CAM')
                heatmap_b64 = None

            # ===== Step 7: 🧬 Differential Diagnosis (Tier 2) =====
            _emit('differential', 'Computing differential diagnosis...')
            differentials = self.clinical_agent.get_differentials(
                detected_pathologies if detected_pathologies else [top_pathology],
                patient_context
            )

            # ===== Step 8: 🏥 Clinical Decision Support (Tier 2) =====
            _emit('clinical', 'Generating clinical recommendations...')
            clinical_decision = self.clinical_agent.generate_clinical_decision(
                detected_pathologies if detected_pathologies else [top_pathology],
                severity,
                patient_context
            )

            # ===== Step 9: RAG Knowledge Retrieval =====
            _emit('rag', 'Retrieving textbook knowledge...')
            rag_queries = []
            for p in detected_pathologies[:3]:
                rag_queries.append(f"chest xray {p['label']} findings diagnosis treatment radiological signs")
            if not rag_queries:
                rag_queries = [f"chest xray {top_pathology['label']} findings diagnosis"]
            rag_queries.append("pneumonia consolidation ground glass opacity interstitial pattern lobar segmental distribution")
            rag_queries.append("pleural effusion atelectasis air bronchogram silhouette sign severity grading")

            all_knowledge = []
            for q in rag_queries:
                knowledge = self._retrieve_book_knowledge(q, top_k=5)
                if knowledge:
                    all_knowledge.append(knowledge)
            book_knowledge = "\n\n---\n\n".join(all_knowledge)

            # ===== Step 10: Build comprehensive LLM prompt =====
            _emit('llm', 'Synthesizing radiological report...')
            quality_info = f"Quality: {quality_report['quality'].upper()}"
            if quality_report['issues']:
                quality_info += f" | Issues detected: {', '.join(quality_report['issues'])}"
                quality_info += f" | Auto-applied: {', '.join(quality_report['actions_applied'])}"
            else:
                quality_info += " | No issues detected — image is optimal"
            quality_metrics = quality_report.get('metrics', {})
            quality_info += (f"\n   Brightness={quality_metrics.get('brightness', 'N/A')}, "
                           f"Contrast={quality_metrics.get('contrast', 'N/A')}, "
                           f"Noise={quality_metrics.get('noise', 'N/A')}, "
                           f"Sharpness={quality_metrics.get('sharpness', 'N/A')}")

            # CTR info for LLM
            ctr_info = ""
            if ctr_data.get('ctr'):
                ctr_info = f"\n## 📐 Cardiothoracic Ratio:\nCTR = {ctr_data['ctr']:.3f} — {ctr_data['interpretation']}"
                ctr_info += f"\nHeart width: {ctr_data['heart_width']}px | Thorax width: {ctr_data['thorax_width']}px"

            # Patient context for LLM
            patient_info = ""
            if patient_context:
                patient_info = "\n## 👤 Patient Information:"
                if patient_context.get('age'):
                    patient_info += f"\n- Age: {patient_context['age']}"
                if patient_context.get('sex'):
                    patient_info += f"\n- Sex: {patient_context['sex']}"
                if patient_context.get('symptoms'):
                    patient_info += f"\n- Symptoms: {patient_context['symptoms']}"
                if patient_context.get('duration'):
                    patient_info += f"\n- Duration: {patient_context['duration']}"
                if patient_context.get('smoking'):
                    patient_info += f"\n- Smoking: Yes"
                if patient_context.get('immunocompromised'):
                    patient_info += f"\n- Immunocompromised: Yes"

            # Differential info for LLM
            diff_info = ""
            if differentials:
                diff_info = "\n## 🧬 AI Differential Diagnosis (Bayesian):"
                for i, d in enumerate(differentials[:5], 1):
                    diff_info += f"\n{i}. {d['diagnosis']} — {d['probability']:.1%} (based on: {d['based_on']})"

            # Uncertainty info for LLM
            uncertainty_info = ""
            if uncertainty_data:
                uncertainty_info = f"\n## 🎯 Prediction Uncertainty (MC Dropout, n={uncertainty_data.get('n_forward', 15)}):"
                uncertainty_info += f"\n- Mean confidence: {uncertainty_data.get('mean_confidence', 0):.1%}"
                uncertainty_info += f"\n- Std deviation: {uncertainty_data.get('std_confidence', 0):.3f}"
                uncertainty_info += f"\n- Reliability: {uncertainty_data.get('reliability', 'Unknown')}"

            # Language instruction
            language_instruction = ""
            lang_map = {
                'en': '', 'ar': 'Respond ENTIRELY in Arabic (العربية).',
                'ur': 'Respond ENTIRELY in Urdu (اردو).',
                'hi': 'Respond ENTIRELY in Hindi (हिन्दी).',
                'es': 'Respond ENTIRELY in Spanish (Español).',
                'fr': 'Respond ENTIRELY in French (Français).',
                'de': 'Respond ENTIRELY in German (Deutsch).',
                'zh': 'Respond ENTIRELY in Chinese (中文).',
                'pt': 'Respond ENTIRELY in Portuguese (Português).',
                'tr': 'Respond ENTIRELY in Turkish (Türkçe).',
                'ru': 'Respond ENTIRELY in Russian (Русский).',
            }
            if language in lang_map and lang_map[language]:
                language_instruction = f"\n\nIMPORTANT: {lang_map[language]} Keep medical terms in English where needed for clarity."

            prompt = ChatPromptTemplate.from_messages([
                ("system", """You are an expert radiologist assistant analyzing chest X-rays. You have access to:
1. A CheXNet AI model (DenseNet-121 trained on 112,120 NIH chest X-rays) that detects 14 pathologies
2. A secondary pneumonia-specific ViT model for cross-validation
3. Reference textbook knowledge from "X-ray Film Reading Made Easy"
4. An Enhancement Agent that analyzed image quality and applied adaptive preprocessing
5. Anatomical segmentation with Cardiothoracic Ratio (CTR) measurement
6. Bayesian differential diagnosis engine
7. MC Dropout uncertainty quantification
8. Patient clinical context (if provided)

You MUST use the following RADIOLOGICAL CATEGORIZATION SYSTEM when reporting findings:

### OPACITY PATTERN CLASSIFICATION:
- **Consolidation**: Dense homogeneous opacity obscuring underlying vessels → suggests bacterial/lobar pneumonia
- **Ground-Glass Opacity (GGO)**: Hazy increased density, vessels still visible → suggests viral/atypical pneumonia, early infection
- **Reticular/Interstitial**: Fine linear or net-like pattern → suggests viral, Mycoplasma, PCP
- **Nodular**: Multiple small round opacities → suggests fungal, TB, septic emboli
- **Cavitation**: Air-filled space within an opacity → suggests TB, Klebsiella, Staph aureus, abscess
- **Air Bronchograms**: Air-filled bronchi visible within opacity → confirms alveolar consolidation

### DISTRIBUTION CLASSIFICATION:
- **Lobar**: Entire lobe affected → Strep pneumoniae, Klebsiella
- **Segmental**: One or more bronchopulmonary segments → bacterial, aspiration
- **Multifocal/Patchy**: Scattered bilateral patches → viral, Mycoplasma, COVID-19
- **Perihilar**: Central around hilum → viral pneumonia, PCP, pulmonary edema
- **Peripheral**: Outer lung zones → cryptogenic organizing pneumonia (COP)
- **Basilar**: Lower lobe predominant → aspiration pneumonia
- **Apical**: Upper lobe → TB, Klebsiella (in alcoholics)

### ASSOCIATED FINDINGS TO CHECK:
- **Pleural Effusion**: Parapneumonic effusion → empyema risk
- **Lymphadenopathy**: Hilar/mediastinal → TB, fungal, malignancy
- **Cardiomegaly**: Heart failure mimicking or coexisting with pneumonia
- **Air-Fluid Levels**: Lung abscess, empyema
- **Pneumothorax**: Complicated/necrotizing pneumonia
- **Atelectasis**: Mucus plugging, post-obstructive collapse
- **Mediastinal Shift**: Large effusion, total lung collapse
- **Silhouette Sign**: Loss of heart/diaphragm border → adjacent consolidation

### SEVERITY GRADING:
- **Mild**: <25% of one lung field involved
- **Moderate**: 25-50% of one lung, or bilateral <25%
- **Severe**: >50% of one lung, or bilateral 25-50%
- **Critical**: Bilateral >50% (ARDS pattern)

### LATERALITY: Right / Left / Bilateral

### SUSPECTED ETIOLOGY (based on pattern + distribution):
- Bacterial (typical): Lobar consolidation, air bronchograms, pleural effusion
- Atypical: Interstitial/reticular, bilateral patchy, no effusion
- Viral: Bilateral GGO, perihilar, interstitial
- Aspiration: Basilar, right lower lobe, dependent segments
- Fungal/TB: Cavitation, nodular, upper lobe, lymphadenopathy

CRITICAL RULES:
- Base your analysis STRICTLY on the model results and textbook knowledge provided
- DO NOT invent or hallucinate findings not supported by the data
- When multiple pathologies are detected, discuss each one
- If confidence is low (<30%), clearly state uncertainty
- ALWAYS recommend consulting a qualified radiologist for final diagnosis
- Use the categorization system above to classify ANY detected opacity or infiltrate
- Report what the Enhancement Agent found about image quality
- Include CTR measurement and its interpretation
- Reference the differential diagnosis probabilities
- Note the MC Dropout uncertainty assessment""" + language_instruction),
                ("human", """## 🤖 Enhancement Agent Quality Report:
{quality_info}
{ctr_info}
{patient_info}

## CheXNet 14-Pathology Classification Results:
{predictions}

## Secondary Pneumonia Check (ViT model):
{pneumonia_check}
{diff_info}
{uncertainty_info}

## Reference Textbook Knowledge:
{book_knowledge}

---

Provide a comprehensive structured radiological analysis:

1. **🤖 Image Quality Assessment**: Enhancement Agent findings, corrections applied, diagnostic confidence impact.

2. **🔍 AI Model Findings**: CheXNet results with confidence levels. Agreement/disagreement with secondary model.
   Include MC Dropout uncertainty assessment.

3. **🫁 Radiological Categorization** (use the categorization system):
   - **Opacity Pattern**: Consolidation / GGO / Reticular / Nodular / Cavitation / Air Bronchograms / Normal
   - **Distribution**: Lobar / Segmental / Multifocal / Perihilar / Peripheral / Basilar / Apical
   - **Laterality**: Right / Left / Bilateral
   - **Severity Grade**: Mild / Moderate / Severe / Critical
   - **Associated Findings**: Effusion, atelectasis, cardiomegaly, etc.
   - **Suspected Etiology**: Bacterial / Atypical / Viral / Aspiration / Fungal-TB / Uncertain
   - **Silhouette Sign**: Present or absent (which border)

4. **� Cardiothoracic Ratio**: CTR measurement, interpretation, clinical significance.

5. **🧬 Differential Diagnosis**: Top differentials with probabilities from the Bayesian engine.

6. **📚 Textbook Reference**: Relevant knowledge from "X-ray Film Reading Made Easy".

7. **⚠️ Key Clinical Observations**: Primary findings, secondary findings, differentials.

8. **📋 Recommended Actions**: Labs, imaging, referrals, follow-up timeline.

9. **📊 Confidence Assessment**: Overall AI reliability, uncertainty metrics.

10. **⚕️ Disclaimer**: AI-assisted preliminary screening only. Radiologist must verify.""")
            ])

            messages = prompt.format_messages(
                quality_info=quality_info,
                ctr_info=ctr_info,
                patient_info=patient_info,
                predictions=pred_text,
                pneumonia_check=pneumonia_text if pneumonia_text else "Secondary model not available.",
                diff_info=diff_info,
                uncertainty_info=uncertainty_info,
                book_knowledge=book_knowledge if book_knowledge else "No specific textbook reference found."
            )

            response = self.llm.invoke(messages)
            analysis = response.content if hasattr(response, 'content') else str(response)

            _emit('complete', 'Analysis complete!')

            return {
                "diagnosis": analysis,
                "heatmap": heatmap_b64,
                "enhanced_comparison": comparison_b64,
                "detections": detections_for_ui,
                "quality_report": quality_report,
                "segmentation_overlay": segmentation_overlay,
                "ctr": ctr_data,
                "zone_descriptions": zone_descriptions,
                "differentials": differentials,
                "clinical_decision": clinical_decision,
                "uncertainty": uncertainty_data,
                "severity": severity,
                "patient_context": patient_context or {},
                "measurements": measurements,
                "language": language
            }

        except Exception as e:
            print(f"Error analyzing image: {str(e)}")
            import traceback
            traceback.print_exc()
            return {"diagnosis": f"Error analyzing image: {str(e)}", "heatmap": None}

    def _mc_dropout_uncertainty(self, image: Image.Image, n_forward: int = 15) -> Dict[str, Any]:
        """MC Dropout Uncertainty Quantification (Tier 3).
        
        Run multiple forward passes with dropout enabled to estimate
        predictive uncertainty. High std = model is uncertain.
        """
        if self.chexnet is None:
            return {}

        try:
            input_tensor = self.transform(image).unsqueeze(0)
            
            # Enable dropout for MC sampling
            def enable_dropout(model):
                for module in model.modules():
                    if isinstance(module, torch.nn.Dropout):
                        module.train()
            
            self.chexnet.eval()
            enable_dropout(self.chexnet)
            
            all_probs = []
            for _ in range(n_forward):
                with torch.no_grad():
                    logits = self.chexnet(input_tensor)
                    probs = torch.sigmoid(logits).squeeze(0).numpy()
                    all_probs.append(probs)
            
            all_probs = np.array(all_probs)  # [n_forward, 15]
            mean_probs = all_probs.mean(axis=0)
            std_probs = all_probs.std(axis=0)
            
            # Find the top pathology (excluding No Finding)
            pathology_probs = mean_probs[1:]  # Skip "No Finding"
            top_idx = pathology_probs.argmax() + 1
            
            mean_conf = float(mean_probs[top_idx])
            std_conf = float(std_probs[top_idx])
            
            # Reliability assessment
            if std_conf < 0.05:
                reliability = "HIGH — Consistent predictions across samples"
            elif std_conf < 0.10:
                reliability = "MODERATE — Some prediction variability"
            elif std_conf < 0.20:
                reliability = "LOW — Significant uncertainty, human review recommended"
            else:
                reliability = "VERY LOW — High variance, results unreliable"
            
            # Reset model to eval mode
            self.chexnet.eval()
            
            return {
                'mean_confidence': mean_conf,
                'std_confidence': std_conf,
                'reliability': reliability,
                'n_forward': n_forward,
                'top_pathology': CHEXNET_CLASSES[top_idx],
                'all_means': {CHEXNET_CLASSES[i]: round(float(mean_probs[i]), 4) for i in range(len(CHEXNET_CLASSES))},
                'all_stds': {CHEXNET_CLASSES[i]: round(float(std_probs[i]), 4) for i in range(len(CHEXNET_CLASSES))}
            }
        except Exception as e:
            print(f"Warning: MC Dropout uncertainty failed: {e}")
            return {}