#!/usr/bin/env python3
"""酒類速查頁：滿額贈卡「適用商品」連結＋小圖，及折扣/贈品酒品圖補齊。
用法：python3 promo_links.py promotion/index.html dutyliquorwiki/index.html giftlinks.json [extra_photos.json]
- giftlinks.json：贈品名 → [[顯示名, p|b|x, 百科id 或 品牌清單]]
- extra_photos.json（可省略）：百科沒有照片的商品 id → 圖片網址
會檢查：每組贈品都有對照、每個 id / 品牌都存在於百科；有缺會列出並以非 0 結束。
重複執行安全（以標記覆蓋舊版注入）。
"""
import json, re, sys

WIKI = 'https://xsos32-design.github.io/dutyliquorwiki/'

def load_wiki(path):
    w = open(path, encoding='utf-8').read()
    P = json.loads(re.search(r'<script id="DATA" type="application/json">(.*?)</script>', w, re.S).group(1))
    return {p['id']: p for p in P}, {p.get('brand') for p in P}

def abs_photo(u):
    if not u: return ''
    return u if re.match(r'https?://', u) else WIKI + u.lstrip('./')

def main():
    promo, wikip, glp = sys.argv[1:4]
    extra = json.load(open(sys.argv[4], encoding='utf-8')) if len(sys.argv) > 4 else {}
    W, BR = load_wiki(wikip)
    GL = {k: v for k, v in json.load(open(glp, encoding='utf-8')).items() if not k.startswith('_')}
    s = open(promo, encoding='utf-8').read()
    i = s.find('const DATA = ') + len('const DATA = ')
    D, end = json.JSONDecoder().raw_decode(s[i:])
    bad = []
    photo = lambda pid: extra.get(pid) or abs_photo(W[pid].get('photo'))
    out = {}
    SKIP = ('品牌PG', '入境滿', '採購銷售目標', '零散贈品')
    for g in D['gifts']:
        n = g['name']
        if n not in GL:
            if not n.startswith(SKIP): bad.append('贈品沒有對照：' + n)
            continue
        rows = []
        for e in GL[n]:
            lab, kind = e[0], e[1]
            if kind == 'p':
                if e[2] not in W: bad.append('百科沒有 id：%s（%s）' % (e[2], n)); continue
                rows.append([lab, 'p', e[2], photo(e[2])])
            elif kind == 'b':
                miss = [b for b in e[2] if b not in BR]
                if miss: bad.append('百科沒有品牌：%s（%s）' % (miss, n)); continue
                rows.append([lab, 'b', e[2], ''])
            else:
                rows.append([lab, 'x', '', ''])
        out[n] = rows
    D['giftlinks'] = out
    # 酒品圖補齊：沒有圖的贈品 → 用連到的商品照片；折扣品項 → 用 WIKILINK 對到的商品照片
    pool, gmap = D['gallery']['pool'], D['gallery']['map']
    def pidx(url, zh, en):
        for k, p in enumerate(pool):
            if p[0] == url: return k
        pool.append([url, zh, en]); return len(pool) - 1
    for n, rows in out.items():
        key = 'G|' + n
        if gmap.get(key): continue
        ids = [pidx(r[3], W[r[2]]['nameZh'], W[r[2]].get('nameEn') or '') for r in rows if r[1] == 'p' and r[3]]
        if ids: gmap[key] = ids
    m = re.search(r'const WIKILINK=(\{.*?\});', s)
    WL = json.loads(m.group(1)) if m else {}
    for t in D['tiles']:
        for it in t['items']:
            key = 'S|' + it[0]
            if gmap.get(key): continue
            pid = WL.get(it[0])
            if pid and pid in W and photo(pid):
                gmap[key] = [pidx(photo(pid), W[pid]['nameZh'], W[pid].get('nameEn') or '')]
            else:
                bad.append('折扣品項沒有酒品圖：' + it[0])
    s = s[:i] + json.dumps(D, ensure_ascii=False) + s[i + end:]
    # JS：贈品卡標題下加「適用商品」
    old = "'</h3></div>'+gdv+galHTML('G|'+b.name)+'<ol>'"
    new = "'</h3></div>'+gplHTML(b.name)+gdv+galHTML('G|'+b.name)+'<ol>'"
    if old in s: s = s.replace(old, new)
    elif new not in s: bad.append('找不到贈品卡模板，JS 未注入')
    JS = ('/*GPL*/function gplHTML(n){var L=(DATA.giftlinks||{})[n];if(!L||!L.length)return \'\';'
          'return \'<div class="gpl"><span class="gpl-h">適用商品</span>\'+L.map(function(r){'
          'if(r[1]===\'p\')return \'<a class="gp" target="_blank" rel="noopener" title="開啟商品完整檔案" href="\'+WIKI_BASE+\'#\'+encodeURIComponent(r[2])+\'">\''
          '+(r[3]?\'<img loading="lazy" alt="" src="\'+esc(r[3])+\'" onerror="this.remove()">\':\'\')+\'<span>\'+esc(r[0])+\'</span><i class="wlk-i">\\u2197</i></a>\';'
          'if(r[1]===\'b\')return \'<a class="gp b" target="_blank" rel="noopener" title="在酒類百科只看這個品牌" href="\'+WIKI_BASE+\'#brand=\'+encodeURIComponent(r[2].join(\'|\'))+\'"><span>\'+esc(r[0])+\'</span><i class="wlk-i">\\u2197</i></a>\';'
          'return \'<span class="gp x" title="酒類百科尚無這支的商品檔"><span>\'+esc(r[0])+\'</span></span>\';}).join(\'\')+\'</div>\';}/*/GPL*/')
    s = re.sub(r'/\*GPL\*/.*?/\*/GPL\*/', '', s, flags=re.S)
    s = s.replace('function galHTML(key){', JS + '\nfunction galHTML(key){', 1)
    CSS = ('/*GPLCSS*/.gpl{display:flex;flex-wrap:wrap;gap:6px;margin:6px 0 4px;align-items:center}'
           '.gpl-h{font-size:12px;color:var(--ink-3);margin-right:2px}'
           '.gp{display:inline-flex;align-items:center;gap:5px;font-size:12.5px;line-height:1.2;padding:3px 8px 3px 4px;border:1px solid var(--line-strong);border-radius:6px;background:var(--surface);color:var(--ink);text-decoration:none}'
           '.gp img{width:26px;height:26px;object-fit:contain;background:#fff;border-radius:4px;flex:0 0 auto}'
           '.gp.b{padding-left:8px;border-style:dashed}.gp.x{padding-left:8px;color:var(--ink-3);border-color:var(--line)}'
           'a.gp:hover{border-color:var(--accent);color:var(--accent)}.gp .wlk-i{font-style:normal;font-size:11px;opacity:.7}'
           '@media print{.gpl{display:none}}/*/GPLCSS*/')
    s = re.sub(r'/\*GPLCSS\*/.*?/\*/GPLCSS\*/', '', s, flags=re.S)
    s = s.replace('</style>', CSS + '</style>', 1)
    open(promo, 'w', encoding='utf-8').write(s)
    print('gifts linked:', len(out), ' items p/b/x:',
          sum(r[1] == 'p' for v in out.values() for r in v), sum(r[1] == 'b' for v in out.values() for r in v), sum(r[1] == 'x' for v in out.values() for r in v))
    for b in bad: print('!!', b)
    sys.exit(1 if bad else 0)

if __name__ == '__main__':
    main()
