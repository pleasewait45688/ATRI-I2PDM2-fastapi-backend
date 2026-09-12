import torch.nn as nn
import torch
from torchvision import models
import json
import cv2
import numpy as np
from torchvision import transforms
import torch.nn.functional as F
import math
from PIL import Image


# ===== Otsu 面積特徵相關常量和函數 =====
IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]

USE_LARGEST_COMPONENT = True
AUTO_INVERT = True
DO_MORPH = True
USE_LOG1P = True  # 使用 log1p(area) 進行面積特徵轉換


def otsu_area_absolute(img_bgr: np.ndarray) -> int:
    """
    使用 Otsu 閾值計算物體面積（絕對像素數）
    
    Args:
        img_bgr: BGR 格式的圖像
        
    Returns:
        int: 物體的面積（像素數）
    """
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    gray_blur = cv2.GaussianBlur(gray, (5, 5), 0)

    _, otsu = cv2.threshold(gray_blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    if AUTO_INVERT and (otsu == 255).mean() > 0.5:
        otsu = cv2.bitwise_not(otsu)

    if DO_MORPH:
        k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        otsu = cv2.morphologyEx(otsu, cv2.MORPH_OPEN, k, iterations=1)
        otsu = cv2.morphologyEx(otsu, cv2.MORPH_CLOSE, k, iterations=1)

    if USE_LARGEST_COMPONENT:
        num, labels, stats, _ = cv2.connectedComponentsWithStats(otsu, connectivity=8)
        if num <= 1:
            return 0
        comp_areas = stats[1:, cv2.CC_STAT_AREA]
        kmax = 1 + int(np.argmax(comp_areas))
        return int(stats[kmax, cv2.CC_STAT_AREA])
    else:
        return int((otsu == 255).sum())


def area_to_feature(area: int) -> float:
    """
    將面積轉換為特徵值
    
    Args:
        area: 物體面積
        
    Returns:
        float: 特徵值
    """
    if area <= 0:
        area = 1
    if USE_LOG1P:
        return float(math.log1p(area))
    else:
        return float(area)


class ResizeWithOpenCV:
    """
    使用 OpenCV 進行圖像縮放（與訓練時一致）
    """
    def __init__(self, size: int):
        self.size = size

    def __call__(self, img_pil: Image.Image) -> Image.Image:
        img = np.array(img_pil)
        img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        img = cv2.resize(img, (self.size, self.size), interpolation=cv2.INTER_LANCZOS4)
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        return Image.fromarray(img)


class ResNet18WithSize(nn.Module):
    """
    ResNet18 + Size Feature 模型
    將 ResNet18 的 512D 特徵與 1D size 特徵拼接後進行分類
    """
    def __init__(self, num_classes: int, pretrained: bool = False):
        super().__init__()
        base = models.resnet18(pretrained=pretrained)
        self.backbone = nn.Sequential(*list(base.children())[:-1])  # (B,512,1,1)
        self.fc = nn.Linear(512 + 1, num_classes)

    def forward(self, x_img, x_size):
        feat = self.backbone(x_img).flatten(1)  # (B,512)
        x = torch.cat([feat, x_size], dim=1)    # (B,513)
        return self.fc(x)


class ResNetClassifier(nn.Module):
    """
    ResNet18 + Otsu Size Feature 分類器
    結合圖像特徵和物體面積特徵進行分類
    """
    def __init__(self,
                 model_path: str,
                 label_path: str = "labels.json",
                 img_size: int = 128,
                 device: str = "cuda"):
        super(ResNetClassifier, self).__init__()
        
        # 強制確定性計算（針對不同 GPU 架構）
        if torch.cuda.is_available():
            # 禁用 TF32 以確保跨 GPU 架構的數值一致性
            torch.backends.cuda.matmul.allow_tf32 = False
            torch.backends.cudnn.allow_tf32 = False
        
        self.device = torch.device(device if torch.cuda.is_available() else "cpu")
        
        # Load label mapping
        with open(label_path, 'r') as f:
            label_dict = json.load(f)
        self.idx2cls = {v: k for k, v in label_dict.items()}
        num_classes = len(self.idx2cls)

        # 初始化 ResNet18 + Size Feature 模型（512+1D）
        self.model = ResNet18WithSize(num_classes=num_classes, pretrained=False)
        
        # Load trained weights
        state = torch.load(model_path, map_location="cpu")
        self.model.load_state_dict(state)
        self.model.to(self.device)
        self.model.eval()

        # Preprocessing（與訓練時一致：OpenCV Resize + ToTensor + ImageNet Normalize）
        self.preprocess = transforms.Compose([
            transforms.ToPILImage(),
            ResizeWithOpenCV(img_size),
            transforms.ToTensor(),
            transforms.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD),
        ])

    @torch.no_grad()
    def predict(self, bgr_crop):
        """
        預測單個裁剪圖像的類別
        
        Args:
            bgr_crop: BGR格式的圖像 (numpy array)
            
        Returns:
            tuple: (predicted_label, confidence)
        """
        # 1. 計算 size feature（從原始 crop 計算，不要用 resize 後的）
        area = otsu_area_absolute(bgr_crop)
        size_feat = area_to_feature(area)
        x_size = torch.tensor([[size_feat]], dtype=torch.float32, device=self.device)  # (1,1)

        # 2. 處理圖像特徵
        rgb = cv2.cvtColor(bgr_crop, cv2.COLOR_BGR2RGB)
        x_img = self.preprocess(rgb).unsqueeze(0).to(self.device)  # (1,3,128,128)

        # 3. Forward
        logits = self.model(x_img, x_size)
        probs = torch.softmax(logits, dim=1)[0]
        idx = int(torch.argmax(probs))
        return self.idx2cls[idx], float(probs[idx])
    
    @torch.no_grad()
    def predict_with_probs(self, bgr_crop):
        """
        預測並返回所有類別的機率分布
        
        Args:
            bgr_crop: BGR格式的圖像 (numpy array)
            
        Returns:
            tuple: (predicted_label, confidence, probability_dict)
        """
        # 1. 計算 size feature
        area = otsu_area_absolute(bgr_crop)
        size_feat = area_to_feature(area)
        x_size = torch.tensor([[size_feat]], dtype=torch.float32, device=self.device)

        # 2. 處理圖像特徵
        rgb = cv2.cvtColor(bgr_crop, cv2.COLOR_BGR2RGB)
        x_img = self.preprocess(rgb).unsqueeze(0).to(self.device)

        # 3. Forward
        logits = self.model(x_img, x_size)
        probs = F.softmax(logits, dim=1)[0].detach().cpu().numpy()
        idx = int(probs.argmax())
        label = self.idx2cls[idx]
        dist = {self.idx2cls[i]: float(probs[i]) for i in range(len(probs))}
        return label, float(probs[idx]), dist
