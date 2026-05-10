import request from './request'

export function generateStory(data) {
  return request.post('/generate/story', data, { timeout: 120000 })
}

export function generateStoryAsync(data) {
  return request.post('/generate/story/async', data, { timeout: 30000 })
}

export function generateImage(data) {
  return request.post('/generate/image', data, { timeout: 120000 })
}

export function generateImageAsync(data) {
  return request.post('/generate/image/async', data, { timeout: 30000 })
}

export function generateVideo(data) {
  return request.post('/generate/video', data, { timeout: 180000 })
}

export function generateVideoAsync(data) {
  return request.post('/generate/video/async', data, { timeout: 30000 })
}
