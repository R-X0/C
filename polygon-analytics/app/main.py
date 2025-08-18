from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import asyncio

from app.models.database import engine, get_db
from app.models.models import Base, TickData, AnalyticsTemplate, QueryHistory
from app.services.polygon_service import PolygonService
from app.agents.analytics_agent import AnalyticsAgent
from app.services.template_executor import TemplateExecutor

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Polygon Analytics API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request/Response models
class FetchDataRequest(BaseModel):
    symbol: str
    start_date: str
    end_date: str

class GenerateTemplateRequest(BaseModel):
    prompt: str
    save_template: bool = False
    template_name: Optional[str] = None

class ExecuteTemplateRequest(BaseModel):
    template_id: Optional[int] = None
    template_code: Optional[str] = None
    symbol: str
    start_date: str
    end_date: str

class TemplateResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    prompt: str
    output_type: str
    created_at: datetime

# Initialize services
polygon_service = PolygonService()
analytics_agent = AnalyticsAgent()
template_executor = TemplateExecutor()

@app.get("/")
async def root():
    return {"message": "Polygon Analytics API", "version": "1.0.0"}

@app.post("/api/fetch-data")
async def fetch_data(request: FetchDataRequest, db: Session = Depends(get_db)):
    """Fetch and store tick data from Polygon"""
    try:
        records = await polygon_service.fetch_and_store_data(
            request.symbol,
            request.start_date,
            request.end_date,
            db
        )
        return {
            "success": True,
            "message": f"Fetched and stored {records} records",
            "symbol": request.symbol,
            "date_range": f"{request.start_date} to {request.end_date}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/generate-template")
async def generate_template(request: GenerateTemplateRequest, db: Session = Depends(get_db)):
    """Generate analytics template from natural language prompt"""
    try:
        # Generate template using AI
        template_data = analytics_agent.generate_template(request.prompt)
        
        # Validate the generated code
        validation = template_executor.validate_template(template_data["code"])
        if not validation["valid"]:
            raise HTTPException(status_code=400, detail=validation["error"])
        
        # Save template if requested
        if request.save_template:
            template = AnalyticsTemplate(
                name=request.template_name or f"Template_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                description=f"Generated from: {request.prompt[:100]}",
                prompt=request.prompt,
                python_code=template_data["code"],
                output_type=template_data["output_type"]
            )
            db.add(template)
            db.commit()
            db.refresh(template)
            
            return {
                "success": True,
                "template_id": template.id,
                "template_name": template.name,
                "code": template_data["code"],
                "output_type": template_data["output_type"]
            }
        
        return {
            "success": True,
            "code": template_data["code"],
            "output_type": template_data["output_type"]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/execute-template")
async def execute_template(request: ExecuteTemplateRequest, db: Session = Depends(get_db)):
    """Execute a template and return results"""
    try:
        # Get template code
        if request.template_id:
            template = db.query(AnalyticsTemplate).filter(
                AnalyticsTemplate.id == request.template_id
            ).first()
            if not template:
                raise HTTPException(status_code=404, detail="Template not found")
            code = template.python_code
        elif request.template_code:
            code = request.template_code
        else:
            raise HTTPException(status_code=400, detail="Either template_id or template_code required")
        
        # Execute the template
        result = template_executor.execute_template(
            code, db, request.symbol, request.start_date, request.end_date
        )
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result["error"])
        
        # Save to query history
        history = QueryHistory(
            prompt=f"Execute template for {request.symbol}",
            template_id=request.template_id,
            result=result["result"]
        )
        db.add(history)
        db.commit()
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/templates")
async def list_templates(db: Session = Depends(get_db)):
    """List all saved templates"""
    templates = db.query(AnalyticsTemplate).all()
    return [TemplateResponse(
        id=t.id,
        name=t.name,
        description=t.description,
        prompt=t.prompt,
        output_type=t.output_type,
        created_at=t.created_at
    ) for t in templates]

@app.get("/api/template/{template_id}")
async def get_template(template_id: int, db: Session = Depends(get_db)):
    """Get a specific template"""
    template = db.query(AnalyticsTemplate).filter(
        AnalyticsTemplate.id == template_id
    ).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    return {
        "id": template.id,
        "name": template.name,
        "description": template.description,
        "prompt": template.prompt,
        "code": template.python_code,
        "output_type": template.output_type,
        "created_at": template.created_at
    }

@app.get("/api/data-summary")
async def data_summary(symbol: str, db: Session = Depends(get_db)):
    """Get summary of available data for a symbol"""
    count = db.query(TickData).filter(TickData.symbol == symbol).count()
    
    if count == 0:
        return {
            "symbol": symbol,
            "record_count": 0,
            "date_range": None
        }
    
    min_date = db.query(TickData.timestamp).filter(
        TickData.symbol == symbol
    ).order_by(TickData.timestamp).first()
    
    max_date = db.query(TickData.timestamp).filter(
        TickData.symbol == symbol
    ).order_by(TickData.timestamp.desc()).first()
    
    return {
        "symbol": symbol,
        "record_count": count,
        "date_range": {
            "start": min_date[0] if min_date else None,
            "end": max_date[0] if max_date else None
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)