/**
 * Zod-based form validation helper.
 */

import { useState } from 'react';
import { z } from 'zod';

export const useFormValidation = <T extends z.ZodTypeAny>(schema: T) => {
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [touched, setTouched] = useState<Record<string, boolean>>({});

  const validateField = (field: string, value: unknown) => {
    const shape = (schema as unknown as { shape?: Record<string, z.ZodTypeAny> }).shape;
    const fieldSchema = shape?.[field];
    if (!fieldSchema) return;

    try {
      fieldSchema.parse(value);
      setErrors((prev) => {
        const next = { ...prev };
        delete next[field];
        return next;
      });
    } catch (err) {
      if (err instanceof z.ZodError) {
        setErrors((prev) => ({
          ...prev,
          [field]: err.issues[0]?.message || 'Invalid value',
        }));
      }
    }
  };

  const validateForm = (data: unknown) => {
    try {
      schema.parse(data);
      setErrors({});
      setTouched({});
      return true;
    } catch (err) {
      if (err instanceof z.ZodError) {
        const next: Record<string, string> = {};
        err.issues.forEach((issue: z.ZodIssue) => {
          const path = issue.path.join('.');
          next[path] = issue.message;
        });
        setErrors(next);
        setTouched((prev) => {
          const touchedNext = { ...prev };
          Object.keys(next).forEach((key) => {
            touchedNext[key] = true;
          });
          return touchedNext;
        });
      }
      return false;
    }
  };

  const handleBlur = (field: string) => {
    setTouched((prev) => ({ ...prev, [field]: true }));
  };

  const getFieldError = (field: string) => {
    return touched[field] ? errors[field] : undefined;
  };

  return {
    errors,
    validateField,
    validateForm,
    handleBlur,
    getFieldError,
  };
};
