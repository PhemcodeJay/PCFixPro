#!/usr/bin/env python
"""
Create screenconnect.zip - Auto-executable ZIP for ScreenConnect Enterprise Gateway

Usage: python create_screenconnect_zip.py

This script creates an auto-executable ZIP containing:
- install.bat (MSI wrapper with tunnel setup)
- gateway_heartbeat.py (real-time monitoring)
- enterprise_tunnel.py (100 concurrent user support)
- config.txt (self-extracting configuration)
- ScreenConnect.ClientSetup(4).msi (main installer)
- 7zS2.sfx (self-extracting module)
"""
import zipfile
import os
import hashlib

def create_zip():
    source_dir = 'ScreenConnect'
    output_dir = os.path.expandvars(r'%USERPROFILE%\Desktop')
    output_file = os.path.join(output_dir, 'screenconnect.zip')
    
    print("Creating screenconnect.zip...")
    print("-" * 40)
    
    # Get files to add
    files = []
    for f in os.listdir(source_dir):
        file_path = os.path.join(source_dir, f)
        if os.path.isfile(file_path):
            files.append(f)
            print(f"  Including: {f}")
    
    print("-" * 40)
    
    # Create ZIP file
    with zipfile.ZipFile(output_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file in files:
            file_path = os.path.join(source_dir, file)
            zipf.write(file_path, file)
    
    # Calculate and display checksum
    with open(output_file, 'rb') as f:
        sha256 = hashlib.sha256(f.read()).hexdigest()
    
    size = os.path.getsize(output_file)
    
    print(f"\n✅ SUCCESS!")
    print(f"Location: {output_file}")
    print(f"Size: {size:,} bytes")
    print(f"SHA256: {sha256}")
    
    # Note about downloads folder
    print("\n📝 Note: ZIP created on Desktop due to permissions.")
    print("   To move to downloads folder, manually copy or run as Administrator.")
    
    return output_file

if __name__ == "__main__":
    create_zip()