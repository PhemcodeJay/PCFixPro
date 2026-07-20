#!/usr/bin/env python
"""Create screenconnect.zip archive"""
import zipfile
import os
import hashlib
import base64

def main():
    # Create ZIP file
    zip_content = []
    base = r'c:\Users\Bossman\Documents\PCFixPro'
    source = os.path.join(base, 'ScreenConnect')
    
    # Get all files
    files_data = {}
    for f in os.listdir(source):
        fp = os.path.join(source, f)
        if os.path.isfile(fp):
            with open(fp, 'rb') as file:
                files_data[f] = file.read()
    
    # Create ZIP data
    import io
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for name, data in files_data.items():
            zipf.writestr(name, data)
    
    zip_data = zip_buffer.getvalue()
    checksum = hashlib.sha256(zip_data).hexdigest()
    
    print(f"Files to archive: {list(files_data.keys())}")
    print(f"ZIP size: {len(zip_data)} bytes")
    print(f"SHA256: {checksum}")
    
    # Save to Desktop or temp location
    temp_path = os.path.join(os.environ.get('USERPROFILE', ''), 'Desktop', 'screenconnect.zip')
    os.makedirs(os.path.dirname(temp_path), exist_ok=True)
    with open(temp_path, 'wb') as f:
        f.write(zip_data)
    print(f"Saved to: {temp_path}")
    print(f"Exists check: {os.path.exists(temp_path)}")

if __name__ == "__main__":
    main()