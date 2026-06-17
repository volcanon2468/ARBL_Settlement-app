import calendar
from typing import Optional
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from pydantic import BaseModel
from typing import List, Optional
from datetime import date, datetime
from app.infrastructure.database import get_db
from app.infrastructure.models import (
    SettlementTimeframe,
    SettlementVariables,
    EBCFiledValue,
    SettlementResult,
    UploadSession,
    RawGeneratorBlock,
    RawConsumerBlock,
    RawIexBlock,
    CalculatedBlock,
    ShutdownWindow,
    CustomLossWindow)
from fastapi.responses import StreamingResponse
import io
import pandas as pd
from app.use_cases.upload_files import handle_upload
from app.core.security import verify_token
router = APIRouter(prefix="/api/v1", dependencies=[Depends(verify_token)])


class TimeframeCreate(BaseModel):
    Month: int
    Year: int
    Label: Optional[str] = None


@router.post("/timeframes")
async def create_timeframe(
        tf: TimeframeCreate,
        db: AsyncSession = Depends(get_db)):
    if tf.Month < 1 or tf.Month > 12:
        raise HTTPException(status_code=400,
                            detail="Month must be between 1 and 12")
    if not tf.Label:
        tf.Label = f"{calendar.month_name[tf.Month]} {tf.Year}"
    start_date = date(tf.Year, tf.Month, 1)
    end_date = date(
        tf.Year,
        tf.Month,
        calendar.monthrange(
            tf.Year,
            tf.Month)[1])
    res = await db.execute(select(SettlementTimeframe).where(SettlementTimeframe.Month == tf.Month, SettlementTimeframe.Year == tf.Year))
    existing = res.scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"A timeframe for {tf.Month}/{tf.Year} already exists.")
    tf_dict = tf.dict()
    tf_dict['Start_Date'] = start_date
    tf_dict['End_Date'] = end_date
    new_tf = SettlementTimeframe(**tf_dict)
    db.add(new_tf)
    try:
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500,
                            detail=f"Database transaction failed: {e}")
    await db.refresh(new_tf)
    return {"success": True, "data": {"Id": new_tf.Id, "Label": new_tf.Label}}


@router.get("/timeframes")
async def list_timeframes(db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(SettlementTimeframe).order_by(SettlementTimeframe.Year.desc(), SettlementTimeframe.Month.desc()))
    tfs = res.scalars().all()
    return {"success": True, "data": [
        {"Id": t.Id, "Label": t.Label, "Status": t.Status} for t in tfs]}


@router.post("/timeframes/{id}/upload/{file_type}")
async def upload_file(
        id: int,
        file_type: str,
        file: UploadFile = File(...),
        db: AsyncSession = Depends(get_db)):
    if file_type not in ['gen_cdf', 'con1_cdf', 'con2_cdf', 'iex1', 'iex2']:
        raise HTTPException(status_code=400, detail="Invalid file type")
    result = await handle_upload(db, id, file_type, file)
    return result


@router.post("/timeframes/{id}/calculate")
async def trigger_calculation(id: int,
                              background_tasks: BackgroundTasks,
                              db: AsyncSession = Depends(get_db)):
    from app.use_cases.run_calculation import _run_calculation_async
    background_tasks.add_task(_run_calculation_async, id)
    return {"success": True, "data": {"job_id": f"local_task_{id}"}}


@router.get("/timeframes/{id}/results")
async def get_results(id: int, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(SettlementResult).where(SettlementResult.Timeframe_Id == id))
    results = res.scalars().all()
    data = []
    for r in results:
        d = r.__dict__.copy()
        d.pop('_sa_instance_state', None)
        data.append(d)
    return {"success": True, "data": data}


