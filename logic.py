# Part 1: logic / data-integrity checks run inside the page
from playwright.sync_api import sync_playwright
import sys
URL=sys.argv[1]
JS=r"""()=>{
const R=[]; const ck=(n,c,d)=>R.push([n,!!c,c?'':String(d===undefined?'':d)]);
const L=BrewLogic; const near=(a,b,e)=>Math.abs(a-b)<=e;
let seed=12345; const rnd=()=>{seed=(seed*1664525+1013904223)%4294967296;return seed/4294967296;};
// ---- built-in recipes
const bi=state.recipes.filter(r=>r.builtIn);
ck('6 built-in recipes',bi.length===6,bi.length);
ck('built-in ids unique',new Set(state.recipes.map(r=>r.id)).size===state.recipes.length);
bi.forEach(r=>{
  ck('valid '+r.id,L.validateRecipe(r).length===0,JSON.stringify(L.validateRecipe(r)));
  ck('dose x ratio ~ water '+r.id,near(r.dose*r.ratio,r.water,0.5),`${r.dose}*${r.ratio}!=${r.water}`);
  const t=r.steps.map(s=>s.targetWater);
  if(L.isPouring(r.method)){ ck('targets cumulative '+r.id,t.every((x,i)=>i===0||x>=t[i-1]),t); ck('last target = water '+r.id,near(t[t.length-1],r.water,0.01),t); }
  else ck('targets within range '+r.id,t.every(x=>x>=0&&x<=r.water),t);
  const before=JSON.stringify(r); try{r.dose=999;r.steps[0].duration=1;r.steps.push({});}catch(e){}
  ck('built-in immutable '+r.id,JSON.stringify(r)===before);
});
// ---- calculator properties
let bad=[];
for(let i=0;i<3000;i++){
  const dose=Math.round((1+rnd()*499)*10)/10, ratio=Math.round((1+rnd()*29)*10)/10;
  const a=L.calcFrom('dose',{dose:String(dose),ratio:String(ratio)});
  if(!a.ok||a.water!==L.round(dose*ratio,1)||a.dose!==dose) {bad.push(['dose',dose,ratio,a]);continue;}
  const b=L.calcFrom('water',{water:String(a.water),ratio:String(ratio)});
  if(!b.ok||!near(b.dose*ratio,a.water,0.005*ratio+0.051)) bad.push(['water',a.water,ratio,b]);
}
ck('calcFrom 3000 random cases consistent',bad.length===0,JSON.stringify(bad.slice(0,2)));
ck('calcFrom comma decimal',L.calcFrom('dose',{dose:'15,5',ratio:'16'}).water===248);
['','  ','abc','-1','0','NaN','Infinity','1e999'].forEach(v=>{ck('calcFrom rejects "'+v+'"',L.calcFrom('dose',{dose:v,ratio:'16'}).ok===false);ck('calcFrom rejects ratio "'+v+'"',L.calcFrom('dose',{dose:'15',ratio:v}).ok===false);});
// ---- scaleSteps
let sb=[];
bi.filter(r=>L.isPouring(r.method)).forEach(r=>{
  for(let i=0;i<300;i++){
    const nw=Math.round((5+rnd()*4995)*10)/10, snap=JSON.stringify(r.steps), out=L.scaleSteps(r.steps,r.water,nw), t=out.map(s=>s.targetWater);
    if(JSON.stringify(r.steps)!==snap) sb.push(['mutated',r.id]);
    if(out.length!==r.steps.length||!t.every((x,j)=>x<=nw&&(j===0||x>=t[j-1]))||!near(t[t.length-1],nw,0.001)||out.some((s,j)=>s.duration!==r.steps[j].duration)) sb.push([r.id,nw,t]);
  }
});
ck('scaleSteps 1200 cases (cumulative, last=water, no mutation)',sb.length===0,JSON.stringify(sb.slice(0,2)));
// ---- units
for(let i=0;i<500;i++){const g=Math.round((1+rnd()*999)*100)/100; if(!near(L.ozToG(L.gToOz(g)),g,1e-9)){ck('oz roundtrip',false,g);break;} const c=Math.round(rnd()*100*10)/10; if(!near(L.fToC(L.cToF(c)),c,1e-9)){ck('temp roundtrip',false,c);break;}}
ck('unit roundtrip g/oz and C/F',true);
ck('known conversions',near(L.cToF(100),212,1e-9)&&near(L.cToF(0),32,1e-9)&&near(L.gToOz(28.349523125),1,1e-9));
// ---- formatting
ck('formatTime',L.formatTime(0)==='00:00'&&L.formatTime(59)==='00:59'&&L.formatTime(61)==='01:01'&&L.formatTime(3600)==='1:00:00'&&L.formatTime(43200)==='12:00:00',[L.formatTime(0),L.formatTime(59),L.formatTime(61),L.formatTime(3600),L.formatTime(43200)]);
ck('formatNumber no float noise',L.formatNumber(0.1+0.2)==='0.3'&&L.formatNumber(15)==='15'&&L.formatNumber(112.50000001)==='112.5',[L.formatNumber(0.1+0.2),L.formatNumber(15),L.formatNumber(112.50000001)]);
// ---- timer engine with a fake clock, every built-in recipe, both modes
bi.forEach(r=>{
  [true,false].forEach(auto=>{
    let t=1e12; const e=L.createTimerEngine(r.steps,{now:()=>t,isAutoAdvance:()=>auto});
    const total=r.steps.reduce((a,s)=>a+s.duration*1000,0);
    ck(`engine total ${r.id}`,e.timeline.total===total,[e.timeline.total,total]);
    e.start(); let ev={step:0,stepEnd:0,complete:0}, lastIdx=0, ok=true, why='', guard=0;
    while(e.status!=='complete'&&guard++<200000){
      t+= rnd()<0.01 ? 60000+rnd()*600000 : 50+rnd()*3000;
      const s=e.update(); s.events.forEach(x=>ev[x]++);
      if(s.index<lastIdx){ok=false;why='index went backwards';}
      lastIdx=s.index;
      if(s.stepElapsedMs<0||s.stepElapsedMs>s.stepDurationMs+1){ok=false;why='stepElapsed out of range '+s.stepElapsedMs;}
      if(!auto&&s.waiting&&e.status==='running'){ // manual: tapping skip moves on, time stays frozen meanwhile
        const frozen=s.overallMs; t+=3600000; const s2=e.update(); if(s2.overallMs>frozen+1){ok=false;why='manual wait not frozen';} if(s2.events.includes('stepEnd')){ok=false;why='duplicate stepEnd';}
        e.skip().events.forEach(x=>ev[x]++);
      }
    }
    ck(`engine run ${r.id} ${auto?'auto':'manual'} completes, ordered, in-range`,ok&&e.status==='complete',why||e.status);
    ck(`engine ${r.id} ${auto?'auto':'manual'} exactly one complete`,ev.complete===1,JSON.stringify(ev));
    if(!auto) ck(`engine ${r.id} manual stepEnd per step`,ev.stepEnd>=r.steps.length-1,JSON.stringify(ev));
    const fin=e.update(); ck(`engine ${r.id} ${auto?'auto':'manual'} final overall = total`,fin.overallMs===total,fin.overallMs);
  });
});
// pause/resume/skip/reset semantics
(()=>{ const r=bi[0]; let t=5e11; const e=L.createTimerEngine(r.steps,{now:()=>t,isAutoAdvance:()=>true});
  ck('idle before start',e.update().status==='idle');
  e.skip(); ck('skip while idle is a no-op',e.status==='idle');
  e.start(); t+=10000; e.pause(); const p1=e.update().overallMs; t+=999999; const p2=e.update().overallMs;
  ck('pause freezes elapsed',p1===p2&&p1===10000,[p1,p2]);
  e.resume(); t+=5000; ck('resume continues from paused time',e.update().overallMs===15000,e.update().overallMs);
  e.reset(); const s=e.update(); ck('reset returns to idle at zero',s.status==='idle'&&s.overallMs===0&&s.index===0);
  e.start(); for(let i=0;i<r.steps.length-1;i++) e.skip(); ck('skip x(n-1) reaches last step',e.update().index===r.steps.length-1);
  const ev=e.skip().events; ck('skip on last step completes',ev.includes('complete')&&e.status==='complete',ev);
  e.start(); ck('start after complete does not restart silently',e.status==='complete'); })();
// ---- parseRecipeDraft
const draft={name:'  My Cup  ',method:'V60 / Pour Over',dose:'20',water:'320',ratio:'16',temp:'93',grind:'Medium',estimate:'1:30',steps:[{name:'Bloom',duration:'30',target:'60',instruction:'Pour {target}'},{name:'Pour',duration:'60',target:'320',instruction:''}]};
const pr=L.parseRecipeDraft(draft,'metric'); ck('draft parses (metric)',pr.errors.length===0&&pr.recipe&&pr.recipe.name==='My Cup'&&pr.recipe.water===320,JSON.stringify(pr.errors));
const imp=L.parseRecipeDraft({...draft,dose:String(L.round(L.gToOz(20),2)),water:String(L.round(L.gToOz(320),2)),temp:String(L.round(L.cToF(93),1)),steps:draft.steps.map(s=>({...s,target:String(L.round(L.gToOz(+s.target),2))}))},'imperial');
ck('draft parses (imperial) back to ~grams',imp.errors.length===0&&near(imp.recipe.dose,20,0.2)&&near(imp.recipe.water,320,0.5)&&near(imp.recipe.temp,93,0.1),JSON.stringify(imp.errors)+JSON.stringify(imp.recipe&&[imp.recipe.dose,imp.recipe.water,imp.recipe.temp]));
// ---- sanitizeStored resilience
const junk=[null,undefined,5,'x',[],{},{settings:'x'},{settings:{language:'fr',theme:7,units:{}}},{userRecipes:{}},{userRecipes:[null,5,'x',[],{steps:'x'}]},{favorites:'x',recent:5},{favorites:[1,{},null,'nope'],recent:['v60-classic','v60-classic','zzz']},{version:99999},{userRecipes:Array.from({length:5000},(_,i)=>({name:'n'+i}))}];
let thrown=[]; junk.forEach((j,i)=>{try{const o=L.sanitizeStored(j,bi.map(r=>r.id)); if(!o||!o.data||!Array.isArray(o.data.userRecipes)||!Array.isArray(o.data.favorites)) thrown.push(['shape',i]);}catch(e){thrown.push([i,String(e)]);}});
ck('sanitizeStored never throws on junk (14 inputs)',thrown.length===0,JSON.stringify(thrown));
const o2=L.sanitizeStored({favorites:['v60-classic','ghost','v60-classic'],recent:['espresso-starter','ghost']},bi.map(r=>r.id)).data; ck('favorites/recent dedupe + drop unknown ids',JSON.stringify(o2.favorites)==='["v60-classic"]'&&JSON.stringify(o2.recent)==='["espresso-starter"]',JSON.stringify([o2.favorites,o2.recent]));
return R;}"""
with sync_playwright() as p:
    b=p.chromium.launch(); pg=b.new_page(); errs=[]
    pg.on('pageerror',lambda e:errs.append(str(e))); pg.on('console',lambda m:m.type=='error' and errs.append(m.text))
    pg.goto(URL); pg.wait_for_timeout(400)
    R=pg.evaluate(JS); b.close()
fails=[r for r in R if not r[1]]
print(f'LOGIC: {len(R)-len(fails)}/{len(R)} passed; console errors: {errs or "none"}')
for n,_,d in fails: print('  FAIL',n,'|',d[:300])
sys.exit(1 if fails else 0)
