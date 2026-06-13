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
        shutdown_count = len(shutdown_blocks)
        active_blocks = (self.num_days * 96) - shutdown_count
        cap_gen = self.variables.get('Cap_Gen_KW', float('inf'))
        effective_gen_kws = []
        for d in self.date_list:
            for slot in range(1, 97):
                raw_kw = self.gen_data.get((d, slot), 0.0)
                if (d, slot) in shutdown_blocks:
                    effective_gen_kws.append(0.0)
                else:
                    effective_gen_kws.append(min(raw_kw, cap_gen))
        total_gen_kwh = sum(effective_gen_kws) / 4.0
        avg_gen_kw = total_gen_kwh /\
            (active_blocks / 4.0) if active_blocks > 0 else 0.0
        share1_kwh = total_gen_kwh * (self.variables['Share_Cons1'] / 100.0)
        share2_kwh = total_gen_kwh * (self.variables['Share_Cons2'] / 100.0)
        flat_kw_1 = (share1_kwh / active_blocks) *\
            4.0 if active_blocks > 0 else 0.0
        flat_kw_2 = (share2_kwh / active_blocks) *\
            4.0 if active_blocks > 0 else 0.0
        cap_cons1 = self.variables.get('Cap_Cons1_KW')
        cap_cons2 = self.variables.get('Cap_Cons2_KW')
        spilled_kw_1 = 0.0
        spilled_kw_2 = 0.0
        if cap_cons1 and flat_kw_1 > cap_cons1:
            spilled_kw_1 = flat_kw_1 - cap_cons1
            flat_kw_1 = cap_cons1
        if cap_cons2 and flat_kw_2 > cap_cons2:
            spilled_kw_2 = flat_kw_2 - cap_cons2
            flat_kw_2 = cap_cons2
        net_old_bank = self.variables['Old_Bank_KWH'] *\
            (1 - (self.variables['Bank_Loss_Pct'] / 100.0))
        bank_per_cons = net_old_bank / 2.0
        bank_inj_flat = (bank_per_cons / active_blocks) *\
            4.0 if active_blocks > 0 else 0.0
        total_bank_blocks = self.num_days * 64
        bank_inj_iso = (bank_per_cons / total_bank_blocks) *\
            4.0 if total_bank_blocks > 0 else 0.0
        res1, res2 = {}, {}
        for d in self.date_list:
            for slot in range(1, 97):
                is_peak_block = (25 <= slot <= 40) or (73 <= slot <= 88)
                is_shutdown = (d, slot) in shutdown_blocks
                self._calc_block(
                    d,
                    slot,
                    is_peak_block,
                    is_shutdown,
                    flat_kw_1,
                    bank_inj_flat,
                    bank_inj_iso,
                    self.cons1_data,
                    self.iex1_data,
                    self.variables['Con1_Label'],
                    res1)
                self._calc_block(
                    d,
                    slot,
                    is_peak_block,
                    is_shutdown,
                    flat_kw_2,
                    bank_inj_flat,
                    bank_inj_iso,
                    self.cons2_data,
                    self.iex2_data,
                    self.variables['Con2_Label'],
                    res2)
        s1 = self._aggregate(res1, flat_kw_1, active_blocks, bank_per_cons)
        s2 = self._aggregate(res2, flat_kw_2, active_blocks, bank_per_cons)
        total_accountable = s1['Energy_Accountable_To_Gen'] +\
            s2['Energy_Accountable_To_Gen']
        self._prepare_result(
            self.variables['Con1_Label'],
            s1,
            total_gen_kwh,
            active_blocks,
            flat_kw_1,
            avg_gen_kw,
            total_accountable,
            spilled_kw_1)
        self._prepare_result(
            self.variables['Con2_Label'],
            s2,
            total_gen_kwh,
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
            bank_inj_flat,
            bank_inj_iso,
            cons_data,
            iex_data,
            label,
            res_dict):
        c_raw = cons_data.get(
            (d, slot), {
                'Apparent_KVA': 0, 'Active_KW_Raw': 0})
        kva = c_raw['Apparent_KVA']
        act_i_raw = c_raw['Active_KW_Raw']
        ct_ratio = self.variables.get('CT_Ratio', 1.0)
        app_i = kva / ct_ratio if ct_ratio else 0
        pf = round(act_i_raw / app_i, 3) if app_i > 0 else 1.0
        iex = iex_data.get((d, slot), 0.0)
        actual_kw = max(0.0, kva - iex) * pf
        demand_kva = (actual_kw / pf) if pf > 0 else 0.0
        gen_share = flat_kw if not is_shutdown else 0.0
        block_loss_pct = get_block_loss(
            d, slot, self.custom_losses, self.variables.get('Default_Loss', 0.0))
        loss_mult = 1 - (block_loss_pct / 100.0)
        aft_main = (gen_share + bank_inj_flat) * loss_mult
        bank_in_main = max(0.0, aft_main - actual_kw)
        net_gen_main = aft_main - bank_in_main
        bank_share_iso = 0.0 if is_peak else bank_inj_iso
        aft_iso = (gen_share + bank_share_iso) * loss_mult
        bank_in_iso = max(0.0, aft_iso - actual_kw)
        net_gen_iso = aft_iso - bank_in_iso
        discom_kva_block = max(
            0.0, (actual_kw - net_gen_iso) / pf) if pf > 0 else 0.0
        raw_gen_kw = self.gen_data.get((d, slot), 0.0)
        gen_capped = min(
            raw_gen_kw,
            self.variables.get('Cap_Gen_KW', float('inf'))) if not is_shutdown else 0.0
        res_dict[(d, slot)] = {
            'bank_in_iso': bank_in_iso,
            'net_gen_main': net_gen_main,
            'gen_share_kw': gen_share,
            'loss_pct': block_loss_pct,
            'actual_kw': actual_kw,
            'net_gen_iso': net_gen_iso,
            'pf': pf
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
            'IEX_KW': iex,
            'Actual_KW': actual_kw,
            'Gen_Share_KW': gen_share,
            'Loss_Pct': block_loss_pct,
            'Aft_KW_Main': aft_main,
            'Bank_In_Main': bank_in_main,
            'Net_Gen_Main': net_gen_main,
            'Aft_KW_ISO': aft_iso,
            'Bank_In_ISO': bank_in_iso,
            'Net_Gen_ISO': net_gen_iso,
            'Demand_KVA': demand_kva,
            'Discom_KVA_Block': discom_kva_block
        })

    def _aggregate(self, res, flat_kw, active_blocks, bank_per_cons):
        tot_bank_in = sum(r['bank_in_iso'] for r in res.values()) / 4.0
        tot_net_gen = sum(r['net_gen_main'] for r in res.values()) / 4.0
        prior_entry = (flat_kw * active_blocks) / 4.0
        revised_entry = prior_entry + bank_per_cons
        prior_exit = sum((r['gen_share_kw'] + (bank_per_cons / active_blocks if r['gen_share_kw']
                         > 0 else 0)) * (1 - r['loss_pct'] / 100.0) for r in res.values()) / 4.0
        banked_entry = sum(r['bank_in_iso'] * (1 + r['loss_pct'] / 100.0)
                           for r in res.values()) / 4.0
        rmd_after_oa = 0.0
        pf_at_rmd = 1.0
        max_date = None
        max_slot_str = ""
        discom_kvah = 0.0
        discom_kw = 0.0
        max_actual_kw = 0.0
        for (d, slot), r in res.items():
            if r['actual_kw'] > max_actual_kw:
                max_actual_kw = r['actual_kw']
            dkva = 0.0
            if r['pf'] > 0:
                dkva = max(0.0, (r['actual_kw'] - r['net_gen_iso']) / r['pf'])
                discom_kvah += dkva
            discom_kw += (r['actual_kw'] - r['net_gen_iso'])
            if dkva > rmd_after_oa:
                rmd_after_oa = dkva
                pf_at_rmd = r['pf']
                max_date = d
                start_h = (slot - 1) * 15 // 60
                start_m = (slot - 1) * 15 % 60
                end_h = slot * 15 // 60
                end_m = slot * 15 % 60
                max_slot_str = f"{start_h:02d}:{start_m:02d} to {end_h:02d}:{end_m:02d}"
        discom_kvah /= 4.0
        discom_kw /= 4.0
        avg_pf = discom_kw / discom_kvah if discom_kvah > 0 else 1.0
        total_actual = sum(r['actual_kw'] for r in res.values()) / 4.0
        return {
            'Prior_Sch_At_Entry': prior_entry,
            'Sch_From_Bank': bank_per_cons,
            'Revised_Gen_Allocated': revised_entry,
            'Energy_Accountable_To_Gen': revised_entry - banked_entry,
            'Bank_KWH': tot_bank_in,
            'Gen_Prior_Sch_At_Exit': prior_exit,
            'Cons_Actual_Cons_From_Gen': tot_net_gen,
            'Discom_KVAH': discom_kvah,
            'Max_Demand_KVA': rmd_after_oa,
            'Max_Date': max_date,
            'Max_Slot_Str': max_slot_str,
            'Average_PF': avg_pf,
            'PF_Value': pf_at_rmd,
            'Max_Actual_KW': max_actual_kw,
            'Total_Consumer_Actual_KWH': total_actual
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
        bank_report = s['Bank_KWH'] + (spilled_kw * (96 * self.num_days) / 4.0)
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
            'Cons_Actual_From_Gen_KWH': s['Cons_Actual_Cons_From_Gen'],
            'Discom_KVAH': s['Discom_KVAH'],
            'Max_Demand_KVA': s['Max_Demand_KVA'],
            'Max_Demand_Date': s['Max_Date'],
            'Max_Demand_Slot_Str': s['Max_Slot_Str'],
            'PF_Value': s['PF_Value'],
            'Average_PF': s['Average_PF'],
            'Schedule_At_Entry_KW': flat_kw,
            'Actual_Gen_KW': avg_gen_kw,
            'Revised_Sch_At_Exit_KW': flat_kw * (1 - self.variables.get('Default_Loss', 0.0) / 100.0),
            'Cons_From_Gen_KW': flat_kw * (1 - self.variables.get('Default_Loss', 0.0) / 100.0),
            'Accountable_To_Discom_KW': s['Max_Actual_KW'] - (flat_kw * (1 - self.variables.get('Default_Loss', 0.0) / 100.0)),
            'Total_Consumer_Actual_KWH': s['Total_Consumer_Actual_KWH']
        })
