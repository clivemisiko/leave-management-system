def render_pdf(html, base_url):
    try:
        from weasyprint import HTML
    except OSError as exc:
        raise RuntimeError(
            "PDF generation is unavailable because WeasyPrint native libraries "
            "are not installed in this hosting environment."
        ) from exc

    return HTML(string=html, base_url=base_url).write_pdf()
