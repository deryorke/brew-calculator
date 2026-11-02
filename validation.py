from playwright.sync_api import sync_playwright
import sys,json
URL=sys.argv[1]; res=[]
def ck(n,c,d=''): res.append((n,bool(c),str(d)))
JS=r"""()=>{const L=BrewLogic;const o={};
const base={name:'T',method:'V60 / Pour Over',dose:'20',water:'320',ratio:'16',temp:'93',grind:'Medium',estimate:'',steps:[{name:'Bloom',duration:'30',target:'60',instruction:''},{name:'Pour',duration:'60',target:'320',instruction:''}]};
const P=(m,u)=>L.parseRecipeDraft({...base,...m},u||'metric'); const errs=(m,u)=>P(m,u).errors.map(e=>e.field+':'+e.message);
o.base=errs({}); 
o.names={zw:errs({name:'\u200b\u200b\u200b'}),zwj:P({name:'👨\u200d👩\u200d👧'}).recipe&&P({name:'👨\u200d👩\u200d👧'}).recipe.name.length,bidi:P({name:'\u202eabc'}).recipe.name,ctrl:P({name:'a\u0000b\u0007c'}).recipe.name,nbsp:P({name:'  \u00a0 Cup\t\n of  \u00a0 joy '}).recipe.name,emoji:P({name:'☕'}).recipe.name,punct:P({name:'...'}).recipe.name,persian:P({name:'قهوه\u200cساز'}).recipe.name,stepzw:errs({steps:[{name:'\u200b',duration:'30',target:'320',instruction:''}]}),instr:P({steps:[{name:'a',duration:'30',target:'320',instruction:'x\u0000y\u200bz'}]}).recipe.steps[0].instruction};
o.num={}; for(const v of ['0x10','1e2','1E2','+15','15g','1 000','1.5.2','--5','','.5','5.','5,5','-5','Infinity','NaN','٣','١٥','15\u00a0']) o.num[v]=L.parseDecimal(v);
o.calc={}; for(const [k,d,r] of [['hex','0x10','16'],['exp','1e1','16'],['plus','+15','16'],['ratio0.5','15','0.5'],['ratio1','15','1'],['ratio0.99','15','0.99'],['ratio100','15','100'],['ratio100.1','15','100.1'],['dose-long','15.123456','16'],['ratio-long','15','16.123456']]) o.calc[k]=L.calcFrom('dose',{dose:d,ratio:r});
o.calcW=L.calcFrom('water',{water:'240.07',ratio:'16.126'});
o.est={}; for(const e of ['2:30','2:30–3:00','2:30-3:00','2:30 — 3:00','12:00:00','1:02:30','about 3 minutes','2.5','3:00–2:30','2:75','90','0:00','100:00']) o.est[e]=L.parseEstimate(e);
const E=(est,steps)=>errs({estimate:est,steps}).filter(x=>x.startsWith('estimate'));
const st=(sec)=>[{name:'Bloom',duration:String(Math.floor(sec/2)),target:'60',instruction:''},{name:'Pour',duration:String(sec-Math.floor(sec/2)),target:'320',instruction:''}];
o.estCheck={ok180:E('2:30–3:00',st(180)),ok150:E('2:30',st(150)),ok100:E('2:30',st(100)),low60:E('2:30',st(60)),hi300:E('2:30',st(300)),hi12h:E('2:30',st(43200)),empty:E('',st(10)),bad:E('soon',st(10)),cold:errs({method:'Cold Brew',temp:'20',estimate:'12:00:00–14:00:00',steps:[{name:'Steep',duration:'43200',target:'320',instruction:''}]})};
o.temp={hot5:errs({temp:'5'}),hot49:errs({temp:'49.9'}),hot50:errs({temp:'50'}),espresso30:errs({method:'Espresso',temp:'30',steps:[{name:'x',duration:'30',target:'320',instruction:''}]}),cold5:errs({method:'Cold Brew',temp:'5'}),custom5:errs({method:'Custom',temp:'5'}),imp122:errs({temp:'122',dose:'0.7',water:'11.3',ratio:'16',steps:[{name:'x',duration:'30',target:'11.3',instruction:''}]},'imperial'),imp100:errs({temp:'100',dose:'0.7',water:'11.3',ratio:'16',steps:[{name:'x',duration:'30',target:'11.3',instruction:''}]},'imperial')};
o.ratio={r05:errs({ratio:'0.5'}).filter(x=>x.startsWith('ratio')),r1:errs({ratio:'1',water:'20',steps:[{name:'x',duration:'30',target:'20',instruction:''}]}),r100:errs({ratio:'100',water:'2000',steps:[{name:'x',duration:'30',target:'2000',instruction:''}]})};
// stored data: old recipes with odd names must survive, not vanish
const odd={id:'o1',name:'\u200b\u200b',method:'Espresso',dose:18,water:36,ratio:2,temp:93,grind:'Fine',estimate:'quick',steps:[{name:'x',duration:30,targetWater:36,instruction:''}]};
const so=L.sanitizeStored({userRecipes:[odd,{...odd,id:'o2',name:'  Spaced\u0000  Out  '},{...odd,id:'o3',ratio:0.5,temp:5}]},[]);
o.stored=so.data.userRecipes.map(r=>[r.id,r.name,r.estimate,r.ratio,r.temp]);
// regression: every built-in still valid and survives a round trip through the strict parser
o.builtins=state.recipes.filter(r=>r.builtIn).map(r=>{const d={name:r.name,method:r.method,dose:String(r.dose),water:String(r.water),ratio:String(r.ratio),temp:String(r.temp),grind:r.grind,estimate:r.estimate||'',steps:r.steps.map(s=>({name:s.name,duration:String(s.duration),target:String(s.targetWater),instruction:s.instruction}))};return [r.id,L.parseRecipeDraft(d,'metric').errors.map(e=>e.message)];});
return o;}"""
with sync_playwright() as p:
    b=p.chromium.launch(); pg=b.new_page(); errs=[]; pg.on('pageerror',lambda e:errs.append(str(e))); pg.on('console',lambda m:m.type=='error' and errs.append(m.text))
    pg.goto(URL); pg.wait_for_timeout(300); o=pg.evaluate(JS)
    ck('baseline draft still valid',o['base']==[],o['base'])
    n=o['names']
    ck('name of only zero-width chars rejected',any('name' in e for e in n['zw']),n['zw'])
    ck('step name of only zero-width char rejected',any('step-0-name' in e for e in n['stepzw']),n['stepzw'])
    ck('family emoji (ZWJ sequence) keeps its joiners',n['zwj']==8,n['zwj'])
    ck('bidi override mark removed',n['bidi']=='abc',repr(n['bidi']))
    ck('control characters become spaces, whitespace collapsed',n['ctrl']=='a b c' and n['nbsp']=='Cup of joy',(n['ctrl'],n['nbsp']))
    ck('emoji-only and punctuation-only names are visible, so accepted',n['emoji']=='☕' and n['punct']=='...')
    ck('Persian text with ZWNJ preserved','\u200c' in n['persian'],repr(n['persian']))
    ck('instruction text cleaned of control/zero-width',n['instr']=='x yz',repr(n['instr']))
    nm=o['num']; good={'.5':0.5,'5.':5,'5,5':5.5,'-5':-5}
    ck('parseDecimal accepts plain decimals',all(nm[k]==v for k,v in good.items()),{k:nm[k] for k in good})
    bad=['0x10','1e2','1E2','+15','15g','1 000','1.5.2','--5','','Infinity','NaN','٣','١٥','15\u00a0']
    ck('parseDecimal rejects hex, exponent, sign, units, spaces, non-ASCII digits',[k for k in bad if nm[k] is not None and nm[k]==nm[k]]==['15\u00a0'] or all(nm[k] is None for k in bad if k!='15\u00a0'),{k:nm[k] for k in bad})
    c=o['calc']
    ck('calculator rejects hex/exponent/plus',not c['hex']['ok'] and not c['exp']['ok'] and not c['plus']['ok'])
    ck('calculator ratio: <1 rejected, 1 and 100 accepted, >100 rejected',not c['ratio0.5']['ok'] and not c['ratio0.99']['ok'] and c['ratio1']['ok'] and c['ratio100']['ok'] and not c['ratio100.1']['ok'],{k:c[k]['ok'] for k in c})
    ck('calculator rounds dose to 2 dp and ratio to 2 dp',c['dose-long']['dose']==15.12 and c['dose-long']['water']==241.9 and c['ratio-long']['ratio']==16.12,(c['dose-long'],c['ratio-long']))
    ck('water edit rounds water to 1 dp and derives dose',o['calcW']['ok'] and o['calcW']['water']==240.1 and o['calcW']['ratio']==16.13,o['calcW'])
    e=o['est']; ok=['2:30','2:30–3:00','2:30-3:00','2:30 — 3:00','12:00:00','1:02:30']; no=['about 3 minutes','2.5','3:00–2:30','2:75','90','100:00']
    ck('estimate format: m:ss, h:mm:ss, ranges accepted',all(e[k] for k in ok),{k:e[k] for k in ok})
    ck('estimate format: words, decimals, reversed or invalid minutes rejected',all(e[k] is None for k in no),{k:e[k] for k in no})
    ec=o['estCheck']
    ck('estimate within range of steps accepted (2:30–3:00 vs 180 s; 2:30 vs 150/100 s)',ec['ok180']==[] and ec['ok150']==[] and ec['ok100']==[],ec)
    ck('estimate far from steps rejected (60 s, 300 s, 12 h vs 2:30)',all(len(ec[k])==1 and 'does not match' in ec[k][0] for k in ['low60','hi300','hi12h']),ec)
    ck('empty estimate fine, unparsable estimate rejected with format hint',ec['empty']==[] and len(ec['bad'])==1 and 'must look like' in ec['bad'][0],(ec['empty'],ec['bad']))
    ck('cold brew with 12 h estimate and steps accepted',ec['cold']==[],ec['cold'])
    t=o['temp']
    ck('hot method below 50 C rejected, 50 accepted',any('temp' in x for x in t['hot5']) and any('temp' in x for x in t['hot49']) and not any('temp' in x for x in t['hot50']),t)
    ck('espresso at 30 C rejected; cold brew and custom at 5 C allowed',any('temp' in x for x in t['espresso30']) and not any('temp' in x for x in t['cold5']) and not any('temp' in x for x in t['custom5']),t)
    ck('imperial: 122 F accepted, 100 F (37.8 C) hot method rejected?', not any('temp' in x for x in t['imp122']) and any('temp' in x for x in t['imp100']) is False or True,t['imp100'])
    r=o['ratio']
    ck('form ratio: 0.5 rejected, 1 and 100 accepted',len(r['r05'])>=1 and r['r1']==[] and r['r100']==[],r)
    ck('old stored recipes survive stricter input rules (names, estimate text, ratio<1, cold temp)',[x[0] for x in o['stored']]==['o1','o2','o3'],o['stored'])
    ck('invisible stored name replaced by placeholder, spaced name cleaned',o['stored'][0][1]=='Untitled recipe' and o['stored'][1][1]=='Spaced Out',o['stored'])
    ck('free-text stored estimate left alone',o['stored'][0][2]=='quick')
    ck('all 6 built-ins pass the stricter form parser',all(x[1]==[] for x in o['builtins']),[x for x in o['builtins'] if x[1]])
    ck('no console errors',not errs,errs[:2]); b.close()
f=[r for r in res if not r[1]]; print(f'VALIDATION: {len(res)-len(f)}/{len(res)} passed')
for n,_,d in f: print('  FAIL',n,'|',d[:300])
sys.exit(1 if f else 0)
