import logging
from sqlalchemy import select

from app.infrastructure.database import engine
from app.infrastructure.models import (
    SettlementTimeframe,
    SettlementVariables,
    ShutdownWindow,
    CustomLossWindow,
    RawGeneratorBlock,
    RawConsumerBlock,
    RawIexBlock,
    CalculatedBlock,
    SettlementResult,
    BankLedgerTransaction)
from app.domain.settlement_engine import SettlementEngine
import time
from datetime import datetime
logger = logging.getLogger(__name__)


async def _run_calculation_async(timeframe_id: int):
    logger.info(f"Starting calculation for timeframe {timeframe_id}")
    try:
        async with engine.begin() as conn:
            from sqlalchemy.ext.asyncio import AsyncSession
            async_session = AsyncSession(conn)
            tf = await async_session.execute(select(SettlementTimeframe).where(SettlementTimeframe.Id == timeframe_id))
            tf = tf.scalar_one_or_none()
            if not tf:
                raise ValueError("Timeframe not found")
            import calendar
            from datetime import date
            start_date = date(tf.Year, tf.Month, 1)
            end_date = date(
                tf.Year, tf.Month, calendar.monthrange(
                    tf.Year, tf.Month)[1])
            start_slot = 1
            end_slot = 96
            from sqlalchemy import update
            await async_session.execute(
                update(SettlementTimeframe)
                .where(SettlementTimeframe.Id == timeframe_id)
                .values(Status='CALCULATING')
            )
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
                    'Bank_Loss_Pct': variables.Bank_Loss_Pct,
                    'Override_Capacity_MW': variables.Override_Capacity_MW,
                    'Cap_Share_Cons1': variables.Cap_Share_Cons1,
                    'Cap_Share_Cons2': variables.Cap_Share_Cons2,
                    'Con1_Label': 'TPT145',
                    'Con2_Label': 'CTR2005'
                }
                from sqlalchemy import delete, update
                past_tx_res = await async_session.execute(
                    select(BankLedgerTransaction).where(BankLedgerTransaction.Consumer_Timeframe_Id == timeframe_id)
                )
                past_txs = past_tx_res.scalars().all()
                for tx in past_txs:
                    await async_session.execute(
                        update(SettlementVariables)
                        .where(SettlementVariables.Timeframe_Id == tx.Source_Timeframe_Id)
                        .values(Banked_Remaining_KWH=SettlementVariables.Banked_Remaining_KWH + tx.Amount_KWH)
                    )
                if past_txs:
                    await async_session.execute(
                        delete(BankLedgerTransaction).where(BankLedgerTransaction.Consumer_Timeframe_Id == timeframe_id)
                    )
                s_month = variables.Bank_Usage_Start_Month
                s_year = variables.Bank_Usage_Start_Year
                e_month = variables.Bank_Usage_End_Month
                e_year = variables.Bank_Usage_End_Year
                available_sources = []
                total_old_bank = 0.0
                if s_month and s_year and e_month and e_year:
                    all_tf_res = await async_session.execute(
                        select(SettlementTimeframe, SettlementVariables)
                        .join(SettlementVariables, SettlementVariables.Timeframe_Id == SettlementTimeframe.Id)
                        .where(SettlementVariables.Banked_Remaining_KWH > 0)
                    )
                    start_val = s_year * 12 + s_month
                    end_val = e_year * 12 + e_month
                    for tf_row, var_row in all_tf_res.all():
                        val = tf_row.Year * 12 + tf_row.Month
                        if start_val <= val <= end_val and tf_row.Id != timeframe_id:
                            available_sources.append({
                                'Id': tf_row.Id,
                                'Month': tf_row.Month,
                                'Year': tf_row.Year,
                                'Remaining': var_row.Banked_Remaining_KWH,
                                'SortVal': val
                            })
                    available_sources.sort(key=lambda x: x['SortVal'])
                    total_old_bank = sum(s['Remaining']
                                         for s in available_sources)
                var_dict['Old_Bank_KWH'] = total_old_bank
                
                def parse_dt(dt_str, is_end=False):
                    dt_str = dt_str.strip()
                    if ' ' not in dt_str:
                        if len(dt_str.split('-')[0]) == 4:
                            dt = datetime.strptime(dt_str, '%Y-%m-%d')
                        else:
                            dt = datetime.strptime(dt_str, '%d-%m-%Y')
                        if is_end:
                            dt = dt.replace(hour=23, minute=59, second=59, microsecond=999999)
                        return dt
                    if len(dt_str.split('-')[0]) == 4:
                        return datetime.strptime(dt_str, '%Y-%m-%d %H:%M')
                    return datetime.strptime(dt_str, '%d-%m-%Y %H:%M')
                
                sh_res = await async_session.execute(select(ShutdownWindow).where(ShutdownWindow.Timeframe_Id == timeframe_id))
                shutdowns = [{'Window_Start': parse_dt(s.Window_Start),
                              'Window_End': parse_dt(s.Window_End, is_end=False)} for s in sh_res.scalars().all()]
                cl_res = await async_session.execute(select(CustomLossWindow).where(CustomLossWindow.Timeframe_Id == timeframe_id))
                custom_losses = [{'Window_Start': parse_dt(c.Window_Start),
                                  'Window_End': parse_dt(c.Window_End, is_end=True),
                                  'Loss_Pct': c.Loss_Pct} for c in cl_res.scalars().all()]
                gen_res = await async_session.execute(select(RawGeneratorBlock).where(RawGeneratorBlock.Timeframe_Id == timeframe_id))
                raw_gen = [{'Block_Date': b.Block_Date, 'Slot': b.Slot,
                            'Active_KW': b.Active_KW} for b in gen_res.scalars().all()]
                c1_res = await async_session.execute(select(RawConsumerBlock).where(
                    RawConsumerBlock.Timeframe_Id == timeframe_id, RawConsumerBlock.Consumer_Label == 'TPT145'))
                raw_c1 = [{'Block_Date': b.Block_Date,
                           'Slot': b.Slot,
                           'Apparent_KVA': b.Apparent_KVA,
                           'Active_KW_Raw': b.Active_KW_Raw} for b in c1_res.scalars().all()]
                c2_res = await async_session.execute(select(RawConsumerBlock).where(
                    RawConsumerBlock.Timeframe_Id == timeframe_id, RawConsumerBlock.Consumer_Label == 'CTR2005'))
                raw_c2 = [{'Block_Date': b.Block_Date,
                           'Slot': b.Slot,
                           'Apparent_KVA': b.Apparent_KVA,
                           'Active_KW_Raw': b.Active_KW_Raw} for b in c2_res.scalars().all()]
                iex1_res = await async_session.execute(select(RawIexBlock).where(
                    RawIexBlock.Timeframe_Id == timeframe_id, RawIexBlock.Consumer_Label == 'TPT145'))
                raw_iex1 = [{'Block_Date': b.Block_Date, 'Slot': b.Slot,
                             'IEX_KW': b.IEX_KW} for b in iex1_res.scalars().all()]
                iex2_res = await async_session.execute(select(RawIexBlock).where(
                    RawIexBlock.Timeframe_Id == timeframe_id, RawIexBlock.Consumer_Label == 'CTR2005'))
                raw_iex2 = [{'Block_Date': b.Block_Date, 'Slot': b.Slot,
                             'IEX_KW': b.IEX_KW} for b in iex2_res.scalars().all()]
                engine_calc = SettlementEngine(
                    start_date=start_date,
                    end_date=end_date,
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
                from sqlalchemy import delete
                await async_session.execute(delete(CalculatedBlock).where(CalculatedBlock.Timeframe_Id == timeframe_id))
                await async_session.execute(delete(SettlementResult).where(SettlementResult.Timeframe_Id == timeframe_id))
                calc_blocks = []
                for b in res['calculated_blocks']:
                    calc_blocks.append(
                        CalculatedBlock(
                            Timeframe_Id=timeframe_id, **b))
                async_session.add_all(calc_blocks)
                for r in res['results']:
                    async_session.add(SettlementResult(
                        Timeframe_Id=timeframe_id,
                        Calculated_At=datetime.utcnow(),
                        Calc_Duration_Seconds=duration,
                        **r
                    ))
                await async_session.execute(
                    update(SettlementTimeframe)
                    .where(SettlementTimeframe.Id == timeframe_id)
                    .values(Status='COMPLETED')
                )
                total_consumed_bank = sum(r.get('Sch_From_Bank_KWH', 0) for r in res['results'])
                remaining_to_deduct = total_consumed_bank
                transactions_to_insert = []
                for source in available_sources:
                    if remaining_to_deduct <= 0.001:
                        break
                    take = min(source['Remaining'], remaining_to_deduct)
                    remaining_to_deduct -= take
                    await async_session.execute(
                        update(SettlementVariables)
                        .where(SettlementVariables.Timeframe_Id == source['Id'])
                        .values(Banked_Remaining_KWH=SettlementVariables.Banked_Remaining_KWH - take)
                    )
                    transactions_to_insert.append(BankLedgerTransaction(
                        Consumer_Timeframe_Id=timeframe_id,
                        Source_Timeframe_Id=source['Id'],
                        Amount_KWH=take
                    ))
                if transactions_to_insert:
                    async_session.add_all(transactions_to_insert)
                total_new_bank = sum(r.get('Bank_KWH', 0) for r in res['results'])
                await async_session.execute(
                    update(SettlementVariables)
                    .where(SettlementVariables.Timeframe_Id == timeframe_id)
                    .values(Banked_Added_KWH=total_new_bank, Banked_Remaining_KWH=total_new_bank)
                )
                await async_session.commit()
                logger.info(
                    f"Calculation for timeframe {timeframe_id} completed in {duration:.2f}s")
            except Exception as e:
                logger.error(f"Error during calculation: {e}", exc_info=True)
                await async_session.rollback()
                raise e
    except Exception as e:
        async with engine.begin() as conn:
            from sqlalchemy import update
            from sqlalchemy.ext.asyncio import AsyncSession
            async_session = AsyncSession(conn)
            try:
                await async_session.execute(
                    update(SettlementTimeframe).where(SettlementTimeframe.Id == timeframe_id).values(Status='ERROR')
                )
                await async_session.commit()
            except Exception as inner_e:
                await async_session.rollback()
                logger.error(
                    f"Failed to set ERROR status for timeframe {timeframe_id}: {inner_e}")
        raise e
