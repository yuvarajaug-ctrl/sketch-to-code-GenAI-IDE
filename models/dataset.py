import os
import json
import torch
from torch.utils.data import Dataset
from PIL import Image
import torchvision.transforms.functional as F

class SketchDataset(Dataset):
    def __init__(self, root_dir, transforms=None):
        self.root_dir = root_dir
        self.transforms = transforms
        self.sketches_dir = os.path.join(root_dir, 'sketches')
        self.labels_dir = os.path.join(root_dir, 'labels')
        
        # In a real scenario, we check valid pairs
        # For this setup, we assume every image has a corresponding JSON label
        self.imgs = []
        if os.path.exists(self.sketches_dir):
            self.imgs = [img for img in os.listdir(self.sketches_dir) if img.endswith(('.png', '.jpg', '.jpeg'))]
        
        # Define a class mapping (example mapping)
        self.class_mapping = {
            'background': 0,
            'button': 1,
            'textbox': 2,
            'image': 3,
            'label': 4,
            'checkbox': 5
        }

    def __len__(self):
        return len(self.imgs)

    def __getitem__(self, idx):
        # Load image
        img_name = self.imgs[idx]
        img_path = os.path.join(self.sketches_dir, img_name)
        img = Image.open(img_path).convert("RGB")
        
        # Load label JSON
        label_name = img_name.rsplit('.', 1)[0] + '.json'
        label_path = os.path.join(self.labels_dir, label_name)
        
        boxes = []
        labels = []
        
        if os.path.exists(label_path):
            with open(label_path, 'r') as f:
                data = json.load(f)
                # Ensure data is a list of elements containing 'class' and 'bbox'
                for element in data:
                    cls_name = element.get('class', 'background')
                    label = self.class_mapping.get(cls_name.lower(), 0)
                    bbox = element.get('bbox', [0, 0, 10, 10]) # [xmin, ymin, xmax, ymax]
                    
                    boxes.append(bbox)
                    labels.append(label)
        
        # Convert to tensor
        if len(boxes) > 0:
            boxes = torch.as_tensor(boxes, dtype=torch.float32)
        else:
            # Handle empty labels by producing a dummy background label to avoid collate errors
            boxes = torch.zeros((0, 4), dtype=torch.float32)
            
        labels = torch.as_tensor(labels, dtype=torch.int64)
        
        target = {}
        target["boxes"] = boxes
        target["labels"] = labels
        target["image_id"] = torch.tensor([idx])
        
        if self.transforms is not None:
            img, target = self.transforms(img, target)
        else:
            img = F.to_tensor(img)
            
        return img, target
