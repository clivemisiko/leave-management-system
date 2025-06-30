import os
import base64
from flask import current_app

def get_logo_base64():
    """Get the logo as base64 encoded string"""
    logo_path = os.path.join(current_app.root_path, 'static', 'images', 'gov_logo.png')
    
    if not os.path.exists(logo_path):
        current_app.logger.error(f"Logo file not found at: {logo_path}")
        return ""
    
    try:
        with open(logo_path, 'rb') as f:
            encoded = base64.b64encode(f.read()).decode('utf-8')
        return f"data:image/png;base64,{encoded}"
    except Exception as e:
        current_app.logger.error(f"Error reading logo: {str(e)}")
        return ""