@router.get("/timeframes/{id}/calculated")
async def get_calculated_blocks(id: int, db: AsyncSession = Depends(get_db)):
    res = await db.execute(
        select(CalculatedBlock)
        .where(CalculatedBlock.Timeframe_Id == id)
        .order_by(CalculatedBlock.Id)
        .limit(192)
    )
    blocks = res.scalars().all()
    data = []
    for b in blocks:
        d = b.__dict__.copy()
        d.pop('_sa_instance_state', None)
        data.append(d)
    return {"success": True, "data": data}


class VariablesModel(BaseModel):
    Share_Cons1: float
    Share_Cons2: float
    Cap_Share_Cons1: float = 50.0
    Cap_Share_Cons2: float = 50.0
    Override_Capacity_MW: Optional[float] = None
    Old_Bank_KWH: Optional[float] = None
    Bank_Usage_Start_Month: Optional[int] = None
    Bank_Usage_Start_Year: Optional[int] = None
    Bank_Usage_End_Month: Optional[int] = None
    Bank_Usage_End_Year: Optional[int] = None
    Bank_Loss_Pct: float


@router.post("/timeframes/{id}/variables")
async def save_variables(
        id: int,
        vars_data: VariablesModel,
        db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(SettlementVariables).where(SettlementVariables.Timeframe_Id == id))
    variables = res.scalar_one_or_none()
    if not variables:
        variables = SettlementVariables(Timeframe_Id=id)
        db.add(variables)
    for key, value in vars_data.dict().items():
        setattr(variables, key, value)
    try:
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500,
                            detail=f"Database transaction failed: {e}")
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


class ShutdownWindowModel(BaseModel):
    Window_Start: str
    Window_End: str


class ShutdownWindowsPayload(BaseModel):
    windows: List[ShutdownWindowModel]


class CustomLossModel(BaseModel):
    Window_Start: str
    Window_End: str
    Loss_Pct: float


class CustomLossPayload(BaseModel):
    losses: List[CustomLossModel]


@router.get("/timeframes/{id}/shutdown_windows")
async def get_shutdown_windows(id: int, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(ShutdownWindow).where(ShutdownWindow.Timeframe_Id == id).order_by(ShutdownWindow.Id))
    windows = res.scalars().all()
    data = [{"Window_Start": w.Window_Start, "Window_End": w.Window_End}
            for w in windows]
    return {"success": True, "data": data}


@router.post("/timeframes/{id}/shutdown_windows")
async def save_shutdown_windows(
        id: int,
        payload: ShutdownWindowsPayload,
        db: AsyncSession = Depends(get_db)):
    await db.execute(delete(ShutdownWindow).where(ShutdownWindow.Timeframe_Id == id))
    for w in payload.windows:
        new_window = ShutdownWindow(
            Timeframe_Id=id,
            Window_Start=w.Window_Start,
            Window_End=w.Window_End
        )
        db.add(new_window)
    try:
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500,
                            detail=f"Database transaction failed: {e}")
    return {"success": True}


@router.get("/timeframes/{id}/custom_losses")
async def get_custom_losses(id: int, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(CustomLossWindow).where(CustomLossWindow.Timeframe_Id == id).order_by(CustomLossWindow.Id))
    losses = res.scalars().all()
    data = [{"Window_Start": c.Window_Start, "Window_End": c.Window_End, "Loss_Pct": c.Loss_Pct} for c in losses]
    return {"success": True, "data": data}


