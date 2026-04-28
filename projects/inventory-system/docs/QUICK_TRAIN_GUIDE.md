# Quick Training Guide

## TL;DR - Start Training Now

```bash
# 1. Install Jupyter
pip install jupyter notebook

# 2. Launch notebook
cd /Users/felipecardozo/Desktop/coding/Poke-Bowl---updated-January
jupyter notebook train_pokebowl_model.ipynb

# 3. In Jupyter: Run > Run All Cells
# 4. Wait for training to complete (1-6 hours depending on hardware)
# 5. New model will be saved as best.pt (old one backed up)
```

---

## What Was Wrong?

The current model was trained with:
- ❌ **CPU only** (10-50x slower than GPU)
- ❌ **50 epochs** (too few for 40 classes)
- ❌ **No data loading workers** (slow data pipeline)
- ❌ **Basic augmentation** (poor generalization)

## What's Fixed?

The new training notebook uses:
- ✅ **GPU acceleration** (CUDA/MPS/CPU with warning)
- ✅ **200 epochs** with early stopping
- ✅ **8 workers** for fast data loading
- ✅ **Aggressive augmentation** (mosaic, mixup, rotation, scaling, color jitter)
- ✅ **AdamW optimizer** (better for small datasets)
- ✅ **Comprehensive validation** and metrics

---

## Training Options

### Option 1: Local Training (Your Mac/PC)
**Best for**: Quick iteration, small changes
**Time**: 3-6 hours on Apple Silicon, 1-3 hours on NVIDIA GPU

```bash
jupyter notebook train_pokebowl_model.ipynb
```

### Option 2: Google Colab (Free GPU)
**Best for**: No local GPU, free training
**Time**: 1-2 hours on T4 GPU

1. Go to [Google Colab](https://colab.research.google.com)
2. Upload `train_pokebowl_model.ipynb`
3. Upload dataset folder or mount Google Drive
4. Runtime > Change runtime type > GPU (T4)
5. Update paths in first cells
6. Run all cells

### Option 3: Cloud GPU (AWS/GCP/Azure)
**Best for**: Fastest training, production setup
**Time**: 30-60 minutes on high-end GPU

---

## Expected Results

### Metrics Improvement
| Metric | Before | After (Expected) |
|--------|--------|-----------------|
| mAP50 | ~0.65 | 0.80-0.90 |
| mAP50-95 | ~0.40 | 0.55-0.70 |
| Precision | ~0.70 | 0.80-0.90 |
| Recall | ~0.65 | 0.75-0.85 |

### Training Time
| Hardware | Time |
|----------|------|
| CPU | 16-33 hours ⚠️ |
| Apple M1/M2 | 3-6 hours |
| RTX 3060 | 1.5-3 hours |
| RTX 4090 | 45-90 min |
| Google Colab T4 | 1-2 hours |

---

## What the Notebook Does

### 1. Dataset Analysis (5 minutes)
- Counts images and labels
- Analyzes class distribution
- Visualizes sample images
- Creates distribution plots

### 2. Training (1-6 hours)
- Loads YOLOv8n model
- Trains for up to 200 epochs
- Applies data augmentation
- Saves checkpoints every 10 epochs
- Early stopping if no improvement

### 3. Validation (5 minutes)
- Evaluates on validation set
- Generates confusion matrix
- Creates prediction visualizations
- Calculates mAP, precision, recall

### 4. Export (1 minute)
- Backs up old model
- Copies new model to `best.pt`
- Verifies model integrity

---

## Monitoring Training

### Good Signs ✅
- Training loss decreasing steadily
- Validation loss decreasing
- mAP increasing
- Confusion matrix has strong diagonal

### Warning Signs ⚠️
- Validation loss increasing (overfitting)
- Training loss stuck (underfitting)
- Very low recall (<0.5)
- Confusion matrix shows many misclassifications

### What to Do If...

**Training is too slow:**
- Reduce batch size: `'batch': 8`
- Reduce image size: `'imgsz': 416`
- Use fewer workers: `'workers': 4`

**Out of memory:**
- Reduce batch size: `'batch': 4`
- Disable caching: `'cache': False`
- Use smaller image size: `'imgsz': 416`

**Model is overfitting:**
- Already has early stopping
- Increase augmentation
- Collect more data

**Model is underfitting:**
- Train longer (increase patience)
- Use larger model: `'model': 'yolov8s.pt'`
- Reduce augmentation slightly

---

## After Training

### 1. Test the New Model
```bash
cd backend
python3 main.py
```

Open browser to `http://localhost:8080` and verify:
- Detections are accurate
- No false positives
- All classes detected correctly
- Inference speed is good (>15 FPS)

### 2. Compare with Old Model
- Check confusion matrix
- Review validation predictions
- Test on real camera feed
- Monitor for 1-2 days

### 3. If Results Are Good
- Keep new model
- Delete backup if confident
- Update documentation

### 4. If Results Are Bad
- Restore backup: `mv best_backup_*.pt best.pt`
- Review training logs
- Adjust hyperparameters
- Collect more data for problem classes

---

## Customization

### Use Larger Model (Better Accuracy)
```python
TRAINING_CONFIG = {
    'model': 'yolov8s.pt',  # Small (11MB)
    # or
    'model': 'yolov8m.pt',  # Medium (25MB)
    ...
}
```

### Reduce Training Time
```python
TRAINING_CONFIG = {
    'epochs': 100,  # Instead of 200
    'patience': 25,  # Instead of 50
    'imgsz': 416,   # Instead of 640
    ...
}
```

### More Aggressive Augmentation
```python
TRAINING_CONFIG = {
    'mosaic': 1.0,
    'mixup': 0.3,      # Increase from 0.15
    'copy_paste': 0.2, # Increase from 0.1
    'degrees': 15.0,   # Increase from 10.0
    ...
}
```

---

## Troubleshooting

### Jupyter Not Installed
```bash
pip install jupyter notebook ipykernel
```

### Can't Find Dataset
Check paths in notebook cell 2:
```python
DATASET_PATH = PROJECT_ROOT / 'dataset' / 'pokebowl_dataset'
```

### CUDA Out of Memory
Reduce batch size in cell 6:
```python
'batch': 4,  # or even 2
```

### Training Stops Early
Check early stopping patience:
```python
'patience': 50,  # Increase if needed
```

### Model Not Improving
- Check learning rate (might be too high/low)
- Verify data augmentation isn't too aggressive
- Ensure dataset labels are correct
- Consider collecting more data

---

## Support

### Check Training Logs
All logs are in: `runs/train/pokebowl_yolov8n_YYYYMMDD_HHMMSS/`

### View Training Curves
Open: `runs/train/pokebowl_yolov8n_YYYYMMDD_HHMMSS/results.png`

### Check Confusion Matrix
Open: `runs/train/pokebowl_yolov8n_YYYYMMDD_HHMMSS/confusion_matrix.png`

### Validation Predictions
Check: `runs/train/pokebowl_yolov8n_YYYYMMDD_HHMMSS/val_batch*_pred.jpg`

---

## Summary

1. **Open notebook**: `jupyter notebook train_pokebowl_model.ipynb`
2. **Run all cells**: Kernel > Restart & Run All
3. **Wait**: 1-6 hours depending on hardware
4. **Test**: `cd backend && python3 main.py`
5. **Deploy**: New model automatically saved as `best.pt`

**That's it!** The notebook handles everything automatically.

---

**Questions?** Check `TRAINING_ANALYSIS.md` for detailed information.

**Last Updated**: January 11, 2026

