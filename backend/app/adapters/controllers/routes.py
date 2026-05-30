from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from pydantic import BaseModel
from typing import List, Optional
from datetime import date
from app.infrastructure.database import get_db
from app.infrastructure.models import (
    SettlementTimeframe, SettlementVariables, EBCFiledValue, SettlementResult,
    UploadSession, RawGeneratorBlock, RawConsumerBlock, RawIexBlock, CalculatedBlock
)
from fastapi.responses import StreamingResponse
import io
import pandas as pd
from app.use_cases.upload_files import handle_upload
from app.use_cases.run_calculation import run_settlement_task

router = APIRouter(prefix="/api/v1")

class TimeframeCreate(BaseModel):
    Start_Date: date
    End_Date: date
    Label: str

@router.post("/timeframes")
async def create_timeframe(tf: TimeframeCreate, db: AsyncSession = Depends(get_db)):
    new_tf = SettlementTimeframe(**tf.dict())
    db.add(new_tf)
    await db.commit()
    await db.refresh(new_tf)
    return {"success": True, "data": {"Id": new_tf.Id, "Label": new_tf.Label}}

@router.get("/timeframes")
async def list_timeframes(db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(SettlementTimeframe))
    tfs = res.scalars().all()
    return {"success": True, "data": [{"Id": t.Id, "Label": t.Label, "Status": t.Status} for t in tfs]}

