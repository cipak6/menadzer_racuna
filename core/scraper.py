"""
Scrapes invoice data from purs.gov.rs given a verification URL.
Parsing logic adapted from https://github.com/ivang5/Moji-Racuni
"""

import requests
from bs4 import BeautifulSoup

try:
    from srtools import cyrillic_to_latin
except ImportError:
    def cyrillic_to_latin(text):
        table = {
            'А':'A','Б':'B','В':'V','Г':'G','Д':'D','Ђ':'Dj','Е':'E','Ж':'Z','З':'Z','И':'I',
            'Ј':'J','К':'K','Л':'L','Љ':'Lj','М':'M','Н':'N','Њ':'Nj','О':'O','П':'P','Р':'R',
            'С':'S','Т':'T','Ћ':'C','У':'U','Ф':'F','Х':'H','Ц':'C','Ч':'C','Џ':'Dz','Ш':'S',
            'а':'a','б':'b','в':'v','г':'g','д':'d','ђ':'dj','е':'e','ж':'z','з':'z','и':'i',
            'ј':'j','к':'k','л':'l','љ':'lj','м':'m','н':'n','њ':'nj','о':'o','п':'p','р':'r',
            'с':'s','т':'t','ћ':'c','у':'u','ф':'f','х':'h','ц':'c','ч':'c','џ':'dz','ш':'s',
        }
        return ''.join(table.get(c, c) for c in text)


def _remove_line_breaks(receipt):
    new_receipt = receipt
    finding = True
    start = 0
    while finding:
        index = new_receipt[start:].find('\r\n')
        if index != -1:
            if new_receipt[index + start + 2:index + start + 5] == "   ":
                start = index + start + 2
            else:
                try:
                    int(new_receipt[index + start - 1])
                    start = index + start + 2
                except ValueError:
                    new_receipt = new_receipt[:index + start] + new_receipt[index + start + 2:]
        else:
            finding = False
    return new_receipt


def _remove_item_code(name):
    parts_space = name.split(' ')
    parts_dash = name.split('-')
    parts_comma = name.split(',')
    if len(name.rstrip()) == len(parts_space[0]):
        return name
    try:
        int(parts_space[0])
        new_name = name.split(' ', 1)[1]
        if parts_space[1] == '-':
            new_name = new_name.split(' ', 1)[1]
        return new_name
    except (ValueError, IndexError):
        try:
            int(parts_space[0][1:])
            if parts_space[0][0] != '(':
                return name.split(' ', 1)[1]
        except (ValueError, IndexError):
            try:
                int(parts_dash[0])
                return name.split('-', 1)[1]
            except (ValueError, IndexError):
                try:
                    int(parts_comma[0])
                    return name.split(',', 1)[1]
                except (ValueError, IndexError):
                    pass
    try:
        int(parts_space[-1])
        if len(parts_space[-1]) > 4:
            new_name = name.rsplit(' ', 1)[0]
            if parts_space[-2] == '-':
                new_name = new_name.rsplit(' ', 1)[0]
            return new_name
    except (ValueError, IndexError):
        pass
    return name


def _get_vat(item_part):
    if '(e)' in item_part:
        return {'new_part': item_part.replace('(e)', ''), 'vat': '10%'}
    elif '(a)' in item_part or '(g)' in item_part:
        return {'new_part': item_part.replace('(a)', '').replace('(g)', ''), 'vat': '0%'}
    else:
        return {'new_part': item_part.replace('(đ)', '').replace('(dj)', ''), 'vat': '20%'}


def _get_measure_prefix(item_part):
    end = item_part.rstrip()[-6:]
    if '[' in end and ']' in end:
        return '['
    elif '(' in end and ')' in end:
        return '('
    elif '/' in end:
        return '/'
    return '{'


def _get_measure_type(item_part, prefix):
    checks = [
        (['kom', ' kom'], 'kom'),
        (['kg', ' kg'], 'kg'),
        (['l', ' l', 'lit', ' lit'], 'l'),
        (['kut', ' kut'], 'kut'),
        (['pce', ' pce'], 'pce'),
        (['m', ' m'], 'm'),
    ]
    for suffixes, unit in checks:
        for s in suffixes:
            if (prefix + s) in item_part:
                return unit
    return 'kom'


def _get_name(item_part, measure_type, prefix):
    item = item_part.split(f' {prefix}{measure_type}')[0]
    if item == item_part:
        item = item_part.split(f' {prefix} {measure_type}')[0]
    if item == item_part:
        item = item_part.split(f' {measure_type}')[0]
    if item and item[-1] == '(':
        item = item[:-1]
    item = item.strip()
    if item.endswith(prefix + measure_type):
        item = item.replace(prefix + measure_type, '')
    return _remove_item_code(item)


