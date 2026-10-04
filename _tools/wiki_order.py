#!/usr/bin/env python3
"""酒類百科排序：保留 類別 → 集團 → 品牌 的分類，品牌內「同系列放一起、按順序排」。
用法：python3 wiki_order.py dutyliquorwiki/index.html [--write]
規則：
 - 系列：依 SERIES 關鍵字判定（品名中英文），沒有命中的是「核心系列」
 - 核心系列排最前：無年份 → 年份由小到大
 - 其他系列依「最小年份／第一次出現」排；系列內依 代數/章/No./版次 → 年份 → 年份(西元) → 容量
 - ORDER_OVERRIDE 可指定某品牌的完整順序（id 清單）
編號 no 依新順序重編（001…），百科內文提到的 no.xxx 會一起換成新編號。
"""
import json, re, sys

CN = {'一': 1, '二': 2, '三': 3, '四': 4, '五': 5, '六': 6, '七': 7, '八': 8, '九': 9, '十': 10, '首': 1}
SERIES = [
    '馬球', 'Small Batch', '迷霧之徑', 'Ardbeg Day', '懷舊', '山川首席', 'OMAR原桶', '窖藏恆久', 'Yellow Label', '桶匠精選', 'Sample Room', '開創者', '時光永恆', 'Aston Martin', 'Frank Quitely', ' FQ', '旅遊零售獨家',
    '台灣之美', '新年典藏', '紅門窖藏', '雋永醞藏', 'Colour Collection', '色彩系列', 'RED COLLECTION', '和諧系列', '傳奇之初',
    '時空旅行', '精萃世界', 'M Decanter', 'Home Collection', 'Earth', 'Rare Cask', 'Portfolio', '島民', '經典獨奏', '大師精選',
    'PEATIST', '旅人限定', '藍牌', '黑牌', '奧特摩', '62 禮讚', '時光系列', 'Time Series', 'VAT', '時光臻藏',
    '皇家自治市', '玉璽酒', '龍騰九霄', '時光窖藏', '陳年', 'Paradis', 'Gran', 'XXO', 'X.O', 'XO', 'VSOP', '藍帶', '名仕黑耀', '名士',
    'Assemblage', '黑中白', '貴婦', '皇牌', '二割三分', 'Grange', 'Bin', '單桶', '單一酒桶', '新春限定', '三桶', '雙黑',
    '季節限定', '春季限定', '秋季限定', 'Signet', '稀印', '四重奏', '五重奏', '三重奏', 'Quartet', 'Quintet', '築光大師',
    '紀念', '獨奏', '純米大吟釀', '六琴酒', '奶酒', '香甜酒', '琴酒', '冰釀', '帝國', '黑桃王 黑中白', '璀璨金', '杜氏', '輕泥煤', '純麥 水楢', '純麥15年',
]
# 同義系列合併（後者併入前者）
ALIAS = {'Frank Quitely': ' FQ', '色彩系列': 'Colour Collection', 'Home Collection': 'Home Collection', '單一酒桶': '單桶',
         '稀印': 'Signet', 'Quartet': '四重奏', 'Quintet': '五重奏', '春季限定': '季節限定', '秋季限定': '季節限定',
         '純麥15年': '純麥 水楢', 'X.O': 'XO', '經典獨奏': '獨奏', 'Yellow Label': '皇牌'}
