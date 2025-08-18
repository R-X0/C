import pandas as pd
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import numpy as np
from io import BytesIO
import base64
from typing import Dict, Any, Optional
from datetime import datetime
import traceback
from sqlalchemy.orm import Session

class TemplateExecutor:
    def __init__(self):
        self.globals_dict = {
            'pd': pd,
            'plt': plt,
            'go': go,
            'np': np,
            'datetime': datetime,
            'BytesIO': BytesIO,
            'base64': base64
        }
    
    def execute_template(self, code: str, db_session: Session, symbol: str, 
                        start_date: str, end_date: str) -> Dict[str, Any]:
        """Execute a Python template and return results"""
        try:
            # Create a local namespace for execution
            local_namespace = self.globals_dict.copy()
            
            # Add helper function for converting figures to base64
            local_namespace['fig_to_base64'] = self._fig_to_base64
            
            # Convert dates to full timestamps if they're just dates
            if len(start_date) == 10:  # Format: YYYY-MM-DD
                start_date = f"{start_date} 00:00:00"
            if len(end_date) == 10:  # Format: YYYY-MM-DD
                end_date = f"{end_date} 23:59:59"
            
            # Execute the code to define the function
            exec(code, local_namespace)
            
            # Check if analyze_data function was defined
            if 'analyze_data' not in local_namespace:
                raise ValueError("Template must define an 'analyze_data' function")
            
            # Call the analyze_data function
            result = local_namespace['analyze_data'](
                db_session, symbol, start_date, end_date
            )
            
            # Ensure result is properly formatted
            if not isinstance(result, dict):
                result = {'type': 'table', 'data': result}
            
            # Convert any non-serializable objects in the result
            result = self._make_json_serializable(result)
            
            return {
                'success': True,
                'result': result,
                'error': None
            }
            
        except Exception as e:
            return {
                'success': False,
                'result': None,
                'error': f"Execution error: {str(e)}\n{traceback.format_exc()}"
            }
    
    def _fig_to_base64(self, fig) -> str:
        """Convert matplotlib figure to base64 string"""
        buffer = BytesIO()
        fig.savefig(buffer, format='png', bbox_inches='tight')
        buffer.seek(0)
        img_str = base64.b64encode(buffer.getvalue()).decode()
        plt.close(fig)
        return img_str
    
    def _make_json_serializable(self, obj):
        """Convert non-JSON-serializable objects to serializable format"""
        import pandas as pd
        import numpy as np
        from datetime import datetime, date
        
        if isinstance(obj, dict):
            # Convert both keys and values to be JSON serializable
            result = {}
            for k, v in obj.items():
                # Convert key if it's a non-serializable type
                if isinstance(k, (pd.Timestamp, datetime, date)):
                    key = str(k)
                elif isinstance(k, (np.integer, np.int64)):
                    key = int(k)
                elif isinstance(k, (np.floating, np.float64)):
                    key = float(k)
                else:
                    key = k
                # Convert value recursively
                result[key] = self._make_json_serializable(v)
            return result
        elif isinstance(obj, list):
            return [self._make_json_serializable(item) for item in obj]
        elif isinstance(obj, (pd.Timestamp, datetime, date)):
            return str(obj)
        elif isinstance(obj, (np.integer, np.int64)):
            return int(obj)
        elif isinstance(obj, (np.floating, np.float64)):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif pd.isna(obj):
            return None
        else:
            return obj
    
    def validate_template(self, code: str) -> Dict[str, Any]:
        """Validate that a template is safe and properly formatted"""
        try:
            # Check for dangerous operations
            dangerous_keywords = [
                '__import__', 'eval', 'exec', 'compile', 
                'open', 'file', 'input', 'raw_input',
                'os.', 'subprocess', 'sys.exit'
            ]
            
            for keyword in dangerous_keywords:
                if keyword in code:
                    return {
                        'valid': False,
                        'error': f"Template contains potentially dangerous operation: {keyword}"
                    }
            
            # Try to compile the code
            compile(code, '<string>', 'exec')
            
            # Check if it defines analyze_data function
            if 'def analyze_data' not in code:
                return {
                    'valid': False,
                    'error': "Template must define an 'analyze_data' function"
                }
            
            return {'valid': True, 'error': None}
            
        except SyntaxError as e:
            return {
                'valid': False,
                'error': f"Syntax error: {str(e)}"
            }