"use client";

import { useParams } from 'next/navigation';
import useSWR from 'swr';
import api from '@/app/hooks/useApi';
import { useState } from 'react';
import { useRouter } from 'next/navigation';

type Building = {
  id: number;
  guid: string;
  dataset_id: number;
  properties: Record<string, any>;
  asset_value: number | null;
  created_at: string;
};

type BuildingDataset = {
  id: number;
  name: string;
  feature_count: number;
  created_at: string;
};

export default function BuildingDatasetDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  
  // Fetch dataset info
  const { data: dataset } = useSWR<BuildingDataset>(
    `datasets/buildings/${id}`,
    (url: string) => api.get(url).then((r) => r.data)
  );
  
  // Fetch buildings for this dataset
  const { data: buildings, mutate } = useSWR<Building[]>(
    `datasets/buildings/${id}/buildings`,
    (url: string) => api.get(url).then((r) => r.data)
  );
  
  const [editingBuilding, setEditingBuilding] = useState<string | null>(null);
  const [editValue, setEditValue] = useState<string>('');
  const [saving, setSaving] = useState(false);
  
  const handleEditStart = (buildingGuid: string, currentValue: number | null) => {
    setEditingBuilding(buildingGuid);
    setEditValue(currentValue?.toString() || '');
  };
  
  const handleSave = async (buildingGuid: string) => {
    if (!editValue || isNaN(Number(editValue))) {
      alert('Please enter a valid number');
      return;
    }
    
    setSaving(true);
    try {
      await api.post(`datasets/buildings/${id}/${buildingGuid}`, {
        asset_value: parseFloat(editValue)
      });
      
      // Update local data
      mutate();
      setEditingBuilding(null);
      setEditValue('');
    } catch (error) {
      console.error('Failed to update asset value:', error);
      alert('Failed to update asset value');
    } finally {
      setSaving(false);
    }
  };
  
  const handleCancel = () => {
    setEditingBuilding(null);
    setEditValue('');
  };
  
  if (!buildings || !dataset) {
    return <div>Loading...</div>;
  }
  
  // Get unique property keys from all buildings
  const propertyKeys = new Set<string>();
  buildings.forEach(building => {
    Object.keys(building.properties).forEach(key => propertyKeys.add(key));
  });
  const sortedKeys = Array.from(propertyKeys).sort();
  
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <button
            onClick={() => router.push('/datasets/buildings')}
            className="text-blue-600 hover:text-blue-800 mb-2"
          >
            ← Back to Building Datasets
          </button>
          <h2 className="text-2xl font-semibold">{dataset.name}</h2>
          <p className="text-gray-600">
            {dataset.feature_count} buildings • ID: {dataset.id}
          </p>
        </div>
      </div>
      
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-2 font-medium">Building ID</th>
              {sortedKeys.map(key => (
                <th key={key} className="px-4 py-2 font-medium">
                  {key}
                </th>
              ))}
              <th className="px-4 py-2 font-medium">Asset Value ($)</th>
              <th className="px-4 py-2 font-medium">Actions</th>
            </tr>
          </thead>
          <tbody>
            {buildings.map((building) => (
              <tr key={building.guid} className="border-t hover:bg-gray-50">
                <td className="px-4 py-2 font-mono text-xs">{building.guid}</td>
                {sortedKeys.map(key => (
                  <td key={key} className="px-4 py-2">
                    {building.properties[key]?.toString() || '-'}
                  </td>
                ))}
                <td className="px-4 py-2">
                  {editingBuilding === building.guid ? (
                    <input
                      type="number"
                      value={editValue}
                      onChange={(e) => setEditValue(e.target.value)}
                      className="w-32 px-2 py-1 border rounded"
                      placeholder="Enter value"
                      autoFocus
                    />
                  ) : (
                    <span className={building.asset_value ? 'font-medium' : 'text-gray-400'}>
                      {building.asset_value ? `$${building.asset_value.toLocaleString()}` : 'Not set'}
                    </span>
                  )}
                </td>
                <td className="px-4 py-2">
                  {editingBuilding === building.guid ? (
                    <div className="flex gap-2">
                      <button
                        onClick={() => handleSave(building.guid)}
                        disabled={saving}
                        className="px-3 py-1 bg-green-600 text-white rounded text-sm disabled:opacity-50"
                      >
                        {saving ? 'Saving...' : 'Save'}
                      </button>
                      <button
                        onClick={handleCancel}
                        disabled={saving}
                        className="px-3 py-1 bg-gray-600 text-white rounded text-sm disabled:opacity-50"
                      >
                        Cancel
                      </button>
                    </div>
                  ) : (
                    <button
                      onClick={() => handleEditStart(building.guid, building.asset_value)}
                      className="px-3 py-1 bg-blue-600 text-white rounded text-sm"
                    >
                      Edit
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}