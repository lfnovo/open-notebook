"""
Archive file processor
Handles ZIP, TAR, GZ archives by extracting and processing contents
"""

import os
import shutil
import tempfile
import zipfile
import tarfile
from pathlib import Path
from typing import List, Tuple

from loguru import logger


def extract_archive(archive_path: str) -> Tuple[str, List[str]]:
    """
    Extract archive to temporary directory and return list of extracted files.
    
    Args:
        archive_path: Path to archive file
        
    Returns:
        Tuple of (temp_dir_path, list_of_extracted_file_paths)
    """
    try:
        logger.info(f"Extracting archive: {Path(archive_path).name}")
        
        # Create temporary directory
        temp_dir = tempfile.mkdtemp(prefix='open_notebook_archive_')
        extracted_files = []
        
        lower_path = archive_path.lower()
        
        # Extract based on file type
        if lower_path.endswith('.zip'):
            with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)
                extracted_files = [
                    os.path.join(temp_dir, name) 
                    for name in zip_ref.namelist() 
                    if not name.endswith('/')
                ]
                
        elif lower_path.endswith(('.tar', '.tar.gz', '.tgz', '.tar.bz2')):
            with tarfile.open(archive_path, 'r:*') as tar_ref:
                tar_ref.extractall(temp_dir)
                extracted_files = [
                    os.path.join(temp_dir, member.name)
                    for member in tar_ref.getmembers()
                    if member.isfile()
                ]
        
        elif lower_path.endswith('.gz') and not lower_path.endswith('.tar.gz'):
            # Single gzipped file
            import gzip
            output_path = os.path.join(temp_dir, Path(archive_path).stem)
            with gzip.open(archive_path, 'rb') as gz_file:
                with open(output_path, 'wb') as out_file:
                    shutil.copyfileobj(gz_file, out_file)
            extracted_files = [output_path]
        
        else:
            raise ValueError(f"Unsupported archive format: {archive_path}")
        
        logger.info(f"Extracted {len(extracted_files)} files from archive")
        return temp_dir, extracted_files
        
    except Exception as e:
        logger.error(f"Failed to extract archive {archive_path}: {e}")
        # Clean up temp dir on error
        if 'temp_dir' in locals():
            try:
                shutil.rmtree(temp_dir)
            except Exception:
                pass
        raise


def cleanup_temp_dir(temp_dir: str):
    """
    Clean up temporary extraction directory.
    
    Args:
        temp_dir: Path to temporary directory
    """
    try:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
            logger.debug(f"Cleaned up temporary directory: {temp_dir}")
    except Exception as e:
        logger.warning(f"Failed to clean up temporary directory {temp_dir}: {e}")


def is_archive_file(file_path: str) -> bool:
    """
    Check if file is a supported archive format.
    
    Args:
        file_path: Path to check
        
    Returns:
        True if file is a supported archive
    """
    lower_path = file_path.lower()
    return lower_path.endswith(('.zip', '.tar', '.tar.gz', '.tgz', '.tar.bz2', '.gz'))


def get_processable_files(file_list: List[str]) -> List[str]:
    """
    Filter list of files to only include processable document types.
    
    Args:
        file_list: List of file paths
        
    Returns:
        Filtered list of processable files
    """
    processable_extensions = {
        '.pdf', '.doc', '.docx', '.ppt', '.pptx', '.xls', '.xlsx',
        '.txt', '.md', '.epub', '.html', '.htm'
    }
    
    processable = []
    for file_path in file_list:
        ext = Path(file_path).suffix.lower()
        if ext in processable_extensions:
            processable.append(file_path)
    
    logger.info(f"Found {len(processable)} processable files out of {len(file_list)} total")
    return processable