import xml.etree.ElementTree as ET
from datetime import datetime
from typing import List, Dict
SLOTS = 96


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


def parse_gen_cdf(path: str, start_date, end_date,
                  ct_ratio: int = 4) -> List[Dict]:
    blocks = []
    context = ET.iterparse(path, events=('end',))
    for event, elem in context:
        if elem.tag == 'DAYPROFILE':
            try:
                d = str_to_date(elem.attrib.get('DATE', ''))
                if start_date <= d <= end_date:
                    for ip in elem.findall('IP'):
                        slot = int(ip.attrib.get('INTERVAL', '0'))
                        if 1 <= slot <= SLOTS:
                            for param in ip.findall('PARAMETER'):
                                if param.attrib.get(
                                        'PARAMCODE') == 'P7-1-5-1-0':
                                    raw_val = float(
                                        param.attrib.get('VALUE', 0))
                                    val = raw_val * ct_ratio
                                    blocks.append({
                                        "Block_Date": d,
                                        "Slot": slot,
                                        "Active_KW": val
                                    })
                                    break
            except Exception:
                pass
            elem.clear()
    return blocks


def parse_cons_cdf(
        path: str,
        consumer_label: str,
        start_date,
        end_date,
        ct_ratio: int = 4) -> List[Dict]:
    tree = ET.parse(path)
    root = tree.getroot()
    blocks = []
    for dp in root.findall('UTILITYTYPE/D4/DAYPROFILE'):
        try:
            d = str_to_date(dp.attrib.get('DATE', ''))
        except BaseException:
            continue
        if d < start_date or d > end_date:
            continue
        for ip in dp.findall('IP'):
            slot = int(ip.attrib.get('INTERVAL', '0'))
            if 1 <= slot <= SLOTS:
                app_i = 0.0
                act_i = 0.0
                for param in ip.findall('PARAMETER'):
                    pc = param.attrib.get('PARAMCODE')
                    if pc == 'P7-3-5-0-0':
                        app_i = float(param.attrib.get('VALUE', 0))
                    elif pc == 'P7-1-5-1-0':
                        act_i = float(param.attrib.get('VALUE', 0))
                kva = app_i * ct_ratio
                act = act_i * ct_ratio
                blocks.append({
                    "Consumer_Label": consumer_label,
                    "Block_Date": d,
                    "Slot": slot,
                    "Apparent_KVA": kva,
                    "Active_KW_Raw": act
                })
    return blocks
