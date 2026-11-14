from src.models.entities import ControlStudy
from src.utils import repository as repo
from src.utils.identity import new_id,now

def list_studies():return repo.all_rows('studies')
def create(data):
 baseline=repo.get('baselines',data.baseline_id)
 if data.lsl>=data.usl:raise ValueError('规格下限必须小于上限')
 if data.monitoring_start<=baseline['end']:raise ValueError('监控区间必须严格位于锁定基线之后，防止基线泄漏')
 if data.monitoring_start>data.monitoring_end:raise ValueError('监控起始序号不能大于结束序号')
 if data.segmentation_enabled:
  if data.min_segment_length<1:raise ValueError('最短段长至少为1次观测')
  if data.min_segment_length>5000:raise ValueError('最短段长不能超过5000次观测')
  if not 0<data.change_penalty<=1e6:raise ValueError('变点惩罚值必须为正值，且不超过1e6')
 return repo.put('studies',ControlStudy(new_id('study'),data.name,data.baseline_id,data.monitoring_start,data.monitoring_end,data.smoothing,data.control_width,data.lsl,data.usl,data.segmentation_enabled,data.min_segment_length,data.change_penalty,now()))
