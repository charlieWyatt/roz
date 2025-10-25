"""
Simple heatmap generation using background subtraction.
"""

import cv2
import numpy as np
from pathlib import Path
from typing import Optional
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')


def generate_heatmap(video_path: Path, downscale: float = 0.25) -> Optional[np.ndarray]:
    """
    Generate heatmap from video using background subtraction.

    Args:
        video_path: Path to video file
        downscale: Scale factor for processing (smaller = faster)

    Returns:
        Heatmap array or None if failed
    """
    cap = cv2.VideoCapture(str(video_path))
    ret, frame = cap.read()
    if not ret:
        return None

    h, w = frame.shape[:2]
    heatmap = np.zeros((int(h*downscale), int(w*downscale)), dtype=np.float32)
    bg_subtractor = cv2.createBackgroundSubtractorMOG2(
        history=500,
        varThreshold=16,
        detectShadows=False
    )

    while ret:
        fg_mask = bg_subtractor.apply(frame)
        small = cv2.resize(fg_mask, (0, 0), fx=downscale, fy=downscale)
        heatmap += small / 255.0
        ret, frame = cap.read()

    cap.release()
    return heatmap


def save_heatmap(heatmap: np.ndarray,
                 output_path: Path,
                 reference_frame: Optional[np.ndarray] = None,
                 colormap: str = 'jet',
                 alpha: float = 0.6):
    """
    Save heatmap as image file.

    Args:
        heatmap: Heatmap array from generate_heatmap
        output_path: Path to save image
        reference_frame: Optional background frame
        colormap: Matplotlib colormap name
        alpha: Transparency (0-1)
    """
    # Normalize
    if heatmap.max() > 0:
        normalized = heatmap / heatmap.max()
    else:
        normalized = heatmap

    # Apply gaussian blur
    blurred = cv2.GaussianBlur(normalized, (51, 51), 0)

    # Create figure
    fig, ax = plt.subplots(figsize=(16, 9), dpi=150)

    # Background frame if provided
    if reference_frame is not None:
        ax.imshow(cv2.cvtColor(reference_frame, cv2.COLOR_BGR2RGB))

    # Overlay heatmap
    ax.imshow(blurred, cmap=colormap, alpha=alpha, interpolation='bilinear')
    ax.axis('off')

    # Save
    plt.tight_layout()
    plt.savefig(output_path, bbox_inches='tight', dpi=150, format='jpg')
    plt.close(fig)


def get_reference_frame(video_path: Path) -> Optional[np.ndarray]:
    """
    Extract a reference frame from video (middle frame).

    Args:
        video_path: Path to video file

    Returns:
        Frame as numpy array or None
    """
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        return None

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    frame_number = total_frames // 2

    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
    ret, frame = cap.read()
    cap.release()

    return frame if ret else None


def create_heatmap_from_video(video_path: Path,
                              output_path: Path,
                              use_background: bool = True,
                              downscale: float = 0.25) -> bool:
    """
    Complete pipeline: generate and save heatmap from video.

    Args:
        video_path: Path to input video
        output_path: Path to save heatmap image
        use_background: Whether to overlay on video frame
        downscale: Processing scale factor

    Returns:
        True if successful, False otherwise
    """
    try:
        # Generate heatmap
        heatmap = generate_heatmap(video_path, downscale)
        if heatmap is None:
            return False

        # Get reference frame if requested
        reference_frame = None
        if use_background:
            reference_frame = get_reference_frame(video_path)

        # Save
        save_heatmap(heatmap, output_path, reference_frame)
        return True

    except Exception as e:
        print(f"Error creating heatmap: {e}")
        return False
