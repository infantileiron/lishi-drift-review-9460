from dataclasses import dataclass,field
from typing import Any
@dataclass
class MeasurementDataset:
 id:str
 name:str
 source:str
 rows:list[dict]
 created_at:str=''
@dataclass
class BaselineWindow:
 id:str
 name:str
 dataset_id:str
 machine:str
 start:int
 end:int
 values:list[float]
 mean:float
 sigma:float
 created_at:str=''
@dataclass
class ControlStudy:
 id:str
 name:str
 baseline_id:str
 monitoring_start:int
 monitoring_end:int
 smoothing:float=.2
 control_width:float=3
 lsl:float=19.95
 usl:float=20.05
 segmentation_enabled:bool=False
 min_segment_length:int=5
 change_penalty:float=.001
 created_at:str=''
@dataclass
class ControlRun:
 id:str
 study_id:str
 status:str='queued'
 result:dict[str,Any]=field(default_factory=dict)
 error:str=''
 created_at:str=''
@dataclass
class DeviationReview:
 id:str
 run_id:str
 comment:str
 status:str='pending'
 reviewer:str=''
 created_at:str=''
@dataclass
class Report:
 id:str
 run_id:str
 review_id:str
 title:str
 created_at:str=''
