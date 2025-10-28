"""
Configuration management for the heatmap worker.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# PostgreSQL Database Configuration
# For direct connections (individual params)
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = int(os.getenv('DB_PORT', '5432'))
DB_NAME = os.getenv('DB_NAME', 'postgres')
DB_USER = os.getenv('DB_USER', '')
DB_PASSWORD = os.getenv('DB_PASSWORD', '')

# Alternative: Connection string (useful for Supabase pooler)
DB_CONNECTION_STRING = os.getenv('DATABASE_URL', '')
# Note: DB credentials are required for worker/processing scripts but not for S3-only scripts

# S3/Cloudflare R2 Configuration
S3_ENDPOINT_URL = os.getenv(
    'S3_ENDPOINT_URL',
    'https://75ae5041529c1b7efc9e8196bbb9cf57.r2.cloudflarestorage.com'
)
S3_ACCESS_KEY = os.getenv('S3_ACCESS_KEY', '')
S3_SECRET_KEY = os.getenv('S3_SECRET_KEY', '')
S3_BUCKET_NAME = os.getenv('S3_BUCKET_NAME', 'roz')

# S3 Directory structure
S3_VIDEOS_PREFIX = os.getenv('S3_VIDEOS_PREFIX', 'raw_videos/')
S3_HEATMAPS_PREFIX = os.getenv('S3_HEATMAPS_PREFIX', 'heatmaps/')

# Local storage
LOCAL_TEMP_DIR = os.getenv('LOCAL_TEMP_DIR', './temp')
LOCAL_DOWNLOADS_DIR = os.path.join(LOCAL_TEMP_DIR, 'downloads')
LOCAL_HEATMAPS_DIR = os.path.join(LOCAL_TEMP_DIR, 'heatmaps')

# Video processing
VIDEO_PREFIX = os.getenv('VIDEO_PREFIX', '')
VIDEO_EXTENSION = os.getenv('VIDEO_EXTENSION', '.mp4')

# Heatmap settings
USE_BACKGROUND = os.getenv('USE_BACKGROUND', 'true').lower() == 'true'
DOWNSCALE = float(os.getenv('DOWNSCALE', '0.25'))

# Worker settings
MAX_VIDEOS_PER_RUN = int(os.getenv('MAX_VIDEOS_PER_RUN', '10'))
CLEANUP_LOCAL_FILES = os.getenv(
    'CLEANUP_LOCAL_FILES', 'true').lower() == 'true'

# Camera identification
CAMERA_ID = os.getenv('CAMERA_ID', 'default')

# Data retention
RETENTION_DAYS = int(os.getenv('RETENTION_DAYS', '90'))


def ensure_directories():
    """Create necessary local directories if they don't exist."""
    Path(LOCAL_DOWNLOADS_DIR).mkdir(parents=True, exist_ok=True)
    Path(LOCAL_HEATMAPS_DIR).mkdir(parents=True, exist_ok=True)
