import torch
import torchvision
from torchvision.models.detection.faster_rcnn import FastRCNNPredictor

def get_detector_model(num_classes):
    """
    Load a pre-trained ResNet50-FPN model and replace the classification head.
    `num_classes` includes background (0).
    """
    # load a model pre-trained on COCO
    model = torchvision.models.detection.fasterrcnn_resnet50_fpn(pretrained=True)
    
    # get number of input features for the classifier
    in_features = model.roi_heads.box_predictor.cls_score.in_features
    # replace the pre-trained head with a new one
    model.roi_heads.box_predictor = FastRCNNPredictor(in_features, num_classes)
    
    return model