@router.post("/timeframes/{id}/custom_losses")
async def save_custom_losses(
        id: int,
        payload: CustomLossPayload,
        db: AsyncSession = Depends(get_db)):
    await db.execute(delete(CustomLossWindow).where(CustomLossWindow.Timeframe_Id == id))
    for l in payload.losses:
        new_loss = CustomLossWindow(
            Timeframe_Id=id,
            Window_Start=l.Window_Start,
            Window_End=l.Window_End,
            Loss_Pct=l.Loss_Pct
        )
        db.add(new_loss)
    try:
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500,
                            detail=f"Database transaction failed: {e}")
    return {"success": True}


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
    from app.infrastructure.models import BankLedgerTransaction, SettlementVariables
    from fastapi import HTTPException
    source_check = await db.execute(select(BankLedgerTransaction).where(BankLedgerTransaction.Source_Timeframe_Id == id))
    if source_check.scalars().first():
        raise HTTPException(
            status_code=400,
            detail="Cannot delete this timeframe because its banked units have been consumed by a subsequent month. Please recalculate or delete the dependent months first.")
    res = await db.execute(select(SettlementTimeframe).where(SettlementTimeframe.Id == id))
    tf = res.scalar_one_or_none()
    if tf:
        past_tx_res = await db.execute(select(BankLedgerTransaction).where(BankLedgerTransaction.Consumer_Timeframe_Id == id))
        for tx in past_tx_res.scalars().all():
            from sqlalchemy import update
            await db.execute(
                update(SettlementVariables)
                .where(SettlementVariables.Timeframe_Id == tx.Source_Timeframe_Id)
                .values(Banked_Remaining_KWH=SettlementVariables.Banked_Remaining_KWH + tx.Amount_KWH)
            )
        await db.execute(delete(RawGeneratorBlock).where(RawGeneratorBlock.Timeframe_Id == id))
        await db.execute(delete(RawConsumerBlock).where(RawConsumerBlock.Timeframe_Id == id))
        await db.execute(delete(RawIexBlock).where(RawIexBlock.Timeframe_Id == id))
        await db.execute(delete(CalculatedBlock).where(CalculatedBlock.Timeframe_Id == id))
        await db.execute(delete(SettlementResult).where(SettlementResult.Timeframe_Id == id))
        await db.execute(delete(UploadSession).where(UploadSession.Timeframe_Id == id))
        await db.execute(delete(EBCFiledValue).where(EBCFiledValue.Timeframe_Id == id))
        await db.delete(tf)
        try:
            await db.commit()
        except Exception as e:
            await db.rollback()
            raise HTTPException(status_code=500,
                                detail=f"Database transaction failed: {e}")
        import shutil
        import os
        from app.infrastructure.config import settings
        upload_dir = os.path.join(settings.UPLOAD_DIR, str(id))
        if os.path.exists(upload_dir):
            try:
                shutil.rmtree(upload_dir)
            except Exception as e:
                pass
    return {"success": True}


@router.get("/timeframes/{id}/raw/generator")
async def raw_generator(id: int, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(RawGeneratorBlock).where(RawGeneratorBlock.Timeframe_Id == id).order_by(RawGeneratorBlock.Block_Date, RawGeneratorBlock.Slot))
    blocks = res.scalars().all()
    return {
        "success": True, "data": [
            b.__dict__ for b in blocks if not b.__dict__.pop(
                '_sa_instance_state', None)]}


@router.get("/timeframes/{id}/raw/consumers")
async def raw_consumers(
        id: int,
        consumer: str = None,
        db: AsyncSession = Depends(get_db)):
    query = select(RawConsumerBlock).where(
        RawConsumerBlock.Timeframe_Id == id).order_by(
        RawConsumerBlock.Block_Date,
        RawConsumerBlock.Slot)
    if consumer:
        query = query.where(RawConsumerBlock.Consumer_Label == consumer)
    res = await db.execute(query)
    blocks = res.scalars().all()
    return {
        "success": True, "data": [
            b.__dict__ for b in blocks if not b.__dict__.pop(
                '_sa_instance_state', None)]}


@router.get("/timeframes/{id}/calculated")
async def calculated_blocks(
        id: int,
        consumer: str = None,
        db: AsyncSession = Depends(get_db)):
    query = select(CalculatedBlock).where(
        CalculatedBlock.Timeframe_Id == id).order_by(
        CalculatedBlock.Block_Date,
        CalculatedBlock.Slot)
    if consumer:
        query = query.where(CalculatedBlock.Consumer_Label == consumer)
    res = await db.execute(query)
    blocks = res.scalars().all()
    return {
        "success": True, "data": [
            b.__dict__ for b in blocks if not b.__dict__.pop(
                '_sa_instance_state', None)]}