ORDER_OVERRIDE = {
 '皇家禮炮 Royal Salute': ['royalsalute-21y','royalsalute-21y-4','royalsalute-21y-large','royalsalute-21y-5','royal-salute-rs','royal-salute-fashion',
    'royalsalute-21y-polo5','royalsalute-21y-6','royal-salute-rio-polo','royalsalute-25y','royalsalute-25y-sb','royalsalute-32y',
    'royalsalute-51y-time-series','royalsalute-62-original','royalsalute-62-peated','royalsalute-coronation-kc3'],
 '約翰走路 Johnnie Walker': ['jw-4','jw-7','jw-5','jw-8','jw-6','jw-9','jw','jw-blue-azure','jw-blue-xordinaire','jw-blue-futurecity-tw','jw-blue-cny-horse','jw-john-walker-40y'],
 '軒尼詩 Hennessy': ['hennessy-vsop-hennessy-1l','hennessy-07l-2','hennessy-xo-1l','cognac-brandy-hennessy-1l','hennessy-xo-kim-jones','hennessy-xo-cny-2026',
    'hennessy-xxo-1l','hennessy','hennessy-paradis-hennessy-005l','hennessy-paradis-hennessy-035l','hennessy-paradis-hennessy-07l','hennessy-07l',
    'hennessy-paradis-bernardaud-1l','hennessy-07l-3','hennessy-mbs-no4-05l','hennessy-no5-05l'],
 '馬爹利 Martell': ['martell-vsop-redbarrel-1l','martell-07l-2','martell-noblige-1l','martell-07l-3','martell-noir-cny','martell-035l','martell-07l','martell-3l',
    'martell-1l','martell-05l','martell-07l-4','martell-1l-2','martell-15l','martell-xo-cny-2026','martell-xxo-07l','martell-lor-snake-2025'],
}
BRAND_FIX = {('麥卡倫 Macallan',): '麥卡倫 The Macallan', ('Rosebank',): '羅斯班克 Rosebank', ('Glen deveron',): '格蘭德弗倫 Glen Deveron'}

def num(s):
    s = s.strip()
    return CN.get(s) if s in CN else (int(s) if s.isdigit() else None)

def feats(p):
    t = (p.get('nameZh') or '') + ' ' + (p.get('nameEn') or '')
    tz = p.get('nameZh') or ''
    gen = None
    for pat in [r'第\s*([一二三四五六七八九十\d]+)\s*[代章版批]', r'([首])部曲', r'No\.?\s*(\d+)', r'N°\s*(\d+)', r'RESERVE\s+(I{1,3})\b',
                r'系列\s*(\d+)-(\d+)', r'VAT\s*0?(\d+)', r'POLO\s*(\d+)', r'Release\s+(\w+)', r'(\d+)\.(\d)\s*泥煤', r'Bin\s*(\d+)']:
        m = re.search(pat, t, re.I)
        if m:
            g = m.groups()
            if pat.startswith('RESERVE'): gen = (len(g[0]),)
            elif len(g) == 2 and g[1] is not None: gen = (int(g[0]), int(g[1]))
            else:
                v = num(g[0]) if g[0] else None
                if v is None and g[0] and g[0].lower() in ('one', 'two', 'three'): v = ['one', 'two', 'three'].index(g[0].lower()) + 1
                gen = (v or 0,)
            break
    ages = [int(a) for a in re.findall(r'(?<![\d.])(\d{1,2})\s*(?:年|YO\b|Y\b|Years?\b|Year\b)', t, re.I) if int(a) <= 85]
    age = min(ages) if ages else None
    vint = re.findall(r'(?<!\d)(19[4-9]\d|20[0-2]\d)(?!\d)', tz)
    vint = int(vint[0]) if vint else None
    vol = None
    m = re.search(r'(\d+(?:\.\d+)?)\s*(ml|L)\b', (p.get('vol') or '') + ' ' + tz, re.I)
    if m: vol = float(m.group(1)) * (1000 if m.group(2).lower() == 'l' else 1)
    ser = None
    for k in SERIES:
        if k.lower() in t.lower():
            ser = ALIAS.get(k, k); break
    return ser, gen, age, vint, vol

