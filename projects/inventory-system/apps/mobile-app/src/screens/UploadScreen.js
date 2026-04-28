/**
 * Upload Restock Screen
 * Capture photos and submit restock documentation
 */

import React, { useState } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  ScrollView,
  Image,
  Alert,
  ActivityIndicator,
  TextInput,
} from 'react-native';
import { launchCamera, launchImageLibrary } from 'react-native-image-picker';
import { restockService } from '../services/api';
import * as Location from 'expo-location';

const UploadScreen = ({ navigation }) => {
  const [photos, setPhotos] = useState([]);
  const [detections, setDetections] = useState({});
  const [station, setStation] = useState('');
  const [product, setProduct] = useState('');
  const [notes, setNotes] = useState('');
  const [uploading, setUploading] = useState(false);
  const [detecting, setDetecting] = useState({});

  const takePhoto = (index) => {
    launchCamera(
      {
        mediaType: 'photo',
        quality: 0.8,
        maxWidth: 1920,
        maxHeight: 1920,
      },
      async (response) => {
        if (response.didCancel || response.errorMessage) {
          return;
        }

        if (response.assets && response.assets[0]) {
          const photo = {
            uri: response.assets[0].uri,
            index: index,
          };

          const newPhotos = [...photos];
          newPhotos[index] = photo;
          setPhotos(newPhotos);

          // Run detection preview
          runDetection(photo.uri, index);
        }
      }
    );
  };

  const runDetection = async (photoUri, index) => {
    setDetecting(prev => ({ ...prev, [index]: true }));
    try {
      const result = await restockService.detectPhoto(photoUri);
      if (result.success) {
        setDetections(prev => ({
          ...prev,
          [index]: result.product_counts,
        }));
      }
    } catch (error) {
      console.error('Detection error:', error);
    } finally {
      setDetecting(prev => ({ ...prev, [index]: false }));
    }
  };

  const removePhoto = (index) => {
    const newPhotos = photos.filter((_, i) => i !== index);
    setPhotos(newPhotos);
    const newDetections = { ...detections };
    delete newDetections[index];
    setDetections(newDetections);
  };

  const handleSubmit = async () => {
    if (photos.length < 3) {
      Alert.alert('Error', 'Please take at least 3 photos');
      return;
    }

    if (!station || !product) {
      Alert.alert('Error', 'Please enter station and product');
      return;
    }

    setUploading(true);
    try {
      let location = null;
      try {
        const { status } = await Location.requestForegroundPermissionsAsync();
        if (status === 'granted') {
          location = await Location.getCurrentPositionAsync({});
        }
      } catch (e) {
        // Location not available, continue without it
      }

      const result = await restockService.uploadSubmission(
        photos,
        station,
        product,
        notes,
        location?.coords
      );

      if (result.success) {
        Alert.alert('Success', 'Restock submitted successfully!', [
          {
            text: 'OK',
            onPress: () => {
              // Reset form
              setPhotos([]);
              setDetections({});
              setStation('');
              setProduct('');
              setNotes('');
              navigation.navigate('Submissions');
            },
          },
        ]);
      } else {
        Alert.alert('Error', result.message || 'Upload failed');
      }
    } catch (error) {
      Alert.alert('Error', 'Network error. Please try again.');
    } finally {
      setUploading(false);
    }
  };

  return (
    <ScrollView style={styles.container}>
      <View style={styles.content}>
        <Text style={styles.title}>Upload Restock</Text>
        <Text style={styles.subtitle}>Take at least 3 photos from different angles</Text>

        {/* Photo Grid */}
        <View style={styles.photoGrid}>
          {[0, 1, 2].map((index) => (
            <View key={index} style={styles.photoSlot}>
              {photos[index] ? (
                <View style={styles.photoContainer}>
                  <Image
                    source={{ uri: photos[index].uri }}
                    style={styles.photo}
                  />
                  {detecting[index] && (
                    <View style={styles.detectingOverlay}>
                      <ActivityIndicator color="#10b981" />
                      <Text style={styles.detectingText}>Detecting...</Text>
                    </View>
                  )}
                  {detections[index] && (
                    <View style={styles.detectionBadge}>
                      <Text style={styles.detectionText}>
                        {Object.entries(detections[index])
                          .map(([name, count]) => `${name}: ${count}`)
                          .join(', ')}
                      </Text>
                    </View>
                  )}
                  <TouchableOpacity
                    style={styles.removeButton}
                    onPress={() => removePhoto(index)}
                  >
                    <Text style={styles.removeButtonText}>×</Text>
                  </TouchableOpacity>
                </View>
              ) : (
                <TouchableOpacity
                  style={styles.addPhotoButton}
                  onPress={() => takePhoto(index)}
                >
                  <Text style={styles.addPhotoText}>+</Text>
                  <Text style={styles.addPhotoLabel}>
                    {index === 0 ? 'Front' : index === 1 ? 'Left' : 'Right'}
                  </Text>
                </TouchableOpacity>
              )}
            </View>
          ))}
        </View>

        {/* Additional photos */}
        {photos.length >= 3 && photos.length < 10 && (
          <TouchableOpacity
            style={styles.addMoreButton}
            onPress={() => takePhoto(photos.length)}
          >
            <Text style={styles.addMoreText}>+ Add More Photos</Text>
          </TouchableOpacity>
        )}

        {/* Form Fields */}
        <View style={styles.form}>
          <Text style={styles.label}>Station</Text>
          <TextInput
            style={styles.input}
            placeholder="e.g., Main Display, Station 1"
            placeholderTextColor="#64748b"
            value={station}
            onChangeText={setStation}
          />

          <Text style={styles.label}>Product / SKU</Text>
          <TextInput
            style={styles.input}
            placeholder="e.g., Passion Fruit, Mango"
            placeholderTextColor="#64748b"
            value={product}
            onChangeText={setProduct}
          />

          <Text style={styles.label}>Notes (Optional)</Text>
          <TextInput
            style={[styles.input, styles.textArea]}
            placeholder="Additional notes..."
            placeholderTextColor="#64748b"
            value={notes}
            onChangeText={setNotes}
            multiline
            numberOfLines={4}
          />
        </View>

        {/* Submit Button */}
        <TouchableOpacity
          style={[styles.submitButton, uploading && styles.submitButtonDisabled]}
          onPress={handleSubmit}
          disabled={uploading || photos.length < 3}
        >
          {uploading ? (
            <ActivityIndicator color="#fff" />
          ) : (
            <Text style={styles.submitButtonText}>Submit Restock</Text>
          )}
        </TouchableOpacity>
      </View>
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#070b12',
  },
  content: {
    padding: 16,
  },
  title: {
    fontSize: 28,
    fontWeight: '700',
    color: '#f1f5f9',
    marginBottom: 8,
  },
  subtitle: {
    fontSize: 14,
    color: '#94a3b8',
    marginBottom: 24,
  },
  photoGrid: {
    flexDirection: 'row',
    gap: 12,
    marginBottom: 16,
  },
  photoSlot: {
    flex: 1,
    aspectRatio: 1,
  },
  addPhotoButton: {
    flex: 1,
    backgroundColor: '#1a2332',
    borderWidth: 2,
    borderColor: 'rgba(255,255,255,0.1)',
    borderStyle: 'dashed',
    borderRadius: 12,
    justifyContent: 'center',
    alignItems: 'center',
  },
  addPhotoText: {
    fontSize: 32,
    color: '#64748b',
    marginBottom: 8,
  },
  addPhotoLabel: {
    fontSize: 12,
    color: '#64748b',
  },
  photoContainer: {
    flex: 1,
    position: 'relative',
  },
  photo: {
    width: '100%',
    height: '100%',
    borderRadius: 12,
  },
  detectingOverlay: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(0,0,0,0.7)',
    justifyContent: 'center',
    alignItems: 'center',
    borderRadius: 12,
  },
  detectingText: {
    color: '#10b981',
    marginTop: 8,
    fontSize: 12,
  },
  detectionBadge: {
    position: 'absolute',
    bottom: 8,
    left: 8,
    right: 8,
    backgroundColor: 'rgba(16,185,129,0.9)',
    padding: 6,
    borderRadius: 6,
  },
  detectionText: {
    color: '#fff',
    fontSize: 10,
    fontWeight: '600',
  },
  removeButton: {
    position: 'absolute',
    top: 8,
    right: 8,
    backgroundColor: 'rgba(239,68,68,0.9)',
    width: 28,
    height: 28,
    borderRadius: 14,
    justifyContent: 'center',
    alignItems: 'center',
  },
  removeButtonText: {
    color: '#fff',
    fontSize: 20,
    fontWeight: '700',
  },
  addMoreButton: {
    backgroundColor: '#1a2332',
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.1)',
    borderRadius: 12,
    padding: 16,
    alignItems: 'center',
    marginBottom: 24,
  },
  addMoreText: {
    color: '#10b981',
    fontSize: 16,
    fontWeight: '600',
  },
  form: {
    gap: 16,
    marginBottom: 24,
  },
  label: {
    fontSize: 14,
    fontWeight: '600',
    color: '#f1f5f9',
    marginBottom: 8,
  },
  input: {
    backgroundColor: '#1a2332',
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.06)',
    borderRadius: 12,
    padding: 16,
    fontSize: 16,
    color: '#f1f5f9',
  },
  textArea: {
    height: 100,
    textAlignVertical: 'top',
  },
  submitButton: {
    backgroundColor: '#10b981',
    borderRadius: 12,
    padding: 18,
    alignItems: 'center',
    marginBottom: 24,
  },
  submitButtonDisabled: {
    opacity: 0.6,
  },
  submitButtonText: {
    color: '#fff',
    fontSize: 18,
    fontWeight: '700',
  },
});

export default UploadScreen;


