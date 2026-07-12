import os
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session

import models
from database import engine, get_db, Base
from agent import run_agent_workflow

# Initialize database
Base.metadata.create_all(bind=engine)

app = FastAPI(title="AI-First CRM HCP Module API")

# Setup CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Seed database with sample HCPs and Materials if empty
@app.on_event("startup")
def seed_data():
    db = next(get_db())
    try:
        # Seed HCPs
        if db.query(models.HCP).count() == 0:
            hcps = [
                models.HCP(name="Dr. Emily Smith", specialty="Oncology", clinic="Metro Cancer Center", email="emily.smith@metro.com", phone="555-0192"),
                models.HCP(name="Dr. James Clark", specialty="Cardiology", clinic="Heart & Vascular Institute", email="james.clark@hvi.org", phone="555-0143"),
                models.HCP(name="Dr. Sarah Patel", specialty="Neurology", clinic="Neurological Specialists", email="sarah.patel@neuro.net", phone="555-0177"),
                models.HCP(name="Dr. Robert Chen", specialty="Oncology", clinic="City General Oncology", email="r.chen@citygen.org", phone="555-0185"),
                models.HCP(name="Dr. Lisa Warren", specialty="Pediatrics", clinic="Sunny Days Clinic", email="l.warren@sunnydays.com", phone="555-0155")
            ]
            db.add_all(hcps)
            db.commit()

        # Seed Materials / Samples
        if db.query(models.Material).count() == 0:
            materials = [
                models.Material(name="OncoBoost Phase III PDF", type="Material", stock=100),
                models.Material(name="CardioCare Brochure", type="Material", stock=100),
                models.Material(name="NeuroShield Clinical Study", type="Material", stock=100),
                models.Material(name="OncoBoost Starter Kit", type="Sample", stock=25),
                models.Material(name="CardioCare 10mg Samples", type="Sample", stock=50),
                models.Material(name="NeuroShield Starter Packs", type="Sample", stock=15)
            ]
            db.add_all(materials)
            db.commit()
    finally:
        db.close()


# Pydantic Schemas
class HCPOut(BaseModel):
    id: int
    name: str
    specialty: str
    clinic: str
    email: str
    phone: str
    class Config:
        from_attributes = True

class MaterialOut(BaseModel):
    id: int
    name: str
    type: str
    stock: int
    class Config:
        from_attributes = True

class InteractionIn(BaseModel):
    hcp_id: int
    interaction_type: str
    date: str
    time: str
    attendees: Optional[str] = ""
    topics_discussed: Optional[str] = ""
    sentiment: Optional[str] = "Neutral"
    outcomes: Optional[str] = ""
    follow_up_actions: Optional[str] = ""
    materials_shared: Optional[str] = ""
    samples_distributed: Optional[str] = ""

class InteractionOut(BaseModel):
    id: int
    hcp_id: int
    hcp_name: Optional[str] = None
    interaction_type: str
    date: str
    time: str
    attendees: Optional[str] = ""
    topics_discussed: Optional[str] = ""
    sentiment: Optional[str] = "Neutral"
    outcomes: Optional[str] = ""
    follow_up_actions: Optional[str] = ""
    materials_shared: Optional[str] = ""
    samples_distributed: Optional[str] = ""

    class Config:
        from_attributes = True

class ChatRequest(BaseModel):
    message: str
    history: Optional[List[Dict[str, str]]] = []

class ChatResponse(BaseModel):
    reply: str
    form_data: Dict[str, Any]
    tool_calls_executed: List[str]


# Routes
@app.get("/api/hcps", response_model=List[HCPOut])
def get_hcps(db: Session = Depends(get_db)):
    return db.query(models.HCP).all()

@app.get("/api/materials", response_model=List[MaterialOut])
def get_materials(db: Session = Depends(get_db)):
    return db.query(models.Material).all()

