import os
import base64
from flask import current_app

def get_logo_base64():
    """Finds and returns the organization logo as base64"""
    # Check multiple possible locations
    possible_paths = [
        os.path.join(current_app.root_path, 'static', 'images', 'gov_logo.png'),
        os.path.join(current_app.root_path, 'static', 'images', 'kenya_logo.png'),
        os.path.join(current_app.root_path, 'static', 'logo.png')
    ]
    
    for logo_path in possible_paths:
        if os.path.exists(logo_path):
            try:
                with open(logo_path, 'rb') as f:
                    return f"data:image/png;base64,{base64.b64encode(f.read()).decode('utf-8')}"
            except Exception as e:
                current_app.logger.error(f"Error reading logo at {logo_path}: {str(e)}")
                continue
    
    current_app.logger.warning("Logo not found in any standard location")
    return None