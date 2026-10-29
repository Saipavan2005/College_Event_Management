import os
import uuid
from reportlab.lib.pagesizes import landscape, A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor


def generate_certificate(student_name, event_title, event_date, output_dir=None):
    """
    Creates a landscape PDF certificate and returns just the filename
    (the caller stores this filename in the Certificate model).
    """
    if output_dir is None:
        output_dir = os.path.join(os.path.dirname(__file__))

    filename = f"certificate_{uuid.uuid4().hex}.pdf"
    filepath = os.path.join(output_dir, filename)

    page_size = landscape(A4)
    width, height = page_size
    c = canvas.Canvas(filepath, pagesize=page_size)

    navy = HexColor("#1a2b4c")
    gold = HexColor("#c9a227")

    # Border
    c.setStrokeColor(navy)
    c.setLineWidth(6)
    c.rect(1.2 * cm, 1.2 * cm, width - 2.4 * cm, height - 2.4 * cm)
    c.setStrokeColor(gold)
    c.setLineWidth(1.5)
    c.rect(1.5 * cm, 1.5 * cm, width - 3 * cm, height - 3 * cm)

    # Title
    c.setFillColor(navy)
    c.setFont("Helvetica-Bold", 34)
    c.drawCentredString(width / 2, height - 4.5 * cm, "CERTIFICATE OF PARTICIPATION")

    c.setStrokeColor(gold)
    c.setLineWidth(2)
    c.line(width / 2 - 4 * cm, height - 5 * cm, width / 2 + 4 * cm, height - 5 * cm)

    c.setFont("Helvetica", 16)
    c.setFillColor(colors.black)
    c.drawCentredString(width / 2, height - 6.5 * cm, "This certificate is proudly presented to")

    c.setFont("Helvetica-Bold", 28)
    c.setFillColor(navy)
    c.drawCentredString(width / 2, height - 8 * cm, student_name)

    c.setFont("Helvetica", 15)
    c.setFillColor(colors.black)
    c.drawCentredString(
        width / 2, height - 9.5 * cm,
        f'for participating in "{event_title}"'
    )
    c.drawCentredString(
        width / 2, height - 10.5 * cm,
        f"held on {event_date.strftime('%B %d, %Y')}"
    )

    c.setFont("Helvetica-Oblique", 11)
    c.drawCentredString(width / 2, 3 * cm, "College Event Management Platform")

    c.setFont("Helvetica", 11)
    c.drawString(width - 8 * cm, 3.8 * cm, "___________________________")
    c.drawString(width - 8 * cm, 3.3 * cm, "Authorized Signature")

    c.showPage()
    c.save()

    return filename
