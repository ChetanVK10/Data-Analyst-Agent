import React, { useCallback, useState, useRef } from 'react';
import { Upload as UploadIcon, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';

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
    e.target.value = '';
  };

  return (
    <div className="w-full max-w-2xl mx-auto space-y-4">
      <div
        className={cn(
          "glass-card relative flex flex-col items-center justify-center rounded-2xl border-2 border-dashed p-12 transition-all duration-300",
          isDragOver ? "border-primary bg-primary/5 scale-[1.02]" : "border-border hover:border-primary/50 hover:bg-white/5",
          (disabled || loading) && "opacity-50 cursor-not-allowed",
          !disabled && !loading && "cursor-pointer"
        )}
        onClick={handleClick}
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        role="button"
        tabIndex={0}
      >
        <input
          ref={inputRef}
          type="file"
          accept={accept}
          onChange={handleChange}
          style={{ display: 'none' }}
          disabled={disabled || loading}
        />

        <div className="mb-4 rounded-full bg-primary/10 p-4 text-primary">
          {loading ? (
            <Loader2 className="h-8 w-8 animate-spin" />
          ) : (
            <UploadIcon className="h-8 w-8" />
          )}
        </div>

        <div className="text-center space-y-2">
          <h3 className="text-lg font-semibold tracking-tight">
            {loading ? 'Processing dataset...' : 'Drop your CSV here or click to browse'}
          </h3>
          <p className="text-sm text-muted-foreground">
            {loading ? 'Normalizing encoding and registering table' : `CSV files up to ${maxSizeMB}MB`}
          </p>
        </div>
      </div>

      {error && (
        <div className="text-center text-sm font-medium text-destructive">
          {error}
        </div>
      )}
    </div>
  );
};
