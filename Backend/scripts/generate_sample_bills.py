"""
scripts/generate_sample_bills.py
Generates realistic sample bills (Uber, Jio, Swiggy, AWS, Starbucks) in PNG & PDF formats inside Backend/bill directory for testing OCR and document upload.
"""
import os
import sys

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "bill")
os.makedirs(OUTPUT_DIR, exist_ok=True)

try:
    from PIL import Image, ImageDraw, ImageFont
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

try:
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False


def create_uber_receipt_png():
    width, height = 600, 800
    img = Image.new("RGB", (width, height), "#FFFFFF")
    draw = ImageDraw.Draw(img)

    # Header - Uber
    draw.rectangle([0, 0, width, 100], fill="#000000")
    draw.text((30, 30), "Uber", fill="#FFFFFF", font_size=36)
    draw.text((width - 180, 35), "TRIP RECEIPT", fill="#CCCCCC", font_size=18)

    # Date & Trip Info
    draw.text((30, 130), "Total: ₹450.00", fill="#000000", font_size=28)
    draw.text((30, 175), "Date: September 12, 2026", fill="#555555", font_size=16)
    draw.text((30, 200), "Trip ID: UB-98402194-IN", fill="#777777", font_size=14)

    draw.line([(30, 230), (width - 30, 230)], fill="#E0E0E0", width=2)

    # Locations
    draw.ellipse([30, 255, 42, 267], fill="#00AA00")
    draw.text((55, 252), "Pickup: Indiranagar 100ft Road, Bengaluru", fill="#333333", font_size=15)

    draw.rectangle([30, 295, 42, 307], fill="#CC0000")
    draw.text((55, 292), "Dropoff: MG Road Metro Station, Bengaluru", fill="#333333", font_size=15)

    draw.line([(30, 330), (width - 30, 330)], fill="#E0E0E0", width=2)

    # Fare Breakdown
    draw.text((30, 350), "Fare Breakdown", fill="#000000", font_size=20)

    items = [
        ("Base Fare", "₹120.00"),
        ("Distance (8.4 km)", "₹210.00"),
        ("Time (26 mins)", "₹65.00"),
        ("Tolls & Surcharges", "₹25.00"),
        ("CGST (2.5%)", "₹15.00"),
        ("SGST (2.5%)", "₹15.00"),
    ]

    y = 390
    for label, val in items:
        draw.text((40, y), label, fill="#444444", font_size=15)
        draw.text((width - 150, y), val, fill="#222222", font_size=15)
        y += 30

    draw.line([(30, y + 10), (width - 30, y + 10)], fill="#000000", width=2)

    draw.text((40, y + 25), "Total Amount Paid", fill="#000000", font_size=18)
    draw.text((width - 150, y + 25), "₹450.00", fill="#000000", font_size=18)

    # Footer
    draw.rectangle([0, height - 70, width, height], fill="#F4F4F4")
    draw.text((30, height - 45), "Payment Method: Personal Credit Card (•••• 4821)", fill="#666666", font_size=13)

    out_path = os.path.join(OUTPUT_DIR, "uber_trip_receipt.png")
    img.save(out_path)
    print(f"Created: {out_path}")


def create_jio_bill_pdf():
    pdf_path = os.path.join(OUTPUT_DIR, "jio_fiber_bill.pdf")
    doc = SimpleDocTemplate(pdf_path, pagesize=letter)
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=24, textColor=colors.HexColor("#0A2885"), spaceAfter=10)
    normal_style = ParagraphStyle('Normal', parent=styles['Normal'], fontSize=11, leading=15, textColor=colors.HexColor("#333333"))
    header_style = ParagraphStyle('Header', parent=styles['Normal'], fontSize=12, leading=15, textColor=colors.white, fontName="Helvetica-Bold")

    elements = []

    elements.append(Paragraph("<b>Reliance Jio Infocomm Limited</b>", title_style))
    elements.append(Paragraph("Tax Invoice / Monthly Statement — JioFiber", ParagraphStyle('Sub', parent=normal_style, fontSize=14, textColor=colors.HexColor("#666666"))))
    elements.append(Spacer(1, 15))

    # Invoice Meta Data Table
    meta_data = [
        [Paragraph("<b>Customer Name:</b> Vickey Kumar", normal_style), Paragraph("<b>Invoice No:</b> JIO-20260901-8849", normal_style)],
        [Paragraph("<b>Service ID:</b> 080-49201948", normal_style), Paragraph("<b>Bill Date:</b> 01-Sep-2026", normal_style)],
        [Paragraph("<b>Plan:</b> JioFiber 300 Mbps Unlimited", normal_style), Paragraph("<b>Billing Period:</b> 01-Aug-2026 to 31-Aug-2026", normal_style)],
    ]
    t_meta = Table(meta_data, colWidths=[250, 250])
    t_meta.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#F0F4FF")),
        ('PADDING', (0,0), (-1,-1), 8),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor("#D0DDFB")),
    ]))
    elements.append(t_meta)
    elements.append(Spacer(1, 20))

    # Line items table
    table_data = [
        [Paragraph("Description", header_style), Paragraph("HSN/SAC", header_style), Paragraph("Amount (INR)", header_style)],
        [Paragraph("JioFiber Monthly Subscription (300 Mbps)", normal_style), Paragraph("998422", normal_style), Paragraph("999.00", normal_style)],
        [Paragraph("CGST @ 9%", normal_style), Paragraph("-", normal_style), Paragraph("89.91", normal_style)],
        [Paragraph("SGST @ 9%", normal_style), Paragraph("-", normal_style), Paragraph("89.91", normal_style)],
        [Paragraph("<b>Total Amount Payable</b>", normal_style), Paragraph("", normal_style), Paragraph("<b>₹ 1,178.82</b>", normal_style)],
    ]
    t_items = Table(table_data, colWidths=[300, 100, 100])
    t_items.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#0A2885")),
        ('ALIGN', (2,0), (2,-1), 'RIGHT'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CCCCCC")),
        ('PADDING', (0,0), (-1,-1), 8),
    ]))
    elements.append(t_items)
    elements.append(Spacer(1, 30))

    elements.append(Paragraph("<b>Status:</b> PAID via UPI (Ref: UPI/625194012891)", ParagraphStyle('Status', parent=normal_style, textColor=colors.HexColor("#008800"), fontSize=12)))
    elements.append(Paragraph("This is a computer-generated tax invoice and does not require a physical signature.", ParagraphStyle('Note', parent=normal_style, fontSize=9, textColor=colors.gray)))

    doc.build(elements)
    print(f"Created: {pdf_path}")


