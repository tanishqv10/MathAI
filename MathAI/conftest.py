"""
Pytest configuration - adds project root to Python path and loads .env.
"""
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path so 'core' module can be imported
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Load .env file so tests can access OPENAI_API_KEY
load_dotenv(project_root / ".env")