async def _generate_history_workbook(
        db: AsyncSession,
        tf_id: Optional[int] = None,
        start: Optional[date] = None,
        end: Optional[date] = None) -> io.BytesIO:
    if tf_id is not None:
        gen_where = [RawGeneratorBlock.Timeframe_Id == tf_id]
        con_where = [RawConsumerBlock.Timeframe_Id == tf_id]
        iex_where = [RawIexBlock.Timeframe_Id == tf_id]
        calc_where = [CalculatedBlock.Timeframe_Id == tf_id]
    else:
        gen_where = [
            RawGeneratorBlock.Block_Date >= start,
            RawGeneratorBlock.Block_Date <= end]
        con_where = [
            RawConsumerBlock.Block_Date >= start,
            RawConsumerBlock.Block_Date <= end]
        iex_where = [
            RawIexBlock.Block_Date >= start,
            RawIexBlock.Block_Date <= end]
        calc_where = [
            CalculatedBlock.Block_Date >= start,
            CalculatedBlock.Block_Date <= end]
    res = await db.execute(select(RawGeneratorBlock).where(*gen_where).order_by(RawGeneratorBlock.Block_Date, RawGeneratorBlock.Slot))
    gen_raw = [{"Date": b.Block_Date, "Slot": b.Slot,
                "Active_KW": b.Active_KW} for b in res.scalars().all()]
    res = await db.execute(select(RawConsumerBlock).where(*con_where).order_by(RawConsumerBlock.Block_Date, RawConsumerBlock.Slot))
    con_raw_all = res.scalars().all()
    con_tpt145 = [{"Date": b.Block_Date, "Slot": b.Slot, "Apparent_KVA": b.Apparent_KVA,
                   "Active_KW_Raw": b.Active_KW_Raw} for b in con_raw_all if b.Consumer_Label == "TPT145"]
    con_ctr2005 = [{"Date": b.Block_Date, "Slot": b.Slot, "Apparent_KVA": b.Apparent_KVA,
                    "Active_KW_Raw": b.Active_KW_Raw} for b in con_raw_all if b.Consumer_Label == "CTR2005"]
    res = await db.execute(select(RawIexBlock).where(*iex_where).order_by(RawIexBlock.Block_Date, RawIexBlock.Slot))
    iex_raw_all = res.scalars().all()
    iex_tpt145 = [{"Date": b.Block_Date, "Slot": b.Slot, "IEX_KW": b.IEX_KW}
                  for b in iex_raw_all if b.Consumer_Label == "TPT145"]
    iex_ctr2005 = [{"Date": b.Block_Date, "Slot": b.Slot, "IEX_KW": b.IEX_KW}
                   for b in iex_raw_all if b.Consumer_Label == "CTR2005"]
    res = await db.execute(select(CalculatedBlock).where(*calc_where).order_by(CalculatedBlock.Block_Date, CalculatedBlock.Slot))
    calc_all = res.scalars().all()
    calc_tpt145 = []
    calc_ctr2005 = []
    for b in calc_all:
        d = b.__dict__.copy()
        d.pop('_sa_instance_state', None)
        if b.Consumer_Label == "TPT145":
            calc_tpt145.append(d)
        else:
            calc_ctr2005.append(d)
    stream = io.BytesIO()
    with pd.ExcelWriter(stream, engine='openpyxl') as writer:
        pd.DataFrame(gen_raw).to_excel(
            writer, index=False, sheet_name='Raw Generator')
        pd.DataFrame(con_tpt145).to_excel(
            writer, index=False, sheet_name='Raw Cons (TPT145)')
        pd.DataFrame(con_ctr2005).to_excel(
            writer, index=False, sheet_name='Raw Cons (CTR2005)')
        pd.DataFrame(iex_tpt145).to_excel(
            writer, index=False, sheet_name='IEX (TPT145)')
        pd.DataFrame(iex_ctr2005).to_excel(
            writer, index=False, sheet_name='IEX (CTR2005)')
        pd.DataFrame(calc_tpt145).to_excel(
            writer, index=False, sheet_name='Calc Blocks (TPT145)')
        pd.DataFrame(calc_ctr2005).to_excel(
            writer, index=False, sheet_name='Calc Blocks (CTR2005)')
    stream.seek(0)
    return stream


