#!/usr/bin/env python3
"""巧克力速查＋巧克力百科：品名連結與商品圖補齊、滿額贈卡「適用商品」。
用法：python3 choc_links.py chocolatepromo/index.html chocolatewiki/index.html repo_paths.txt choc_extra.json
- repo_paths.txt：chocolatepromo repo 內所有檔案路徑（一行一個），用來判斷 img/cut/<code>.webp、img/p/<code>.jpg 是否存在
- choc_extra.json：{"cats": {品牌|品號: 分類}, "brands": [新品牌資料], "newcats": [新分類], "photoSrc": {品號: 來源說明}}
做的事：
 1. 速查頁每一項（含只有滿額贈的）沒有商品圖 → 用 img/cut、img/p，再不行用百科照片
 2. 百科沒有這張商品卡 → 依促銷表新增一張（品名、價格、折扣、滿額贈、照片）；百科卡沒照片 → 補
 3. 速查頁滿額贈卡加「適用商品」（依贈品代碼對到品項，附小圖、連到百科）
最後列出仍然缺圖／缺連結的品項。重複執行安全。
"""
import json, re, sys

PROMO_BASE = 'https://xsos32-design.github.io/chocolatepromo/'
WIKI_BASE = 'https://xsos32-design.github.io/chocolatewiki/'

def nt(n): return 'NT$' + format(int(round(n)), ',')

