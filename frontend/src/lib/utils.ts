import { type ClassValue, clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

export const cn = (...inputs: ClassValue[]) => twMerge(clsx(inputs));

export const formatDateTime = (dateIso?: string) => {
  if (!dateIso) return '';
  try {
    const date = new Date(dateIso);
    return date.toLocaleString();
  } catch (error) {
    return dateIso;
  }
};