@router.get("/timeframes/{id}/export")
async def export_excel(
        id: int,
        type: str,
        consumer: str = "ALL",
        db: AsyncSession = Depends(get_db)):
    if type == "raw_gen":
        res = await db.execute(select(RawGeneratorBlock).where(RawGeneratorBlock.Timeframe_Id == id).order_by(RawGeneratorBlock.Block_Date, RawGeneratorBlock.Slot))
        data = [{"Date": b.Block_Date, "Slot": b.Slot, "Active_KW": b.Active_KW}
                for b in res.scalars().all()]
    elif type == "raw_con":
        query = select(RawConsumerBlock).where(
            RawConsumerBlock.Timeframe_Id == id).order_by(
            RawConsumerBlock.Block_Date,
            RawConsumerBlock.Slot)
        if consumer != "ALL":
            query = query.where(RawConsumerBlock.Consumer_Label == consumer)
        res = await db.execute(query)
        data = [{"Consumer": b.Consumer_Label,
                 "Date": b.Block_Date,
                 "Slot": b.Slot,
                 "Apparent_KVA": b.Apparent_KVA,
                 "Active_KW_Raw": b.Active_KW_Raw} for b in res.scalars().all()]
    elif type == "calculated":
        query = select(CalculatedBlock).where(
            CalculatedBlock.Timeframe_Id == id).order_by(
            CalculatedBlock.Block_Date,
            CalculatedBlock.Slot)
        if consumer != "ALL":
            query = query.where(CalculatedBlock.Consumer_Label == consumer)
        res = await db.execute(query)
        data = [b.__dict__ for b in res.scalars().all()]
        for d in data:
            d.pop('_sa_instance_state', None)
    elif type == "final":
        from sqlalchemy.orm import selectinload
        query = select(SettlementTimeframe).options(
            selectinload(
                SettlementTimeframe.variables)).where(
            SettlementTimeframe.Id == id)
        tf_res = await db.execute(query)
        tf = tf_res.scalar_one_or_none()
        if not tf:
            raise HTTPException(status_code=404, detail="Timeframe not found")
        res_query = select(SettlementResult).where(
            SettlementResult.Timeframe_Id == id)
        res_db = await db.execute(res_query)
        res_db_all = res_db.scalars().all()
        
        total_gen_capped = sum(r.Prior_Sch_At_Entry_KWH for r in res_db_all)

        results = res_db_all
        if consumer != "ALL":
            results = [r for r in results if r.Consumer_Label == consumer]
            
        data = []
        for r in results:
            c_name = 'TPT2831 (19.5MW)'
            data.append({
                "From date": tf.Start_Date,
                "To date": tf.End_Date,
                "Consumer": r.Consumer_Label,
                "Generator": c_name,
                "Max demand date": r.Max_Demand_Date,
                "Max demand time slot": r.Max_Demand_Slot_Str,
                "Prior Schedule At Entry Point": r.Prior_Sch_At_Entry_KWH,
                "Schedule From Bank": r.Sch_From_Bank_KWH,
                "Generator Actual Generation (*)": r.Total_Gen_KWH,
                "Generator Actual Generation Limited to Contracted Capacity": total_gen_capped,
                "Revised Generator Generation Allocated to Consumer at Entry": r.Revised_Gen_Allocated_KWH,
                "Energy Consumed Accountable to Generator": r.Energy_Accountable_KWH,
                "Total Energy Accountable to Generator from all consumers": r.Total_Accountable_KWH,
                "Inadvartent Power to Discoms Due to Less Drawn by Consumer": "-",
                "Bank": r.Bank_KWH,
                "Consumer Actual Consumption": r.Total_Consumer_Actual_KWH,
                "Generator Prior Sch at exit": r.Gen_Prior_Sch_At_Exit_KWH,
                "Generator Realloc Sch at exit": r.Gen_Prior_Sch_At_Exit_KWH,
                "Generator Wise Deviation": 0,
                "Consumer Actual Cons from gen": r.Cons_Actual_From_Gen_KWH,
                "Energy Accountable to Discom in KVAH": r.Discom_KVAH,
                "Schedule At Entry Point in KW": r.Schedule_At_Entry_KW,
                "Actual Generation in KW": r.Actual_Gen_KW,
                "Revised Schedule At Exit Point in KW": r.Revised_Sch_At_Exit_KW,
                "Actual Drawn By Consumer in KW": r.Max_Actual_KW,
                "Consumer Actual Consumption From Generator in KW": r.Cons_From_Gen_KW,
                "Accountable to Discom in KW": r.Accountable_To_Discom_KW,
                "PF Value": r.PF_Value,
                "MAXDEMAND (KVA)": r.Max_Demand_KVA
            })
    elif type == "history_workbook":
        stream = await _generate_history_workbook(db, tf_id=id)
        return StreamingResponse(
            stream,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f"attachment; filename=history_workbook_{id}.xlsx"})

    elif type == "history_workbook":
        stream = await _generate_history_workbook(db, start=start, end=end)
        return StreamingResponse(
            stream,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f"attachment; filename=history_workbook_{start}_to_{end}.xlsx"})
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
        headers={
            "Content-Disposition": f"attachment; filename=export_{type}_{id}.xlsx"})