def main():
    pp, wp, rp, xp = sys.argv[1:5]
    paths = set(l.strip() for l in open(rp, encoding='utf-8') if l.strip())
    X = json.load(open(xp, encoding='utf-8'))
    s = open(pp, encoding='utf-8').read()
    mC = re.search(r'(<script[^>]*id="CMP"[^>]*>)(.*?)(</script>)', s, re.S)
    D = json.loads(mC.group(2))
    w = open(wp, encoding='utf-8').read()
    mW = re.search(r'(<script id="DATA" type="application/json">)(.*?)(</script>)', w, re.S)
    CD = json.loads(mW.group(2))
    WP = {p['id']: p for p in CD['P']}
    TL = D.get('TL', {})

    def local_img(code):
        if 'img/cut/%s.webp' % code in paths: return 'img/cut/%s.webp' % code
        for ext in ('jpg', 'png', 'webp'):
            if 'img/p/%s.%s' % (code, ext) in paths: return 'img/p/%s.%s' % (code, ext)
        return ''

    def wphoto(p):
        u = (p or {}).get('photo') or ''
        if u and not re.match(r'https?://', u): u = WIKI_BASE + u
        return u

    groups = ['new', 'tchg', 'pchg', 'same', 'gwponly']
    allo = [o for g in groups for o in D[g]]
    # 1. 速查頁補圖
    for o in allo:
        if o.get('img'): continue
        li = local_img(o['code'])
        if li:
            o['img'] = li; o['imgsrc'] = X.get('photoSrc', {}).get(o['code'], '官方商品圖（去背）' if '/cut/' in li else '零售通路商品圖')
        else:
            u = wphoto(WP.get('c' + o['code']))
            if u: o['img'] = u; o['imgsrc'] = WP['c' + o['code']].get('photoSrc') or '巧克力百科'
    # 2. 百科補卡／補照片
    country = {b['name']: b['country'] for b in CD['BRANDS']}
    for b in X.get('brands', []):
        if b['name'] not in country: CD['BRANDS'].append(b); country[b['name']] = b['country']
    for c in X.get('newcats', []):
        if c['n'] not in [k['n'] for k in CD['CATS']]: CD['CATS'].append(c)
    added = []
    seen = set()
    for o in allo:
        cid = 'c' + o['code']
        if cid in seen: continue
        seen.add(cid)
        img = o.get('img') or ''
        absimg = img if re.match(r'https?://', img) else (PROMO_BASE + img if img else '')
        if cid in WP:
            p = WP[cid]
            if not p.get('photo') and absimg:
                p['photo'] = absimg; p['photoSrc'] = o.get('imgsrc') or ''
            continue
        cat = X['cats'].get(o['code']) or X['cats'].get(o['brand'])
        if not cat: print('!! 沒有分類：', o['code'], o['name']); continue
        promo = []
        t = o.get('tier')
        if t and t != 'FIX':
            sub = []
            if o.get('r2'): sub.append('2 件 ' + nt(o['price'] * o['r2']))
            if o.get('r3'): sub.append('3 件 ' + nt(o['price'] * o['r3']))
            promo.append({'t': TL.get(t, o.get('tlabel', '')), 'sub': '　'.join(sub), 'k': '10 月促銷表'})
        elif t == 'FIX' and o.get('sale'):
            promo.append({'t': '單一促銷價 ' + nt(o['sale']), 'sub': '原價 %s・單件即享' % nt(o['price']), 'k': '10 月促銷表'})
        for g in o.get('gwp') or []:
            promo.append({'t': g, 'sub': '可累送', 'k': '滿額贈 GWP'})
        name = o['name'] if o['name'].lower().startswith(o['brand'].lower()) else o['brand'] + ' ' + o['name']
        rec = {'id': cid, 'no': o.get('no') or '', 'code': o['code'], 'nameZh': name, 'nameEn': name, 'cat': cat,
               'brand': o['brand'], 'group': country.get(o['brand'], ''), 'spec': '', 'pv': o['price'], 'price': nt(o['price']),
               'sale': o.get('sale'), 'tier': t, 'promo': promo,
               'pos': ('10 月促銷表新進品項：' + (promo[0]['t'] if promo else '滿額贈適用品項') + '。品名依促銷表原文，詳細規格以包裝為準。'),
               'photo': absimg, 'photoSrc': o.get('imgsrc') or '', 'photoNote': ''}
        CD['P'].append(rec); WP[cid] = rec; added.append(name)
    cnt = {}
    for p in CD['P']: cnt[p['cat']] = cnt.get(p['cat'], 0) + 1
    for c in CD['CATS']: c['c'] = cnt.get(c['n'], 0)
    w = w[:mW.start(2)] + json.dumps(CD, ensure_ascii=False) + w[mW.end(2):]
    # 3. 滿額贈卡「適用商品」
    gl = []
    for g in D['sgwp']:
        codes = re.findall(r'279\d{10}', g['text'])
        L = []
        for o in allo:
            if any(c in ' '.join(o.get('gwp') or []) for c in codes) and o['code'] not in [x[0] for x in L]:
                im = o.get('img') or ''
                L.append([o['code'], o.get('no') or '', o['name'], im])
        gl.append(L)
    D['sgwpItems'] = gl
    s = s[:mC.start(2)] + json.dumps(D, ensure_ascii=False) + s[mC.end(2):]
    old = "'<ol><li>'+esc(g.text)+'</li><li><em>'+(g.scope?"
    new = "gplHTML(i)+'<ol><li>'+esc(g.text)+'</li><li><em>'+(g.scope?"
    if old in s: s = s.replace(old, new).replace("var h=DATA.sgwp.map(function(g){", "var h=DATA.sgwp.map(function(g,i){", 1)
    elif new not in s: print('!! 找不到滿額贈模板')
    JS = ('/*GPL*/function gplHTML(i){var L=(DATA.sgwpItems||[])[i];if(!L||!L.length)return \'\';'
          'return \'<div class="gpl"><span class="gpl-h">適用商品 \'+L.length+\'</span>\'+L.map(function(r){'
          'return \'<a class="gp" target="_blank" rel="noopener" title="開啟商品完整檔案" href="\'+WIKI+esc(r[0])+\'">\''
          '+(r[3]?\'<img loading="lazy" alt="" src="\'+esc(r[3])+\'" onerror="this.remove()">\':\'\')'
          '+(r[1]?\'<b>\'+esc(r[1])+\'</b>\':\'\')+\'<span>\'+esc(r[2])+\'</span><i class="wlk-i">\\u2197</i></a>\';}).join(\'\')+\'</div>\';}/*/GPL*/')
    s = re.sub(r'/\*GPL\*/.*?/\*/GPL\*/', '', s, flags=re.S)
    s = s.replace('function renderGift(){', JS + '\nfunction renderGift(){', 1)
    CSS = ('/*GPLCSS*/.gpl{display:flex;flex-wrap:wrap;gap:6px;margin:6px 10px 6px;align-items:center}'
           '.gpl-h{font-size:12px;opacity:.7;margin-right:2px}'
           '.gp{display:inline-flex;align-items:center;gap:5px;font-size:12.5px;line-height:1.2;padding:3px 8px 3px 4px;border:1px solid rgba(127,127,127,.45);border-radius:6px;text-decoration:none;color:inherit}'
           '.gp img{width:26px;height:26px;object-fit:contain;background:#fff;border-radius:4px;flex:0 0 auto}'
           '.gp b{font-weight:800;font-size:11.5px}.gp .wlk-i{font-style:normal;font-size:11px;opacity:.7}'
           '@media print{.gpl{display:none}}/*/GPLCSS*/')
    s = re.sub(r'/\*GPLCSS\*/.*?/\*/GPLCSS\*/', '', s, flags=re.S)
    s = s.replace('</style>', CSS + '</style>', 1)
    open(pp, 'w', encoding='utf-8').write(s)
    open(wp, 'w', encoding='utf-8').write(w)
    ids = {p['id'] for p in CD['P']}
    noimg = [(o.get('no'), o['code'], o['name']) for o in allo if not o.get('img')]
    nolink = [(o.get('no'), o['code'], o['name']) for o in allo if 'c' + o['code'] not in ids]
    print('百科新增', len(added), added)
    print('滿額贈適用商品', [len(x) for x in gl])
    print('仍缺圖', noimg); print('仍缺連結', nolink)
    print('百科仍缺照片', [(p['no'], p['nameZh']) for p in CD['P'] if not p.get('photo')])

if __name__ == '__main__':
    main()
