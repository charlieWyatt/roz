"""
S3 Database Helpers for managing video and heatmap files.
Handles listing, downloading, and uploading files to/from S3 (Cloudflare R2).
"""

import os
import boto3
from botocore.exceptions import ClientError
from typing import List, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class S3Manager:
    """Manages interactions with S3/Cloudflare R2 storage."""

    def __init__(self, endpoint_url: str, access_key: str, secret_key: str, bucket_name: str):
        """
        Initialize S3 client for Cloudflare R2.

        Args:
            endpoint_url: S3 endpoint URL
            access_key: AWS/R2 access key ID
            secret_key: AWS/R2 secret access key
            bucket_name: Name of the bucket
        """
        self.bucket_name = bucket_name
        self.s3_client = boto3.client(
            's3',
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name='auto'  # Cloudflare R2 uses 'auto'
        )
        logger.info(f"S3Manager initialized for bucket: {bucket_name}")

    def list_videos(self, prefix: str = "", extension: str = ".mp4") -> List[str]:
        """
        List all video files in the bucket.

        Args:
            prefix: Optional prefix to filter files (e.g., "2025/10/")
            extension: File extension to filter by (default: .mp4)

        Returns:
            List of S3 keys for video files
        """
        try:
            video_files = []
            paginator = self.s3_client.get_paginator('list_objects_v2')

            for page in paginator.paginate(Bucket=self.bucket_name, Prefix=prefix):
                if 'Contents' not in page:
                    continue

                for obj in page['Contents']:
                    key = obj['Key']
                    if key.endswith(extension) and not self._is_heatmap(key):
                        video_files.append(key)

            logger.info(
                f"Found {len(video_files)} video files with prefix '{prefix}'")
            return video_files

        except ClientError as e:
            logger.error(f"Error listing videos: {e}")
            raise

    def list_heatmaps(self, prefix: str = "") -> List[str]:
        """
        List all heatmap files in the bucket.

        Args:
            prefix: Optional prefix to filter files

        Returns:
            List of S3 keys for heatmap files
        """
        try:
            heatmap_files = []
            paginator = self.s3_client.get_paginator('list_objects_v2')

            for page in paginator.paginate(Bucket=self.bucket_name, Prefix=prefix):
                if 'Contents' not in page:
                    continue

                for obj in page['Contents']:
                    key = obj['Key']
                    if self._is_heatmap(key):
                        heatmap_files.append(key)

            logger.info(
                f"Found {len(heatmap_files)} heatmap files with prefix '{prefix}'")
            return heatmap_files

        except ClientError as e:
            logger.error(f"Error listing heatmaps: {e}")
            raise

    def get_videos_without_heatmaps(self, prefix: str = "") -> List[str]:
        """
        Find all videos that don't have corresponding heatmaps.

        Args:
            prefix: Optional prefix to filter files

        Returns:
            List of S3 keys for videos without heatmaps
        """
        videos = self.list_videos(prefix)
        heatmaps = self.list_heatmaps(prefix)

        # Extract base names from heatmaps (remove _heatmap suffix and extension)
        heatmap_base_names = set()
        for heatmap in heatmaps:
            base_name = heatmap.replace(
                '_heatmap.jpg', '.mp4').replace('_heatmap.png', '.mp4')
            heatmap_base_names.add(base_name)

        # Find videos without heatmaps
        videos_without_heatmaps = [
            v for v in videos if v not in heatmap_base_names]

        logger.info(
            f"Found {len(videos_without_heatmaps)} videos without heatmaps")
        return videos_without_heatmaps

    def download_file(self, s3_key: str, local_path: str) -> bool:
        """
        Download a file from S3 to local storage.

        Args:
            s3_key: S3 object key
            local_path: Local file path to save to

        Returns:
            True if successful, False otherwise
        """
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(local_path), exist_ok=True)

            logger.info(f"Downloading {s3_key} to {local_path}")
            self.s3_client.download_file(self.bucket_name, s3_key, local_path)
            logger.info(f"Successfully downloaded {s3_key}")
            return True

        except ClientError as e:
            logger.error(f"Error downloading {s3_key}: {e}")
            return False

    def upload_file(self, local_path: str, s3_key: str, content_type: Optional[str] = None) -> bool:
        """
        Upload a file from local storage to S3.

        Args:
            local_path: Local file path to upload
            s3_key: S3 object key to upload to
            content_type: Optional content type (e.g., 'image/jpeg')

        Returns:
            True if successful, False otherwise
        """
        try:
            extra_args = {}
            if content_type:
                extra_args['ContentType'] = content_type

            logger.info(f"Uploading {local_path} to {s3_key}")
            self.s3_client.upload_file(
                local_path, self.bucket_name, s3_key, ExtraArgs=extra_args)
            logger.info(f"Successfully uploaded {s3_key}")
            return True

        except ClientError as e:
            logger.error(f"Error uploading {local_path}: {e}")
            return False

    def file_exists(self, s3_key: str) -> bool:
        """
        Check if a file exists in S3.

        Args:
            s3_key: S3 object key to check

        Returns:
            True if file exists, False otherwise
        """
        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=s3_key)
            return True
        except ClientError:
            return False

    def get_heatmap_key_for_video(self, video_key: str, extension: str = ".jpg") -> str:
        """
        Generate the S3 key for a heatmap corresponding to a video.

        Args:
            video_key: S3 key of the video file
            extension: Extension for heatmap file (default: .jpg)

        Returns:
            S3 key for the heatmap file
        """
        base_key = os.path.splitext(video_key)[0]
        return f"{base_key}_heatmap{extension}"

    @staticmethod
    def _is_heatmap(key: str) -> bool:
        """
        Check if a key represents a heatmap file.

        Args:
            key: S3 object key

        Returns:
            True if key represents a heatmap, False otherwise
        """
        return '_heatmap.' in key.lower()

    def get_file_size(self, s3_key: str) -> Optional[int]:
        """
        Get the size of a file in S3.

        Args:
            s3_key: S3 object key

        Returns:
            File size in bytes, or None if file doesn't exist
        """
        try:
            response = self.s3_client.head_object(
                Bucket=self.bucket_name, Key=s3_key)
            return response['ContentLength']
        except ClientError:
            return None