@router.get("/export/daterange")
async def export_daterange(
        start: date,
        end: date,
        type: str,
        consumer: str = "ALL",
        db: AsyncSession = Depends(get_db)):
    if type == "raw_gen":
        res = await db.execute(select(RawGeneratorBlock).where(RawGeneratorBlock.Block_Date >= start, RawGeneratorBlock.Block_Date <= end).order_by(RawGeneratorBlock.Block_Date, RawGeneratorBlock.Slot))
        data = [{"Date": b.Block_Date, "Slot": b.Slot, "Active_KW": b.Active_KW}
                for b in res.scalars().all()]
    elif type == "raw_con":
        query = select(RawConsumerBlock).where(
            RawConsumerBlock.Block_Date >= start,
            RawConsumerBlock.Block_Date <= end).order_by(
            RawConsumerBlock.Block_Date,
            RawConsumerBlock.Slot)
        if consumer != "ALL":
            query = query.where(RawConsumerBlock.Consumer_Label == consumer)
        res = await db.execute(query)
        data = [{"Consumer": b.Consumer_Label,
                 "Date": b.Block_Date,
                 "Slot": b.Slot,
                 "Apparent_KVA": b.Apparent_KVA,
                 "Active_KW_Raw": b.Active_KW_Raw} for b in res.scalars().all()]
    elif type == "calculated":
        query = select(CalculatedBlock).where(
            CalculatedBlock.Block_Date >= start,
            CalculatedBlock.Block_Date <= end).order_by(
            CalculatedBlock.Block_Date,
            CalculatedBlock.Slot)
        if consumer != "ALL":
            query = query.where(CalculatedBlock.Consumer_Label == consumer)
        res = await db.execute(query)
        data = [b.__dict__ for b in res.scalars().all()]
        for d in data:
            d.pop('_sa_instance_state', None)
    elif type == "history_workbook":
        stream = await _generate_history_workbook(db, start=start, end=end)
        return StreamingResponse(
            stream,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f"attachment; filename=history_workbook_{start}_to_{end}.xlsx"})
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
        headers={
            "Content-Disposition": f"attachment; filename=export_{type}_{start}_to_{end}.xlsx"})


