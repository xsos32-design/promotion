#!/usr/bin/env python3
"""每月折扣小卡產生器（card.html）
用法：python3 cards.py <promotion/index.html> <chocolatepromo/index.html> <月份數字> <年>
資料直接讀兩個速查頁內嵌的資料（promotion 的 const DATA、chocolatepromo 的 #CMP），
所以每月先把速查頁更新好，再跑這支，小卡就會跟頁面一致。
輸出：out/promotion_card.html、out/chocolatepromo_card.html
"""
import json, re, sys, os, html, calendar

def esc(s): return html.escape(str(s), quote=False)

def tw(t):
    return sum(0.55 if ord(c) < 0x2E80 else 1.0 for c in t)

def split_weighted(groups, ncol, width):
    """依估計行數平均分欄（每列行數 = ceil(字寬/欄寬)），標題算 1.6"""
    import math
    def w_item(x): return max(1, math.ceil(tw(re.sub('<[^>]+>', '', x)) / width))
    def w_head(h): return 1.6 * max(1, math.ceil(tw(h) / (width * 0.9)))
    total = sum(w_head(h) + sum(w_item(x) for x in it) for h, it in groups)
    best = None
    for k in range(0, 40):
        target = total / ncol + k * 0.5
        cols, cur, cw = [], [], 0
        for h, items in groups:
            if cur and cw + w_head(h) + w_item(items[0]) > target:
                cols.append(cur); cur, cw = [], 0
            cur.append('<li class="h">%s</li>' % h); cw += w_head(h)
            for x in items:
                if cw + w_item(x) > target and len(cur) > 1:
                    cols.append(cur); hh = h + '（續）'
                    cur, cw = ['<li class="h">%s</li>' % hh], w_head(hh)
                cur.append(x); cw += w_item(x)
        cols.append(cur)
        if len(cols) <= ncol:
            return cols
    return cols

def split_cols(groups, ncol, cap):
    """groups=[(header,[li_html...])]; 依序填入 ncol 欄，每欄最多 cap 列（含標題），跨欄時補「（續）」標題"""
    cols = [[]]
    for h, items in groups:
        if len(cols[-1]) >= cap - 1:
            cols.append([])
        cols[-1].append('<li class="h">%s</li>' % h)
        for it in items:
            if len(cols[-1]) >= cap:
                cols.append(['<li class="h">%s（續）</li>' % h])
            cols[-1].append(it)
    return cols

# ---------------------------------------------------------------- 巧克力
CHOC_CSS = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'card_choc.css'), encoding='utf-8').read()
TIER_ORDER = [('T0', '任 2 件 7 折／任 3 件 65 折'), ('T1', '任 2 件 85 折／任 3 件 75 折'),
              ('A2', '任 2 件 85 折／任 3 件 8 折'), ('T2', '任 3 件 8 折'),
              ('T3', '任 2 件 85 折'), ('FIX', '單一促銷價（單件即享）')]
BRAND_PREFIX = ['妙卡 Milka ', '妙卡', 'Godiva', 'GODIVA ', '加倍佳', 'Hawaiian Host 賀氏 ', 'Venchi ',
                'HARIBO ', '吉利蓮', 'Hershey']

def choc_short(o):
    n = o['name']
    for p in BRAND_PREFIX:
        if n.startswith(p) and len(n) > len(p) + 2:
            n = n[len(p):].strip(); break
    n = re.sub(r'（TIKI）', '', n)
    return n if len(n) <= 26 else n[:25] + '…'

