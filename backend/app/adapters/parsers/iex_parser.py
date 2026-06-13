import openpyxl
from datetime import datetime
from typing import List, Dict


def str_to_date(s: str):
    s = s.strip().lower()
    month_map = {
        '-jan-': '-01-', '-feb-': '-02-', '-mar-': '-03-', '-apr-': '-04-',
        '-may-': '-05-', '-jun-': '-06-', '-jul-': '-07-', '-aug-': '-08-',
        '-sep-': '-09-', '-oct-': '-10-', '-nov-': '-11-', '-dec-': '-12-',
    }
    for name, num in month_map.items():
        s = s.replace(name, num)
    return datetime.strptime(s, "%d-%m-%Y").date()


def parse_iex_excel(
        path: str,
        consumer_label: str,
        start_date,
        end_date) -> List[Dict]:
    wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
    ws = wb.active
    blocks = []
    for row in ws.iter_rows(min_row=4, max_col=98):
        cell_val = row[1].value
        if not cell_val:
            break
        if isinstance(cell_val, datetime):
            d = cell_val.date()
        elif isinstance(cell_val, str):
            try:
                d = str_to_date(cell_val)
            except BaseException:
                continue
        else:
            continue
        if d < start_date or d > end_date:
            continue
        for slot in range(1, 97):
            try:
                v = row[slot + 1].value
                iex_val = float(v) if v is not None else 0.0
            except BaseException:
                iex_val = 0.0
            blocks.append({
                "Consumer_Label": consumer_label,
                "Block_Date": d,
                "Slot": slot,
                "IEX_KW": iex_val
            })
    wb.close()
    return blocks
