#!/usr/bin/env python
"""Create auto-executable screenconnect.zip from ScreenConnect directory"""
import zipfile
import os
import hashlib

def create_zip():
    source_dir = 'ScreenConnect'
    output_file = 'downloads/screenconnect.zip'
    
    # Ensure downloads directory exists with absolute path
    downloads_dir = os.path.abspath('downloads')
    os.makedirs(downloads_dir, exist_ok=True)
    
    # Get files to add
    files = []
    for f in os.listdir(source_dir):
        file_path = os.path.join(source_dir, f)
        if os.path.isfile(file_path):
            files.append(f)
    
    print(f"Files to archive: {files}")
    
    # Create ZIP file with absolute path
    abs_output_file = os.path.join(downloads_dir, 'screenconnect.zip')
    with zipfile.ZipFile(abs_output_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file in files:
            file_path = os.path.join(source_dir, file)
            zipf.write(file_path, file)
            print(f"Added: {file}")
    
    # Calculate and display checksum
    if os.path.exists(abs_output_file):
        with open(abs_output_file, 'rb') as f:
            sha256 = hashlib.sha256(f.read()).hexdigest()
        print(f"\nZIP created successfully!")
        print(f"Path: {abs_output_file}")
        print(f"SHA256: {sha256}")
        return True
    return False

if __name__ == "__main__":
    create_zip()