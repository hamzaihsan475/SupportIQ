"""Shared helpers for image upload validation and on-disk persistence.

Used by both public listing submission (routes/listings.py) and admin
listing creation (routes/admin.py) so the rules (5MB max, jpg/png/webp only)
stay in one place.
"""
from __future__ import annotations

import os
import uuid
from typing import List, Tuple

from fastapi import HTTPException, UploadFile, status

# --- Configuration -----------------------------------------------------------

# Stored under the frontend's /static mount so the existing StaticFiles mount
# in main.py serves these files automatically at /static/uploads/listings/...
UPLOAD_DIR_REL = os.path.join("frontend", "static", "uploads", "listings")

# Frontend static dir is resolved relative to this backend file's location.
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR_ABS = os.path.normpath(os.path.join(BACKEND_DIR, "..", "..", UPLOAD_DIR_REL))

# Public URL prefix served by FastAPI StaticFiles mount("/static", ...).
PUBLIC_URL_PREFIX = "/static/uploads/listings"

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB
MAX_IMAGES_PER_LISTING = 5

# Maps a validated content-type back to a canonical file extension.
_CONTENT_TYPE_TO_EXT = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}


def ensure_upload_dir() -> None:
    """Create the on-disk upload directory if it does not already exist."""
    os.makedirs(UPLOAD_DIR_ABS, exist_ok=True)


def _validate_image(file: UploadFile, size_bytes: int) -> None:
    """Raise HTTPException(400) if a single file fails the rules."""
    # Browsers sometimes send an empty content_type for empty file inputs.
    ctype = (file.content_type or "").lower()
    if ctype not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Invalid file type for '{file.filename or 'unnamed'}': "
                f"'{ctype or 'unknown'}'. Only JPG, PNG, and WebP are allowed."
            ),
        )
    if size_bytes > MAX_FILE_SIZE_BYTES:
        mb = size_bytes / (1024 * 1024)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"File '{file.filename or 'unnamed'}' is too large ({mb:.2f} MB). "
                f"Maximum allowed size is 5 MB."
            ),
        )


def save_listing_images(files: List[UploadFile]) -> List[str]:
    """Validate, save to disk, and return a list of public URL paths.

    The returned list is ordered and contains zero or more URLs of the form
    '/static/uploads/listings/<uuid>.<ext>'. An empty list is valid (zero
    images attached). Validation failures raise 400 BEFORE any file is
    written to disk, so a partial upload never persists.
    """
    # Normalize: a single <input> may submit empty file entries.
    real_files = [f for f in files if f and f.filename]
    if len(real_files) > MAX_IMAGES_PER_LISTING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Too many images: {len(real_files)} submitted, "
                f"maximum is {MAX_IMAGES_PER_LISTING}."
            ),
        )

    ensure_upload_dir()

    saved_urls: List[str] = []
    try:
        for f in real_files:
            # Read the whole body so we can check size deterministically.
            # UploadFile keeps the file in memory anyway for small files;
            # the explicit read is what gives us an accurate byte count.
            contents = f.file.read()
            _validate_image(f, len(contents))

            ext = _CONTENT_TYPE_TO_EXT[f.content_type.lower()]
            unique_name = f"{uuid.uuid4().hex}{ext}"
            abs_path = os.path.join(UPLOAD_DIR_ABS, unique_name)

            with open(abs_path, "wb") as out:
                out.write(contents)

            saved_urls.append(f"{PUBLIC_URL_PREFIX}/{unique_name}")
    except HTTPException:
        # Re-raise validation errors as-is. We must not leave orphan files
        # on disk if a later file in the same batch failed validation, so
        # clean up any we managed to save before the failure.
        for url in saved_urls:
            try:
                os.remove(os.path.join(UPLOAD_DIR_ABS, os.path.basename(url)))
            except OSError:
                pass
        raise
    finally:
        for f in real_files:
            try:
                f.file.close()
            except Exception:
                pass

    return saved_urls