def _remove_blacklisted(s):
    return ''.join(c for c in s if c not in {'\ufffd', 'ø'}).replace('å', 'a')


def _parse_items(pre_text):
    try:
        body = pre_text.split('========================================')[1]
        items_raw = body.split('----------------------------------------')[0].split('Укупно')[1]
    except IndexError:
        return []

    lines = _remove_line_breaks(items_raw).split('\r\n')
    items = []
    expect_name = True

    current = {}
    for i, line in enumerate(lines):
        if i == len(lines) - 1:
            continue
        if expect_name:
            lower = cyrillic_to_latin(line.lower())
            vat_result = _get_vat(lower)
            cleaned = _remove_blacklisted(vat_result['new_part'])
            prefix = _get_measure_prefix(cleaned)
            measure = _get_measure_type(cleaned, prefix)
            name = _get_name(cleaned, measure, prefix)
            current = {'name': name.title(), 'unit': measure.upper(), 'vat': vat_result['vat']}
            expect_name = False
        else:
            pos = 0
            success = False
            while not success:
                try:
                    parts = ' '.join(line.replace('.', '').split()).split(' ')
                    price = float(parts[pos].replace(',', '.'))
                    qty = float(parts[pos + 1].replace(',', '.'))
                    current['price'] = price
                    current['quantity'] = qty
                    current['total'] = round(price * qty, 2)
                    items.append(current)
                    success = True
                    expect_name = True
                except (ValueError, IndexError):
                    pos += 1
                    if pos > 5:
                        expect_name = True
                        break

    # Normalize units
    for item in items:
        if item.get('unit') == 'PCE':
            item['unit'] = 'KOM'
    return items


def scrape_invoice(url: str) -> dict | None:
    """
    Given a purs.gov.rs verification URL, returns a dict with:
      - company_tin, company_name
      - store_name, store_address, store_place, store_municipality
      - date, total_price, total_vat
      - items: list of {name, unit, vat, price, quantity, total}
      - url
    Returns None on failure.
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'sr-RS,sr;q=0.9,en;q=0.8',
    }
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        raise ConnectionError(f"Failed to fetch URL: {e}")

    soup = BeautifulSoup(resp.text, 'lxml')

    pre = soup.find('pre')
    if not pre:
        raise ValueError("No receipt data found on page. Check the URL.")
    pre_text = pre.text

    panels = soup.find_all('div', class_='panel-info')
    if len(panels) < 2:
        raise ValueError("Unexpected page structure.")

    g1 = panels[0].select('.panel-body .form-group div')
    g2 = panels[1].select('.panel-body .form-group div')

    # Company TIN and name from panel 0
    company_tin = g1[0].text.strip() if len(g1) > 0 else ''
    lines = pre_text.splitlines()
    company_name = cyrillic_to_latin(lines[2].strip().title()) if len(lines) > 2 else ''

    # Store info from panel 0
    store_name = cyrillic_to_latin(g1[1].text.strip().title()) if len(g1) > 1 else ''
    store_address = cyrillic_to_latin(g1[2].text.strip().title()) if len(g1) > 2 else ''
    store_place = cyrillic_to_latin(g1[3].text.strip().title()) if len(g1) > 3 else ''
    store_municipality = cyrillic_to_latin(g1[4].text.strip().title()) if len(g1) > 4 else ''

    # PFR number from panel 1
    tc = g2[1].text.strip() if len(g2) > 1 else ''
    total_c = g2[2].text.strip() if len(g2) > 2 else ''
    payment = g2[3].text.strip() if len(g2) > 3 else ''
    pfr_number = f"{tc}/{total_c}{payment}"

    # Date and total from panel 1
    date_raw = g2[6].text.strip() if len(g2) > 6 else ''
    total_price = 0.0
    try:
        total_price = float(g2[0].text.strip().replace('.', '').replace(',', '.'))
    except (ValueError, IndexError):
        pass

    # Total VAT from pre text
    total_vat = 0.0
    try:
        vat_str = pre_text.split('Укупан износ пореза:')[1].split()[0].strip()
        total_vat = float(vat_str.replace('.', '').replace(',', '.'))
    except (IndexError, ValueError):
        pass

    # Format date
    formatted_date = date_raw
    try:
        parts = date_raw.split(' ')
        d_parts = parts[0].split('.')
        formatted_date = f"{d_parts[2].strip()}-{d_parts[1]}-{d_parts[0]}"
    except Exception:
        pass

    items = _parse_items(pre_text)

    return {
        'url': url,
        'company_tin': company_tin,
        'company_name': company_name,
        'store_name': store_name,
        'store_address': store_address,
        'store_place': store_place,
        'store_municipality': store_municipality,
        'date': formatted_date,
        'total_price': total_price,
        'total_vat': total_vat,
        'items': items,
        'pfr_number': pfr_number,
        'pre_text': pre_text,
    }
