import os
import base64
from flask import current_app

def get_logo_base64():
    """Get base64 encoded logo image for both admin and staff"""
    try:
        # Try multiple possible locations
        possible_paths = [
            os.path.join(current_app.root_path, 'static', 'images', 'gov_logo.png'),
            os.path.join(current_app.root_path, 'app', 'static', 'images', 'gov_logo.png'),
            os.path.join(current_app.root_path, 'backend', 'static', 'images', 'gov_logo.png')
        ]
        
        for logo_path in possible_paths:
            if os.path.exists(logo_path):
                with open(logo_path, 'rb') as f:
                    encoded = base64.b64encode(f.read()).decode('utf-8')
                return f"data:image/png;base64,{encoded}"
        
        current_app.logger.error(f"Logo not found at any of: {possible_paths}")
        return ""
        
    except Exception as e:
        current_app.logger.error(f"Logo loading error: {str(e)}")
        return ""