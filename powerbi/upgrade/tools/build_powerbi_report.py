"""Create three native PBIR NHS analysis pages with separate filtering domains.

Uses Microsoft's scaffold shell and native visual contracts. No screenshot is
presented as a rendered Power BI report until the native runtime is checked.
"""
from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'powerbi/upgrade'
if not OUT.exists():OUT=ROOT
REPORT=OUT/'NHS_Analytics.Report'
DEF=REPORT/'definition'
VSCHEMA='https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.9.0/schema.json'
PSCHEMA='https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/2.1.0/schema.json'
BLUE='#1764A0'; INK='#17324D'; MUTED='#536579'; LIGHT='#E9F1F8'


def write(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(obj,indent=2,ensure_ascii=False)+'\n')


def uid(s): return hashlib.sha256(s.encode()).hexdigest()[:20]
def lit(v):
    val='true' if v is True else 'false' if v is False else str(v)+'D' if isinstance(v,(int,float)) else "'"+v.replace("'","''")+"'"
    return {'expr':{'Literal':{'Value':val}}}
def color(v): return {'solid':{'color':lit(v)}}
def props(p,selector=False):
    d={'properties':p}
    if selector: d['selector']={'id':'default'}
    return [d]
def field(t,c,measure=False):
    return {'Measure' if measure else 'Column':{'Expression':{'SourceRef':{'Entity':t}},'Property':c}}
def projection(t,c,measure=False):
    return {'field':field(t,c,measure),'queryRef':t+'.'+c,'nativeQueryRef':c}
def ms(name): return projection('Summary',name,True)
def col(t,c): return projection(t,c)
def role(items): return {'projections':items}
def chrome(title=None):
    d={'background':props({'show':lit(False)}),'border':props({'show':lit(False)}),
       'padding':props({p:lit(8) for p in ['top','bottom','left','right']})}
    if title: d['title']=props({'show':lit(True),'text':lit(title),'fontSize':lit(12),'fontColor':color(INK)})
    return d


class Page:
    def __init__(self,name,title,subtitle,hidden=False):
        self.id=uid(name);self.count=0;self.visuals=[]
        self.path=DEF/'pages'/self.id
        self.page={'$schema':PSCHEMA,'name':self.id,'displayName':title,
          'displayOption':'FitToPage','height':900,'width':1440}
        if hidden:self.page['visibility']='HiddenInViewMode'
        self.text('title',title,24,18,1392,48,28,INK)
        self.text('subtitle',subtitle,24,67,1392,30,13,MUTED)

    def add(self,key,visual,x,y,w,h):
        self.count+=1;n=uid(self.id+key)
        v={'$schema':VSCHEMA,'name':n,'position':{'x':x,'y':y,'z':self.count*1000,
          'tabOrder':self.count*1000,'width':w,'height':h},'visual':visual}
        write(self.path/'visuals'/n/'visual.json',v);self.visuals.append(v)
        return v

    def text(self,key,text,x,y,w,h,size=13,ink=MUTED):
        paras=[{'textRuns':[{'value':line,'textStyle':{'fontFamily':'Segoe UI','fontSize':str(size)+'px','color':ink}}],
          'horizontalTextAlignment':'left'} for line in text.split('\n')]
        vco=chrome();vco['padding']=props({p:lit(0) for p in ['top','bottom','left','right']})
        return self.add(key,{'visualType':'textbox','objects':{'general':props({'paragraphs':paras})},
          'visualContainerObjects':vco},x,y,w,h)

    def slicer(self,key,t,c,x,y,w,mode="Dropdown"):
        return self.add(key,{'visualType':'slicer','query':{'queryState':{'Values':role([col(t,c)])}},
          'objects':{'data':props({'mode':lit(mode)}),'header':props({'show':lit(True),'text':lit(c)})},
          'visualContainerObjects':chrome()},x,y,w,80)

    def cards(self,key,measures,y=202):
        objects={
          'value':props({'fontSize':lit(30),'fontColor':color(INK),'labelDisplayUnits':lit(1)},True),
          'label':props({'fontSize':lit(11),'fontColor':color(MUTED)},True),
          'padding':props({'paddingUniform':lit(8)},True),
          'layout':props({'orientation':lit(0),'rowCount':lit(1),'columnCount':lit(len(measures)),
            'autoGrid':lit(False),'paddingUniform':lit(0)},True)}
        return self.add(key,{'visualType':'cardVisual','query':{'queryState':{'Data':role([ms(m) for m in measures])}},
          'objects':objects,'visualContainerObjects':chrome()},24,y,1392,104)

    def chart(self,key,kind,t,c,measure,x,y,w,h,title,ascending=False,tooltips=None):
        q={'Category':role([col(t,c)]),'Y':role([ms(m) for m in (measure if isinstance(measure,list) else [measure])])}
        if tooltips:q['Tooltips']=role([ms(m) for m in tooltips])
        sortfield=field(t,c) if ascending else field('Summary',measure,True)
        return self.add(key,{'visualType':kind,'query':{'queryState':q,'sortDefinition':{
          'sort':[{'field':sortfield,'direction':'Ascending' if ascending else 'Descending'}]}},
          'objects':{'dataPoint':props({'defaultColor':color(BLUE)}),
            'legend':props({'show':lit(isinstance(measure,list))})},'visualContainerObjects':chrome(title)},x,y,w,h)

    def table(self,key,fields,x,y,w,h,title):
        return self.add(key,{'visualType':'tableEx','query':{'queryState':{'Values':role(fields)}},
          'objects':{'columnHeaders':props({'autoSizeColumnWidth':lit(True),'columnAdjustment':lit('growToFit'),
            'fontSize':lit(10),'backColor':color(LIGHT),'fontColor':color(INK)}),
            'values':props({'fontSize':lit(10),'backColorPrimary':color('#FFFFFF'),'backColorSecondary':color('#F5F8FB')}),
            'total':props({'totals':lit(False)})},'visualContainerObjects':chrome(title)},x,y,w,h)

    def footer(self):
        self.text('footer','NHS England public aggregate statistics | Static snapshot through Aug 2026 demand / Jun 2026 beds | No patient records',24,853,1392,26,11)

    def save(self):
        write(self.path/'page.json',self.page)
        for v in self.visuals:write(self.path/'visuals'/v['name']/'visual.json',v)


