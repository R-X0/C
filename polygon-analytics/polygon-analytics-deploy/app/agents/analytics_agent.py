from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.schema.output_parser import StrOutputParser
from app.config import get_settings
import json
import re

settings = get_settings()

class AnalyticsAgent:
    def __init__(self):
        self.llm = ChatOpenAI(
            model="gpt-4o",
            temperature=0,
            api_key=settings.openai_api_key
        )
        
        self.system_prompt = """You are an expert data analyst that generates Python code for analyzing stock tick data.
        
        The data is stored in a PostgreSQL database with the following schema:
        - Table: tick_data
        - Columns: id, symbol, timestamp, price, size, exchange, conditions, created_at
        
        You should generate Python code that:
        1. Queries the database using SQLAlchemy
        2. Processes the data using pandas
        3. Returns results as either a table (DataFrame) or chart (matplotlib/plotly)
        
        IMPORTANT RULES:
        - Always import necessary libraries at the top
        - Use parameterized queries for safety
        - Include error handling
        - Return a dictionary with keys: type (table/chart/both), data, chart
        - For charts, save to a BytesIO object and return base64 encoded string
        - Always filter by symbol and date range if specified
        
        Example structure:
        ```python
        import pandas as pd
        import matplotlib.pyplot as plt
        from sqlalchemy import create_engine, text
        import numpy as np
        from io import BytesIO
        import base64
        
        def analyze_data(db_session, symbol, start_date, end_date):
            # Your analysis code here
            query = "SELECT * FROM tick_data WHERE symbol = :symbol AND timestamp BETWEEN :start AND :end"
            df = pd.read_sql(query, db_session.bind, params={{"symbol": symbol, "start": start_date, "end": end_date}})
            
            # Process data
            result = process_data(df)
            
            # Create visualization if needed
            fig, ax = plt.subplots()
            # ... plotting code
            
            # Return results
            return {{
                "type": "both",
                "data": result.to_dict(),
                "chart": fig_to_base64(fig)
            }}
        ```
        """
        
    def generate_template(self, prompt: str) -> dict:
        """Generate Python code template from natural language prompt"""
        
        template = ChatPromptTemplate.from_messages([
            ("system", self.system_prompt),
            ("user", """Generate Python code for the following analysis request:
            
            {prompt}
            
            Return ONLY the Python code, no explanations. The code should be a complete function called 'analyze_data' that takes (db_session, symbol, start_date, end_date) as parameters.""")
        ])
        
        chain = template | self.llm | StrOutputParser()
        
        code = chain.invoke({"prompt": prompt})
        
        # Extract just the Python code
        code = self._extract_python_code(code)
        
        # Determine output type from the prompt
        output_type = self._determine_output_type(prompt)
        
        return {
            "prompt": prompt,
            "code": code,
            "output_type": output_type
        }
    
    def _extract_python_code(self, response: str) -> str:
        """Extract Python code from LLM response"""
        # Look for code blocks
        code_match = re.search(r'```python\n(.*?)\n```', response, re.DOTALL)
        if code_match:
            return code_match.group(1)
        
        # If no code blocks, assume entire response is code
        return response.strip()
    
    def _determine_output_type(self, prompt: str) -> str:
        """Determine if the output should be a table, chart, or both"""
        prompt_lower = prompt.lower()
        
        chart_keywords = ['chart', 'graph', 'plot', 'visualiz', 'show me']
        table_keywords = ['table', 'list', 'dataframe', 'rows']
        
        has_chart = any(keyword in prompt_lower for keyword in chart_keywords)
        has_table = any(keyword in prompt_lower for keyword in table_keywords)
        
        if has_chart and has_table:
            return "both"
        elif has_chart:
            return "chart"
        else:
            return "table"