import os
import shutil
import re
from datetime import date, timedelta
import calendar
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from app.infrastructure.models import (
    UploadSession, SettlementVariables, SettlementTimeframe
)
from app.infrastructure.config import settings
from app.adapters.parsers.cdf_parser import parse_gen_cdf, parse_cons_cdf
from app.adapters.parsers.iex_parser import parse_iex_excel
import logging
logger = logging.getLogger(__name__)


async def handle_upload(
        db: AsyncSession,
        timeframe_id: int,
        file_type: str,
        file: UploadFile):
    var_res = await db.execute(select(SettlementVariables).where(SettlementVariables.Timeframe_Id == timeframe_id))
    variables = var_res.scalar_one_or_none()
    if not variables:
        variables = SettlementVariables(Timeframe_Id=timeframe_id)
        db.add(variables)
        await db.flush()
    tf_res = await db.execute(select(SettlementTimeframe).where(SettlementTimeframe.Id == timeframe_id))
    tf = tf_res.scalar_one_or_none()
    if not tf:
        raise ValueError("Timeframe not found")
    upload_dir = os.path.join(
        settings.UPLOAD_DIR,
        str(timeframe_id),
        file_type)
        
                                                                                 
    if os.path.exists(upload_dir):
        shutil.rmtree(upload_dir)
    os.makedirs(upload_dir, exist_ok=True)
    
                                                                           
    safe_filename = os.path.basename(file.filename) if file.filename else f"{file_type}_file"
    safe_filename = re.sub(r'[^a-zA-Z0-9.\-_ ]', '', safe_filename).strip()
    if not safe_filename:
        safe_filename = f"{file_type}_file"
        
    file_path = os.path.join(upload_dir, safe_filename)
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)
    session_record = UploadSession(
        Timeframe_Id=timeframe_id,
        File_Type=file_type,
        Original_Filename=file.filename,
        Stored_Path=file_path,
        File_Size_Bytes=len(content)
    )
    db.add(session_record)
    try:
        blocks_inserted = 0
        blocks_parsed = 0
        if file_type == 'gen_cdf':
            variables.Gen_CDF_Path = file_path
            month_start = date(tf.Year, tf.Month, 1)
            month_end = date(
                tf.Year, tf.Month, calendar.monthrange(
                    tf.Year, tf.Month)[1])
            blocks = parse_gen_cdf(file_path, month_start, month_end, 4)
            blocks_parsed = len(blocks)
            if blocks:
                await db.execute(text("DELETE FROM Raw_Generator_Blocks WHERE Timeframe_Id = :tf_id"), {"tf_id": timeframe_id})
                stmt = text("""
                    INSERT INTO Raw_Generator_Blocks (Timeframe_Id, Block_Date, Slot, Active_KW)
                    VALUES (:Timeframe_Id, :Block_Date, :Slot, :Active_KW)
                """)
                params = [{"Timeframe_Id": timeframe_id,
                           "Block_Date": b["Block_Date"],
                           "Slot": b["Slot"],
                           "Active_KW": b["Active_KW"]} for b in blocks]
                await db.execute(stmt, params)
                blocks_inserted = len(blocks)
        elif file_type == 'con1_cdf':
            variables.Con1_CDF_Path = file_path
            month_start = date(tf.Year, tf.Month, 1)
            month_end = date(
                tf.Year, tf.Month, calendar.monthrange(
                    tf.Year, tf.Month)[1])
            blocks = parse_cons_cdf(
                file_path, 'TPT145', month_start, month_end, 4)
            blocks_parsed = len(blocks)
            if blocks:
                await db.execute(text("DELETE FROM Raw_Consumer_Blocks WHERE Timeframe_Id = :tf_id AND Consumer_Label = 'TPT145'"), {"tf_id": timeframe_id})
                stmt = text("""
                    INSERT INTO Raw_Consumer_Blocks (Timeframe_Id, Consumer_Label, Block_Date, Slot, Apparent_KVA, Active_KW_Raw)
                    VALUES (:Timeframe_Id, :Consumer_Label, :Block_Date, :Slot, :Apparent_KVA, :Active_KW_Raw)
                """)
                params = [{"Timeframe_Id": timeframe_id,
                           "Consumer_Label": b["Consumer_Label"],
                           "Block_Date": b["Block_Date"],
                           "Slot": b["Slot"],
                           "Apparent_KVA": b["Apparent_KVA"],
                           "Active_KW_Raw": b["Active_KW_Raw"]} for b in blocks]
                await db.execute(stmt, params)
                blocks_inserted = len(blocks)
        elif file_type == 'con2_cdf':
            variables.Con2_CDF_Path = file_path
            month_start = date(tf.Year, tf.Month, 1)
            month_end = date(
                tf.Year, tf.Month, calendar.monthrange(
                    tf.Year, tf.Month)[1])
            blocks = parse_cons_cdf(
                file_path, 'CTR2005', month_start, month_end, 4)
            blocks_parsed = len(blocks)
            if blocks:
                await db.execute(text("DELETE FROM Raw_Consumer_Blocks WHERE Timeframe_Id = :tf_id AND Consumer_Label = 'CTR2005'"), {"tf_id": timeframe_id})
                stmt = text("""
                    INSERT INTO Raw_Consumer_Blocks (Timeframe_Id, Consumer_Label, Block_Date, Slot, Apparent_KVA, Active_KW_Raw)
                    VALUES (:Timeframe_Id, :Consumer_Label, :Block_Date, :Slot, :Apparent_KVA, :Active_KW_Raw)
                """)
                params = [{"Timeframe_Id": timeframe_id,
                           "Consumer_Label": b["Consumer_Label"],
                           "Block_Date": b["Block_Date"],
                           "Slot": b["Slot"],
                           "Apparent_KVA": b["Apparent_KVA"],
                           "Active_KW_Raw": b["Active_KW_Raw"]} for b in blocks]
                await db.execute(stmt, params)
                blocks_inserted = len(blocks)
        elif file_type == 'iex1':
            variables.IEX1_Path = file_path
            month_start = date(tf.Year, tf.Month, 1)
            month_end = date(
                tf.Year, tf.Month, calendar.monthrange(
                    tf.Year, tf.Month)[1])
            blocks = parse_iex_excel(file_path, 'TPT145', month_start, month_end)
            blocks_parsed = len(blocks)
            if blocks:
                await db.execute(text("DELETE FROM Raw_IEX_Blocks WHERE Timeframe_Id = :tf_id AND Consumer_Label = 'TPT145'"), {"tf_id": timeframe_id})
                stmt = text("""
                    INSERT INTO Raw_IEX_Blocks (Timeframe_Id, Consumer_Label, Block_Date, Slot, IEX_KW)
                    VALUES (:Timeframe_Id, :Consumer_Label, :Block_Date, :Slot, :IEX_KW)
                """)
                params = [{"Timeframe_Id": timeframe_id,
                           "Consumer_Label": b["Consumer_Label"],
                           "Block_Date": b["Block_Date"],
                           "Slot": b["Slot"],
                           "IEX_KW": b["IEX_KW"]} for b in blocks]
                await db.execute(stmt, params)
                blocks_inserted = len(blocks)
        elif file_type == 'iex2':
            variables.IEX2_Path = file_path
            month_start = date(tf.Year, tf.Month, 1)
            month_end = date(
                tf.Year, tf.Month, calendar.monthrange(
                    tf.Year, tf.Month)[1])
            blocks = parse_iex_excel(file_path, 'CTR2005', month_start, month_end)
            blocks_parsed = len(blocks)
            if blocks:
                await db.execute(text("DELETE FROM Raw_IEX_Blocks WHERE Timeframe_Id = :tf_id AND Consumer_Label = 'CTR2005'"), {"tf_id": timeframe_id})
                stmt = text("""
                    INSERT INTO Raw_IEX_Blocks (Timeframe_Id, Consumer_Label, Block_Date, Slot, IEX_KW)
                    VALUES (:Timeframe_Id, :Consumer_Label, :Block_Date, :Slot, :IEX_KW)
                """)
                params = [{"Timeframe_Id": timeframe_id,
                           "Consumer_Label": b["Consumer_Label"],
                           "Block_Date": b["Block_Date"],
                           "Slot": b["Slot"],
                           "IEX_KW": b["IEX_KW"]} for b in blocks]
                await db.execute(stmt, params)
                blocks_inserted = len(blocks)
        session_record.Blocks_Parsed = blocks_parsed
        session_record.Blocks_Inserted = blocks_inserted
        session_record.Parse_Status = 'OK'
        await db.commit()
        return {
            "success": True,
            "blocks_parsed": blocks_parsed,
            "blocks_inserted": blocks_inserted
        }
    except Exception as e:
        logger.error(f"Error parsing {file_type}: {e}")
        await db.rollback()
        return {"success": False, "error": str(e)}
