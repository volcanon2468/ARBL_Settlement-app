import logging
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.infrastructure.database import engine
from app.infrastructure.models import (
    SettlementTimeframe, SettlementVariables, ShutdownWindow, CustomLossWindow,
    RawGeneratorBlock, RawConsumerBlock, RawIexBlock, CalculatedBlock, SettlementResult
)
from app.domain.settlement_engine import SettlementEngine
import time
from datetime import datetime

logger = logging.getLogger(__name__)

# This runs inside Celery worker, we use synchronous session for simplicity here,
# or we can use async session if we properly wrap it. Given the celery worker environment,
# async wrapping is preferred if using async engine.
import asyncio

async def _run_calculation_async(timeframe_id: int):
    logger.info(f"Starting calculation for timeframe {timeframe_id}")
    async with engine.begin() as conn:
        from sqlalchemy.ext.asyncio import AsyncSession
        async_session = AsyncSession(conn)
        
        # Load timeframe and variables
        tf = await async_session.execute(select(SettlementTimeframe).where(SettlementTimeframe.Id == timeframe_id))
        tf = tf.scalar_one_or_none()
        if not tf:
            raise ValueError("Timeframe not found")
            
        tf.Status = 'CALCULATING'
        await async_session.commit()
        
        start_time = time.time()
        
        try:
            var_res = await async_session.execute(select(SettlementVariables).where(SettlementVariables.Timeframe_Id == timeframe_id))
            variables = var_res.scalar_one_or_none()
            if not variables:
                raise ValueError("Variables not configured")
                
            var_dict = {
                'Share_Cons1': variables.Share_Cons1,
                'Share_Cons2': variables.Share_Cons2,
                'Default_Loss': variables.Default_Loss,
                'Old_Bank_KWH': variables.Old_Bank_KWH,
                'Bank_Loss_Pct': variables.Bank_Loss_Pct,
                'Cap_Gen_KW': variables.Cap_Gen_KW,
                'Cap_Cons1_KW': variables.Cap_Cons1_KW,
                'Cap_Cons2_KW': variables.Cap_Cons2_KW,
                'CT_Ratio': variables.CT_Ratio,
                'Con1_Label': variables.Con1_Label,
                'Con2_Label': variables.Con2_Label
            }
            
            # Load windows
            sh_res = await async_session.execute(select(ShutdownWindow).where(ShutdownWindow.Timeframe_Id == timeframe_id))
            shutdowns = [{'Window_Start': s.Window_Start, 'Window_End': s.Window_End} for s in sh_res.scalars().all()]
            
            cl_res = await async_session.execute(select(CustomLossWindow).where(CustomLossWindow.Timeframe_Id == timeframe_id))
            custom_losses = [{'Window_Start': c.Window_Start, 'Window_End': c.Window_End, 'Loss_Pct': c.Loss_Pct} for c in cl_res.scalars().all()]
            
            # Load raw blocks
            gen_res = await async_session.execute(select(RawGeneratorBlock).where(RawGeneratorBlock.Timeframe_Id == timeframe_id))
            raw_gen = [{'Block_Date': b.Block_Date, 'Slot': b.Slot, 'Active_KW': b.Active_KW} for b in gen_res.scalars().all()]
            
            c1_res = await async_session.execute(select(RawConsumerBlock).where(
                RawConsumerBlock.Timeframe_Id == timeframe_id, RawConsumerBlock.Consumer_Label == variables.Con1_Label))
            raw_c1 = [{'Block_Date': b.Block_Date, 'Slot': b.Slot, 'Apparent_KVA': b.Apparent_KVA, 'Active_KW_Raw': b.Active_KW_Raw} for b in c1_res.scalars().all()]
            
            c2_res = await async_session.execute(select(RawConsumerBlock).where(
                RawConsumerBlock.Timeframe_Id == timeframe_id, RawConsumerBlock.Consumer_Label == variables.Con2_Label))
            raw_c2 = [{'Block_Date': b.Block_Date, 'Slot': b.Slot, 'Apparent_KVA': b.Apparent_KVA, 'Active_KW_Raw': b.Active_KW_Raw} for b in c2_res.scalars().all()]
            
            iex1_res = await async_session.execute(select(RawIexBlock).where(
                RawIexBlock.Timeframe_Id == timeframe_id, RawIexBlock.Consumer_Label == variables.Con1_Label))
            raw_iex1 = [{'Block_Date': b.Block_Date, 'Slot': b.Slot, 'IEX_KW': b.IEX_KW} for b in iex1_res.scalars().all()]
            
            iex2_res = await async_session.execute(select(RawIexBlock).where(
                RawIexBlock.Timeframe_Id == timeframe_id, RawIexBlock.Consumer_Label == variables.Con2_Label))
            raw_iex2 = [{'Block_Date': b.Block_Date, 'Slot': b.Slot, 'IEX_KW': b.IEX_KW} for b in iex2_res.scalars().all()]
            
            # Run Engine
            engine_calc = SettlementEngine(
                start_date=tf.Start_Date,
                end_date=tf.End_Date,
                variables=var_dict,
                shutdown_windows=shutdowns,
                custom_losses=custom_losses,
                raw_gen_blocks=raw_gen,
                raw_cons1_blocks=raw_c1,
                raw_cons2_blocks=raw_c2,
                raw_iex1_blocks=raw_iex1,
                raw_iex2_blocks=raw_iex2
            )
            
            import asyncio
            res = await asyncio.to_thread(engine_calc.run)
            duration = time.time() - start_time
            
            # Clear old calculated data
            from sqlalchemy import delete
            await async_session.execute(delete(CalculatedBlock).where(CalculatedBlock.Timeframe_Id == timeframe_id))
            await async_session.execute(delete(SettlementResult).where(SettlementResult.Timeframe_Id == timeframe_id))
            
            # Insert calculated blocks in batches to avoid huge memory/query sizes
            calc_blocks = []
            for b in res['calculated_blocks']:
                calc_blocks.append(CalculatedBlock(Timeframe_Id=timeframe_id, **b))
            
            async_session.add_all(calc_blocks)
            
            # Insert results
            for r in res['results']:
                async_session.add(SettlementResult(
                    Timeframe_Id=timeframe_id, 
                    Calculated_At=datetime.utcnow(),
                    Calc_Duration_Seconds=duration,
                    **r
                ))
                
            tf.Status = 'COMPLETE'
            await async_session.commit()
            logger.info("Calculation complete.")
            
        except Exception as e:
            await async_session.rollback()
            from sqlalchemy import update
            await async_session.execute(
                update(SettlementTimeframe).where(SettlementTimeframe.Id == timeframe_id).values(Status='ERROR')
            )
            await async_session.commit()
            logger.error(f"Error during calculation: {e}")
            raise e


