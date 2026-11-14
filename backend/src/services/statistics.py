import hashlib,json
from src.services.ewma import ewma_series
from src.services.capability import capability
from src.services.segmentation import segment_series,DEFAULT_MIN_SEGMENT_LENGTH,DEFAULT_CHANGE_PENALTY

def study_settings(study):
 return {'min_segment_length':study.get('min_segment_length',DEFAULT_MIN_SEGMENT_LENGTH),'change_penalty':study.get('change_penalty',DEFAULT_CHANGE_PENALTY),'enabled':bool(study.get('segmentation_enabled',False))}

def analyze(rows,baseline,study):
 monitoring=sorted([r for r in rows if r['machine']==baseline['machine'] and study['monitoring_start']<=r['sequence']<=study['monitoring_end']],key=lambda r:r['sequence'])
 series=ewma_series(monitoring,baseline['mean'],baseline['sigma'],study['smoothing'],study['control_width'])
 for row in series:row['out_of_spec']=row['value']<study['lsl'] or row['value']>study['usl']
 cap=capability([r['value'] for r in monitoring],study['lsl'],study['usl'],baseline['sigma'])
 alarms=sum(r['out_of_control'] for r in series)
 settings=study_settings(study)
 if not settings['enabled']:
  segmentation={'enabled':False,'min_segment_length':settings['min_segment_length'],'change_penalty':settings['change_penalty'],'note':'方案未启用分段，仅输出逐点信号','segments':[],'change_points':[],'change_count':0,'sample_count':len(monitoring),'rss_total':None,'penalty_total':None,'total_cost':None}
 elif not monitoring:
  segmentation={'enabled':True,'min_segment_length':settings['min_segment_length'],'change_penalty':settings['change_penalty'],'note':'监控区间没有观测，未进行分段','segments':[],'change_points':[],'change_count':0,'sample_count':0,'rss_total':None,'penalty_total':None,'total_cost':None}
 else:
  try:
   block=segment_series(monitoring,settings['min_segment_length'],settings['change_penalty'])
   segmentation={'enabled':True,'note':'按实测值分段：各段残差平方和加每个变点的惩罚值取全局最优；同代价先取变点更少、再取变点位置更靠前者','error':None,**block}
  except ValueError as exc:
   segmentation={'enabled':True,'min_segment_length':settings['min_segment_length'],'change_penalty':settings['change_penalty'],'note':'分段未能完成','error':str(exc),'segments':[],'change_points':[],'change_count':0,'sample_count':len(monitoring),'rss_total':None,'penalty_total':None,'total_cost':None}
 return {'series':series,'baseline':baseline,'study':study,'machine':baseline['machine'],'control_signals':alarms,'first_signal':next((r['sequence'] for r in series if r['out_of_control']),None),'capability':cap,'capability_interpretation_allowed':alarms==0,'segmentation':segmentation,'checksum':hashlib.sha256(json.dumps({'rows':rows,'baseline':baseline,'study':study},sort_keys=True).encode()).hexdigest(),'limitations':['数据为模拟单值尺寸，EWMA每次使用一个观测，不再除以sqrt(n)','基线均值和样本标准差ddof=1在整个监控区间固定，Z0=基线均值；t为监控区间第t个观测','控制界限随t变化，反映稳定过程的波动；规格界限是19.95/20.05mm等工程要求，两者不得混用','Cp使用固定基线sigma；Cpk使用监控均值和固定基线sigma，仅在过程稳定且近正态等假设下解释','存在EWMA信号时能力数值仅作描述诊断，不作能力合格结论；实测超规格率直接计数，不做正态尾概率替代','分段只聚合实测值与原观测序号，不插值、不改动EWMA序列；变点仅描述均值位置变化，不替代控制信号判据']}
