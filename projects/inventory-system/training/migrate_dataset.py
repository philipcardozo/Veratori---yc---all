#!/usr/bin/env python3
"""
Dataset Migration Script
Migrates Label Studio export to YOLO dataset format with 80/20 train/val split
"""

import os
import shutil
import random
from pathlib import Path

def migrate_dataset():
    """
    Migrate the new Label Studio dataset to YOLO format with train/val split
    """
    # Paths
    project_root = Path(__file__).parent
    source_dir = project_root / "project-2-at-2026-01-11-10-58-95c633c8"
    dataset_dir = project_root / "dataset" / "pokebowl_dataset"
    
    # Verify source exists
    if not source_dir.exists():
        print(f"Error: Source directory not found: {source_dir}")
        return False
    
    source_images = source_dir / "images"
    source_labels = source_dir / "labels"
    
    if not source_images.exists() or not source_labels.exists():
        print("Error: Source images or labels directory not found")
        return False
    
    # Get all image files
    image_files = list(source_images.glob("*.jpg"))
    print(f"Found {len(image_files)} images in source directory")
    
    # Verify matching labels
    valid_pairs = []
    for img_path in image_files:
        label_path = source_labels / f"{img_path.stem}.txt"
        if label_path.exists():
            valid_pairs.append((img_path, label_path))
        else:
            print(f"Warning: No label found for {img_path.name}")
    
    print(f"Valid image-label pairs: {len(valid_pairs)}")
    
    if len(valid_pairs) == 0:
        print("Error: No valid image-label pairs found")
        return False
    
    # Shuffle and split 80/20
    random.seed(42)  # For reproducibility
    random.shuffle(valid_pairs)
    
    split_idx = int(len(valid_pairs) * 0.8)
    train_pairs = valid_pairs[:split_idx]
    val_pairs = valid_pairs[split_idx:]
    
    print(f"Train set: {len(train_pairs)} images")
    print(f"Val set: {len(val_pairs)} images")
    
    # Backup old dataset if exists
    old_images_train = dataset_dir / "images" / "train"
    old_images_val = dataset_dir / "images" / "val"
    old_labels_train = dataset_dir / "labels" / "train"
    old_labels_val = dataset_dir / "labels" / "val"
    
    # Remove old data
    for old_dir in [old_images_train, old_images_val, old_labels_train, old_labels_val]:
        if old_dir.exists():
            print(f"Removing old directory: {old_dir}")
            shutil.rmtree(old_dir)
    
    # Create new directories
    new_images_train = dataset_dir / "images" / "train"
    new_images_val = dataset_dir / "images" / "val"
    new_labels_train = dataset_dir / "labels" / "train"
    new_labels_val = dataset_dir / "labels" / "val"
    
    for new_dir in [new_images_train, new_images_val, new_labels_train, new_labels_val]:
        new_dir.mkdir(parents=True, exist_ok=True)
        print(f"Created directory: {new_dir}")
    
    # Copy training data
    print("\nCopying training data...")
    for img_path, label_path in train_pairs:
        shutil.copy2(img_path, new_images_train / img_path.name)
        shutil.copy2(label_path, new_labels_train / label_path.name)
    
    # Copy validation data
    print("Copying validation data...")
    for img_path, label_path in val_pairs:
        shutil.copy2(img_path, new_images_val / img_path.name)
        shutil.copy2(label_path, new_labels_val / label_path.name)
    
    # Verify copy
    train_images_count = len(list(new_images_train.glob("*.jpg")))
    train_labels_count = len(list(new_labels_train.glob("*.txt")))
    val_images_count = len(list(new_images_val.glob("*.jpg")))
    val_labels_count = len(list(new_labels_val.glob("*.txt")))
    
    print(f"\nVerification:")
    print(f"  Train images: {train_images_count}")
    print(f"  Train labels: {train_labels_count}")
    print(f"  Val images: {val_images_count}")
    print(f"  Val labels: {val_labels_count}")
    
    if (train_images_count == len(train_pairs) and 
        train_labels_count == len(train_pairs) and
        val_images_count == len(val_pairs) and 
        val_labels_count == len(val_pairs)):
        print("\n✓ Dataset migration successful!")
        return True
    else:
        print("\n✗ Verification failed - counts don't match")
        return False


if __name__ == "__main__":
    success = migrate_dataset()
    exit(0 if success else 1)

