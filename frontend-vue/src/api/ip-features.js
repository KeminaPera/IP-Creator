/**
 * IP Features API Client
 * 
 * API endpoints for managing IP feature library including:
 * - Multi-view management (front/side/back views)
 * - Feature library (outfits, expressions, poses, etc.)
 * - Feature images management
 */
import request from '@/api/request'

// ============================================
// Multi-View APIs
// ============================================

/**
 * Create a new multi-view for an IP asset
 */
export function createMultiView(ipId, data) {
  return request({
    url: `/api/v1/ip/${ipId}/multi-views`,
    method: 'post',
    data
  })
}

/**
 * Get all multi-views for an IP asset
 */
export function getMultiViews(ipId) {
  return request({
    url: `/api/v1/ip/${ipId}/multi-views`,
    method: 'get'
  })
}

/**
 * Delete a multi-view
 */
export function deleteMultiView(ipId, viewId) {
  return request({
    url: `/api/v1/ip/${ipId}/multi-views/${viewId}`,
    method: 'delete'
  })
}

// ============================================
// Feature Library APIs
// ============================================

/**
 * Create a new feature for an IP asset
 */
export function createFeature(ipId, data) {
  return request({
    url: `/api/v1/ip/${ipId}/features`,
    method: 'post',
    data
  })
}

/**
 * Get all features for an IP asset
 */
export function getFeatures(ipId, params = {}) {
  return request({
    url: `/api/v1/ip/${ipId}/features`,
    method: 'get',
    params
  })
}

/**
 * Get a specific feature
 */
export function getFeature(ipId, featureId) {
  return request({
    url: `/api/v1/ip/${ipId}/features/${featureId}`,
    method: 'get'
  })
}

/**
 * Update a feature
 */
export function updateFeature(ipId, featureId, data) {
  return request({
    url: `/api/v1/ip/${ipId}/features/${featureId}`,
    method: 'patch',
    data
  })
}

/**
 * Delete a feature
 */
export function deleteFeature(ipId, featureId) {
  return request({
    url: `/api/v1/ip/${ipId}/features/${featureId}`,
    method: 'delete'
  })
}

// ============================================
// Feature Image APIs
// ============================================

/**
 * Add an image to a feature
 */
export function createFeatureImage(featureId, data) {
  return request({
    url: `/api/v1/ip/features/${featureId}/images`,
    method: 'post',
    data
  })
}

/**
 * Get all images for a feature
 */
export function getFeatureImages(featureId) {
  return request({
    url: `/api/v1/ip/features/${featureId}/images`,
    method: 'get'
  })
}

/**
 * Delete a feature image
 */
export function deleteFeatureImage(featureId, imageId) {
  return request({
    url: `/api/v1/ip/features/${featureId}/images/${imageId}`,
    method: 'delete'
  })
}

// ============================================
// Feature Type Configuration APIs
// ============================================

/**
 * Get all supported feature types configuration
 */
export function getFeatureTypes() {
  return request({
    url: '/api/v1/ip/feature-types',
    method: 'get'
  })
}
