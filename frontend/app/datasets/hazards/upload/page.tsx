'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { ArrowLeft, Upload, AlertCircle } from 'lucide-react';

export default function HazardUploadPage() {
  const router = useRouter();
  const [name, setName] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!name || !file) {
      setError('Please provide both a name and file');
      return;
    }

    setUploading(true);
    setError('');

    const formData = new FormData();
    formData.append('name', name);
    formData.append('wse_raster', file);

    try {
      const response = await fetch('/api/datasets/hazards', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Upload failed');
      }

      const hazard = await response.json();
      router.push(`/datasets/hazards/${hazard.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed');
      setUploading(false);
    }
  };

  return (
    <div className="container mx-auto p-6 max-w-2xl">
      <div className="mb-6">
        <Link href="/datasets/hazards">
          <Button variant="ghost" size="sm">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Hazards
          </Button>
        </Link>
      </div>

      <Card className="p-6">
        <div className="mb-6">
          <h1 className="text-2xl font-bold">Upload Flood Hazard</h1>
          <p className="text-muted-foreground mt-1">
            Upload a water surface elevation GeoTIFF raster file
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="space-y-2">
            <Label htmlFor="name">Hazard Name</Label>
            <Input
              id="name"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g., Denver 100-Year Flood"
              required
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="file">GeoTIFF File</Label>
            <Input
              id="file"
              type="file"
              accept=".tif,.tiff"
              onChange={(e) => setFile(e.target.files?.[0] || null)}
              required
            />
            <p className="text-sm text-muted-foreground">
              Upload a .tif or .tiff file containing water surface elevation data
            </p>
          </div>

          {error && (
            <div className="flex items-center gap-2 p-3 bg-red-50 text-red-600 rounded-md">
              <AlertCircle className="h-4 w-4" />
              <span className="text-sm">{error}</span>
            </div>
          )}

          <div className="flex gap-3">
            <Button
              type="submit"
              disabled={uploading || !name || !file}
              className="flex-1"
            >
              {uploading ? (
                <>Uploading...</>
              ) : (
                <>
                  <Upload className="mr-2 h-4 w-4" />
                  Upload Hazard
                </>
              )}
            </Button>
            <Link href="/datasets/hazards">
              <Button type="button" variant="outline">
                Cancel
              </Button>
            </Link>
          </div>
        </form>
      </Card>
    </div>
  );
}