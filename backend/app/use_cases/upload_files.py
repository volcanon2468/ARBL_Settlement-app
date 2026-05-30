import os
from datetime import datetime
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from app.infrastructure.models import (
    UploadSession, RawGeneratorBlock, RawConsumerBlock, RawIexBlock, SettlementVariables
)
from app.infrastructure.config import settings
from app.adapters.parsers.cdf_parser import parse_gen_cdf, parse_cons_cdf
from app.adapters.parsers.iex_parser import parse_iex_excel
import logging

logger = logging.getLogger(__name__)

async def handle_upload(db: AsyncSession, timeframe_id: int, file_type: str, file: UploadFile):
    # Ensure variables exist
    var_res = await db.execute(select(SettlementVariables).where(SettlementVariables.Timeframe_Id == timeframe_id))
    variables = var_res.scalar_one_or_none()
    if not variables:
        variables = SettlementVariables(Timeframe_Id=timeframe_id)
        db.add(variables)
        await db.flush()

    upload_dir = os.path.join(settings.UPLOAD_DIR, str(timeframe_id), file_type)
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, file.filename)
    
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
            blocks = parse_gen_cdf(file_path, variables.CT_Ratio)
            blocks_parsed = len(blocks)
            if blocks:
                stmt = text("""
                    MERGE Raw_Generator_Blocks AS target
                    USING (VALUES (:Timeframe_Id, :Block_Date, :Slot, :Active_KW)) AS source (Timeframe_Id, Block_Date, Slot, Active_KW)
                    ON target.Timeframe_Id = source.Timeframe_Id AND target.Block_Date = source.Block_Date AND target.Slot = source.Slot
                    WHEN NOT MATCHED THEN
                        INSERT (Timeframe_Id, Block_Date, Slot, Active_KW)
                        VALUES (source.Timeframe_Id, source.Block_Date, source.Slot, source.Active_KW);
                """)
                for b in blocks:
                    res = await db.execute(stmt, {"Timeframe_Id": timeframe_id, "Block_Date": b["Block_Date"], "Slot": b["Slot"], "Active_KW": b["Active_KW"]})
                    blocks_inserted += res.rowcount
                
        elif file_type == 'con1_cdf':
            variables.Con1_CDF_Path = file_path
            blocks = parse_cons_cdf(file_path, variables.Con1_Label, variables.CT_Ratio)
            blocks_parsed = len(blocks)
            if blocks:
                stmt = text("""
                    MERGE Raw_Consumer_Blocks AS target
                    USING (VALUES (:Timeframe_Id, :Consumer_Label, :Block_Date, :Slot, :Apparent_KVA, :Active_KW_Raw)) AS source (Timeframe_Id, Consumer_Label, Block_Date, Slot, Apparent_KVA, Active_KW_Raw)
                    ON target.Timeframe_Id = source.Timeframe_Id AND target.Consumer_Label = source.Consumer_Label AND target.Block_Date = source.Block_Date AND target.Slot = source.Slot
                    WHEN NOT MATCHED THEN
                        INSERT (Timeframe_Id, Consumer_Label, Block_Date, Slot, Apparent_KVA, Active_KW_Raw)
                        VALUES (source.Timeframe_Id, source.Consumer_Label, source.Block_Date, source.Slot, source.Apparent_KVA, source.Active_KW_Raw);
                """)
                for b in blocks:
                    res = await db.execute(stmt, {"Timeframe_Id": timeframe_id, "Consumer_Label": b["Consumer_Label"], "Block_Date": b["Block_Date"], "Slot": b["Slot"], "Apparent_KVA": b["Apparent_KVA"], "Active_KW_Raw": b["Active_KW_Raw"]})
                    blocks_inserted += res.rowcount
                
        elif file_type == 'con2_cdf':
            variables.Con2_CDF_Path = file_path
            blocks = parse_cons_cdf(file_path, variables.Con2_Label, variables.CT_Ratio)
            blocks_parsed = len(blocks)
            if blocks:
                stmt = text("""
                    MERGE Raw_Consumer_Blocks AS target
                    USING (VALUES (:Timeframe_Id, :Consumer_Label, :Block_Date, :Slot, :Apparent_KVA, :Active_KW_Raw)) AS source (Timeframe_Id, Consumer_Label, Block_Date, Slot, Apparent_KVA, Active_KW_Raw)
                    ON target.Timeframe_Id = source.Timeframe_Id AND target.Consumer_Label = source.Consumer_Label AND target.Block_Date = source.Block_Date AND target.Slot = source.Slot
                    WHEN NOT MATCHED THEN
                        INSERT (Timeframe_Id, Consumer_Label, Block_Date, Slot, Apparent_KVA, Active_KW_Raw)
                        VALUES (source.Timeframe_Id, source.Consumer_Label, source.Block_Date, source.Slot, source.Apparent_KVA, source.Active_KW_Raw);
                """)
                for b in blocks:
                    res = await db.execute(stmt, {"Timeframe_Id": timeframe_id, "Consumer_Label": b["Consumer_Label"], "Block_Date": b["Block_Date"], "Slot": b["Slot"], "Apparent_KVA": b["Apparent_KVA"], "Active_KW_Raw": b["Active_KW_Raw"]})
                    blocks_inserted += res.rowcount
                
        elif file_type == 'iex1':
            variables.IEX1_Path = file_path
            blocks = parse_iex_excel(file_path, variables.Con1_Label)
            blocks_parsed = len(blocks)
            if blocks:
                stmt = text("""
                    MERGE Raw_IEX_Blocks AS target
                    USING (VALUES (:Timeframe_Id, :Consumer_Label, :Block_Date, :Slot, :IEX_KW)) AS source (Timeframe_Id, Consumer_Label, Block_Date, Slot, IEX_KW)
                    ON target.Timeframe_Id = source.Timeframe_Id AND target.Consumer_Label = source.Consumer_Label AND target.Block_Date = source.Block_Date AND target.Slot = source.Slot
                    WHEN NOT MATCHED THEN
                        INSERT (Timeframe_Id, Consumer_Label, Block_Date, Slot, IEX_KW)
                        VALUES (source.Timeframe_Id, source.Consumer_Label, source.Block_Date, source.Slot, source.IEX_KW);
                """)
                for b in blocks:
                    res = await db.execute(stmt, {"Timeframe_Id": timeframe_id, "Consumer_Label": b["Consumer_Label"], "Block_Date": b["Block_Date"], "Slot": b["Slot"], "IEX_KW": b["IEX_KW"]})
                    blocks_inserted += res.rowcount
                
        elif file_type == 'iex2':
            variables.IEX2_Path = file_path
            blocks = parse_iex_excel(file_path, variables.Con2_Label)
            blocks_parsed = len(blocks)
            if blocks:
                stmt = text("""
                    MERGE Raw_IEX_Blocks AS target
                    USING (VALUES (:Timeframe_Id, :Consumer_Label, :Block_Date, :Slot, :IEX_KW)) AS source (Timeframe_Id, Consumer_Label, Block_Date, Slot, IEX_KW)
                    ON target.Timeframe_Id = source.Timeframe_Id AND target.Consumer_Label = source.Consumer_Label AND target.Block_Date = source.Block_Date AND target.Slot = source.Slot
                    WHEN NOT MATCHED THEN
                        INSERT (Timeframe_Id, Consumer_Label, Block_Date, Slot, IEX_KW)
                        VALUES (source.Timeframe_Id, source.Consumer_Label, source.Block_Date, source.Slot, source.IEX_KW);
                """)
                for b in blocks:
                    res = await db.execute(stmt, {"Timeframe_Id": timeframe_id, "Consumer_Label": b["Consumer_Label"], "Block_Date": b["Block_Date"], "Slot": b["Slot"], "IEX_KW": b["IEX_KW"]})
                    blocks_inserted += res.rowcount

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
        session_record.Parse_Status = 'ERROR'
        session_record.Error_Message = str(e)
        await db.commit()
        return {"success": False, "error": str(e)}
