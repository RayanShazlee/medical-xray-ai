---
title: Medical X-ray AI Clinical Platform
emoji: 🏥
colorFrom: blue
colorTo: indigo
sdk: docker
pinned: false
license: mit
app_port: 7860
---

# 🏥 Medical X-ray AI Clinical Platform

Advanced AI-powered chest X-ray analysis with clinical decision support.

## Features

- 🔬 **CheXNet 14-Pathology Detection** — DenseNet-121 trained on 112K+ NIH chest X-rays
- 🤖 **Enhancement Agent** — Adaptive image preprocessing with calibrated thresholds
- 🔥 **Grad-CAM++ Heatmaps** — Pixel-level disease localization
- 🫁 **Anatomical Segmentation** — Lung fields, heart, mediastinum, CTR measurement
- 🧠 **Differential Diagnosis** — Bayesian-adjusted with patient context modifiers
- 💊 **Clinical Decision Support** — CURB-65, antibiotic guidelines, lab recommendations
- 📊 **Uncertainty Quantification** — MC Dropout with reliability assessment
- 🩻 **DICOM Support** — Full metadata extraction and VOI windowing
- 📄 **PDF Reports** — Professional radiology-style exports
- 🌐 **Multi-Language** — 11 languages supported
- 📚 **RAG Knowledge Base** — Textbook-referenced analysis

## Environment Variables

Set these as **Secrets** in your Hugging Face Space settings:

| Variable | Description |
|----------|-------------|
| `GROQ_API_KEY` | Groq API key for LLM inference |
| `PINECONE_API_KEY` | Pinecone API key for RAG knowledge base |
| `PINECONE_ENVIRONMENT` | Pinecone environment (e.g., `us-east-1-aws`) |

## Usage

1. Upload a chest X-ray image (PNG, JPG, or DICOM)
2. Optionally fill in patient context (age, sex, symptoms)
3. Select report language
4. Click "Analyze X-ray Image"
5. Review the comprehensive AI analysis
6. Export as PDF if needed

## Disclaimer

⚠️ This is an AI-assisted screening tool for **educational and research purposes only**.
All findings must be verified by a qualified radiologist. Not intended for clinical diagnosis.