import cv2
import numpy as np
cimport numpy as np

def otsu_ratio(np.ndarray[np.uint8_t, ndim=3] image):
    """
    Calculate the OTSU thresholding ratio for a given BGR image.

    Parameters:
    image (np.ndarray): Input image in BGR format.

    Returns:
    float: Ratio of black pixels after OTSU thresholding.
    """
    cdef int width = 3200
    cdef int height = 2400

    # Convert BGR image to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Apply OTSU thresholding
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    # Calculate the number of black pixels
    black_pixels = np.sum(thresh == 0)

    # Compute the ratio
    ratio = black_pixels / (width * height)

    return ratio

def resize_image(np.ndarray[np.uint8_t, ndim=3] img_sr):
    img_sr_128 = cv2.resize(img_sr, (128, 128))
    return img_sr_128

def get_output_layers(nnet):
    """
    Retrieve the names of the output layers from a neural network.

    Parameters:
    nnet (cv2.dnn_Net): The neural network from which to get the output layers.

    Returns:
    list: A list of names of the output layers.
    """
    # Get the names of all layers in the network
    layer_names = nnet.getLayerNames()

    # Get the indices of the unconnected output layers
    unconnected_layers = nnet.getUnconnectedOutLayers()

    # Initialize an empty list to store the names of the output layers
    output_layers = []

    # Check if unconnected_layers is a list or numpy array
    if isinstance(unconnected_layers, (list, np.ndarray)):
        # Iterate over the indices and retrieve the corresponding layer names
        for i in unconnected_layers:
            output_layers.append(layer_names[i - 1])
    else:
        # If unconnected_layers is a single integer, retrieve the corresponding layer name
        output_layers.append(layer_names[unconnected_layers - 1])

    return output_layers

def nms_boxes(np.ndarray[np.float64_t, ndim=2] boxes,
              np.ndarray[np.float64_t, ndim=1] scores,
              float score_threshold,
              float nms_threshold):
    """
    Apply Non-Maximum Suppression to bounding boxes.

    Parameters:
    boxes (ndarray): Array of bounding boxes with shape (N, 4).
    scores (ndarray): Array of confidence scores with shape (N,).
    score_threshold (float): Threshold for filtering boxes by score.
    nms_threshold (float): Threshold for NMS overlap.

    Returns:
    list: Indices of the boxes to keep after NMS.
    """
    # Convert boxes and scores to lists as required by cv2.dnn.NMSBoxes
    boxes_list = boxes.tolist()
    scores_list = scores.tolist()

    # Apply NMS
    indices = cv2.dnn.NMSBoxes(boxes_list, scores_list, score_threshold, nms_threshold)

    # Flatten the indices and convert to a list
    # indices = [i[0] for i in indices]

    return indices