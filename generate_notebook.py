import json
import os

def generate_notebook():
    notebook = {
        "cells": [
            {
                "cell_type": "markdown",
                "metadata": {},
                "source": [
                    "# YOLOv11 Coke Detection: Dataset Merging & Training\n",
                    "This notebook automates the process of merging two Roboflow datasets and training a production-ready YOLOv11 model for Coke detection."
                ]
            },
            {
                "cell_type": "markdown",
                "metadata": {},
                "source": [
                    "## 1. Setup Environment"
                ]
            },
            {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "outputs": [],
                "source": [
                    "!pip install -q ultralytics roboflow"
                ]
            },
            {
                "cell_type": "markdown",
                "metadata": {},
                "source": [
                    "## 2. Download Datasets\n",
                    "Please provide your Roboflow API key when prompted."
                ]
            },
            {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "outputs": [],
                "source": [
                    "from roboflow import Roboflow\n",
                    "import os\n",
                    "import yaml\n",
                    "import shutil\n",
                    "from pathlib import Path\n",
                    "from google.colab import userdata\n",
                    "\n",
                    "try:\n",
                    "    ROBOFLOW_API_KEY = userdata.get('ROBOFLOW_API_KEY')\n",
                    "except:\n",
                    "    from google.colab import drive\n",
                    "    ROBOFLOW_API_KEY = input(\"Enter your Roboflow API Key: \")\n",
                    "\n",
                    "rf = Roboflow(api_key=ROBOFLOW_API_KEY)\n",
                    "workspace = \"felipes-workspace-06bww\"\n",
                    "\n",
                    "# Download Project 1\n",
                    "project1 = rf.workspace(workspace).project(\"coke-newqe-rrg9b\")\n",
                    "dataset1 = project1.version(1).download(\"yolov11\")\n",
                    "\n",
                    "# Download Project 2\n",
                    "project2 = rf.workspace(workspace).project(\"coke-can-gdbwi-9o9kg\")\n",
                    "dataset2 = project2.version(1).download(\"yolov11\")"
                ]
            },
            {
                "cell_type": "markdown",
                "metadata": {},
                "source": [
                    "## 3. Merge Datasets & Unify Classes"
                ]
            },
            {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "outputs": [],
                "source": [
                    "def merge_yolo_datasets(ds1_path, ds2_path, output_path):\n",
                    "    output_path = Path(output_path)\n",
                    "    output_path.mkdir(parents=True, exist_ok=True)\n",
                    "    \n",
                    "    # Load yaml files\n",
                    "    with open(os.path.join(ds1_path, 'data.yaml'), 'r') as f:\n",
                    "        yaml1 = yaml.safe_load(f)\n",
                    "    with open(os.path.join(ds2_path, 'data.yaml'), 'r') as f:\n",
                    "        yaml2 = yaml.safe_load(f)\n",
                    "    \n",
                    "    # Unify classes\n",
                    "    classes1 = yaml1['names']\n",
                    "    classes2 = yaml2['names']\n",
                    "    \n",
                    "    # Using a list to maintain order, but set for lookup\n",
                    "    unified_classes = list(dict.fromkeys(classes1 + classes2))\n",
                    "    class_map1 = {i: unified_classes.index(name) for i, name in enumerate(classes1)}\n",
                    "    class_map2 = {i: unified_classes.index(name) for i, name in enumerate(classes2)}\n",
                    "    \n",
                    "    splits = ['train', 'valid', 'test']\n",
                    "    \n",
                    "    for split in splits:\n",
                    "        (output_path / split / 'images').mkdir(parents=True, exist_ok=True)\n",
                    "        (output_path / split / 'labels').mkdir(parents=True, exist_ok=True)\n",
                    "        \n",
                    "        # Process first dataset\n",
                    "        process_split(ds1_path, split, output_path, class_map1, prefix=\"ds1_\")\n",
                    "        # Process second dataset\n",
                    "        process_split(ds2_path, split, output_path, class_map2, prefix=\"ds2_\")\n",
                    "    \n",
                    "    # Create new data.yaml\n",
                    "    new_yaml = {\n",
                    "        'train': str((output_path / 'train' / 'images').absolute()),\n",
                    "        'val': str((output_path / 'valid' / 'images').absolute()),\n",
                    "        'test': str((output_path / 'test' / 'images').absolute()),\n",
                    "        'nc': len(unified_classes),\n",
                    "        'names': unified_classes\n",
                    "    }\n",
                    "    \n",
                    "    with open(output_path / 'data.yaml', 'w') as f:\n",
                    "        yaml.dump(new_yaml, f)\n",
                    "    \n",
                    "    return unified_classes, new_yaml\n",
                    "\n",
                    "def process_split(src_path, split, dest_path, class_map, prefix=\"\"):\n",
                    "    src_img_dir = Path(src_path) / split / 'images'\n",
                    "    src_lbl_dir = Path(src_path) / split / 'labels'\n",
                    "    \n",
                    "    if not src_img_dir.exists(): return\n",
                    "    \n",
                    "    for img_file in src_img_dir.glob('*'):\n",
                    "        if img_file.suffix.lower() not in ['.jpg', '.jpeg', '.png']:\n",
                    "            continue\n",
                    "            \n",
                    "        new_img_name = prefix + img_file.name\n",
                    "        shutil.copy(img_file, dest_path / split / 'images' / new_img_name)\n",
                    "        \n",
                    "        lbl_file = src_lbl_dir / (img_file.stem + '.txt')\n",
                    "        if lbl_file.exists():\n",
                    "            with open(lbl_file, 'r') as f:\n",
                    "                lines = f.readlines()\n",
                    "            \n",
                    "            new_lines = []\n",
                    "            for line in lines:\n",
                    "                parts = line.split()\n",
                    "                if not parts: continue\n",
                    "                old_idx = int(parts[0])\n",
                    "                new_idx = class_map[old_idx]\n",
                    "                new_lines.append(f\"{new_idx} {' '.join(parts[1:])}\\n\")\n",
                    "            \n",
                    "            with open(dest_path / split / 'labels' / (prefix + lbl_file.name), 'w') as f:\n",
                    "                f.writelines(new_lines)\n",
                    "\n",
                    "unified_classes, final_config = merge_yolo_datasets(dataset1.location, dataset2.location, \"merged_dataset\")\n",
                    "\n",
                    "print(f\"Unified Classes: {unified_classes}\")\n",
                    "print(f\"Final Dataset YAML: {final_config}\")"
                ]
            },
            {
                "cell_type": "markdown",
                "metadata": {},
                "source": [
                    "## 4. Dataset Statistics"
                ]
            },
            {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "outputs": [],
                "source": [
                    "import os\n",
                    "from collections import Counter\n",
                    "\n",
                    "def get_stats(path):\n",
                    "    stats = {}\n",
                    "    for split in ['train', 'valid', 'test']:\n",
                    "        img_count = len(os.listdir(os.path.join(path, split, 'images')))\n",
                    "        label_path = os.path.join(path, split, 'labels')\n",
                    "        class_counts = Counter()\n",
                    "        \n",
                    "        for lbl in os.listdir(label_path):\n",
                    "            with open(os.path.join(label_path, lbl), 'r') as f:\n",
                    "                for line in f:\n",
                    "                    cls = int(line.split()[0])\n",
                    "                    class_counts[cls] += 1\n",
                    "        \n",
                    "        stats[split] = {\n",
                    "            'images': img_count,\n",
                    "            'classes': dict(class_counts)\n",
                    "        }\n",
                    "    return stats\n",
                    "\n",
                    "stats = get_stats(\"merged_dataset\")\n",
                    "for split, data in stats.items():\n",
                    "    print(f\"\\n--- {split.upper()} ---\")\n",
                    "    print(f\"Total Images: {data['images']}\")\n",
                    "    for cls_idx, count in data['classes'].items():\n",
                    "        print(f\"Class '{unified_classes[cls_idx]}': {count} instances\")"
                ]
            },
            {
                "cell_type": "markdown",
                "metadata": {},
                "source": [
                    "## 5. Train YOLOv11m"
                ]
            },
            {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "outputs": [],
                "source": [
                    "from ultralytics import YOLO\n",
                    "\n",
                    "# Load pre-trained YOLOv11m\n",
                    "model = YOLO(\"yolo11m.pt\")\n",
                    "\n",
                    "# Start training\n",
                    "results = model.train(\n",
                    "    data=\"merged_dataset/data.yaml\",\n",
                    "    epochs=100,\n",
                    "    imgsz=1024,\n",
                    "    batch=8,\n",
                    "    optimizer='AdamW',\n",
                    "    cos_lr=True,\n",
                    "    patience=25,\n",
                    "    name='coke_v11_training'\n",
                    ")"
                ]
            },
            {
                "cell_type": "markdown",
                "metadata": {},
                "source": [
                    "## 6. Validation & Results"
                ]
            },
            {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "outputs": [],
                "source": [
                    "# Run validation on test set\n",
                    "validation_results = model.val(split='test')\n",
                    "\n",
                    "# The results are automatically saved in 'runs/detect/coke_v11_training/'\n",
                    "from IPython.display import Image, display\n",
                    "\n",
                    "# Display Confusion Matrix\n",
                    "conf_matrix_path = f\"{model.trainer.save_dir}/confusion_matrix.png\"\n",
                    "if os.path.exists(conf_matrix_path):\n",
                    "    display(Image(filename=conf_matrix_path))"
                ]
            },
            {
                "cell_type": "markdown",
                "metadata": {},
                "source": [
                    "## 7. Sample Inference"
                ]
            },
            {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "outputs": [],
                "source": [
                    "import random\n",
                    "import glob\n",
                    "import matplotlib.pyplot as plt\n",
                    "import cv2\n",
                    "\n",
                    "# Get test images\n",
                    "test_images = glob.glob(\"merged_dataset/valid/images/*\")\n",
                    "sample_images = random.sample(test_images, 5)\n",
                    "\n",
                    "for img_path in sample_images:\n",
                    "    results = model.predict(source=img_path, conf=0.25)\n",
                    "    \n",
                    "    # Plot results\n",
                    "    for r in results:\n",
                    "        im_array = r.plot()  # plot a BGR numpy array of predictions\n",
                    "        im_rgb = cv2.cvtColor(im_array, cv2.COLOR_BGR2RGB)\n",
                    "        plt.figure(figsize=(10, 10))\n",
                    "        plt.imshow(im_rgb)\n",
                    "        plt.axis('off')\n",
                    "        plt.title(f\"Inference: {os.path.basename(img_path)}\")\n",
                    "        plt.show()"
                ]
            }
        ],
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3"
            },
            "language_info": {
                "codemirror_mode": {
                    "name": "ipython",
                    "version": 3
                },
                "file_extension": ".py",
                "mimetype": "text/x-python",
                "name": "python",
                "nbconvert_exporter": "python",
                "pygments_lexer": "ipython3",
                "version": "3.10.12"
            }
        },
        "nbformat": 4,
        "nbformat_minor": 0
    }

    output_file = "YOLO11_Coke_Training.ipynb"
    with open(output_file, 'w') as f:
        json.dump(notebook, f, indent=4)
    print(f"Notebook generated: {output_file}")

if __name__ == "__main__":
    generate_notebook()
