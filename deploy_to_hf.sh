#!/bin/bash
# =====================================================
# 🚀 Deploy Medical X-ray AI to Hugging Face Spaces
# =====================================================
#
# Prerequisites:
#   1. A Hugging Face account (https://huggingface.co/join)
#   2. A Hugging Face token with WRITE access
#      → Go to: https://huggingface.co/settings/tokens
#      → Create a new token with "Write" permission
#
# Usage:
#   chmod +x deploy_to_hf.sh
#   ./deploy_to_hf.sh
# =====================================================

set -e

echo "🏥 Medical X-ray AI — Hugging Face Spaces Deployment"
echo "====================================================="
echo ""

# Check if huggingface-cli is available
if ! command -v huggingface-cli &> /dev/null; then
    echo "📦 Installing huggingface_hub..."
    pip install huggingface_hub -q
fi

# Login check
echo "🔑 Step 1: Hugging Face Authentication"
echo "---------------------------------------"
if ! python3 -c "from huggingface_hub import HfApi; HfApi().whoami()" 2>/dev/null; then
    echo "You need to log in to Hugging Face."
    echo "Get your token from: https://huggingface.co/settings/tokens"
    echo ""
    huggingface-cli login
fi

WHOAMI=$(python3 -c "from huggingface_hub import HfApi; print(HfApi().whoami()['name'])")
echo "✅ Logged in as: $WHOAMI"
echo ""

# Space name
SPACE_NAME="medical-xray-ai"
REPO_ID="$WHOAMI/$SPACE_NAME"

echo "🚀 Step 2: Creating Hugging Face Space"
echo "---------------------------------------"
echo "Space: $REPO_ID"
echo ""

# Create the space
python3 << PYTHON_SCRIPT
from huggingface_hub import HfApi, create_repo
import os

api = HfApi()
repo_id = "$REPO_ID"

# Create the Space (Docker SDK)
try:
    create_repo(
        repo_id=repo_id,
        repo_type="space",
        space_sdk="docker",
        private=False,
        exist_ok=True
    )
    print(f"✅ Space created/exists: https://huggingface.co/spaces/{repo_id}")
except Exception as e:
    print(f"Space creation: {e}")

# Set secrets
print("\n🔐 Step 3: Setting environment secrets...")
secrets = {}

# Read from .env file
env_file = os.path.join(os.path.dirname(os.path.abspath("$0")), ".env")
if os.path.exists(".env"):
    with open(".env") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                key = key.strip()
                val = val.strip()
                if key in ("GROQ_API_KEY", "PINECONE_API_KEY", "PINECONE_ENVIRONMENT"):
                    if val and not val.startswith("your_"):
                        secrets[key] = val

for key, val in secrets.items():
    try:
        api.add_space_secret(repo_id=repo_id, key=key, value=val)
        print(f"  ✅ {key} set")
    except Exception as e:
        print(f"  ⚠️  {key}: {e}")

if not secrets:
    print("  ⚠️  No secrets found in .env — you'll need to set them manually:")
    print("     Go to: https://huggingface.co/spaces/{}/settings".format(repo_id))
    print("     Add: GROQ_API_KEY, PINECONE_API_KEY, PINECONE_ENVIRONMENT")

PYTHON_SCRIPT

echo ""
echo "📤 Step 4: Uploading application files..."
echo "------------------------------------------"

# Upload all files using the HF API
python3 << 'UPLOAD_SCRIPT'
from huggingface_hub import HfApi
import os

api = HfApi()
repo_id = os.environ.get("REPO_ID", "") or "$REPO_ID"

# Files and folders to upload
upload_items = [
    "app.py",
    "requirements.txt",
    "Dockerfile",
    "README.md",
    ".dockerignore",
    "agents/",
    "templates/",
    "utils/",
    "vectordb/__init__.py",
    "vectordb/book_vectordb.py",
    "vectordb/upload_to_vectordb.py",
]

# Upload individual files
for item in upload_items:
    if os.path.isfile(item):
        print(f"  📄 Uploading {item}...")
        api.upload_file(
            path_or_fileobj=item,
            path_in_repo=item,
            repo_id=repo_id,
            repo_type="space"
        )
    elif os.path.isdir(item.rstrip("/")):
        folder = item.rstrip("/")
        print(f"  📁 Uploading {folder}/...")
        api.upload_folder(
            folder_path=folder,
            path_in_repo=folder,
            repo_id=repo_id,
            repo_type="space",
            ignore_patterns=["__pycache__/*", "*.pyc"]
        )

# Upload books directory for RAG (if it exists and has files)
if os.path.isdir("books") and os.listdir("books"):
    print("  📚 Uploading books/...")
    api.upload_folder(
        folder_path="books",
        path_in_repo="books",
        repo_id=repo_id,
        repo_type="space",
        ignore_patterns=["__pycache__/*"]
    )

# Create empty directories that are needed
for empty_dir in ["static/uploads", "static/reports", "data", "uploads/books"]:
    placeholder = os.path.join(empty_dir, ".gitkeep")
    os.makedirs(empty_dir, exist_ok=True)
    if not os.path.exists(placeholder):
        open(placeholder, "w").close()
    api.upload_file(
        path_or_fileobj=placeholder,
        path_in_repo=placeholder,
        repo_id=repo_id,
        repo_type="space"
    )
    print(f"  📁 Created {empty_dir}/")

print("\n✅ All files uploaded!")
UPLOAD_SCRIPT

echo ""
echo "====================================================="
echo "🎉 DEPLOYMENT COMPLETE!"
echo "====================================================="
echo ""
echo "Your app is now building on Hugging Face Spaces."
echo ""
echo "🔗 Live URL: https://huggingface.co/spaces/$REPO_ID"
echo "⚙️  Settings: https://huggingface.co/spaces/$REPO_ID/settings"
echo "📊 Build log: https://huggingface.co/spaces/$REPO_ID/logs/build"
echo ""
echo "⏱️  First build takes ~5-10 minutes (downloading models)."
echo "   Subsequent updates are faster due to Docker layer caching."
echo ""
echo "📌 To update later, just run this script again!"
echo ""
