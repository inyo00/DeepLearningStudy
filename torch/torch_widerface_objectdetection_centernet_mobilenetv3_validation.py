import torch
import random
import torchvision
import numpy as np
import cv2

from torchsummary import summary
from torch.utils.data import DataLoader

from util.centernet_helper import batch_loader
from util.centernet_helper import batch_accuracy
from util.centernet_helper import batch_box_extractor

from model.MobileNetV3SmallCenterNet import MobileNetV3SmallCenterNet



USE_CUDA = torch.cuda.is_available() # GPU를 사용가능하면 True, 아니라면 False를 리턴
device = torch.device("cuda" if USE_CUDA else "cpu") # GPU 사용 가능하면 사용하고 아니면 CPU 사용
print("다음 기기로 학습합니다:", device)


# for reproducibility
random.seed(777)
torch.manual_seed(777)
if device == 'cuda':
    torch.cuda.manual_seed_all(777)


## Hyper parameter
batch_size = 10
class_score_threshold = 0.35
iou_threshold = 0.5
input_image_width = 800
input_image_height = 800
feature_map_scale_factor = 4
pretrained = True
## Hyper parameter



#Model Setting
MobileNetV3SmallCenterNet = MobileNetV3SmallCenterNet(fpn_conv_filters=64).to(device)
print('==== model info ====')
summary(MobileNetV3SmallCenterNet, (3, input_image_height, input_image_width))
print('====================')


MobileNetV3SmallCenterNetWeight = torch.jit.load("C://Github//DeepLearningStudy//trained_model//TRAIN_WIDERFACE(MobileNetV3SmallCenterNet).pt")
MobileNetV3SmallCenterNet.load_state_dict(MobileNetV3SmallCenterNetWeight.state_dict())



print('==== model info ====')
summary(MobileNetV3SmallCenterNet, (3, input_image_height, input_image_width))
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
    batch = batch_loader(object_detection_data_loader,
                         batch_size,
                         input_image_width,
                         input_image_height,
                         feature_map_scale_factor,
                         device,
                         isNorm=False)
    label_image = batch[0]          #Original Image
    label_bbox = batch[1]           #BBox Info
    label_heatmap = batch[2]        #Gaussian Heatmap
    label_sizemap = batch[3]        #Size Map
    label_offsetmap = batch[4]      #Offset Map

    gpu_label_image = label_image.to(device)
    gpu_label_heatmap = label_heatmap.to(device)
    gpu_label_sizemap = label_sizemap.to(device)
    gpu_label_offsetmap = label_offsetmap.to(device)

    MobileNetV3SmallCenterNet.eval_mode()
    prediction = MobileNetV3SmallCenterNet(gpu_label_image)
    prediction_heatmap = prediction[0]
    prediction_features = prediction[1]
    prediction_sizemap = prediction[2]
    prediction_offsetmap = prediction[3]



    validation = batch_accuracy(input_image_width=input_image_width,
                                input_image_height=input_image_height,
                                scale_factor=feature_map_scale_factor,
                                score_threshold=class_score_threshold,
                                iou_threshold=iou_threshold,
                                gaussian_map_batch=prediction_heatmap,
                                size_map_batch=prediction_sizemap,
                                offset_map_batch=prediction_offsetmap,
                                bbox_list=label_bbox)

    box_extraction = batch_box_extractor(input_image_width=input_image_width,
                                         input_image_height=input_image_height,
                                         scale_factor=feature_map_scale_factor,
                                         score_threshold=class_score_threshold,
                                         gaussian_map_batch=prediction_heatmap,
                                         size_map_batch=prediction_sizemap,
                                         offset_map_batch=prediction_offsetmap)

    accuracy = validation[0]
    prediction_result = validation[1]
    avg_acc += (accuracy / total_batch)
    print('batch accuracy=', accuracy)

    input_image = label_image[0].detach().permute(1, 2, 0).cpu().numpy()
    input_image = input_image
    input_image = input_image.astype(np.uint8)
    input_image = cv2.cvtColor(input_image, cv2.COLOR_RGB2BGR)
    ##BBox Visualization
    for bbox in label_bbox[0]:
        bbox_x = int(bbox[0])
        bbox_y = int(bbox[1])
        bbox_width = int(bbox[2])
        bbox_height = int(bbox[3])
        cv2.rectangle(input_image, (bbox_x, bbox_y), (bbox_x + bbox_width, bbox_y + bbox_height), (255, 0, 0))

    for bbox in box_extraction[0]:
        if len(box_extraction) == 0:
            break
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
