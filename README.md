# SASDG (Jittor)
### SASDG: Shape-Aware Stylized Dance Motion Generation Driven by Music. Code based on Jittor framework.
![image](https://github.com/user-attachments/assets/d3376f95-e60b-4e6b-a193-3ced3e04ecde)

## Demo Link！[SASDG demo](https://www.bilibili.com/video/BV1Xy4qeQEmj)

## 1. Installation（安装）

### 1. Requirements
- **An NVIDIA GPU**. All shown results come from an RTX 3090.
-  **Python**. python 3.9 is recommended.
-  **Jittor**. Refer to [link](https://github.com/Jittor/jittor) to install jittor as recommended.

### 2. Install other dependencies 
Install the basic environment under the SASDG repo:
```shell
# Editable install, with dependencies from environment.yml
conda env create -f environment.yml
```

## 2. Training（训练）
```shell
python train.py --batch_size 128  --epochs 2000 --feature_type jukebox
```

## 2. Testing（测试）
```shell
python test_by_text.py --music_dir ./data/test/music --save_motions --text_prompt 'raise up both hands'
```