def build_choc(path, mon, yr):
    s = open(path, encoding='utf-8').read()
    D = json.loads(re.search(r'<script[^>]*id="CMP"[^>]*>(.*?)</script>', s, re.S).group(1))
    seen, items = set(), []
    for o in D['new'] + D['tchg'] + D['pchg'] + D['same']:
        k = o['code'] + '|' + str(o['tier'])
        if k not in seen and o.get('shot') and o.get('no'):
            seen.add(k); items.append(o)
    TL = D.get('TL', {})
    groups = []
    for t, label in TIER_ORDER:
        L = sorted([o for o in items if o['tier'] == t], key=lambda o: o['no'])
        if not L: continue
        lis = []
        for o in L:
            extra = '<i>$%s</i>' % format(o['sale'], ',') if t == 'FIX' and o.get('sale') else ''
            lis.append('<li><b>%s</b>%s%s</li>' % (esc(o['no']), esc(choc_short(o)), extra))
        groups.append((label, lis))
    n = len(items)
    cap = -(-(n + len(groups) + 3) // 4)
    cols = split_cols(groups, 4, cap)
    top = ''.join('<div class="col"><ul>%s</ul></div>' % ''.join(c) for c in cols)
    # 出清
    clr = ''
    if D.get('clear'):
        cis = ''.join('<div class="ci"><b>%s</b><span>%s<i>%s・NT$%s</i></span><u>%s</u></div>' % (
            esc(c.get('no', '')), esc(c.get('name', '')), esc(c.get('brand', '')), format(c.get('price', 0), ','), esc(c.get('qty', '')))
            for c in D['clear'])
        clr = '<div class="clr"><div class="lbl">%d月出清目標</div>%s</div>' % (mon, cis)
    # 滿額贈
    ms = []
    for g in D['sgwp']:
        txt = re.sub(r'（\d{10,}）|（盲盒／款式隨機，\d+）', lambda m: '（盲盒／款式隨機）' if '盲盒' in m.group(0) else '', g['text'])
        txt = txt.replace('GWP ', '').replace('・可累送', '')
        scope = g.get('scope', '')
        note = ''
        if '表上列' in scope:
            note = '<i>限表列 %d 品號</i>' % g['n']
        ms.append('<div class="m"><b>%s</b><span>%s</span>%s</div>' % (esc(' / '.join(g['brands'])), esc(txt), note))
    for g in D.get('agwp', []):
        ms.append('<div class="m"><b>%s</b><span>%s</span></div>' % (esc(g.get('brand', '')), esc(g.get('text', ''))))
    mid = '<div class="mid">%s</div>' % ''.join(ms)
    last = calendar.monthrange(yr, mon)[1]
    foot = ('<div class="foot"><div class="f b">「任 2 件 85 折／3 件 8 折」湊到 3 件是 <u>8 折不是 75 折</u>；'
            '「任 2 件 85 折」<u>沒有 3 件加碼</u>。同檔可跨品牌混搭，<u>不同檔次不可互湊</u>；保、完稅品號皆適用。</div>'
            '%s</div>')
    extra_f = ''
    if 'A2' not in [t for t, _ in TIER_ORDER if any(o['tier'] == t for o in items)]:
        foot = foot.replace('「任 2 件 85 折／3 件 8 折」湊到 3 件是 <u>8 折不是 75 折</u>；', '')
    if 'T2' in [o['tier'] for o in items]:
        foot = foot.replace('<div class="f b">', '<div class="f b">「任 3 件 8 折」<u>沒有 2 件折扣</u>，必須湊滿 3 件；', 1)
    if '滿 $2,000 折 $150' in s or '滿 2,000 折 150' in s:
        m = re.search(r'國產食品 &amp; 巧克力<br/>滿 \$2,000 折 \$150</b>\s*<ul class="anv-days"><li data-e="(\d{4})-(\d\d)-(\d\d)"', s)
        if m and (int(m.group(1)), int(m.group(2))) >= (yr, mon):
            extra_f = '<div class="f">全館：國產食品＆巧克力滿 $2,000 折 $150（至 %s/%s・樂高不算）</div>' % (m.group(2), m.group(3))
    foot = foot % extra_f
    title = '%d月巧克力折扣卡' % mon
    body = ('<div class="page"><p class="lead"><b>%s</b>　110×78mm <b>一張</b>，門市實拍確認得到的 %d 項全在這張。'
            '列印後沿外框剪下護貝即可。每項前的粗體編號（如 LI-12）可回巧克力完整檔案查品號、商訓與話術；單一促銷價後面的金額是促銷價。</p>'
            '<section class="card"><div class="hd"><b>%d月巧克力促銷</b><span>%d/%02d/01–%02d/%02d・全區・同檔可跨品牌混搭・單件無折扣（單一促銷價除外）</span></div>'
            '<div class="top">%s</div>%s%s%s<div class="stamp">%d/%02d 版・單張・商務本部</div></section></div>') % (
        title, n, mon, yr, mon, mon, last, top, clr, mid, foot, yr, mon)
    return page(title, CHOC_CSS, body)

# ---------------------------------------------------------------- 酒類
LIQ_CSS = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'card_liq.css'), encoding='utf-8').read()
EN_BRAND = ["Ballantine's", 'Caperdonich', 'Longmorn', 'Bowmore', 'GF', 'Miyagikyo', 'Taketsuru', 'Yoichi', 'RS', 'DAL',
            'Chivas', 'GN', 'Aberlour', 'TGL', 'Craigellachie', 'Tamdhu', 'Tomatin', 'Dalmore', 'VCP', 'HSY', 'Martell',
            'KVL', 'BLD']

