"""
File operation utilities for IDA Plugin Manager.

Provides safe file operations including copy, delete, backup, etc.
"""

import hashlib
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import Optional

from src.utils.logger import get_logger

logger = get_logger(__name__)


class Result:
    """
    Standard result object for file operations.

    Provides consistent success/error reporting.
    """

    def __init__(self, success: bool, data=None, error: Optional[str] = None):
        """
        Initialize result.

        Args:
            success: Whether operation succeeded
            data: Optional data payload
            error: Optional error message
        """
        self.success = success
        self.data = data
        self.error = error

    def __bool__(self) -> bool:
        """Return True if operation succeeded."""
        return self.success

    @staticmethod
    def ok(data=None) -> "Result":
        """Create successful result."""
        return Result(True, data, None)

    @staticmethod
    def fail(error: str) -> "Result":
        """Create failed result."""
        return Result(False, None, error)


def safe_copy_file(src: Path, dst: Path) -> Result:
    """
    Safely copy a file.

    Args:
        src: Source file path
        dst: Destination file path

    Returns:
        Result object
    """
    try:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        logger.debug(f"Copied {src} to {dst}")
        return Result.ok(dst)
    except Exception as e:
        logger.error(f"Failed to copy {src} to {dst}: {e}")
        return Result.fail(str(e))


def safe_copy_directory(src: Path, dst: Path) -> Result:
    """
    Safely copy a directory.

    Args:
        src: Source directory path
        dst: Destination directory path

    Returns:
        Result object
    """
    try:
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(src, dst)
        logger.debug(f"Copied directory {src} to {dst}")
        return Result.ok(dst)
    except Exception as e:
        logger.error(f"Failed to copy directory {src} to {dst}: {e}")
        return Result.fail(str(e))


def safe_delete_file(path: Path) -> Result:
    """
    Safely delete a file.

    Args:
        path: File path to delete

    Returns:
        Result object
    """
    try:
        if path.exists():
            path.unlink()
            logger.debug(f"Deleted file {path}")
        return Result.ok()
    except Exception as e:
        logger.error(f"Failed to delete file {path}: {e}")
        return Result.fail(str(e))


def safe_delete_directory(path: Path) -> Result:
    """
    Safely delete a directory.

    Args:
        path: Directory path to delete

    Returns:
        Result object
    """
    try:
        if path.exists() and path.is_dir():
            shutil.rmtree(path)
            logger.debug(f"Deleted directory {path}")
        return Result.ok()
    except Exception as e:
        logger.error(f"Failed to delete directory {path}: {e}")
        return Result.fail(str(e))


def backup_file(file_path: Path, backup_dir: Optional[Path] = None) -> Path:
    """
    Create backup of a file.

    Args:
        file_path: File to backup
        backup_dir: Directory to store backups (default: temp directory)

    Returns:
        Path to backup file
    """
    if backup_dir is None:
        backup_dir = Path(tempfile.gettempdir()) / "ida-plugin-manager" / "backups"

    backup_dir.mkdir(parents=True, exist_ok=True)

    # Create backup filename with timestamp
    import time

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    backup_name = f"{file_path.stem}_{timestamp}{file_path.suffix}"
    backup_path = backup_dir / backup_name

    shutil.copy2(file_path, backup_path)
    logger.info(f"Created backup: {backup_path}")

    return backup_path


def backup_directory(dir_path: Path, backup_dir: Optional[Path] = None) -> Path:
    """
    Create backup of a directory.

    Args:
        dir_path: Directory to backup
        backup_dir: Directory to store backups

    Returns:
        Path to backup directory
    """
    if backup_dir is None:
        backup_dir = Path(tempfile.gettempdir()) / "ida-plugin-manager" / "backups"

    backup_dir.mkdir(parents=True, exist_ok=True)

    # Create backup directory name with timestamp
    import time

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    backup_name = f"{dir_path.name}_{timestamp}"
    backup_path = backup_dir / backup_name

    shutil.copytree(dir_path, backup_path)
    logger.info(f"Created backup: {backup_path}")

    return backup_path


