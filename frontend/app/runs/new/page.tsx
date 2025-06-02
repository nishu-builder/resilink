"use client";

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import useSWR from 'swr';
import api from '@/app/hooks/useApi';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Button } from '@/components/ui/button';

type Hazard = { id: number; name: string };
type MappingSet = { id: number; name: string };
type BuildingDataset = { id: number; name: string };

export default function NewRunPage() {
  const router = useRouter();
  const [name, setName] = useState('');
  const [hazardId, setHazardId] = useState<string>('');
  const [mappingSetId, setMappingSetId] = useState<string>('');
  const [buildingDatasetId, setBuildingDatasetId] = useState<string>('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const { data: hazards, isLoading: isLoadingHazards } = useSWR<Hazard[]>('datasets/hazards/', (url: string) => api.get(url).then((r) => r.data));
  const { data: mappingSets, isLoading: isLoadingMappings } = useSWR<MappingSet[]>('datasets/mappings/', (url: string) => api.get(url).then((r) => r.data));
  const { data: buildingDatasets, isLoading: isLoadingBuildings } = useSWR<BuildingDataset[]>('datasets/buildings/', (url: string) => api.get(url).then((r) => r.data));

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError(null);
    setIsLoading(true);

    if (!name || !hazardId || !mappingSetId || !buildingDatasetId) {
      setError('All fields are required.');
      setIsLoading(false);
      return;
    }

    try {
      await api.post('runs/', {
        name,
        hazard_id: parseInt(hazardId, 10),
        mapping_set_id: parseInt(mappingSetId, 10),
        building_dataset_id: parseInt(buildingDatasetId, 10),
      });
      router.push('/runs'); // Redirect to runs list after successful creation
    } catch (err: any) {
      console.error("Failed to create run:", err);
      setError(err.response?.data?.detail || 'Failed to create run. Please check inputs and try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const isFetchingData = isLoadingHazards || isLoadingMappings || isLoadingBuildings;

  return (
    <div className="space-y-6 max-w-2xl mx-auto">
      <h1 className="text-2xl font-semibold">Create New Run</h1>

      {isFetchingData ? (
        <p>Loading datasets...</p>
      ) : (
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <Label htmlFor="run-name">Run Name</Label>
            <Input
              id="run-name"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              className="mt-1"
            />
          </div>

          <div>
            <Label htmlFor="hazard-select">Hazard Dataset</Label>
            <Select value={hazardId} onValueChange={setHazardId} required>
              <SelectTrigger id="hazard-select" className="mt-1">
                <SelectValue placeholder="Select a hazard dataset" />
              </SelectTrigger>
              <SelectContent>
                {hazards?.map((hazard) => (
                  <SelectItem key={hazard.id} value={String(hazard.id)}>
                    {hazard.name} (ID: {hazard.id})
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div>
            <Label htmlFor="mapping-select">Mapping Set</Label>
            <Select value={mappingSetId} onValueChange={setMappingSetId} required>
              <SelectTrigger id="mapping-select" className="mt-1">
                <SelectValue placeholder="Select a mapping set" />
              </SelectTrigger>
              <SelectContent>
                {mappingSets?.map((mapping) => (
                  <SelectItem key={mapping.id} value={String(mapping.id)}>
                    {mapping.name} (ID: {mapping.id})
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div>
            <Label htmlFor="building-select">Building Dataset</Label>
            <Select value={buildingDatasetId} onValueChange={setBuildingDatasetId} required>
              <SelectTrigger id="building-select" className="mt-1">
                <SelectValue placeholder="Select a building dataset" />
              </SelectTrigger>
              <SelectContent>
                {buildingDatasets?.map((building) => (
                  <SelectItem key={building.id} value={String(building.id)}>
                    {building.name} (ID: {building.id})
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {error && <p className="text-red-600">{'Error'}</p>}

          <Button type="submit" disabled={isLoading || isFetchingData}>
            {isLoading ? 'Creating...' : 'Create Run'}
          </Button>
        </form>
      )}
    </div>
  );
} 