@app.get("/api/interactions", response_model=List[InteractionOut])
def get_interactions(db: Session = Depends(get_db)):
    interactions = db.query(models.Interaction).all()
    out = []
    for i in interactions:
        hcp = db.query(models.HCP).filter(models.HCP.id == i.hcp_id).first()
        out.append(InteractionOut(
            id=i.id,
            hcp_id=i.hcp_id,
            hcp_name=hcp.name if hcp else "Unknown",
            interaction_type=i.interaction_type,
            date=i.date,
            time=i.time,
            attendees=i.attendees,
            topics_discussed=i.topics_discussed,
            sentiment=i.sentiment,
            outcomes=i.outcomes,
            follow_up_actions=i.follow_up_actions,
            materials_shared=i.materials_shared,
            samples_distributed=i.samples_distributed
        ))
    return out

@app.post("/api/interactions", response_model=InteractionOut)
def log_interaction(payload: InteractionIn, db: Session = Depends(get_db)):
    hcp = db.query(models.HCP).filter(models.HCP.id == payload.hcp_id).first()
    if not hcp:
        raise HTTPException(status_code=404, detail="HCP not found")
        
    # Deduct stocks for samples if applicable
    if payload.samples_distributed:
        samples_list = [s.strip() for s in payload.samples_distributed.split(",") if s.strip()]
        for sname in samples_list:
            mat = db.query(models.Material).filter(models.Material.name.ilike(sname), models.Material.type == "Sample").first()
            if mat and mat.stock > 0:
                mat.stock -= 1

    interaction = models.Interaction(**payload.dict())
    db.add(interaction)
    db.commit()
    db.refresh(interaction)
    
    return InteractionOut(
        id=interaction.id,
        hcp_id=interaction.hcp_id,
        hcp_name=hcp.name,
        interaction_type=interaction.interaction_type,
        date=interaction.date,
        time=interaction.time,
        attendees=interaction.attendees,
        topics_discussed=interaction.topics_discussed,
        sentiment=interaction.sentiment,
        outcomes=interaction.outcomes,
        follow_up_actions=interaction.follow_up_actions,
        materials_shared=interaction.materials_shared,
        samples_distributed=interaction.samples_distributed
    )

@app.put("/api/interactions/{interaction_id}", response_model=InteractionOut)
def edit_interaction(interaction_id: int, payload: InteractionIn, db: Session = Depends(get_db)):
    interaction = db.query(models.Interaction).filter(models.Interaction.id == interaction_id).first()
    if not interaction:
        raise HTTPException(status_code=404, detail="Interaction not found")
    
    hcp = db.query(models.HCP).filter(models.HCP.id == payload.hcp_id).first()
    if not hcp:
        raise HTTPException(status_code=404, detail="HCP not found")

    for key, val in payload.dict().items():
        setattr(interaction, key, val)
        
    db.commit()
    db.refresh(interaction)
    
    return InteractionOut(
        id=interaction.id,
        hcp_id=interaction.hcp_id,
        hcp_name=hcp.name,
        interaction_type=interaction.interaction_type,
        date=interaction.date,
        time=interaction.time,
        attendees=interaction.attendees,
        topics_discussed=interaction.topics_discussed,
        sentiment=interaction.sentiment,
        outcomes=interaction.outcomes,
        follow_up_actions=interaction.follow_up_actions,
        materials_shared=interaction.materials_shared,
        samples_distributed=interaction.samples_distributed
    )

@app.delete("/api/interactions/{interaction_id}")
def delete_interaction(interaction_id: int, db: Session = Depends(get_db)):
    interaction = db.query(models.Interaction).filter(models.Interaction.id == interaction_id).first()
    if not interaction:
        raise HTTPException(status_code=404, detail="Interaction not found")
    db.delete(interaction)
    db.commit()
    return {"message": f"Interaction {interaction_id} deleted successfully"}

@app.post("/api/chat", response_model=ChatResponse)
def chat_with_assistant(payload: ChatRequest):
    result = run_agent_workflow(payload.message, payload.history)
    return ChatResponse(
        reply=result["reply"],
        form_data=result["form_data"],
        tool_calls_executed=result["tool_calls_executed"]
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
