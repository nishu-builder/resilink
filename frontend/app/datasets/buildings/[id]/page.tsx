"use client";

import { useParams } from 'next/navigation';
import useSWR from 'swr';
import api from '@/app/hooks/useApi';
import { useState, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import dynamic from 'next/dynamic';

// Dynamically import the map component to avoid SSR issues
const BuildingsMapViewer = dynamic(() => import('@/app/components/BuildingsMapViewer'), {
  ssr: false,
  loading: () => <div className="h-96 bg-gray-100 animate-pulse rounded-lg" />
});

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

type SortField = 'guid' | 'asset_value' | string; // string for property keys
type SortDirection = 'asc' | 'desc';

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
  
  // Sorting state
  const [sortField, setSortField] = useState<SortField>('guid');
  const [sortDirection, setSortDirection] = useState<SortDirection>('asc');
  
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
      await api.post(`datasets/buildings/${id}/buildings/${buildingGuid}`, {
        asset_value: Number(editValue)
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

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      // Toggle direction if same field
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      // New field, default to ascending
      setSortField(field);
      setSortDirection('asc');
    }
  };

  const sortedBuildings = useMemo(() => {
    if (!buildings) return [];
    
    const sorted = [...buildings].sort((a, b) => {
      let aValue: any;
      let bValue: any;
      
      if (sortField === 'guid') {
        aValue = a.guid;
        bValue = b.guid;
      } else if (sortField === 'asset_value') {
        aValue = a.asset_value || 0;
        bValue = b.asset_value || 0;
      } else {
        // Property field
        aValue = a.properties[sortField] || '';
        bValue = b.properties[sortField] || '';
      }
      
      // Convert to string for comparison if not numbers
      if (typeof aValue !== 'number' && typeof bValue !== 'number') {
        aValue = String(aValue).toLowerCase();
        bValue = String(bValue).toLowerCase();
      }
      
      if (aValue < bValue) return sortDirection === 'asc' ? -1 : 1;
      if (aValue > bValue) return sortDirection === 'asc' ? 1 : -1;
      return 0;
    });
    
    return sorted;
  }, [buildings, sortField, sortDirection]);
  
  if (!buildings || !dataset) {
    return <div>Loading...</div>;
  }
  
  // Get unique property keys from all buildings
  const propertyKeys = new Set<string>();
  buildings.forEach(building => {
    Object.keys(building.properties).forEach(key => propertyKeys.add(key));
  });
  const sortedKeys = Array.from(propertyKeys).sort();

  const SortIcon = ({ field }: { field: SortField }) => {
    if (sortField !== field) {
      return <span className="text-gray-400 ml-1">↕</span>;
    }
    return (
      <span className="ml-1">
        {sortDirection === 'asc' ? '↑' : '↓'}
      </span>
    );
  };
  
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

      {/* Map View */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
        <h3 className="text-lg font-semibold mb-3">Building Locations</h3>
        <BuildingsMapViewer datasetId={Number(id)} className="h-96 rounded-lg overflow-hidden" />
      </div>
      
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead className="bg-gray-50">
            <tr>
              <th 
                className="px-4 py-2 font-medium cursor-pointer hover:bg-gray-100"
                onClick={() => handleSort('guid')}
              >
                Building ID
                <SortIcon field="guid" />
              </th>
              {sortedKeys.map(key => (
                <th 
                  key={key} 
                  className="px-4 py-2 font-medium cursor-pointer hover:bg-gray-100"
                  onClick={() => handleSort(key)}
                >
                  {key}
                  <SortIcon field={key} />
                </th>
              ))}
              <th 
                className="px-4 py-2 font-medium cursor-pointer hover:bg-gray-100"
                onClick={() => handleSort('asset_value')}
              >
                Asset Value ($)
                <SortIcon field="asset_value" />
              </th>
              <th className="px-4 py-2 font-medium">Actions</th>
            </tr>
          </thead>
          <tbody>
            {sortedBuildings.map((building) => (
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