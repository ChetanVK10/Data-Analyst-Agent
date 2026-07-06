import React, { useCallback, useState, useRef } from 'react';
import { Upload as UploadIcon } from 'lucide-react';
import './UploadZone.css';

interface UploadZoneProps {
  onFileSelect: (file: File) => void;
  accept?: string;
  loading?: boolean;
  disabled?: boolean;
  maxSizeMB?: number;
}

export const UploadZone: React.FC<UploadZoneProps> = ({
  onFileSelect,
  accept = '.csv',
  loading = false,
  disabled = false,
  maxSizeMB = 100,
}) => {
  const [isDragOver, setIsDragOver] = useState(false);
  const [error, setError] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);

  const validateAndSelect = useCallback((file: File) => {
    setError('');
    if (maxSizeMB && file.size > maxSizeMB * 1024 * 1024) {
      setError(`File exceeds ${maxSizeMB}MB limit.`);
      return;
    }
    onFileSelect(file);
  }, [onFileSelect, maxSizeMB]);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    if (disabled || loading) return;
    const file = e.dataTransfer.files[0];
    if (file) validateAndSelect(file);
  }, [disabled, loading, validateAndSelect]);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    if (!disabled && !loading) setIsDragOver(true);
  }, [disabled, loading]);

  const handleDragLeave = useCallback(() => {
    setIsDragOver(false);
  }, []);

  const handleClick = () => {
    if (!disabled && !loading) inputRef.current?.click();
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) validateAndSelect(file);
    // Reset input so same file can be re-selected
    e.target.value = '';
  };

  return (
    <div className="ds-upload-zone-wrapper">
      <div
        className={`ds-upload-zone ${isDragOver ? 'ds-upload-zone--drag' : ''} ${loading ? 'ds-upload-zone--loading' : ''} ${disabled ? 'ds-upload-zone--disabled' : ''}`}
        onClick={handleClick}
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        role="button"
        tabIndex={0}
        aria-label="Upload file"
      >
        <input
          ref={inputRef}
          type="file"
          accept={accept}
          onChange={handleChange}
          style={{ display: 'none' }}
          disabled={disabled || loading}
        />

        <div className="ds-upload-zone__icon">
          {loading ? (
            <svg className="ds-upload-zone__spinner" width="24" height="24" viewBox="0 0 24 24" fill="none">
              <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeDasharray="50" strokeDashoffset="15" />
            </svg>
          ) : (
            <UploadIcon size={22} />
          )}
        </div>

        <div className="ds-upload-zone__text">
          <span className="ds-upload-zone__primary">
            {loading ? 'Processing file...' : 'Drop your CSV here or click to browse'}
          </span>
          <span className="ds-upload-zone__hint">
            {loading ? 'Normalizing encoding and registering table' : `CSV files up to ${maxSizeMB}MB`}
          </span>
        </div>
      </div>

      {error && <p className="ds-upload-zone__error">{error}</p>}
    </div>
  );
};
