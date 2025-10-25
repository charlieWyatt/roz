"""
Video processor that generates per-minute heatmap data.
Processes videos in chunks to generate time-series heatmap data.
"""

import cv2
import numpy as np
from pathlib import Path
from typing import List, Tuple, Optional
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class HeatmapMinute:
    """Container for one minute of heatmap data."""

    def __init__(self, timestamp: datetime, heatmap: np.ndarray, frame_count: int):
        self.timestamp = timestamp
        self.heatmap = heatmap
        self.frame_count = frame_count

        # Calculate statistics
        self.total_intensity = float(np.sum(heatmap))
        self.max_intensity = float(np.max(heatmap))
        self.nonzero_pixels = int(np.count_nonzero(heatmap))

    def __repr__(self):
        return (f"HeatmapMinute(timestamp={self.timestamp}, "
                f"total_intensity={self.total_intensity:.2f}, "
                f"frame_count={self.frame_count})")


class VideoHeatmapProcessor:
    """Processes videos to generate per-minute heatmap data."""

    def __init__(self, downscale: float = 0.25, fps: Optional[float] = None):
        """
        Initialize the processor.

        Args:
            downscale: Scale factor for processing (smaller = faster)
            fps: Frame rate override (if None, read from video)
        """
        self.downscale = downscale
        self.fps_override = fps

    def process_video(self, video_path: Path, start_time: datetime) -> List[HeatmapMinute]:
        """
        Process a video and generate per-minute heatmap data.

        Args:
            video_path: Path to video file
            start_time: Timestamp of when the video started recording

        Returns:
            List of HeatmapMinute objects
        """
        logger.info(f"Processing video: {video_path}")

        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            logger.error(f"Failed to open video: {video_path}")
            return []

        # Get video properties
        fps = self.fps_override if self.fps_override else cap.get(
            cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration_seconds = total_frames / fps if fps > 0 else 0

        logger.info(
            f"Video: {total_frames} frames @ {fps:.2f} fps = {duration_seconds:.1f}s")

        # Read first frame to get dimensions
        ret, first_frame = cap.read()
        if not ret:
            logger.error("Failed to read first frame")
            cap.release()
            return []

        h, w = first_frame.shape[:2]
        small_h, small_w = int(h * self.downscale), int(w * self.downscale)

        logger.info(
            f"Heatmap resolution: {small_w}x{small_h} (downscaled from {w}x{h})")

        # Reset to beginning
        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

        # Calculate frames per minute
        frames_per_minute = int(fps * 60)

        # Initialize background subtractor
        bg_subtractor = cv2.createBackgroundSubtractorMOG2(
            history=500,
            varThreshold=16,
            detectShadows=False
        )

        minutes = []
        current_minute_heatmap = np.zeros((small_h, small_w), dtype=np.float32)
        current_minute_start = start_time
        current_minute_frames = 0
        frame_idx = 0

        # Process video frame by frame
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            # Calculate which minute this frame belongs to
            seconds_elapsed = frame_idx / fps
            minute_idx = int(seconds_elapsed // 60)
            frame_minute_start = start_time + timedelta(minutes=minute_idx)

            # If we've moved to a new minute, save the previous one
            if frame_minute_start > current_minute_start and current_minute_frames > 0:
                minute = HeatmapMinute(
                    timestamp=current_minute_start,
                    heatmap=current_minute_heatmap.copy(),
                    frame_count=current_minute_frames
                )
                minutes.append(minute)
                logger.debug(f"Completed minute: {minute}")

                # Start new minute
                current_minute_heatmap = np.zeros(
                    (small_h, small_w), dtype=np.float32)
                current_minute_start = frame_minute_start
                current_minute_frames = 0

            # Process frame
            fg_mask = bg_subtractor.apply(frame)
            small_mask = cv2.resize(fg_mask, (small_w, small_h))
            current_minute_heatmap += small_mask / 255.0

            current_minute_frames += 1
            frame_idx += 1

            # Progress logging every 30 seconds
            if frame_idx % 900 == 0:
                progress = (frame_idx / total_frames) * \
                    100 if total_frames > 0 else 0
                logger.info(f"Progress: {progress:.1f}%")

        # Don't forget the last minute
        if current_minute_frames > 0:
            minute = HeatmapMinute(
                timestamp=current_minute_start,
                heatmap=current_minute_heatmap,
                frame_count=current_minute_frames
            )
            minutes.append(minute)
            logger.debug(f"Completed final minute: {minute}")

        cap.release()

        logger.info(f"Processed {len(minutes)} minutes from video")
        return minutes

    @staticmethod
    def parse_timestamp_from_filename(filename: str) -> Optional[datetime]:
        """
        Extract timestamp from filename.

        Expects format like: clip_2025-10-20_13-57-04.mp4

        Args:
            filename: Video filename

        Returns:
            Datetime object or None if parsing fails
        """
        try:
            # Remove extension and 'clip_' prefix
            name = Path(filename).stem
            if name.startswith('clip_'):
                name = name[5:]  # Remove 'clip_'

            # Parse: 2025-10-20_13-57-04
            date_part, time_part = name.split('_')
            year, month, day = map(int, date_part.split('-'))
            hour, minute, second = map(int, time_part.split('-'))

            return datetime(year, month, day, hour, minute, second)

        except Exception as e:
            logger.warning(
                f"Failed to parse timestamp from filename '{filename}': {e}")
            return None
