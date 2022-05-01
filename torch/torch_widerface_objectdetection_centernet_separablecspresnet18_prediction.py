import torch
import random
import torchvision
import numpy as np
import cv2

from torchsummary import summary
from torch.utils.data import DataLoader


from util.centernet_helper import batch_prediction_loader
from util.centernet_helper import batch_box_extractor

from model.CSPSeparableResnet18 import CSPSeparableResnet18
from model.CSPSeparableResnet18CenterNet import CSPSeparableResnet18CenterNet


USE_CUDA = torch.cuda.is_available() # GPU를 사용가능하면 True, 아니라면 False를 리턴
device = torch.device("cuda" if USE_CUDA else "cpu") # GPU 사용 가능하면 사용하고 아니면 CPU 사용
print("다음 기기로 학습합니다:", device)


# for reproducibility
random.seed(777)
torch.manual_seed(777)
if device == 'cuda':
    torch.cuda.manual_seed_all(777)


## Hyper parameter
batch_size = 1
accuracy_threshold = 0.85
class_score_threshold = 0.5
iou_threshold = 0.5
input_image_width = 640
input_image_height = 640
feature_map_scale_factor = 4
pretrained = True
## Hyper parameter



#Model Setting
CSPSeparableResnet18 = CSPSeparableResnet18(class_num=1, activation=torch.nn.SiLU).to(device)
print('==== model info ====')
summary(CSPSeparableResnet18, (3, 640, 640))
print('====================')
CSPSeparableResnet18CenterNet = CSPSeparableResnet18CenterNet(backbone=CSPSeparableResnet18,
                                            activation=torch.nn.SiLU,
                                            pretrained=False).to(device)

CSPSeparableResnet18CenterNetBackBoneWeight = torch.jit.load("C://Github//DeepLearningStudy//trained_model//TRAIN_WIDERFACE(CSPSeparableResnet18CenterNetBackBone).pt")
CSPSeparableResnet18.load_state_dict(CSPSeparableResnet18CenterNetBackBoneWeight.state_dict())
CSPSeparableResnet18CenterNetWeight = torch.jit.load("C://Github//DeepLearningStudy//trained_model//TRAIN_WIDERFACE(CSPSeparableResnet18CenterNet).pt")
CSPSeparableResnet18CenterNet.load_state_dict(CSPSeparableResnet18CenterNetWeight.state_dict())


print('==== model info ====')
summary(CSPSeparableResnet18CenterNet, (3, 640, 640))
print('====================')
#Model Setting



# object detection dataset loader
object_detection_transform = torchvision.transforms.Compose([
        torchvision.transforms.ToTensor()
    ])
objectDetectionDataset = torchvision.datasets.WIDERFace(root="C://Github//Dataset//",
                                                        split="train",
                                                        transform=object_detection_transform,
                                                        download=False)
object_detection_data_loader = DataLoader(dataset=objectDetectionDataset,
                                          batch_size=1,  # 배치 크기는 100
                                          shuffle=True,
                                          drop_last=True)
total_batch = int(len(object_detection_data_loader) / batch_size)
print('total batch=', total_batch)
# object detection dataset loader


avg_acc = 0
for batch_index in range(total_batch):






    input_image = batch_prediction_loader(object_detection_data_loader,
                                         batch_size,
                                         input_image_width,
                                         input_image_height,
                                         device,
                                         isNorm=False)


    gpu_input_image = input_image.to(device)

    CSPSeparableResnet18CenterNet.eval()
    prediction = CSPSeparableResnet18CenterNet(gpu_input_image)
    prediction_heatmap = prediction[0]
    prediction_features = prediction[1]
    prediction_sizemap = prediction[2]
    prediction_offsetmap = prediction[3]



    box_extraction = batch_box_extractor(input_image_width=input_image_width,
                                        input_image_height=input_image_height,
                                        scale_factor=feature_map_scale_factor,
                                        score_threshold=class_score_threshold,
                                        gaussian_map_batch=prediction_heatmap,
                                        size_map_batch=prediction_sizemap,
                                        offset_map_batch=prediction_offsetmap)



    input_image = gpu_input_image[0].detach().permute(1, 2, 0).cpu().numpy()
    input_image = input_image
    input_image = input_image.astype(np.uint8)
    input_image = cv2.cvtColor(input_image, cv2.COLOR_RGB2BGR)
    ##BBox Visualization
    for bbox in box_extraction[0]:
        if len(box_extraction) == 0 : break;
        bbox_x = int(bbox[0])
        bbox_y = int(bbox[1])
        bbox_width = int(bbox[2])
        bbox_height = int(bbox[3])
        cv2.rectangle(input_image, (bbox_x, bbox_y), (bbox_x + bbox_width, bbox_y + bbox_height), (0, 255, 0))
    ##BBox Visualization
    cv2.namedWindow("input", cv2.WINDOW_NORMAL)
    cv2.resizeWindow('input', input_image_width, input_image_height)
    cv2.imshow('input', input_image)
    cv2.waitKey(10)


print('final_average accuracy = ', avg_acc)
