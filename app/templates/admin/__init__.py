from flask import Blueprint

admin_bp = Blueprint('admin', __name__, url_prefix='/admin', template_folder='templates')

# Import routes after blueprint creation
from . import routes