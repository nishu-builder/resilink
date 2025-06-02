"use client";

import { useParams } from 'next/navigation';
import useSWR from 'swr';
import api from '@/app/hooks/useApi';
import { useState, useMemo } from 'react';
import { useRouter } from 'next/navigation';

const typeToEndpoint: Record<string, string> = {
  hazards: 'datasets/hazards',
  fragilities: 'datasets/fragilities',
  mappings: 'datasets/mappings',
  buildings: 'datasets/buildings',
};

type Dataset = {
  id: number;
  name: string;
  created_at: string;
};

export default function DatasetPage() {
  const { type } = useParams<{ type: string }>();
  const endpoint = typeToEndpoint[type];
  const singleUploadEndpoint = typeToEndpoint[type];
  const { data, isLoading, mutate } = useSWR<Dataset[]>(endpoint, (url: string) => api.get(url).then((r) => r.data));

  const [files, setFiles] = useState<FileList | null>(null);
  const router = useRouter();

  const fileTypeDescription = useMemo(() => {
    switch (type) {
      case 'hazards':
        return 'Expected: Raster file (e.g., GeoTIFF .tif) for hazard intensity (WSE).';
      case 'buildings':
        return 'Expected: Zipped Shapefile (.zip) containing building inventory.';
      case 'fragilities':
        return 'Expected: JSON file (.json) defining fragility curves.';
      case 'mappings':
        return 'Expected: JSON file (.json) mapping building types to fragility curves.';
      default:
        return '';
    }
  }, [type]);

  const handleUpload = async () => {
    if (!files || files.length === 0) return;

    const isBatch = type === 'fragilities' && files.length > 1;
    const targetEndpoint = isBatch ? singleUploadEndpoint + 'batch' : singleUploadEndpoint;
    const fileInputKey = isBatch ? 'fragility_files' :
      type === 'hazards' ? 'wse_raster' :
        type === 'buildings' ? 'shapefile_zip' :
          type === 'fragilities' ? 'fragility_json' : 'mapping_json';

    const formData = new FormData();

    if (isBatch) {
      for (let i = 0; i < files.length; i++) {
        formData.append(fileInputKey, files[i]);
      }
    } else {
      const file = files[0];
      const fieldKey = fileInputKey;
      formData.append(fieldKey, file);
      formData.append('name', file.name);
    }

    try {
      await api.post(targetEndpoint, formData, { headers: { 'Content-Type': 'multipart/form-data' } });
      setFiles(null);
      const fileInput = document.getElementById('file-input') as HTMLInputElement;
      if (fileInput) fileInput.value = "";
      mutate();
    } catch (error) {
      console.error("Upload failed:", error);
      alert("Upload failed. Check console for details.");
    }
  };

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-semibold capitalize">{type} Datasets</h2>

      <div className="flex gap-4 items-center">
        <input
          id="file-input"
          type="file"
          multiple={type === 'fragilities'}
          onChange={(e) => setFiles(e.target.files)}
        />
        <button
          className="px-4 py-2 bg-blue-600 text-white rounded disabled:opacity-50"
          disabled={!files || files.length === 0}
          onClick={handleUpload}
        >
          Upload {files && files.length > 1 ? `(${files.length} files)` : ''}
        </button>
      </div>

      {fileTypeDescription && (
        <p className="text-sm text-gray-600 mt-1">
          {fileTypeDescription}
        </p>
      )}

      {isLoading ? (
        <p>Loading…</p>
      ) : (
        <table className="w-full text-left">
          <thead>
            <tr>
              <th className="py-2">ID</th>
              <th>Name</th>
              <th>Created</th>
            </tr>
          </thead>
          <tbody>
            {data?.map((d) => (
              <tr 
                key={d.id} 
                className={`border-t hover:bg-muted/50 ${type === 'buildings' ? 'cursor-pointer' : ''}`}
                onClick={() => type === 'buildings' && router.push(`/datasets/buildings/${d.id}`)}
              >
                <td className="py-2">{d.id}</td>
                <td>{d.name}</td>
                <td>{new Date(d.created_at).toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
