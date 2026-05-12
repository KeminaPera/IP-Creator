/**
 * grade - Quality grade utility functions
 * 
 * Centralizes grade type/color mappings used across multiple components.
 * Eliminates duplicate grade mapping logic.
 * 
 * @example
 * import { getGradeType, getGradeColor, getGradeDescription } from '@/utils/grade'
 * 
 * // In template
 * <el-tag :type="getGradeType('A')">A</el-tag>
 * 
 * // With color
 * <div :style="{ color: getGradeColor('S') }">S Grade</div>
 * 
 * // With i18n
 * const desc = getGradeDescription('A', t)
 */

/**
 * Grade to Element Plus tag type mapping
 */
export const GRADE_TYPE_MAP = {
  S: 'success',
  A: 'success',
  B: 'primary',
  C: 'warning',
  D: 'danger',
  F: 'danger'
}

/**
 * Grade to color mapping
 */
export const GRADE_COLOR_MAP = {
  S: '#67C23A',
  A: '#67C23A',
  B: '#409EFF',
  C: '#E6A23C',
  D: '#F56C6C',
  F: '#F56C6C'
}

/**
 * Grade descriptions (for reference, actual i18n keys are dynamic)
 */
export const GRADE_DESCRIPTIONS = {
  S: 'lora.quality.grade_s',
  A: 'lora.quality.grade_a',
  B: 'lora.quality.grade_b',
  C: 'lora.quality.grade_c',
  D: 'lora.quality.grade_d',
  F: 'lora.quality.grade_f'
}

/**
 * Get Element Plus tag type for a grade
 * 
 * @param {string} grade - Grade letter (S, A, B, C, D, F)
 * @returns {string} Element Plus tag type
 */
export function getGradeType(grade) {
  return GRADE_TYPE_MAP[grade] || 'info'
}

/**
 * Get color for a grade
 * 
 * @param {string} grade - Grade letter (S, A, B, C, D, F)
 * @returns {string} Hex color code
 */
export function getGradeColor(grade) {
  return GRADE_COLOR_MAP[grade] || '#909399'
}

/**
 * Get grade description from i18n
 * 
 * @param {string} grade - Grade letter (S, A, B, C, D, F)
 * @param {Function} t - i18n translation function
 * @returns {string} Localized grade description
 */
export function getGradeDescription(grade, t) {
  const key = GRADE_DESCRIPTIONS[grade]
  if (!key || !t) return grade
  return t(key)
}

/**
 * Get full grade info (type, color, description)
 * 
 * @param {string} grade - Grade letter (S, A, B, C, D, F)
 * @param {Function} t - i18n translation function (optional)
 * @returns {Object} Grade info object
 */
export function getGradeInfo(grade, t = null) {
  return {
    type: getGradeType(grade),
    color: getGradeColor(grade),
    description: t ? getGradeDescription(grade, t) : null
  }
}

/**
 * Check if grade is passing (C or better)
 * 
 * @param {string} grade - Grade letter
 * @returns {boolean} True if passing
 */
export function isPassingGrade(grade) {
  return ['S', 'A', 'B', 'C'].includes(grade)
}

/**
 * Check if grade is excellent (A or S)
 * 
 * @param {string} grade - Grade letter
 * @returns {boolean} True if excellent
 */
export function isExcellentGrade(grade) {
  return ['S', 'A'].includes(grade)
}

/**
 * Get numeric score range for a grade
 * 
 * @param {string} grade - Grade letter
 * @returns {Object} Score range { min, max }
 */
export function getGradeScoreRange(grade) {
  const ranges = {
    S: { min: 95, max: 100 },
    A: { min: 85, max: 94 },
    B: { min: 70, max: 84 },
    C: { min: 60, max: 69 },
    D: { min: 40, max: 59 },
    F: { min: 0, max: 39 }
  }
  return ranges[grade] || { min: 0, max: 100 }
}

/**
 * Convert numeric score to grade letter
 * 
 * @param {number} score - Numeric score (0-100)
 * @returns {string} Grade letter
 */
export function scoreToGrade(score) {
  if (score >= 95) return 'S'
  if (score >= 85) return 'A'
  if (score >= 70) return 'B'
  if (score >= 60) return 'C'
  if (score >= 40) return 'D'
  return 'F'
}
