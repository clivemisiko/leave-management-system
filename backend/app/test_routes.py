from flask import Blueprint, render_template, make_response, request
from backend.app.utils.pdf import render_pdf

test_bp = Blueprint('test', __name__)

@test_bp.route('/test/pdf-logo')
def test_pdf_logo():
    rendered = render_template('test_pdf_logo.html')
    try:
        pdf = render_pdf(rendered, request.url_root)
    except RuntimeError as exc:
        return str(exc), 503

    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'inline; filename=test_logo.pdf'
    return response
