import logging
from pathlib import Path
from collections import Counter
import torch
import numpy as np
import cv2
from ..nn.modules import ResNetClassifier
import gc
from sahi import AutoDetectionModel
from sahi.predict import get_sliced_prediction
from sahi.utils.cv import visualize_object_predictions

logger = logging.getLogger(__name__)


def square_crop_from_box(img: np.ndarray, 
                         x1: int, y1: int, x2: int, y2: int,
                         extra_ratio: float = 0.0) -> np.ndarray:
    """
    給一個矩形框 (x1, y1, x2, y2)，
    以此框的中心為中心，往外擴成正方形，再從 img 上裁切。
    extra_ratio: 額外再放大多少比例，例如 0.2 表示邊長再乘上 1.2。
    回傳：正方形的 crop（可能會因為靠邊界而稍微縮小）。
    """
    h_img, w_img = img.shape[:2]

    box_w = x2 - x1
    box_h = y2 - y1

    # 以較大邊為基準，決定正方形邊長
    side = int(max(box_w, box_h) * (1.0 + extra_ratio))
    if side <= 0:
        return img[0:0, 0:0]

    # 正方形中心 = 原本 bbox 的中心
    cx = (x1 + x2) // 2
    cy = (y1 + y2) // 2

    # 初步計算正方形座標
    x1_sq = cx - side // 2
    y1_sq = cy - side // 2
    x2_sq = x1_sq + side
    y2_sq = y1_sq + side

    # 先 clamp 到圖片範圍內
    if x1_sq < 0:
        x2_sq -= x1_sq      # 把右邊往左補回來
        x1_sq = 0
    if y1_sq < 0:
        y2_sq -= y1_sq
        y1_sq = 0
    if x2_sq > w_img:
        shift = x2_sq - w_img
        x1_sq = max(0, x1_sq - shift)
        x2_sq = w_img
    if y2_sq > h_img:
        shift = y2_sq - h_img
        y1_sq = max(0, y1_sq - shift)
        y2_sq = h_img

    # 最後再保證是正方形（防止邊界 clamp 出現 1~2 pixel 誤差）
    side_final = min(x2_sq - x1_sq, y2_sq - y1_sq)
    x2_sq = x1_sq + side_final
    y2_sq = y1_sq + side_final

    if side_final <= 0:
        return img[0:0, 0:0]

    crop = img[y1_sq:y2_sq, x1_sq:x2_sq]
    return crop


