/**
 * Submissions Screen
 * View employee's restock submission history
 */

import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  RefreshControl,
  Image,
} from 'react-native';
import { restockService } from '../services/api';
import { getApiUrl, API_ENDPOINTS } from '../config/api';

const SubmissionsScreen = () => {
  const [submissions, setSubmissions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    loadSubmissions();
  }, []);

  const loadSubmissions = async () => {
    try {
      const result = await restockService.getSubmissions();
      if (result.success) {
        setSubmissions(result.submissions);
      }
    } catch (error) {
      console.error('Error loading submissions:', error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const onRefresh = () => {
    setRefreshing(true);
    loadSubmissions();
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'approved':
        return '#10b981';
      case 'flagged':
        return '#ef4444';
      case 'adjustment_required':
        return '#f59e0b';
      default:
        return '#64748b';
    }
  };

  const formatDate = (timestamp) => {
    const date = new Date(timestamp * 1000);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  return (
    <ScrollView
      style={styles.container}
      refreshControl={
        <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
      }
    >
      <View style={styles.content}>
        <Text style={styles.title}>My Submissions</Text>

        {submissions.length === 0 ? (
          <View style={styles.empty}>
            <Text style={styles.emptyText}>No submissions yet</Text>
            <Text style={styles.emptySubtext}>Your restock submissions will appear here</Text>
          </View>
        ) : (
          submissions.map((submission) => (
            <View key={submission.submission_id} style={styles.card}>
              <View style={styles.cardHeader}>
                <View>
                  <Text style={styles.cardTitle}>{submission.product}</Text>
                  <Text style={styles.cardSubtitle}>{submission.station}</Text>
                </View>
                <View
                  style={[
                    styles.statusBadge,
                    { backgroundColor: getStatusColor(submission.status) + '20' },
                  ]}
                >
                  <Text
                    style={[
                      styles.statusText,
                      { color: getStatusColor(submission.status) },
                    ]}
                  >
                    {submission.status.replace('_', ' ').toUpperCase()}
                  </Text>
                </View>
              </View>

              {submission.notes && (
                <Text style={styles.notes}>{submission.notes}</Text>
              )}

              {submission.feedback && (
                <View style={styles.feedback}>
                  <Text style={styles.feedbackLabel}>Manager Feedback:</Text>
                  <Text style={styles.feedbackText}>{submission.feedback}</Text>
                </View>
              )}

              {submission.detection_results && (
                <View style={styles.detection}>
                  <Text style={styles.detectionLabel}>Detected Products:</Text>
                  {Object.entries(submission.detection_results.product_counts || {}).map(
                    ([name, count]) => (
                      <Text key={name} style={styles.detectionItem}>
                        {name}: {count}
                      </Text>
                    )
                  )}
                </View>
              )}

              {submission.photos && submission.photos.length > 0 && (
                <ScrollView horizontal style={styles.photos}>
                  {submission.photos.map((photo, index) => (
                    <Image
                      key={index}
                      source={{
                        uri: getApiUrl(API_ENDPOINTS.PHOTO) + '/' + photo,
                      }}
                      style={styles.photo}
                    />
                  ))}
                </ScrollView>
              )}

              <Text style={styles.date}>{formatDate(submission.timestamp_utc)}</Text>
            </View>
          ))
        )}
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
    marginBottom: 24,
  },
  empty: {
    alignItems: 'center',
    padding: 48,
  },
  emptyText: {
    fontSize: 18,
    color: '#94a3b8',
    marginBottom: 8,
  },
  emptySubtext: {
    fontSize: 14,
    color: '#64748b',
  },
  card: {
    backgroundColor: '#1a2332',
    borderRadius: 12,
    padding: 16,
    marginBottom: 16,
  },
  cardHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 12,
  },
  cardTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#f1f5f9',
    marginBottom: 4,
  },
  cardSubtitle: {
    fontSize: 14,
    color: '#94a3b8',
  },
  statusBadge: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 6,
  },
  statusText: {
    fontSize: 11,
    fontWeight: '700',
  },
  notes: {
    fontSize: 14,
    color: '#94a3b8',
    marginBottom: 12,
  },
  feedback: {
    backgroundColor: 'rgba(16,185,129,0.1)',
    padding: 12,
    borderRadius: 8,
    marginBottom: 12,
  },
  feedbackLabel: {
    fontSize: 12,
    fontWeight: '600',
    color: '#10b981',
    marginBottom: 4,
  },
  feedbackText: {
    fontSize: 14,
    color: '#f1f5f9',
  },
  detection: {
    backgroundColor: 'rgba(59,130,246,0.1)',
    padding: 12,
    borderRadius: 8,
    marginBottom: 12,
  },
  detectionLabel: {
    fontSize: 12,
    fontWeight: '600',
    color: '#3b82f6',
    marginBottom: 8,
  },
  detectionItem: {
    fontSize: 14,
    color: '#f1f5f9',
    marginBottom: 4,
  },
  photos: {
    marginBottom: 12,
  },
  photo: {
    width: 100,
    height: 100,
    borderRadius: 8,
    marginRight: 8,
  },
  date: {
    fontSize: 12,
    color: '#64748b',
  },
});

export default SubmissionsScreen;


