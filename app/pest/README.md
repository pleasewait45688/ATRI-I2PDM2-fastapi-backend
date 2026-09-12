# I2PDM2-models
yolov11

Inference code for ML workers.

## Requirements 
* pytorch (>=12.1)
* opencv(4.8) with cuda
* scikit-learn
* cython
* pytest



## Development

For project structure, please refer to [ultralytics](https://github.com/ultralytics/ultralytics).

## How to use

```python
from i2pdm2 import YOLOv4SRGAN

stage_lists= [["others", "whitefly"],
            ["cranefly",
            "fly",
            "gnat",
            "midge",
            "mosquito",
            "mothfly",
            "thrips",
            "unknown"]]
box_colors = [
        (255, 0, 0),  # Color for class index 0
        (0, 255, 0),  # Color for class index 1
        (0, 0, 255),  # Color for class index 2
        (255, 255, 0),  # Color for class index 3
        (255, 0, 255),  # Color for class index 4
        (0, 255, 255),  # Color for class index 5
        (128, 128, 0),  # Color for class index 6
        (128, 0, 128),  # Color for class index 7
        (0, 128, 128),  # Color for class index 8
    ]

class_indices= {
            "cranefly": 0,
            "fly": 1,
            "gnat": 2,
            "midge": 3,
            "mosquito": 4,
            "mothfly": 5,
            "thrips": 6,
            "whitefly": 7,
            "unknown": 8,
        }

model = YOLOv4SRGAN(
        yolo_model="/path/to/yolo_model",
        stage2_model="/path/to/stage2_model",
        stage3_model="/path/to/stage3_model",
        generator_model="/path/to/generator_model",
        stage_lists=stage_lists,
        config="/path/to/config")

result, image = model.detect(
        "/path/to/test/image", box_colors, class_indices
    )

```

Check out [unit test folder](./tests/) for complete usage.

### Download Pretrained Models
```bash
bash ./download.sh
```
