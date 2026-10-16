import xml.etree.ElementTree as ET


def _local(tag):
    if not tag:
        return ''
    return tag.split('}')[-1]


def _first(parent, name):
    if parent is None:
        return None
    for el in parent.iter():
        if _local(el.tag) == name:
            return el
    return None


def _person_name(fio_el):
    if fio_el is None:
        return ''
    parts = [
        fio_el.attrib.get('Фамилия', ''),
        fio_el.attrib.get('Имя', ''),
        fio_el.attrib.get('Отчество', ''),
    ]
    return ' '.join(p for p in parts if p).strip()


def _party_name(party_el):
    if party_el is None:
        return ''
    short = party_el.attrib.get('СокрНаим')
    if short:
        return short
    org = _first(party_el, 'СвЮЛУч')
    if org is not None and org.attrib.get('НаимОрг'):
        return org.attrib.get('НаимОрг')
    return _person_name(_first(party_el, 'ФИО'))


def parse_upd(path):
    """
    Читает электронный УПД (ON_NSCHFDOPPR) и возвращает шапку и коды КИЗ.
    КИЗ в документе короткий: 01 + GTIN + 21 + серийный номер.
    """
    tree = ET.parse(path)
    root = tree.getroot()

    invoice = _first(root, 'СвСчФакт')
    number = invoice.attrib.get('НомерДок', '') if invoice is not None else ''
    date = invoice.attrib.get('ДатаДок', '') if invoice is not None else ''

    seller = ''
    buyer = ''
    if invoice is not None:
        seller = _party_name(_first(invoice, 'СвПрод'))
        buyer = _party_name(_first(invoice, 'СвПокуп'))

    codes = []
    for line in root.iter():
        if _local(line.tag) != 'СведТов':
            continue
        name = line.attrib.get('НаимТов', '')
        extra = _first(line, 'ДопСведТов')
        article = extra.attrib.get('АртикулТов', '') if extra is not None else ''
        for kiz_el in line.iter():
            if _local(kiz_el.tag) != 'КИЗ':
                continue
            kiz = (kiz_el.text or '').strip()
            if not kiz:
                continue
            codes.append({
                'name': name,
                'article': article,
                'kiz': kiz,
            })

    return {
        'number': number,
        'date': date,
        'seller': seller,
        'buyer': buyer,
        'codes': codes,
    }