def liq_short(name):
    toks = name.split(' ')
    if len(toks) > 2 and toks[1] in EN_BRAND:
        toks = [toks[0]] + toks[2:]
    n = ' '.join(toks)
    rep = [('Timeless 0.7', 'Timeless'), (' Grande 0.7L', ' Grande'), ('Peat25Y', 'Peat 25Y'),
           ('56度玉璽酒(鴻兔大展)0.6L', '玉璽酒 兔 0.6L'), ('56度玉璽酒(蛇來運轉)0.6L', '玉璽酒 蛇 0.6L'),
           ('Polo Coll. 5', 'POLO 5'), ('Vintage 2002', '2002'), ('Peated Blend', 'Peated'),
           ('K.Alexander New', '亞歷山大'), ('Portfolio ', 'Portfolio '), ('Madeira', '馬德拉'),
           ('VSOP (2023) 1L', 'VSOP 1L'), ('LGD Blance', 'LGD Blanc ')]
    for a, b in rep: n = n.replace(a, b)
    m = re.match(r'明石\s*(.*?)(威士忌)?\s*(700ml|700ML|0\.7L)$', n)
    if m:
        core = m.group(1).replace('藍標', '藍標').replace('杜氏調和', '杜氏調和').replace('忍輕泥煤水楢桶', '忍 輕泥煤水楢').replace('忍純麥威水楢桶', '忍 純麥水楢').replace('忍純麥水楢桶', '忍 純麥水楢')
        core = core.replace('(龍)', ' 龍')
        n = '明石 ' + core.strip()
    n = re.sub(r'\s*0\.7L?$', '', n).strip()
    n = re.sub(r'(\d+)YO\b', r'\1Y', n)
    return n

def build_liq(path, mon, yr):
    s = open(path, encoding='utf-8').read()
    i = s.find('const DATA = ') + len('const DATA = ')
    D, _ = json.JSONDecoder().raw_decode(s[i:])
    col_groups, mids, zone, manual = [], [], None, []
    for t in D['tiles']:
        if t['k'] == 'zone':
            zone = t; continue
        if t['k'] == 'amt':
            names = '、'.join(liq_short(x[0]) for x in t['items'])
            sub = t.get('sub', '').replace('7 件以上手動折扣', '').strip('・ ')
            mids.append('%s <b>%s</b>%s' % (esc(names), esc(t['t']), ('（%s）' % esc(sub)) if sub else ''))
            if '7 件以上手動' in t.get('sub', ''): manual.append(names)
            continue
        h = t['t'].replace('大摩 Portfolio 系列 ', 'Portfolio ')
        norm = [liq_short(it[0]) for it in t['items'] if not (len(it) > 2 and '完稅' in it[2])]
        duty = [liq_short(it[0]) for it in t['items'] if len(it) > 2 and '完稅' in it[2]]
        if norm: col_groups.append((h, ['<li>%s</li>' % esc(x) for x in norm]))
        if duty: col_groups.append((h + '・限完稅', ['<li>%s</li>' % esc(x) for x in duty]))
    n = sum(len(l) for _, l in col_groups)
    ncol = 6
    cols = split_weighted(col_groups, ncol, 10.5)
    top = ''.join('<div class="col"><ul>%s</ul></div>' % ''.join(c) for c in cols)
    fs = ['<div class="f"><b>每瓶折金額</b>　%s%s</div>' % ('／'.join(mids), ('　<u>%s 7 件以上手動折扣</u>' % '、'.join(dict.fromkeys(m.split(' ')[0] for m in manual))) if manual else '')] if mids else []
    fs += ['<div class="f b">酒類單件滿 $20,000 折 $1,000（全品項）・遇其他活動<u>取對客人最優</u>・<u>不可</u>放成箱折扣價</div>',
          '<div class="f b">員購 9／95 折・聯名卡 95 折：<u>單瓶促銷價、金酒全品項不適用</u></div>']
    if zone:
        fs.append('<div class="f b">日、韓、港、澳籍顧客限定：%s　※ 國籍要 key 對 ※</div>' % esc(zone.get('sub', '').split('・')[0]))
        fs.append('<div class="f">%s</div>' % esc(' / '.join(liq_short(x[0]) for x in zone['items'])))
    title = '%d月折扣卡' % mon
    body = ('<div class="page"><p class="lead"><b>%s</b>　110×78mm 單面，比照現行護貝小卡版型。列印後沿外框剪下護貝即可。'
            '標題寫「限完稅」的那一欄只限完稅品；未標容量者為 0.7L。</p><section class="card"><div class="top">%s</div>'
            '<div class="foot">%s<div class="stamp">未標容量者為 0.7L・%d/%02d 版・%d/01 起</div></div></section></div>') % (
        title, top, ''.join(fs), yr, mon, mon)
    return page(title, LIQ_CSS, body)

def page(title, css, body):
    return ('<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            '<title>%s</title><link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@400;700;900&display=swap">'
            '<style>%s</style></head><body>%s<script defer src="https://xsos32-design.github.io/dutyliquorwiki/nav.js"></script></body></html>') % (title, css, body)

if __name__ == '__main__':
    promo, choc, mon, yr = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
    os.makedirs('out', exist_ok=True)
    open('out/promotion_card.html', 'w', encoding='utf-8').write(build_liq(promo, mon, yr))
    open('out/chocolatepromo_card.html', 'w', encoding='utf-8').write(build_choc(choc, mon, yr))
    print('ok')