def restore_backup(backup_path: Path, destination: Path) -> Result:
    """
    Restore backup to destination.

    Args:
        backup_path: Path to backup
        destination: Destination path

    Returns:
        Result object
    """
    try:
        if backup_path.is_file():
            shutil.copy2(backup_path, destination)
        elif backup_path.is_dir():
            if destination.exists():
                shutil.rmtree(destination)
            shutil.copytree(backup_path, destination)
        else:
            return Result.fail(f"Backup path does not exist: {backup_path}")

        logger.info(f"Restored backup from {backup_path} to {destination}")
        return Result.ok()
    except Exception as e:
        logger.error(f"Failed to restore backup: {e}")
        return Result.fail(str(e))


def calculate_file_hash(file_path: Path, algorithm: str = "sha256") -> str:
    """
    Calculate hash of a file.

    Args:
        file_path: File to hash
        algorithm: Hash algorithm (default: sha256)

    Returns:
        Hexadecimal hash string
    """
    hash_obj = hashlib.new(algorithm)

    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_obj.update(chunk)

    return hash_obj.hexdigest()


def calculate_directory_hash(dir_path: Path, algorithm: str = "sha256") -> str:
    """
    Calculate combined hash of all files in directory.

    Args:
        dir_path: Directory to hash
        algorithm: Hash algorithm (default: sha256)

    Returns:
        Hexadecimal hash string
    """
    hash_obj = hashlib.new(algorithm)

    for file_path in sorted(dir_path.rglob("*")):
        if file_path.is_file():
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_obj.update(chunk)

    return hash_obj.hexdigest()


def is_directory_empty(path: Path) -> bool:
    """
    Check if directory is empty.

    Args:
        path: Directory path to check

    Returns:
        True if directory is empty, False otherwise
    """
    if not path.exists() or not path.is_dir():
        return True

    try:
        next(path.iterdir())
        return False
    except StopIteration:
        return True


def get_directory_size(path: Path) -> int:
    """
    Calculate total size of directory.

    Args:
        path: Directory path

    Returns:
        Size in bytes
    """
    total_size = 0

    for item in path.rglob("*"):
        if item.is_file():
            total_size += item.stat().st_size

    return total_size


def extract_archive(archive_path: Path, destination: Path) -> Result:
    """
    Extract archive file (zip, tar.gz, etc.).

    Args:
        archive_path: Path to archive file
        destination: Destination directory

    Returns:
        Result object
    """
    try:
        destination.mkdir(parents=True, exist_ok=True)

        if archive_path.suffix == ".zip":
            with zipfile.ZipFile(archive_path, "r") as zip_file:
                zip_file.extractall(destination)
            logger.info(f"Extracted ZIP archive to {destination}")
            return Result.ok(destination)

        elif archive_path.suffix in (".tar", ".gz", ".tgz"):
            import tarfile

            with tarfile.open(archive_path, "r:*") as tar_file:
                tar_file.extractall(destination)
            logger.info(f"Extracted tar archive to {destination}")
            return Result.ok(destination)

        else:
            return Result.fail(f"Unsupported archive format: {archive_path.suffix}")

    except Exception as e:
        logger.error(f"Failed to extract archive {archive_path}: {e}")
        return Result.fail(str(e))


def create_temp_directory(prefix: str = "ida_plugin_") -> Path:
    """
    Create a temporary directory.

    Args:
        prefix: Prefix for directory name

    Returns:
        Path to temporary directory
    """
    temp_dir = Path(tempfile.mkdtemp(prefix=prefix))
    logger.debug(f"Created temporary directory: {temp_dir}")
    return temp_dir


def cleanup_temp_directory(temp_dir: Path) -> Result:
    """
    Clean up temporary directory.

    Args:
        temp_dir: Path to temporary directory

    Returns:
        Result object
    """
    try:
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
            logger.debug(f"Cleaned up temporary directory: {temp_dir}")
        return Result.ok()
    except Exception as e:
        logger.error(f"Failed to cleanup temp directory {temp_dir}: {e}")
        return Result.fail(str(e))