@router.get("/timeframes/{timeframe_id}/export")
async def export_timeframe_history(
        timeframe_id: int,
        db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(SettlementTimeframe).filter(SettlementTimeframe.Id == timeframe_id))
    tf = result.scalar_one_or_none()
    if not tf:
        raise HTTPException(status_code=404, detail="Timeframe not found")
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        stmt = select(RawGeneratorBlock).filter(
            RawGeneratorBlock.Timeframe_Id == timeframe_id)
        res = await db.execute(stmt)
        gen_blocks = res.scalars().all()
        if gen_blocks:
            df = pd.DataFrame([{
                'Block_Date': b.Block_Date,
                'Slot': b.Slot,
                'Active_KW': b.Active_KW
            } for b in gen_blocks])
            df_pivot = pd.pivot_table(df, values=['Active_KW'], index=[
                                      'Block_Date'], columns=['Slot'])
            df_pivot.to_excel(writer, sheet_name="Gen_Raw")
        stmt = select(RawConsumerBlock).filter(
            RawConsumerBlock.Timeframe_Id == timeframe_id)
        res = await db.execute(stmt)
        cons_blocks = res.scalars().all()
        if cons_blocks:
            df = pd.DataFrame([{
                'Consumer_Label': b.Consumer_Label,
                'Block_Date': b.Block_Date,
                'Slot': b.Slot,
                'Apparent_KVA': b.Apparent_KVA,
                'Active_KW_Raw': b.Active_KW_Raw
            } for b in cons_blocks])
            for cons_label, grp in df.groupby('Consumer_Label'):
                grp_pivot = pd.pivot_table(
                    grp,
                    values=[
                        'Apparent_KVA',
                        'Active_KW_Raw'],
                    index=['Block_Date'],
                    columns=['Slot'])
                sheet_name = f"{str(cons_label)[:25]}_Raw"
                grp_pivot.to_excel(writer, sheet_name=sheet_name)
        stmt = select(RawIexBlock).filter(
            RawIexBlock.Timeframe_Id == timeframe_id)
        res = await db.execute(stmt)
        iex_blocks = res.scalars().all()
        if iex_blocks:
            df = pd.DataFrame([{
                'Consumer_Label': b.Consumer_Label,
                'Block_Date': b.Block_Date,
                'Slot': b.Slot,
                'IEX_KW': b.IEX_KW
            } for b in iex_blocks])
            for cons_label, grp in df.groupby('Consumer_Label'):
                grp_pivot = pd.pivot_table(grp, values=['IEX_KW'], index=[
                                           'Block_Date'], columns=['Slot'])
                sheet_name = f"{str(cons_label)[:25]}_IEX"
                grp_pivot.to_excel(writer, sheet_name=sheet_name)
        stmt = select(CalculatedBlock).filter(
            CalculatedBlock.Timeframe_Id == timeframe_id)
        res = await db.execute(stmt)
        calc_blocks = res.scalars().all()
        if calc_blocks:
            df = pd.DataFrame([{
                'Consumer_Label': b.Consumer_Label,
                'Block_Date': b.Block_Date,
                'Slot': b.Slot,
                'Gen_Share_KW': b.Gen_Share_KW,
                'Loss_Pct': b.Loss_Pct,
                'Consumer_KVA': b.Consumer_KVA,
                'Actual_KW': b.Actual_KW,
                'IEX_KW': b.IEX_KW,
                'Aft_KW_Main': b.Aft_KW_Main,
                'Bank_In_Main': b.Bank_In_Main,
                'Net_Gen_Main': b.Net_Gen_Main,
                'Demand_KVA': b.Demand_KVA,
                'Discom_KVA_Block': b.Discom_KVA_Block
            } for b in calc_blocks])
            for cons_label, grp in df.groupby('Consumer_Label'):
                grp_pivot = pd.pivot_table(
                    grp,
                    values=[
                        'Gen_Share_KW',
                        'Loss_Pct',
                        'Consumer_KVA',
                        'Actual_KW',
                        'IEX_KW',
                        'Aft_KW_Main',
                        'Bank_In_Main',
                        'Net_Gen_Main',
                        'Demand_KVA',
                        'Discom_KVA_Block'],
                    index=['Block_Date'],
                    columns=['Slot'])
                sheet_name = f"{str(cons_label)[:25]}_Calc"
                grp_pivot.to_excel(writer, sheet_name=sheet_name)
        if not writer.sheets:
            df_empty = pd.DataFrame(
                {'Message': ['No data found for this timeframe']})
            df_empty.to_excel(writer, sheet_name="Empty")
    buffer.seek(0)
    headers = {
        'Content-Disposition': f'attachment; filename="Settlement_History_{tf.Month}_{tf.Year}.xlsx"'
    }
    return StreamingResponse(
        buffer,
        headers=headers,
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

@router.post("/timeframes/{timeframe_id}/verify-check-file")
async def verify_check_file(
        timeframe_id: int,
        file: UploadFile = File(...),
        db: AsyncSession = Depends(get_db)):
    try:
        contents = await file.read()
        import pandas as pd
        import io
        df = pd.read_excel(io.BytesIO(contents), header=None)
        
        stmt = select(SettlementResult).filter(SettlementResult.Timeframe_Id == timeframe_id)
        res = await db.execute(stmt)
        db_results = res.scalars().all()
        
        if not db_results:
            return {"success": False, "error": "No calculated results found for this timeframe."}
        
        mapping = [
            ("Prior Schedule At Entry", "Prior_Sch_At_Entry_KWH", 7),
            ("Schedule From Bank", "Sch_From_Bank_KWH", 8),
            ("Total Generator Output", "Total_Gen_KWH", 10),
            ("Revised Gen Allocated", "Revised_Gen_Allocated_KWH", 11),
            ("Energy Accountable", "Energy_Accountable_KWH", 12),
            ("Total Accountable", "Total_Accountable_KWH", 13),
            ("Bank", "Bank_KWH", 15),
            ("Total Consumer Actual", "Total_Consumer_Actual_KWH", 16),
            ("Gen Prior Sch at Exit", "Gen_Prior_Sch_At_Exit_KWH", 17),
            ("Consumer Actual From Gen", "Cons_Actual_From_Gen_KWH", 20),
            ("Discom KVAH", "Discom_KVAH", 21),
            ("Schedule At Entry KW", "Schedule_At_Entry_KW", 22),
            ("Actual Gen KW", "Actual_Gen_KW", 23),
            ("Revised Sch At Exit KW", "Revised_Sch_At_Exit_KW", 24),
            ("Max Actual KW", "Max_Actual_KW", 25),
            ("Cons From Gen KW", "Cons_From_Gen_KW", 26),
            ("Accountable To Discom KW", "Accountable_To_Discom_KW", 27),
            ("Average PF", "PF_Value", 28),
            ("Max Demand KVA", "Max_Demand_KVA", 29)
        ]
        
        verification_data = []
        
        for db_res in db_results:
            label = db_res.Consumer_Label
            # Find row in Excel
            row = None
            for i in range(len(df)):
                val = df.iloc[i, 3]
                if isinstance(val, str) and label in val:
                    row = df.iloc[i]
                    break
            
            if row is None:
                continue
                
            metrics = []
            for name, db_col, xl_col in mapping:
                app_val = getattr(db_res, db_col, 0.0)
                check_val = row[xl_col]
                
                try:
                    app_val = float(app_val)
                except:
                    app_val = 0.0
                    
                try:
                    check_val = float(check_val)
                except:
                    check_val = 0.0
                
                diff = app_val - check_val
                metrics.append({
                    "name": name,
                    "app_val": app_val,
                    "check_val": check_val,
                    "diff": diff
                })
            
            verification_data.append({
                "consumer": label,
                "metrics": metrics
            })
            
        return {"success": True, "data": verification_data}
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}
