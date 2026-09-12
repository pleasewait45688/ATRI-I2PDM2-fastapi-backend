from transformers import CLIPProcessor, CLIPModel
import pickle
from pathlib import Path
import logging
from typing import Tuple, Dict
from PIL import Image
from sklearn.svm import SVC
import torch
import cv2
import numpy as np
from io import BytesIO

# Configure logging
# logging.basicConfig(
#     level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
# )
logger = logging.getLogger(__name__)


class QualityInspection:
    def __init__(self, svm_model_path: str | Path) -> None:
        """
        Initializes the QualityInspection class by loading the CLIP and SVM models.

        :param svm_model_path: Path to the pre-trained SVM model.
        """
        # self.model = None
        # self.processor = None
        # self.svm_model = None

        logger.info("Initializing QualityInspection...")
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        # Load CLIP model and processor
        try:
            logger.info("Loading CLIP model and processor...")
            self.model: CLIPModel = CLIPModel.from_pretrained(
                "openai/clip-vit-base-patch32"
            )
            # self.model.to(self.device)
            # self.model.eval()
            self.processor: CLIPProcessor = CLIPProcessor.from_pretrained(
                "openai/clip-vit-base-patch32"
            )

            logger.info("CLIP model and processor loaded successfully.")
        except Exception as e:
            logger.error("Failed to load CLIP model or processor: %s", e)
            raise RuntimeError("Error loading CLIP model or processor.") from e

        # Load SVM model
        try:
            logger.info("Loading SVM model from %s...", svm_model_path)
            with open(svm_model_path, "rb") as fr:
                self.svm_model: SVC = pickle.load(fr)
            self.__validate_svm_model()
            logger.info("SVM model loaded successfully.")
        except FileNotFoundError as e:
            logger.error("SVM model file not found: %s", e)
            raise FileNotFoundError("SVM model file not found.") from e
        except Exception as e:
            logger.error("Failed to load SVM model: %s", e)
            raise RuntimeError("Error loading SVM model.") from e

    def inspect_sticky_trap(
        self, image_path: str | Path
    ) -> Tuple[Dict[str, str], Image.Image]:
        """
        Determines whether the provided image is a sticky trap.

        :param image_path: Path to the image file to be inspected.
        :return: A tuple containing the inspection result and the processed image.
        """
        logger.info("Inspecting image: %s", image_path)

        # Load and preprocess the image
        try:
            image = Image.open(image_path)
            original_image = image.copy()
            logger.info("Image loaded successfully: %s", image_path)
        except Exception as e:
            print(f"image_path:{image_path}")
            logger.error("Failed to load image from path %s: %s", image_path, e)
            raise RuntimeError("Error loading image.") from e

        image.thumbnail((100, 100))
        logger.info("Image resized to 100x100 for processing.")

        # Extract features using CLIP model
        try:
            with torch.inference_mode():
                # image =  transforms.ToTensor()(image).unsqueeze(0).to("cuda")
                inputs = self.processor(images=image, return_tensors="pt")
                ## inputs = {k: v.to(self.device) for k, v in inputs.items()}
                image_embedding = (
                    self.model.get_image_features(**inputs).cpu().detach().numpy()
                )
                logger.info("Image features extracted successfully.")

        except Exception as e:
            # logger.error("Failed to make prediction: %s", e)
            # raise RuntimeError("Error making prediction.") from e
            logger.error("Failed to extract image features: %s", e)
            raise RuntimeError("Error extracting image features.") from e

        try:
            prediction = self.svm_model.predict(image_embedding)
            logger.info("Prediction completed: %s", prediction[0])
        except Exception as e:
            # raise
            logger.error("Failed to make prediction: %s", e)
            raise RuntimeError("Error making prediction.") from e
        # Predict using SVM model

        if prediction[0] == "Sticky_Trap":
            logger.info("The image is classified as a Sticky Trap.")

            # modify on 2024/12/19 add image adjustment on clip
            # the format of result_json is -> return {result:"", msg:""}, image

            res = self.__ImageAdjustment(original_image)
            res_rgb = cv2.cvtColor(res[1], cv2.COLOR_BGR2RGB)
            pil_image = Image.fromarray(res_rgb)
            jpeg_buffer = BytesIO()
            pil_image.save(jpeg_buffer, format='JPEG')
            jpeg_buffer.seek(0)
            jpeg_image = Image.open(jpeg_buffer) 
            return res[0], jpeg_image
            
        else:
            logger.info("The image is not classified as a Sticky Trap.")
            return {"result": "fail","msg":"照片非粘蟲紙"}, image

    def __validate_svm_model(self):
        if not hasattr(self.svm_model, "predict"):
            raise TypeError(
                "Loaded SVM model does not have a `predict` method. Verify the file contents."
            )
    
    def __ImageAdjustment(self, image):
        
        # image information
        opencv_image = np.array(image)
        image = cv2.cvtColor(opencv_image, cv2.COLOR_RGB2BGR)
        image_h, image_w, _, = image.shape
        image_size = image_h* image_w

        # Convert the image to HSV & HSL color space
        hsv_image = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        hsl_image = cv2.cvtColor(image, cv2.COLOR_BGR2HLS)

        # Define the yellow HSV range and mask for the yellow areas
        lower_yellow = np.array([20, 100, 100])
        upper_yellow = np.array([32, 255, 255])
        yellow_mask = cv2.inRange(hsv_image, lower_yellow, upper_yellow)

        # Use morphological operations to clean up the masks (closing and opening operations)
        kernel = np.ones((5, 5), np.uint8)
        yellow_mask = cv2.morphologyEx(yellow_mask, cv2.MORPH_CLOSE, kernel)
        yellow_mask = cv2.morphologyEx(yellow_mask, cv2.MORPH_OPEN, kernel)

        # Reflection area mask
        l = hsl_image[:, :, 1]
        _, reflection_mask = cv2.threshold(l, 180, 255, cv2.THRESH_BINARY)
        reflection_mask = cv2.morphologyEx(reflection_mask, cv2.MORPH_CLOSE, kernel)
        reflection_mask = cv2.morphologyEx(reflection_mask, cv2.MORPH_OPEN, kernel)

        # Find the contours of the yellow areas
        contours, _ = cv2.findContours(yellow_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if contours:
            # Find the largest contour by area
            largest_contour = max(contours, key=cv2.contourArea)

            # Draw a red rectangle around the largest yellow area
            x, y, w, h = cv2.boundingRect(largest_contour)
            rect_area = w * h
            red_rectangle_coords = [(x, y), (x + w, y + h)]

            # Ratio of reflective area of ​​sticky paper
            sticky_trap_mask = np.zeros_like(l)
            cv2.rectangle(sticky_trap_mask, red_rectangle_coords[0], red_rectangle_coords[1], 255, thickness=cv2.FILLED)
            sticky_trap_count = cv2.countNonZero(sticky_trap_mask)

            overlap_mask = cv2.bitwise_and(sticky_trap_mask, reflection_mask)
            overlap_count = cv2.countNonZero(overlap_mask)
            if sticky_trap_count > 0:
                overlap_percentage = overlap_count/sticky_trap_count
            else:
                overlap_percentage = 0

            # Check the reflection ratio in the area

            if overlap_percentage > 0.05:
                return ({"result": "fail","msg":"黏蟲紙有部分反光區域請重新拍攝"}, image)
            
            else:
                # Confirm the area ratio of the red area

                if rect_area< 0.5*image_size:
                   return ({"result": "fail","msg":"黏蟲紙區域過小請重新拍攝"}, image)
                
                # Image correction and background removal
                elif rect_area< 0.95* image_size:

                    # Use polygon approximation to get the contour (green quadrilateral)
                    epsilon = 0.05 * cv2.arcLength(largest_contour, True)
                    approx = cv2.approxPolyDP(largest_contour, epsilon, True)

                    # If the contour is a quadrilateral, draw it on the original image
                    if len(approx) == 4:
                        _ = cv2.contourArea(approx)

                        # Perform perspective transform to extract the quadrilateral area
                        pts_src = np.array([point[0] for point in approx], dtype=np.float32)

                        # Define the destination rectangle for the perspective transform
                        height = int(max(np.linalg.norm(pts_src[0] - pts_src[1]), np.linalg.norm(pts_src[2] - pts_src[3])))
                        width = int(max(np.linalg.norm(pts_src[0] - pts_src[3]), np.linalg.norm(pts_src[1] - pts_src[2])))
                        
                        pts_dst = np.float32([[0, 0], [0, height], [width, height], [width, 0]])
                        # Calculate the perspective transform matrix
                        matrix = cv2.getPerspectiveTransform(pts_src, pts_dst)

                        # Perform the perspective transformation
                        warped_image = cv2.warpPerspective(image, matrix, (width, height))

                        # Draw the green quadrilateral
                        #cv2.polylines(image, [approx], isClosed=True, color=(0, 255, 0), thickness=5)  # 使用綠色框線
                        
                        return ({"result":"success","msg":"黏蟲紙已重新校正"}, warped_image)
                    
                    else:
                        #特殊情況需特別儲存處理，有遇到的話要把圖片標記起來，目前先回傳原圖片
                        return ({"result": "fail","msg":"特殊狀況 1 (多邊形)"}, image)
                    
                else:
                    #滿版圖片不需特別處理，直接回傳原圖片
                    return ({"result": "success","msg":"滿版黏蟲紙無須校正"}, image)
            
        else:
            #特殊情況需特別儲存處理，有遇到的話要把圖片標記起來，目前先回傳原圖片
            return ({"result": "fail","msg":"特殊狀況 2 (非黃色黏蟲紙)"}, image)