def order_brand(L):
    ids = [p['id'] for p in L]
    b = L[0]['brand']
    if b in ORDER_OVERRIDE:
        o = ORDER_OVERRIDE[b]; rest = [p for p in L if p['id'] not in o]
        return [next(p for p in L if p['id'] == i) for i in o if i in ids] + rest
    F = {p['id']: feats(p) for p in L}
    first = {}
    for i, p in enumerate(L): first.setdefault(F[p['id']][0], i)
    ser_ages = {}
    for p in L:
        s, g, a, v, vol = F[p['id']]
        ser_ages.setdefault(s, []).append(a if a is not None else 999)
    def skey(s):
        if s is None: return (0, 0, 0)
        return (1, min(ser_ages[s]), first[s])
    vin_ser = {}
    for p in L:
        s, g, a, v, vol = F[p['id']]
        if v: vin_ser[s] = vin_ser.get(s, 0) + 1
    def k(p):
        s, g, a, v, vol = F[p['id']]
        if s is None:   # 核心系列：無年份 → 年份小到大
            return (skey(s), a if a is not None else -1, v or 0, vol or 0, L.index(p))
        if vin_ser.get(s, 0) >= 2:   # 單桶／年份系列：依蒸餾年份
            return (skey(s), v or 9999, g or (0,), a or 0, vol or 0, L.index(p))
        return (skey(s), g or (0,), a if a is not None else 0, v or 0, vol or 0, L.index(p))
    return sorted(L, key=k)

def main():
    path = sys.argv[1]
    w = open(path, encoding='utf-8').read()
    m = re.search(r'(<script id="DATA" type="application/json">)(.*?)(</script>)', w, re.S)
    P = json.loads(m.group(2))
    # 名稱統一（同一品牌被拆成兩個寫法）
    for p in P:
        for k, v in BRAND_FIX.items():
            if p['brand'] in k: p['brand'] = v
        if p['cat'] == '利口酒': p['cat'] = '調酒利口酒'
        p['group'] = {'格蘭父子 William Grant & Sons': '格蘭父子 William Grant', '金門酒廠': '台灣 金車/金門/台酒',
                      'Bottega SpA（義大利 Veneto）': 'Bottega SpA（義大利）', 'Ian Macleod Distillers': 'Ian Macleod 獨立裝瓶'}.get(p['group'], p['group'])
    CATS = ['威士忌', '白蘭地', '高粱白酒', '葡萄酒', '香檳氣泡', '清酒梅酒', '調酒利口酒']
    tree = {}
    gorder, border = {}, {}
    for i, p in enumerate(P):
        c = p['cat']; g = p['group']; b = p['brand']
        gorder.setdefault((c, g), i); border.setdefault((c, g, b), i)
        tree.setdefault((c, g, b), []).append(p)
    newP = []
    for c in CATS + sorted({p['cat'] for p in P} - set(CATS)):
        gs = sorted([k for k in gorder if k[0] == c], key=lambda k: gorder[k])
        for (c2, g) in gs:
            bs = sorted([k for k in border if k[0] == c and k[1] == g], key=lambda k: border[k])
            for kb in bs:
                newP.extend(order_brand(tree[kb]))
    assert len(newP) == len(P)
    old2new = {}
    for i, p in enumerate(newP):
        old2new[p['no']] = '%03d' % (i + 1)
    report = []
    for p in newP:
        report.append('%s\t%s\t%s\t%s\t%s' % (old2new[p['no']], p['no'], p['cat'], p['brand'][:14], p['nameZh'][:40]))
    open('order_report.txt', 'w', encoding='utf-8').write('\n'.join(report))
    if '--write' in sys.argv:
        for p in newP: p['no'] = old2new[p['no']]
        txt = json.dumps(newP, ensure_ascii=False)
        def fixno(mm):
            o = mm.group(2)
            return (mm.group(1) + old2new[o]) if o in old2new else ('舊編號 ' + o)   # 指到已刪除的卡就改成「舊編號」，避免對到別支
        txt = re.sub(r'(no\.)(\d{3}(?:-\d+)?)(?![\d-])', fixno, txt)
        w = w[:m.start(2)] + txt + w[m.end(2):]
        open(path, 'w', encoding='utf-8').write(w)
        json.dump(old2new, open('no_map.json', 'w'), ensure_ascii=False)
    print('ok', len(newP))

if __name__ == '__main__':
    main()
