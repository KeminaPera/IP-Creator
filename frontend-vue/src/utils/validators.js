/**
 * validators - Form validation factory functions
 * 
 * Centralizes form validation rules to avoid duplication.
 * Provides i18n support for validation messages.
 * 
 * @example
 * import { createValidators } from '@/utils/validators'
 * 
 * const v = createValidators()
 * 
 * const formRules = {
 *   name: [v.required('名称'), v.length(2, 50)],
 *   email: [v.required('邮箱'), v.email()],
 *   phone: [v.pattern(/^1\d{10}$/, '请输入正确的手机号')]
 * }
 */
import { useI18n } from 'vue-i18n'

/**
 * Create validator functions with i18n support
 * 
 * @returns {Object} Validator functions
 */
export function createValidators() {
  const { t } = useI18n()

  return {
    /**
     * Required field validator
     * @param {string} fieldName - Field name for error message
     * @param {string} trigger - Validation trigger (default: 'blur')
     * @returns {Object} Validation rule
     */
    required(fieldName = '', trigger = 'blur') {
      const message = fieldName 
        ? t('validation.required_field', { field: fieldName })
        : t('validation.required')
      
      return { 
        required: true, 
        message, 
        trigger 
      }
    },

    /**
     * Length range validator
     * @param {number} min - Minimum length
     * @param {number} max - Maximum length
     * @param {string} trigger - Validation trigger
     * @returns {Object} Validation rule
     */
    length(min, max, trigger = 'blur') {
      return {
        min,
        max,
        message: t('validation.length_range', { min, max }),
        trigger
      }
    },

    /**
     * Minimum length validator
     * @param {number} min - Minimum length
     * @param {string} trigger - Validation trigger
     * @returns {Object} Validation rule
     */
    minLength(min, trigger = 'blur') {
      return {
        min,
        message: t('validation.min_length', { min }),
        trigger
      }
    },

    /**
     * Maximum length validator
     * @param {number} max - Maximum length
     * @param {string} trigger - Validation trigger
     * @returns {Object} Validation rule
     */
    maxLength(max, trigger = 'blur') {
      return {
        max,
        message: t('validation.max_length', { max }),
        trigger
      }
    },

    /**
     * Email format validator
     * @param {string} trigger - Validation trigger
     * @returns {Object} Validation rule
     */
    email(trigger = 'blur') {
      return {
        type: 'email',
        message: t('validation.email_format'),
        trigger
      }
    },

    /**
     * URL format validator
     * @param {string} trigger - Validation trigger
     * @returns {Object} Validation rule
     */
    url(trigger = 'blur') {
      return {
        type: 'url',
        message: t('validation.url_format'),
        trigger
      }
    },

    /**
     * Pattern (regex) validator
     * @param {RegExp} pattern - Regular expression
     * @param {string} message - Error message
     * @param {string} trigger - Validation trigger
     * @returns {Object} Validation rule
     */
    pattern(pattern, message, trigger = 'blur') {
      return {
        pattern,
        message,
        trigger
      }
    },

    /**
     * Number range validator
     * @param {number} min - Minimum value
     * @param {number} max - Maximum value
     * @param {string} trigger - Validation trigger
     * @returns {Object} Validation rule
     */
    range(min, max, trigger = 'blur') {
      return {
        type: 'number',
        min,
        max,
        message: t('validation.number_range', { min, max }),
        trigger
      }
    },

    /**
     * Custom validator function
     * @param {Function} validatorFn - Custom validation function
     * @param {string} message - Error message
     * @param {string} trigger - Validation trigger
     * @returns {Object} Validation rule
     */
    custom(validatorFn, message, trigger = 'blur') {
      return {
        validator: (rule, value, callback) => {
          const result = validatorFn(value)
          if (result === true) {
            callback()
          } else {
            callback(new Error(result || message))
          }
        },
        trigger
      }
    },

    /**
     * Phone number validator (Chinese format)
     * @param {string} trigger - Validation trigger
     * @returns {Object} Validation rule
     */
    phone(trigger = 'blur') {
      return {
        pattern: /^1[3-9]\d{9}$/,
        message: t('validation.phone_format'),
        trigger
      }
    },

    /**
     * Array must have at least one item
     * @param {string} message - Error message
     * @param {string} trigger - Validation trigger
     * @returns {Object} Validation rule
     */
    arrayNotEmpty(message = '', trigger = 'change') {
      return {
        validator: (rule, value, callback) => {
          if (!value || value.length === 0) {
            callback(new Error(message || t('validation.array_not_empty')))
          } else {
            callback()
          }
        },
        trigger
      }
    }
  }
}

/**
 * Predefined common validation rule sets
 */
export const validationPresets = {
  /**
   * Name validation (2-50 characters)
   */
  name() {
    const v = createValidators()
    return [v.required('名称'), v.length(2, 50)]
  },

  /**
   * Description validation (max 500 characters)
   */
  description() {
    const v = createValidators()
    return [v.maxLength(500)]
  },

  /**
   * Email validation (required + format)
   */
  email() {
    const v = createValidators()
    return [v.required('邮箱'), v.email()]
  },

  /**
   * URL validation (required + format)
   */
  url() {
    const v = createValidators()
    return [v.required('链接'), v.url()]
  }
}
