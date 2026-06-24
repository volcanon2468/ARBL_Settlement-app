from datetime import datetime, timedelta, date
from typing import List, Dict, Set, Tuple


def build_shutdown_blocks(
        shutdown_windows: List[Dict]) -> Set[Tuple[date, int]]:
    blocks = set()
    fmt = "%d-%m-%Y %H:%M"
    for window in shutdown_windows:
        dt_from = window['Window_Start'] if isinstance(window['Window_Start'], datetime) else datetime.strptime(window['Window_Start'].strip(), fmt)
        dt_to = window['Window_End'] if isinstance(window['Window_End'], datetime) else datetime.strptime(window['Window_End'].strip(), fmt)
        current = dt_from
        while current < dt_to:
            d = current.date()
            slot = (current.hour * 60 + current.minute) // 15 + 1
            blocks.add((d, slot))
            current += timedelta(minutes=15)
    return blocks


def get_block_loss(
        d: date,
        slot: int,
        custom_losses: List[Dict],
        default_loss: float) -> float:
    start_h = (slot - 1) * 15 // 60
    start_m = (slot - 1) * 15 % 60
    block_dt = datetime(d.year, d.month, d.day, start_h, start_m)
    for cl in custom_losses:
        if cl['Window_Start'] <= block_dt < cl['Window_End']:
            return cl['Loss_Pct']
    return default_loss


