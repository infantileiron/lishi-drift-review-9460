import csv,io
from fastapi import HTTPException
from src.models.entities import Report
from src.config.settings import ARTIFACT_DIR
from src.utils import repository as repo
from src.utils.identity import new_id,now

def safe_cell(value):return "'"+value if isinstance(value,str) and value.lstrip().startswith(('=','+','-','@')) else value
def list_reports():return repo.all_rows('reports')
def create(data):
 run,review=repo.get('runs',data.run_id),repo.get('reviews',data.review_id)
 if review['status']!='approved' or review['run_id']!=run['id'] or run['status']!='completed':raise ValueError('报告必须引用该运行已通过的复核')
 report=repo.put('reports',Report(new_id('rpt'),data.run_id,data.review_id,data.title,now()));ARTIFACT_DIR.mkdir(parents=True,exist_ok=True);(ARTIFACT_DIR/(report['id']+'.csv')).write_text(download(report['id']),encoding='utf-8');return report
def segment_block(segmentation):
 """分段核对：逐段范围、均值与代价，以及样本数与总代价。未启用/失败时为空块。"""
 rows=[]
 if segmentation.get('enabled') and segmentation.get('segments'):
  rows.append(['segmentation_enabled','min_segment_length','change_penalty','change_count','sample_count','rss_total','penalty_total','total_cost'])
  rows.append([True,segmentation['min_segment_length'],segmentation['change_penalty'],segmentation['change_count'],segmentation['sample_count'],segmentation['rss_total'],segmentation['penalty_total'],segmentation['total_cost']])
  rows.append([]);rows.append(['segment_index','sequence_start','sequence_end','sample_count','mean_mm','rss','penalty_applied'])
  for s in segmentation['segments']:rows.append([s['index'],s['sequence_start'],s['sequence_end'],s['sample_count'],s['mean'],s['rss'],segmentation['change_penalty'] if s['index']>1 else 0.0])
  rows.append([]);rows.append(['check_segment_sample_count_sum','monitoring_sample_count','check_rss_and_penalty_sum'])
  rows.append([sum(s['sample_count'] for s in segmentation['segments']),segmentation['sample_count'],segmentation['rss_total']+segmentation['penalty_total']])
  return rows
 rows.append(['segmentation_enabled',segmentation.get('enabled'),segmentation.get('note') if segmentation.get('enabled') else '方案未启用分段，未产生分段结果',segmentation.get('error') or ''])
 return rows
def download(id):
 report=repo.get('reports',id);run=repo.get('runs',report['run_id']);r=run['result']
 if repo.get('reviews',report['review_id'])['status']!='approved':raise HTTPException(403,'复核未通过')
 out=io.StringIO();w=csv.writer(out);c=r['capability']
 w.writerow(['report','machine','baseline_mean','baseline_sigma_ddof1','cp','cpk','outside_count','sample_count','outside_rate','capability_assumptions_allowed','checksum'])
 w.writerow([safe_cell(report['title']),safe_cell(r['machine']),r['baseline']['mean'],r['baseline']['sigma'],c['cp'],c['cpk'],c['outside_count'],c['sample_count'],c['outside_rate'],r['capability_interpretation_allowed'],r['checksum']])
 w.writerow([]);w.writerow(['sample_id','sequence','value_mm','ewma_mm','center','lcl','ucl','lsl','usl','out_of_control','out_of_spec'])
 for p in r['series']:w.writerow([safe_cell(p['sample_id']),p['sequence'],p['value'],p['ewma'],p['center'],p['lcl'],p['ucl'],c['lsl'],c['usl'],p['out_of_control'],p['out_of_spec']])
 w.writerow([])
 for row in segment_block(r.get('segmentation') or {}):w.writerow([safe_cell(cell) for cell in row])
 return '\ufeff'+out.getvalue()
