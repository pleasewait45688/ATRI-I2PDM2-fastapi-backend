__version__ = "0.0.1"


from .models import YOLOv11Detector, QualityInspection
from .utils import PieChart
__all__ = (
    "__version__",
    "YOLOv11Detector",
    "QualityInspection",
    "PieChart"
)