def main():
    import pandas as pd
    summary=pd.read_csv(ROOT/'powerbi/data/admissions_forecast_summary.csv').iloc[0]
    metadata=json.loads((DEF/'pages/pages.json').read_text())
    # Only the empty scaffold page can be removed here.
    for n in metadata['pageOrder']:
        p=DEF/'pages'/n
        if p.exists() and not (p/'visuals').exists():
            (p/'page.json').unlink();p.rmdir()
    pages=[]
    demand=Page('nhs-demand','Emergency demand','England monthly totals. The date selector affects demand only. Counts total selected months; YoY compares matching prior-year months.')
    demand.slicer('months','DemandMonth','Month',24,102,680,'Between')
    demand.cards('demand-kpis',['Admissions','Admissions YoY Percent','Over 12 Hour Delays','Delays YoY Percent'])
    demand.chart('admissions','lineChart','DemandMonth','Month','Admissions',24,330,680,352,'Emergency admissions',True)
    demand.chart('delays','lineChart','DemandMonth','Month','Over 12 Hour Delays',728,330,688,352,'Waits over 12 hours after decision to admit',True)
    demand.text('interpretation','Full-snapshot finding: August 2026 admissions fell 1.6% year on year, while over-12-hour delay counts rose 25.2%.\nLower admission volume did not coincide with fewer long delays. These counts do not measure average waiting time.\nYoY cards stay blank if any selected month lacks its prior-year match.\nThe fixed finding above does not change with slicers; cards and charts do.',24,716,1392,118,14)
    demand.footer();demand.save();pages.append(demand)

    beds=Page('nhs-beds','Bed pressure and trust capacity','Separate populations: national quarter selection does not filter the fixed Apr-Jun 2026 trust snapshot; the trust selector does not filter national history.')
    beds.slicer('quarters','BedQuarter','Quarter end',24,102,680,'Between')
    beds.slicer('trust','DimTrust','Trust',728,102,688)
    beds.cards('occupancy',['Selected Quarter Occupancy','Bed Day Weighted Occupancy','Trust Snapshot Occupancy'])
    beds.chart('national','lineChart','BedQuarter','Quarter end','Selected Quarter Occupancy',24,330,680,352,'National quarterly occupancy | one ratio per quarter',True)
    beds.table('trusts',[col('DimTrust','Trust'),ms('Trust Available Beds'),ms('Trust Occupied Beds'),ms('Trust Snapshot Occupancy')],728,330,688,352,'Trust snapshot | selected providers only')
    beds.text('interpretation','Occupancy is occupied beds divided by available beds. The single-quarter card is blank for a multi-quarter selection.\nAcross selected complete quarters, use occupied bed-days / available bed-days; percentages are never added.\nLatest national quarter: 90.85% occupied, down 0.60 percentage points year on year. These series do not establish why delays changed.',24,716,1392,102,14)
    beds.footer();beds.save();pages.append(beds)

    forecast=Page('nhs-forecast','Forecast evaluation','Repeated one-month-ahead forecasts. The forest is refitted before each target month; parameters are unchanged. Select an evaluation-date range.')
    forecast.slicer('test-months','ForecastMonth','Month',24,102,680,'Between')
    forecast.cards('errors',['Seasonal MAE','Expanding Forest MAE','Fixed Fit Forest MAE','Evaluation Months'])
    forecast.chart('predictions','lineChart','ForecastMonth','Month',['Observed Admissions','Seasonal Forecast','Expanding Forest Forecast'],24,330,880,330,'Actual admissions and forecasts',True)
    forecast.chart('absolute-errors','clusteredColumnChart','ForecastMonth','Month',['Seasonal Absolute Error','Forest Absolute Error'],928,330,488,330,'Absolute error by month',True)
    forecast.table('origins',[col('Forecast','Month'),col('Forecast','Training through'),col('Forecast','Training rows')],24,680,680,150,'Auditable origins | training ends before each target')
    note=(f'Full 24-month test: seasonal MAE {summary.baseline_mae:,.0f}; expanding forest {summary.model_mae:,.0f}; fixed-fit forest {summary.fixed_fit_model_mae:,.0f}.\n'
          'The simpler baseline remains preferred for this period. Refit helps the forest, but does not beat the baseline.\n'
          'Observation-time backtest; publication delays are not simulated. This previously examined historical period is not a new prospective test.')
    forecast.text('interpretation',note,728,690,688,140,13)
    forecast.footer();forecast.save();pages.append(forecast)
    metadata['pageOrder']=[p.id for p in pages];metadata['activePageName']=demand.id
    write(DEF/'pages/pages.json',metadata)
    write(OUT/'verification/layout_manifest.json',{'pages':[{'name':p.page['displayName'],'id':p.id,'width':1440,'height':900,
      'visuals':[{'name':v['name'],'type':v['visual']['visualType'],**v['position']} for v in p.visuals]} for p in pages], 'native_render_verified':False})
    print(json.dumps({'pages':len(pages),'visuals':sum(len(p.visuals) for p in pages),'native_render_verified':False}))


if __name__=='__main__':main()