def create_swiggy_receipt_png():
    width, height = 550, 750
    img = Image.new("RGB", (width, height), "#FFFFFF")
    draw = ImageDraw.Draw(img)

    # Header - Swiggy Orange
    draw.rectangle([0, 0, width, 90], fill="#FC8019")
    draw.text((30, 25), "SWIGGY", fill="#FFFFFF", font_size=32)
    draw.text((width - 170, 35), "ORDER RECEIPT", fill="#FFF0E0", font_size=16)

    # Restaurant Info
    draw.text((30, 110), "Meghana Foods — Koramangala", fill="#000000", font_size=22)
    draw.text((30, 145), "Order #18492019481 | Date: Sep 05, 2026 08:30 PM", fill="#666666", font_size=13)

    draw.line([(30, 175), (width - 30, 175)], fill="#E5E5E5", width=2)

    # Line items
    draw.text((30, 195), "Items Ordered", fill="#333333", font_size=18)

    items = [
        ("1x Chicken Boneless Biryani", "₹340.00"),
        ("1x Paneer Tikka Starter", "₹240.00"),
        ("2x Butter Naan", "₹80.00"),
        ("Packaging Charge", "₹25.00"),
        ("Delivery Partner Fee", "₹45.00"),
        ("Restaurant Packaging & Taxes", "₹35.00"),
        ("Swiggy One Discount", "-₹80.00"),
    ]

    y = 235
    for label, val in items:
        color = "#CC0000" if "-" in val else "#444444"
        draw.text((40, y), label, fill="#333333", font_size=14)
        draw.text((width - 140, y), val, fill=color, font_size=14)
        y += 28

    draw.line([(30, y + 10), (width - 30, y + 10)], fill="#FC8019", width=2)

    draw.text((40, y + 25), "Grand Total", fill="#000000", font_size=20)
    draw.text((width - 140, y + 25), "₹685.00", fill="#000000", font_size=20)

    draw.rectangle([30, y + 70, width - 30, y + 110], fill="#E8F5E9")
    draw.text((45, y + 80), "✔ Paid Online via Corporate Card (Ending 9012)", fill="#2E7D32", font_size=14)

    out_path = os.path.join(OUTPUT_DIR, "swiggy_food_receipt.png")
    img.save(out_path)
    print(f"Created: {out_path}")