class YOLOv11Detector:
    """YOLOv11 (via SAHI) + optional ResNet two-stage classifier"""

    def __init__(
        self,
        yolo_model: str | Path,
        classifier_model_path: str | Path = None,
        classifier_label_path: str | Path = None,
    ):

        # 強制確定性計算（針對不同 GPU 架構）
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False
        
        # 禁用 TF32（Ampere/Ada 架構特有，可能導致精度差異）
        # A6000 和 4090 預設會使用 TF32，這可能導致不同結果
        torch.backends.cuda.matmul.allow_tf32 = False
        torch.backends.cudnn.allow_tf32 = False
        
        logger.info("Initializing YOLOv11Detector with seed=42 and deterministic mode (TF32 disabled)...")
        if torch.cuda.is_available():
            logger.info(f"GPU Device: {torch.cuda.get_device_name(0)}")

        self.TARGET_WIDTH = 3024
        self.TARGET_HEIGHT = 4032

        try:
            self.detection_model = AutoDetectionModel.from_pretrained(
                model_type="yolov8",
                model_path=str(yolo_model),
                confidence_threshold=0.2,
                device="cuda" if torch.cuda.is_available() else "cpu"
            )
            logger.info("Detection model initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize detection model: {e}")
            raise

        # Initialize ResNet Classifier (two-stage classification)
        self.classifier = None
        if classifier_model_path and classifier_label_path:
            try:
                self.classifier = ResNetClassifier(
                    model_path=str(classifier_model_path),
                    label_path=str(classifier_label_path),
                    device="cuda" if torch.cuda.is_available() else "cpu"
                )
                logger.info("ResNet classifier initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize ResNet classifier: {e}")
                logger.warning("Continuing without two-stage classification")
                self.classifier = None

    def detect(self, image_path: str | Path):
        try:
            # 讀取原始圖片 (使用 cv2.imread，和本地一致)
            original_image = cv2.imread(str(image_path))
            if original_image is None:
                raise ValueError(f"無法讀取圖片: {image_path}")
            
            # 執行插值處理 (BGR → BGR)
            processed_image = self.__interpolation(original_image)
            
            # 執行 HSV 處理 (BGR → BGR)
            hsv_processed = self.__hsv_correction(processed_image)
            
            # 轉換為 RGB 供 SAHI 使用
            hsv_processed_rgb = cv2.cvtColor(hsv_processed, cv2.COLOR_BGR2RGB)
            prediction_result = get_sliced_prediction(
                image=hsv_processed_rgb,  # SAHI 接受 RGB 格式
                detection_model=self.detection_model,
                slice_height=640,
                slice_width=640,
                overlap_height_ratio=0.2,
                overlap_width_ratio=0.2,
            )
            
            # 如果有 ResNet 分類器，執行二階段分類
            if self.classifier is not None:
                # 篩除過小的框
                filtered_list = []
                for p in prediction_result.object_prediction_list:
                    x1, y1, x2, y2 = map(int, p.bbox.to_voc_bbox())
                    box_w = x2 - x1
                    box_h = y2 - y1
                    if box_w >= 10 and box_h >= 10:
                        filtered_list.append(p)
                prediction_result.object_prediction_list = filtered_list

                # 對每個檢測框進行 ResNet 重新分類
                for idx, pred in enumerate(prediction_result.object_prediction_list):
                    # 取得框座標並界限裁切
                    x1, y1, x2, y2 = map(int, pred.bbox.to_voc_bbox())
                    h, w = hsv_processed.shape[:2]

                    # Padding 20% 邊界
                    pad_ratio = 0.2
                    box_w = x2 - x1
                    box_h = y2 - y1
                    pad_w = int(box_w * pad_ratio)
                    pad_h = int(box_h * pad_ratio)

                    # 加上 padding 並限制在圖像邊界內
                    x1_pad = max(0, x1 - pad_w)
                    y1_pad = max(0, y1 - pad_h)
                    x2_pad = min(w, x2 + pad_w)
                    y2_pad = min(h, y2 + pad_h)

                    # 使用正方形裁切（從 padding 後的矩形框擴展成正方形）
                    crop = square_crop_from_box(
                        hsv_processed, 
                        x1_pad, y1_pad, x2_pad, y2_pad,
                        extra_ratio=0.0
                    )
                    if crop.size == 0:
                        continue

                    # ResNet 重新分類（直接傳 crop，內部會自動 resize 和計算 Otsu）
                    refined_label, prob, dist = self.classifier.predict_with_probs(crop)
                    
                    # 特殊的後處理邏輯：dust 是 other 的 hard class，統一轉為 other
                    if refined_label == "dust":
                        refined_label = "other"
                        prob = dist.get("other", prob)  # 使用 other 的機率

                    # 更新 prediction 物件的名稱與 id
                    pred.category.name = refined_label
                    # 用 idx2cls 反查 id
                    cls_id = [k for k, v in self.classifier.idx2cls.items() if v == refined_label][0]
                    pred.category.id = cls_id
                    pred.score.value = float(prob)

                # 使用 ResNet 結果統計
                category_counts = Counter(p.category.name for p in prediction_result.object_prediction_list)
                
                # 轉換為最終格式 (ResNet labels -> 中文名稱)
                resnet_name_mapping = {
                    "thrip": "薊馬",
                    "gnat": "蕈蠅",
                    "whitefly": "粉蝨", 
                    "other": "其他",
                    "dust": "其他"  # dust 也對應到「其他」
                }
                
                class_name_counts = {}
                for resnet_name, count in category_counts.items():
                    if resnet_name in resnet_name_mapping:
                        mapped_name = resnet_name_mapping[resnet_name]
                        class_name_counts[mapped_name] = count
                
            else:
                # 沒有 ResNet 分類器，YOLO 只能檢測到物體但無法分類
                # 所有檢測到的物體都歸類為 "未知物體"
                total_objects = len(prediction_result.object_prediction_list)
                class_name_counts = {
                    "未知物體": total_objects
                } if total_objects > 0 else {}
            
            # 視覺化 (轉換為 RGB 格式)
            visualization_result = visualize_object_predictions(
                image=cv2.cvtColor(processed_image, cv2.COLOR_BGR2RGB),
                object_prediction_list=prediction_result.object_prediction_list,
                rect_th=2,
                text_size=0.3,
                text_th=1,
                hide_labels=True,
                hide_conf=True
            )
            
            return class_name_counts, visualization_result["image"]
            
        except Exception as e:
            logger.error(f"Error during detection: {e}")
            raise

        finally:
            # 在這裡清理記憶體
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            gc.collect()
    
    def __interpolation(self, image):
        """新的插值處理方法"""
        height, width = image.shape[:2]
        scale_w = self.TARGET_WIDTH / width
        scale_h = self.TARGET_HEIGHT / height
        scale = min(scale_w, scale_h)
        
        new_width = int(width * scale)
        new_height = int(height * scale)
        
        result = np.zeros((self.TARGET_HEIGHT, self.TARGET_WIDTH, 3), dtype=np.uint8)
        resized = cv2.resize(image, (new_width, new_height), 
                           interpolation=cv2.INTER_LANCZOS4)
        
        x_offset = (self.TARGET_WIDTH - new_width) // 2
        y_offset = (self.TARGET_HEIGHT - new_height) // 2
        
        result[y_offset:y_offset+new_height, x_offset:x_offset+new_width] = resized
        
        return result

    def __hsv_correction(self, image, kernel_size=151):
        """新的 HSV 校正方法"""
        hsv_image = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        h, s, v = cv2.split(hsv_image)
        blurred_v = cv2.GaussianBlur(v, (kernel_size, kernel_size), 0)
        corrected_v = cv2.divide(v, blurred_v, scale=255)
        corrected_hsv = cv2.merge([h, s, corrected_v])
        return cv2.cvtColor(corrected_hsv, cv2.COLOR_HSV2BGR)