class SettlementEngine:
    def __init__(self,
                 start_date: date,
                 end_date: date,
                 variables: Dict,
                 shutdown_windows: List[Dict],
                 custom_losses: List[Dict],
                 raw_gen_blocks: List[Dict],
                 raw_cons1_blocks: List[Dict],
                 raw_cons2_blocks: List[Dict],
                 raw_iex1_blocks: List[Dict],
                 raw_iex2_blocks: List[Dict]):
        self.start_date = start_date
        self.end_date = end_date
        self.variables = variables
        self.shutdown_windows = shutdown_windows
        self.custom_losses = custom_losses
        self.gen_data = {(b['Block_Date'], b['Slot']): b['Active_KW']
                         for b in raw_gen_blocks}
        self.cons1_data = {(b['Block_Date'], b['Slot'])                           : b for b in raw_cons1_blocks}
        self.cons2_data = {(b['Block_Date'], b['Slot'])                           : b for b in raw_cons2_blocks}
        self.iex1_data = {(b['Block_Date'], b['Slot']): b['IEX_KW']
                          for b in raw_iex1_blocks}
        self.iex2_data = {(b['Block_Date'], b['Slot']): b['IEX_KW']
                          for b in raw_iex2_blocks}
        self.date_list = [
            start_date +
            timedelta(
                days=x) for x in range(
                (end_date -
                 start_date).days +
                1)]
        self.num_days = len(self.date_list)
        self.calculated_blocks = []
        self.results = []

    def run(self):
        shutdown_blocks = build_shutdown_blocks(self.shutdown_windows)
        valid_dates = set(self.date_list)
        shutdown_blocks = {(d, s) for (d, s) in shutdown_blocks if d in valid_dates}
        shutdown_count = len(shutdown_blocks)
        active_blocks = (self.num_days * 96) - shutdown_count
        override_cap = self.variables.get('Override_Capacity_MW')
        if override_cap is None:
            override_cap = 25.0
        cap_kw = override_cap * 1000.0
        
        total_raw_gen_kwh = 0.0
        total_gen_kwh = 0.0
        
        for d in self.date_list:
            for slot in range(1, 97):
                if (d, slot) not in shutdown_blocks:
                    raw_kw = self.gen_data.get((d, slot), 0.0)
                    total_raw_gen_kwh += raw_kw / 4.0
                    gen_capped = min(raw_kw, cap_kw)
                    total_gen_kwh += gen_capped / 4.0
        
        avg_gen_kw = total_raw_gen_kwh / (active_blocks / 4.0) if active_blocks > 0 else 0.0
        
        share1_kwh = total_gen_kwh * (self.variables['Share_Cons1'] / 100.0)
        share2_kwh = total_gen_kwh * (self.variables['Share_Cons2'] / 100.0)
        
        flat_kw_1 = (share1_kwh / active_blocks) * 4.0 if active_blocks > 0 else 0.0
        flat_kw_2 = (share2_kwh / active_blocks) * 4.0 if active_blocks > 0 else 0.0
        
        revised_gen_alloc_1 = share1_kwh
        revised_gen_alloc_2 = share2_kwh
        
        cap_cons1 = cap_kw * (self.variables.get('Cap_Share_Cons1', 50.0) / 100.0)
        cap_cons2 = cap_kw * (self.variables.get('Cap_Share_Cons2', 50.0) / 100.0)
        spilled_kw_1 = 0.0
        spilled_kw_2 = 0.0
        if cap_cons1 and flat_kw_1 > cap_cons1:
            spilled_kw_1 = flat_kw_1 - cap_cons1
            flat_kw_1 = cap_cons1
        if cap_cons2 and flat_kw_2 > cap_cons2:
            spilled_kw_2 = flat_kw_2 - cap_cons2
            flat_kw_2 = cap_cons2
                                                                   
        raw_old_bank = self.variables.get('Old_Bank_KWH', self.variables.get('Banked_Remaining_KWH', 0.0))
        bank_loss_pct = self.variables.get('Bank_Loss_Pct', 0.0)
        net_old_bank = raw_old_bank * (1 - (bank_loss_pct / 100.0))
        bank_per_cons = net_old_bank / 2.0
                                                                           
                                                                                     
        total_peak_blocks = self.num_days * 32
        total_non_peak_blocks = (self.num_days * 96) - total_peak_blocks
        
        bank_inj_off_peak = (bank_per_cons / total_non_peak_blocks) * 4.0 if total_non_peak_blocks > 0 else 0.0
        
                                                                                    
        total_bank_kwh = bank_per_cons
        res1, res2 = {}, {}
        for d in self.date_list:
            for slot in range(1, 97):
                is_peak_block = (25 <= slot <= 40) or (73 <= slot <= 88)
                is_shutdown = (d, slot) in shutdown_blocks
                raw_gen_kw = self.gen_data.get((d, slot), 0.0)
                gen_capped = min(raw_gen_kw, cap_kw) if not is_shutdown else 0.0
                excess_gen_kw = max(0.0, raw_gen_kw - cap_kw) if not is_shutdown else 0.0
                
                gen_share1 = gen_capped * (self.variables['Share_Cons1'] / 100.0) if not is_shutdown else 0.0
                gen_share2 = gen_capped * (self.variables['Share_Cons2'] / 100.0) if not is_shutdown else 0.0
                
                allocated_kw = gen_share1 + gen_share2
                unallocated_capped_kw = max(0.0, gen_capped - allocated_kw)
                
                generator_bank_kw = excess_gen_kw + unallocated_capped_kw

                self._calc_block(
                    d,
                    slot,
                    is_peak_block,
                    is_shutdown,
                    flat_kw_1,
                    self.variables['Share_Cons1'],
                    bank_inj_off_peak,
                    self.cons1_data,
                    self.iex1_data,
                    self.variables['Con1_Label'],
                    res1,
                    cap_kw,
                    0.0)
                self._calc_block(
                    d,
                    slot,
                    is_peak_block,
                    is_shutdown,
                    flat_kw_2,
                    self.variables['Share_Cons2'],
                    bank_inj_off_peak,
                    self.cons2_data,
                    self.iex2_data,
                    self.variables['Con2_Label'],
                    res2,
                    cap_kw,
                    generator_bank_kw)
        s1 = self._aggregate(res1, flat_kw_1, bank_per_cons, revised_gen_alloc_1, self.custom_losses, share1_kwh, self.variables['Con1_Label'])
        s2 = self._aggregate(res2, flat_kw_2, bank_per_cons, revised_gen_alloc_2, self.custom_losses, share2_kwh, self.variables['Con2_Label'])
        total_accountable = s1['Energy_Accountable_To_Gen'] +\
            s2['Energy_Accountable_To_Gen']
        total_scheduled_gen = s1['Prior_Sch_At_Entry'] + s2['Prior_Sch_At_Entry']
        total_gen_kwh_report = total_gen_kwh
        self._prepare_result(
            self.variables['Con1_Label'],
            s1,
            total_gen_kwh_report,
            active_blocks,
            flat_kw_1,
            avg_gen_kw,
            total_accountable,
            spilled_kw_1)
        self._prepare_result(
            self.variables['Con2_Label'],
            s2,
            total_gen_kwh_report,
            active_blocks,
            flat_kw_2,
            avg_gen_kw,
            total_accountable,
            spilled_kw_2)
        return {
            "calculated_blocks": self.calculated_blocks,
            "results": self.results
        }

    def _calc_block(
            self,
            d,
            slot,
            is_peak,
            is_shutdown,
            flat_kw,
            share_pct,
            bank_inj_off_peak,
            cons_data,
            iex_data,
            label,
            res_dict,
            cap_kw,
            generator_bank_kw=0.0):
        c_raw = cons_data.get(
            (d, slot), {
                'Apparent_KVA': 0, 'Active_KW_Raw': 0})
        kva = c_raw['Apparent_KVA']
        act_i_raw = c_raw['Active_KW_Raw']
        pf = abs(round(act_i_raw / kva, 3)) if kva > 0 else 1.0
        iex_power = iex_data.get((d, slot), 0.0)
        
                                                                                            
                                                                   
                                                                   
        actual_kw = max(0.0, (kva - iex_power) * pf)
        demand_kva = (actual_kw / pf) if pf > 0 else 0.0
        
        raw_gen_kw = self.gen_data.get((d, slot), 0.0)
        gen_capped = min(raw_gen_kw, cap_kw) if not is_shutdown else 0.0
        gen_share = gen_capped * (share_pct / 100.0) if not is_shutdown else 0.0
        
        bank_inj = bank_inj_off_peak if not is_peak else 0.0
        
        block_loss_pct = get_block_loss(
            d, slot, self.custom_losses, self.variables.get('Default_Loss', 0.0))
        loss_mult = 1 - (block_loss_pct / 100.0)
        
        aft_main = (gen_share + bank_inj) * loss_mult
        bank_in_main = max(0.0, aft_main - actual_kw)
        
        bank_in_main += (generator_bank_kw * loss_mult)
        
        net_gen_main = aft_main - max(0.0, aft_main - actual_kw)
        
        discom_kva_block = max(0.0, (actual_kw - aft_main) / pf) if pf > 0 else 0.0
        
        res_dict[(d, slot)] = {
            'bank_in_main': bank_in_main,
            'net_gen_main': net_gen_main,
            'gen_share_kw': gen_share,
            'bank_inj_kw': bank_inj,
            'loss_pct': block_loss_pct,
            'actual_kw': actual_kw,
            'aft_main': aft_main,
            'pf': pf,
            'consumer_kva': kva,
            'discom_kva_block': discom_kva_block
        }
        self.calculated_blocks.append({
            'Consumer_Label': label,
            'Block_Date': d,
            'Slot': slot,
            'Is_Peak': is_peak,
            'Is_Shutdown': is_shutdown,
            'Gen_KW_Raw': raw_gen_kw,
            'Gen_KW_Capped': gen_capped,
            'Consumer_KVA': kva,
            'Consumer_PF': pf,
            'IEX_KW': iex_power,
            'Actual_KW': actual_kw,
            'Gen_Share_KW': gen_share,
            'Loss_Pct': block_loss_pct,
            'Aft_KW_Main': aft_main,
            'Bank_In_Main': bank_in_main,
            'Net_Gen_Main': net_gen_main,
            'Aft_KW_ISO': aft_main,
            'Bank_In_ISO': bank_in_main,
            'Net_Gen_ISO': net_gen_main,
            'Demand_KVA': demand_kva,
            'Discom_KVA_Block': discom_kva_block
        })

    def _aggregate(self, res, flat_kw, bank_per_cons, revised_gen_alloc, custom_losses, share_kwh, label):
        tot_bank_in_exit = sum(r['bank_in_main'] for r in res.values()) / 4.0
        tot_net_gen_exit = sum(r['net_gen_main'] for r in res.values()) / 4.0
        prior_entry = share_kwh
        total_bank_kwh = bank_per_cons
        
                                       
        if "TPT2005" in label:
            revised_entry = revised_gen_alloc                         
        else:
            revised_entry = revised_gen_alloc + total_bank_kwh                         
        
        prior_exit = sum((r['gen_share_kw'] + r['bank_inj_kw']) * (1 - r['loss_pct'] / 100.0) for r in res.values()) / 4.0
        
        if "TPT2005" in label:
            gen_prior_exit_report = sum((r['gen_share_kw']) * (1 - r['loss_pct'] / 100.0) for r in res.values()) / 4.0
        else:
            gen_prior_exit_report = prior_exit
        
                                                   
        banked_entry = sum(r['bank_in_main'] * (1 + r['loss_pct']/100.0) for r in res.values()) / 4.0
        
                                                                 
                                                          
        energy_accountable_entry = revised_entry - banked_entry
        
        max_actual_kw = 0.0
        max_date = None
        max_slot_str = ""
        
        max_demand_kva = 0.0
        max_demand_date = None
        max_demand_slot_str = ""
        max_demand_pf = 1.0
        
        total_raw_kw = 0.0
        total_raw_kvah = 0.0
        discom_kvah = 0.0
        
        for (d, slot), r in res.items():
            if r['actual_kw'] > max_actual_kw:
                max_actual_kw = r['actual_kw']
                max_date = d
                start_h = (slot - 1) * 15 // 60
                start_m = (slot - 1) * 15 % 60
                end_h = slot * 15 // 60
                end_m = slot * 15 % 60
                max_slot_str = f"{start_h:02d}:{start_m:02d} to {end_h:02d}:{end_m:02d}"
                
            total_raw_kw += r['actual_kw']
            if r['pf'] > 0:
                total_raw_kvah += (r['actual_kw'] / r['pf'])
                                                                 
                dkva = max(0.0, (r['actual_kw'] - r['aft_main']) / r['pf'])
                discom_kvah += dkva
                
                                                                            
                if dkva > max_demand_kva:
                    max_demand_kva = dkva
                    max_demand_date = d
                    max_demand_pf = r['pf']
                    start_h = (slot - 1) * 15 // 60
                    start_m = (slot - 1) * 15 % 60
                    end_h = slot * 15 // 60
                    end_m = slot * 15 % 60
                    max_demand_slot_str = f"{start_h:02d}:{start_m:02d} to {end_h:02d}:{end_m:02d}"
        
        discom_kvah = discom_kvah / 4.0
        
                                                                                            
                                                            
        avg_pf = max_demand_pf if max_demand_kva > 0 else (total_raw_kw / total_raw_kvah if total_raw_kvah > 0 else 1.0)
        avg_pf = round(avg_pf, 3)
        
                                                                                                
        flat_exit_kw = flat_kw * (1 - custom_losses[0]['Loss_Pct'] / 100.0) if custom_losses else flat_kw
        accountable_discom_kw = max_actual_kw - flat_kw
        
                                                                                 
                                               
        
                                                            
                                                                                                  
                                                                          
        total_consumer_actual_kwh = total_raw_kw / 4.0
        
                                                              
        if "TPT2005" in label:
            cons_actual_from_gen = gen_prior_exit_report - tot_bank_in_exit
        else:
            cons_actual_from_gen = prior_exit - tot_bank_in_exit

        return {
            'Prior_Sch_At_Entry': prior_entry,
            'Sch_From_Bank': total_bank_kwh,
            'Revised_Gen_Allocated': revised_entry,
            'Energy_Accountable_To_Gen': energy_accountable_entry,
            'Total_Accountable_To_Gen': energy_accountable_entry,
            'Bank_KWH': banked_entry,                                       
            'Gen_Prior_Sch_At_Exit': gen_prior_exit_report,
            'Gen_Realloc_Sch_At_Exit': gen_prior_exit_report,
            'Gen_Deviation': 0.0,
            'Cons_Actual_From_Gen': cons_actual_from_gen,
            'Discom_KVAH': discom_kvah,
            'Max_Demand_KVA': max_demand_kva,
            'Max_Demand_Date': max_demand_date,
            'Max_Demand_Slot_Str': max_demand_slot_str,
            'PF_Value': avg_pf,
            'Average_PF': avg_pf,
            'Max_Actual_KW': max_actual_kw,
            'Accountable_To_Discom_KW': accountable_discom_kw,
            'Total_Consumer_Actual_KWH': total_consumer_actual_kwh
        }

    def _prepare_result(
            self,
            label,
            s,
            total_gen_kwh,
            active_blocks,
            flat_kw,
            avg_gen_kw,
            total_accountable,
            spilled_kw):
                                                               
                                                                  
        bank_report = s['Bank_KWH']
        self.results.append({
            'Consumer_Label': label,
            'Total_Gen_KWH': total_gen_kwh,
            'Active_Blocks': active_blocks,
            'Flat_KW_Allocated': flat_kw,
            'Avg_Gen_KW': avg_gen_kw,
            'Prior_Sch_At_Entry_KWH': s['Prior_Sch_At_Entry'],
            'Sch_From_Bank_KWH': s['Sch_From_Bank'],
            'Revised_Gen_Allocated_KWH': s['Revised_Gen_Allocated'],
            'Energy_Accountable_KWH': s['Energy_Accountable_To_Gen'],
            'Total_Accountable_KWH': total_accountable,
            'Bank_KWH': bank_report,
            'Gen_Prior_Sch_At_Exit_KWH': s['Gen_Prior_Sch_At_Exit'],
            'Cons_Actual_From_Gen_KWH': s['Cons_Actual_From_Gen'],
            'Discom_KVAH': s['Discom_KVAH'],
            'Max_Demand_KVA': s['Max_Demand_KVA'],
            'Max_Demand_Date': s['Max_Demand_Date'],
            'Max_Demand_Slot_Str': s['Max_Demand_Slot_Str'],
            'PF_Value': s['PF_Value'],
            'Average_PF': s['Average_PF'],
            'Schedule_At_Entry_KW': flat_kw,
            'Actual_Gen_KW': avg_gen_kw,
            'Max_Actual_KW': s['Max_Actual_KW'],
            'Revised_Sch_At_Exit_KW': flat_kw * (1 - self.custom_losses[0]['Loss_Pct'] / 100.0) if self.custom_losses else flat_kw,
            'Cons_From_Gen_KW': flat_kw * (1 - self.custom_losses[0]['Loss_Pct'] / 100.0) if self.custom_losses else flat_kw,
            'Accountable_To_Discom_KW': s['Max_Actual_KW'] - (flat_kw * (1 - self.custom_losses[0]['Loss_Pct'] / 100.0) if self.custom_losses else flat_kw),
            'Total_Consumer_Actual_KWH': s['Total_Consumer_Actual_KWH']
        })