@router.post("/timeframes/{id}/upload/{file_type}")
async def upload_file(id: int, file_type: str, file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    if file_type not in ['gen_cdf', 'con1_cdf', 'con2_cdf', 'iex1', 'iex2']:
        raise HTTPException(status_code=400, detail="Invalid file type")
    result = await handle_upload(db, id, file_type, file)
    return result

@router.post("/timeframes/{id}/calculate")
async def trigger_calculation(id: int, db: AsyncSession = Depends(get_db)):
    # Trigger celery task
    from app.infrastructure.celery_app import celery_app
    task = celery_app.send_task("app.use_cases.run_calculation.run_settlement_task", args=[id])
    return {"success": True, "data": {"job_id": task.id}}

@router.get("/timeframes/{id}/results")
async def get_results(id: int, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(SettlementResult).where(SettlementResult.Timeframe_Id == id))
    results = res.scalars().all()
    return {"success": True, "data": [r.__dict__ for r in results if not r.__dict__.pop('_sa_instance_state', None)]}

class VariablesModel(BaseModel):
    Share_Cons1: float
    Share_Cons2: float
    Default_Loss: float
    Old_Bank_KWH: float
    Bank_Loss_Pct: float
    Cap_Gen_KW: float
    Cap_Cons1_KW: Optional[float] = None
    Cap_Cons2_KW: float
    CT_Ratio: int
    Con1_Label: Optional[str] = None
    Con2_Label: Optional[str] = None
    Con1_Name: Optional[str] = None
    Con2_Name: Optional[str] = None

@router.post("/timeframes/{id}/variables")
async def save_variables(id: int, vars_data: VariablesModel, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(SettlementVariables).where(SettlementVariables.Timeframe_Id == id))
    variables = res.scalar_one_or_none()
    if not variables:
        variables = SettlementVariables(Timeframe_Id=id)
        db.add(variables)
    
    for key, value in vars_data.dict().items():
        setattr(variables, key, value)
    
    await db.commit()
    return {"success": True}

@router.get("/timeframes/{id}/variables")
async def get_variables(id: int, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(SettlementVariables).where(SettlementVariables.Timeframe_Id == id))
    variables = res.scalar_one_or_none()
    if variables:
        d = variables.__dict__.copy()
        d.pop('_sa_instance_state', None)
        return {"success": True, "data": d}
    return {"success": True, "data": None}

@router.get("/timeframes/{id}/upload/status")
async def upload_status(id: int, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(UploadSession).where(UploadSession.Timeframe_Id == id))
    sessions = res.scalars().all()
    status = {}
    for s in sessions:
        status[s.File_Type] = s.Parse_Status
    return {"success": True, "data": status}

@router.get("/timeframes/{id}/calculate/status")
async def calc_status(id: int, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(SettlementTimeframe).where(SettlementTimeframe.Id == id))
    tf = res.scalar_one_or_none()
    if tf:
        return {"success": True, "data": {"status": tf.Status}}
    return {"success": False, "error": "Not found"}
    
@router.get("/timeframes/{id}")
async def get_timeframe(id: int, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(SettlementTimeframe).where(SettlementTimeframe.Id == id))
    tf = res.scalar_one_or_none()
    if tf:
        d = tf.__dict__.copy()
        d.pop('_sa_instance_state', None)
        return {"success": True, "data": d}
    return {"success": False, "error": "Not found"}

@router.delete("/timeframes/{id}")
async def delete_timeframe(id: int, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(SettlementTimeframe).where(SettlementTimeframe.Id == id))
    tf = res.scalar_one_or_none()
    if tf:
        await db.delete(tf)
        await db.commit()
    return {"success": True}

@router.get("/timeframes/{id}/raw/generator")
async def raw_generator(id: int, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(RawGeneratorBlock).where(RawGeneratorBlock.Timeframe_Id == id).order_by(RawGeneratorBlock.Block_Date, RawGeneratorBlock.Slot))
    blocks = res.scalars().all()
    return {"success": True, "data": [b.__dict__ for b in blocks if not b.__dict__.pop('_sa_instance_state', None)]}
    
@router.get("/timeframes/{id}/raw/consumers")
async def raw_consumers(id: int, consumer: str = None, db: AsyncSession = Depends(get_db)):
    query = select(RawConsumerBlock).where(RawConsumerBlock.Timeframe_Id == id).order_by(RawConsumerBlock.Block_Date, RawConsumerBlock.Slot)
    if consumer:
        query = query.where(RawConsumerBlock.Consumer_Label == consumer)
    res = await db.execute(query)
    blocks = res.scalars().all()
    return {"success": True, "data": [b.__dict__ for b in blocks if not b.__dict__.pop('_sa_instance_state', None)]}

@router.get("/timeframes/{id}/calculated")
async def calculated_blocks(id: int, consumer: str = None, db: AsyncSession = Depends(get_db)):
    query = select(CalculatedBlock).where(CalculatedBlock.Timeframe_Id == id).order_by(CalculatedBlock.Block_Date, CalculatedBlock.Slot)
    if consumer:
        query = query.where(CalculatedBlock.Consumer_Label == consumer)
    res = await db.execute(query)
    blocks = res.scalars().all()
    return {"success": True, "data": [b.__dict__ for b in blocks if not b.__dict__.pop('_sa_instance_state', None)]}

@router.get("/timeframes/{id}/export")
async def export_excel(id: int, type: str, consumer: str = "ALL", db: AsyncSession = Depends(get_db)):
    if type == "raw_gen":
        res = await db.execute(select(RawGeneratorBlock).where(RawGeneratorBlock.Timeframe_Id == id).order_by(RawGeneratorBlock.Block_Date, RawGeneratorBlock.Slot))
        data = [{"Date": b.Block_Date, "Slot": b.Slot, "Active_KW": b.Active_KW} for b in res.scalars().all()]
    elif type == "raw_con":
        query = select(RawConsumerBlock).where(RawConsumerBlock.Timeframe_Id == id).order_by(RawConsumerBlock.Block_Date, RawConsumerBlock.Slot)
        if consumer != "ALL": query = query.where(RawConsumerBlock.Consumer_Label == consumer)
        res = await db.execute(query)
        data = [{"Consumer": b.Consumer_Label, "Date": b.Block_Date, "Slot": b.Slot, "Apparent_KVA": b.Apparent_KVA, "Active_KW_Raw": b.Active_KW_Raw} for b in res.scalars().all()]
    elif type == "calculated":
        query = select(CalculatedBlock).where(CalculatedBlock.Timeframe_Id == id).order_by(CalculatedBlock.Block_Date, CalculatedBlock.Slot)
        if consumer != "ALL": query = query.where(CalculatedBlock.Consumer_Label == consumer)
        res = await db.execute(query)
        data = [b.__dict__ for b in res.scalars().all()]
        for d in data: d.pop('_sa_instance_state', None)
    elif type == "final":
        query = select(SettlementResult).where(SettlementResult.Timeframe_Id == id)
        if consumer != "ALL": query = query.where(SettlementResult.Consumer_Label == consumer)
        res = await db.execute(query)
        data = [b.__dict__ for b in res.scalars().all()]
        for d in data: d.pop('_sa_instance_state', None)
    else:
        raise HTTPException(status_code=400, detail="Invalid export type")
        
    df = pd.DataFrame(data)
    stream = io.BytesIO()
    with pd.ExcelWriter(stream, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Export')
    stream.seek(0)
    
    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=export_{type}_{id}.xlsx"}
    )

