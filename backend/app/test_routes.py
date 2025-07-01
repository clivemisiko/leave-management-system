from flask import Blueprint, render_template, make_response, request
from weasyprint import HTML

test_bp = Blueprint('test', __name__)

@test_bp.route('/test/pdf-logo')
def test_pdf_logo():
    rendered = render_template('test_pdf_logo.html')
    pdf = HTML(string=rendered, base_url=request.url_root).write_pdf()

    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'inline; filename=test_logo.pdf'
    return response