def create_aws_invoice_pdf():
    pdf_path = os.path.join(OUTPUT_DIR, "aws_cloud_invoice.pdf")
    doc = SimpleDocTemplate(pdf_path, pagesize=letter)
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=22, textColor=colors.HexColor("#232F3E"), spaceAfter=10)
    normal_style = ParagraphStyle('Normal', parent=styles['Normal'], fontSize=10, leading=14, textColor=colors.HexColor("#222222"))
    header_style = ParagraphStyle('Header', parent=styles['Normal'], fontSize=10, leading=14, textColor=colors.white, fontName="Helvetica-Bold")

    elements = []

    elements.append(Paragraph("<b>Amazon Web Services, Inc.</b>", title_style))
    elements.append(Paragraph("Tax Invoice / Statement — Account # 4829-1049-2918", ParagraphStyle('Sub', parent=normal_style, fontSize=12, textColor=colors.HexColor("#FF9900"))))
    elements.append(Spacer(1, 15))

    meta_data = [
        [Paragraph("<b>Invoice Date:</b> September 1, 2026", normal_style), Paragraph("<b>Invoice Number:</b> AWS-2026-9920194", normal_style)],
        [Paragraph("<b>Billing Period:</b> Aug 1, 2026 - Aug 31, 2026", normal_style), Paragraph("<b>Payment Terms:</b> Immediate", normal_style)],
    ]
    t_meta = Table(meta_data, colWidths=[250, 250])
    t_meta.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#F2F4F8")),
        ('PADDING', (0,0), (-1,-1), 6),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor("#CCCCCC")),
    ]))
    elements.append(t_meta)
    elements.append(Spacer(1, 20))

    table_data = [
        [Paragraph("Service Details", header_style), Paragraph("Usage / Region", header_style), Paragraph("Total ($)", header_style)],
        [Paragraph("Amazon Elastic Compute Cloud (EC2)", normal_style), Paragraph("t3.medium instances (us-east-1)", normal_style), Paragraph("$78.40", normal_style)],
        [Paragraph("Amazon Simple Storage Service (S3)", normal_style), Paragraph("Standard Storage & Requests", normal_style), Paragraph("$18.10", normal_style)],
        [Paragraph("Amazon Relational Database Service (RDS)", normal_style), Paragraph("db.t3.small PostgreSQL", normal_style), Paragraph("$34.00", normal_style)],
        [Paragraph("Estimated Tax (GST 18%)", normal_style), Paragraph("US-IN Tax Agreement", normal_style), Paragraph("$12.00", normal_style)],
        [Paragraph("<b>Total Amount Charged</b>", normal_style), Paragraph("", normal_style), Paragraph("<b>$142.50</b>", normal_style)],
    ]
    t_items = Table(table_data, colWidths=[250, 150, 100])
    t_items.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#232F3E")),
        ('ALIGN', (2,0), (2,-1), 'RIGHT'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#DDDDDD")),
        ('PADDING', (0,0), (-1,-1), 6),
    ]))
    elements.append(t_items)
    elements.append(Spacer(1, 25))

    elements.append(Paragraph("<b>Payment Status:</b> Automatic Charge Successful to Visa ending in 4109", ParagraphStyle('P', parent=normal_style, textColor=colors.HexColor("#006600"))))

    doc.build(elements)
    print(f"Created: {pdf_path}")


def create_starbucks_receipt_png():
    width, height = 450, 650
    img = Image.new("RGB", (width, height), "#FAFAFA")
    draw = ImageDraw.Draw(img)

    # Starbucks Green Top Bar
    draw.rectangle([0, 0, width, 80], fill="#006241")
    draw.text((30, 25), "STARBUCKS", fill="#FFFFFF", font_size=28)
    draw.text((width - 140, 30), "RECEIPT", fill="#D4E9E2", font_size=16)

    # Store Info
    draw.text((30, 100), "Starbucks Coffee — Church Street", fill="#1E3932", font_size=18)
    draw.text((30, 130), "Store #49201 | Reg 02 | Sep 10, 2026 11:15 AM", fill="#666666", font_size=12)

    draw.line([(30, 160), (width - 30, 160)], fill="#D4E9E2", width=2)

    items = [
        ("1x Grande Java Chip Frappuccino", "₹375.00"),
        ("1x Butter Croissant", "₹165.00"),
        ("Subtotal", "₹540.00"),
        ("CGST (2.5%)", "₹13.50"),
        ("SGST (2.5%)", "₹13.50"),
    ]

    y = 180
    for label, val in items:
        font_s = 15 if "Frappuccino" in label or "Croissant" in label else 13
        draw.text((30, y), label, fill="#333333", font_size=font_s)
        draw.text((width - 120, y), val, fill="#333333", font_size=font_s)
        y += 30

    draw.line([(30, y + 10), (width - 30, y + 10)], fill="#006241", width=2)

    draw.text((30, y + 25), "TOTAL PAID", fill="#006241", font_size=20)
    draw.text((width - 120, y + 25), "₹540.00", fill="#006241", font_size=20)

    draw.text((30, y + 70), "Payment: Apple Pay / HDFC Credit Card", fill="#777777", font_size=12)

    out_path = os.path.join(OUTPUT_DIR, "starbucks_coffee_receipt.png")
    img.save(out_path)
    print(f"Created: {out_path}")


if __name__ == "__main__":
    print("Generating sample bills in Backend/bill...")
    if HAS_PIL:
        create_uber_receipt_png()
        create_swiggy_receipt_png()
        create_starbucks_receipt_png()
    else:
        print("Pillow not found, skipping PNG generation.")

    if HAS_REPORTLAB:
        create_jio_bill_pdf()
        create_aws_invoice_pdf()
    else:
        print("ReportLab not found, skipping PDF generation.")

    print("\nAll sample bills generated successfully!")
