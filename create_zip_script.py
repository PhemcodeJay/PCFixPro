#!/usr/bin/env python
"""Create screenconnect.zip from ScreenConnect directory"""
import zipfile
import os
import hashlib

def main():
    base = r'c:\Users\Bossman\Documents\PCFixPro'
    source = os.path.join(base, 'ScreenConnect')
    output = os.path.join(base, 'downloads', 'screenconnect.zip')
    
    print(f"Source directory: {source}")
    print(f"File exists check: {os.path.exists(source)}")
    
    files = os.listdir(source)
    print(f"Files found: {files}")
    
    # Create directory
    out_dir = os.path.dirname(output)
    os.makedirs(out_dir, exist_ok=True)
    
    # Create ZIP
    with open(output, 'wb') as f:
        pass  # Create empty file
    
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for f in files:
            fp = os.path.join(source, f)
            if os.path.isfile(fp):
                zipf.write(fp, f)
                print(f"Added: {f}")
    
    # Verify
    if os.path.exists(output):
        with open(output, 'rb') as f:
            checksum = hashlib.sha256(f.read()).hexdigest()
        print(f"\nZIP created successfully!")
        print(f"Path: {output}")
        print(f"SHA256: {checksum}")
    else:
        print("ZIP creation failed!")

if __name__ == "__main__":
    main()