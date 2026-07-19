#!/usr/bin/env python3
"""
PCFixPro PDF Generator
Creates PDF with installation instructions explaining automatic dashboard connection
"""
import os
import sys
import shutil
from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.units import inch

def create_pdf_with_zip(pdf_path, zip_path, title="PCFixPro Agent Installer"):
    """Create a PDF with installation instructions - agents auto-connect to dashboard"""
    pdf_path = Path(pdf_path)
    pdf_path = pdf_path.resolve()
    
    print(f"[PDF] Creating PDF: {pdf_path}")
    
    # Ensure parent directory exists
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Create PDF using canvas directly (more reliable)
    c = canvas.Canvas(str(pdf_path), pagesize=letter)
    width, height = letter
    
    # Draw content
    y_pos = height - 1 * inch
    
    # Title
    c.setFont("Helvetica-Bold", 24)
    c.setFillColor(colors.darkblue)
    c.drawCentredString(width / 2, y_pos, "PCFixPro Remote Support Agent")
    y_pos -= 0.5 * inch
    
    # Important notice
    c.setFont("Helvetica-Bold", 14)
    c.setFillColor(colors.black)
    c.drawString(1 * inch, y_pos, "IMPORTANT: Auto-Connect Feature")
    y_pos -= 0.3 * inch
    
    c.setFont("Helvetica", 11)
    c.setFillColor(colors.green)
    text = u"\u2713 Once you install this agent, it will automatically connect to the technician's dashboard"
    c.drawString(1 * inch, y_pos, text)
    y_pos -= 0.3 * inch
    
    c.setFillColor(colors.black)
    c.drawString(1 * inch, y_pos, "The agent runs silently in the background and creates a session immediately upon")
    y_pos -= 0.2 * inch
    c.drawString(1 * inch, y_pos, "installation - no manual setup required!")
    y_pos -= 0.4 * inch
    
    # Installation instructions
    c.setFont("Helvetica-Bold", 14)
    c.drawString(1 * inch, y_pos, "Installation Instructions")
    y_pos -= 0.3 * inch
    
    c.setFont("Helvetica-Bold", 11)
    c.drawString(1 * inch, y_pos, "For Windows Users:")
    y_pos -= 0.2 * inch
    
    c.setFont("Helvetica", 10)
    c.drawString(1.2 * inch, y_pos, "1. Extract the ZIP file in the same folder as this PDF")
    y_pos -= 0.15 * inch
    c.drawString(1.2 * inch, y_pos, "2. Right-click INSTALL.bat → 'Run as administrator'")
    y_pos -= 0.15 * inch
    c.drawString(1.2 * inch, y_pos, "3. The installation runs silently (watch for toast notification)")
    y_pos -= 0.15 * inch
    c.drawString(1.2 * inch, y_pos, "4. Agent auto-connects to dashboard - technician will see your PC")
    y_pos -= 0.15 * inch
    c.drawString(1.2 * inch, y_pos, "5. Desktop shortcut to logs will be created")
    y_pos -= 0.3 * inch
    
    c.setFont("Helvetica-Bold", 11)
    c.drawString(1 * inch, y_pos, "For macOS Users:")
    y_pos -= 0.2 * inch
    
    c.setFont("Helvetica", 10)
    c.drawString(1.2 * inch, y_pos, "1. Extract the ZIP file in the same folder as this PDF")
    y_pos -= 0.15 * inch
    c.drawString(1.2 * inch, y_pos, "2. Right-click INSTALL.command → 'Open'")
    y_pos -= 0.15 * inch
    c.drawString(1.2 * inch, y_pos, "3. Enter your password when prompted")
    y_pos -= 0.15 * inch
    c.drawString(1.2 * inch, y_pos, "4. Agent auto-connects to dashboard - technician will see your PC")
    y_pos -= 0.15 * inch
    c.drawString(1.2 * inch, y_pos, "5. Installation proceeds automatically")
    y_pos -= 0.3 * inch
    
    # What happens next
    c.setFont("Helvetica-Bold", 11)
    c.drawString(1 * inch, y_pos, "What Happens Next:")
    y_pos -= 0.2 * inch
    
    c.setFont("Helvetica", 10)
    c.drawString(1.2 * inch, y_pos, u"\u2022 Your PC appears in the technician's dashboard instantly")
    y_pos -= 0.15 * inch
    c.drawString(1.2 * inch, y_pos, u"\u2022 No further action is required from you")
    y_pos -= 0.15 * inch
    c.drawString(1.2 * inch, y_pos, u"\u2022 Technician can now provide remote support")
    y_pos -= 0.15 * inch
    c.drawString(1.2 * inch, y_pos, u"\u2022 Check the desktop shortcut for installation logs if needed")
    y_pos -= 0.3 * inch
    
    # Support
    c.setFont("Helvetica-Bold", 14)
    c.drawString(1 * inch, y_pos, "Support")
    y_pos -= 0.2 * inch
    
    c.setFont("Helvetica", 10)
    c.drawString(1 * inch, y_pos, "Email: support@pcfixpro.com")
    y_pos -= 0.15 * inch
    c.drawString(1 * inch, y_pos, "Phone: +1-XXX-XXX-XXXX")
    y_pos -= 0.3 * inch
    
    c.setFont("Helvetica-Oblique", 9)
    c.drawString(1 * inch, y_pos, "The ZIP installer (PCFixPro_Agent_Universal.zip) is in the same folder as this PDF.")
    
    # Save PDF
    c.save()
    print(f"[OK] PDF created: {pdf_path}")
    
    return True

if __name__ == "__main__":
    script_dir = Path(__file__).parent
    dist_dir = script_dir / "dist"
    downloads_dir = script_dir.parent / "downloads"
    
    # Create downloads folder if not exists
    downloads_dir.mkdir(exist_ok=True)
    
    # Find the universal ZIP
    zip_path = dist_dir / "PCFixPro_Agent_Universal.zip"
    pdf_path = dist_dir / "PCFixPro.pdf"
    pdf_downloads = downloads_dir / "PCFixPro.pdf"
    
    if zip_path.exists():
        create_pdf_with_zip(pdf_path, zip_path)
        # Copy PDF to downloads folder
        shutil.copy(pdf_path, pdf_downloads)
        print(f"[OK] PDF also copied to: {pdf_downloads}")
        print(f"[INFO] Client can extract ZIP and run INSTALL.bat - agent auto-connects!")
    else:
        print("[ERROR] ZIP file not found. Run package_agent.py first.")
        print(f"Looking for: {zip_path}")