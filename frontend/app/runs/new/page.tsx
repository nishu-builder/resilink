"use client";

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import useSWR from 'swr';
import api from '@/app/hooks/useApi';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Button } from '@/components/ui/button';
import { PlusCircle, XCircle } from 'lucide-react';

type Hazard = { id: number; name: string };
type MappingSet = { id: number; name: string };
type BuildingDataset = { id: number; name: string };
type RunGroup = { id: number; name: string };
type Intervention = { id: number; name: string; type: string };

type Building = {
  id: number;
  guid: string;
  dataset_id: number;
  properties: Record<string, any>;
  asset_value: number | null;
  created_at: string;
};

type InterventionInput = {
  building_id: string;
  intervention_id: number;
  parameters: { elevation_ft?: number };
  cost?: number;
};

export default function NewRunPage() {
  const router = useRouter();
  const [name, setName] = useState('');
  const [hazardId, setHazardId] = useState<string>('');
  const [mappingSetId, setMappingSetId] = useState<string>('');
  const [buildingDatasetId, setBuildingDatasetId] = useState<string>('');
  const [runGroupId, setRunGroupId] = useState<string>('');
  const [interventions, setInterventions] = useState<InterventionInput[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const { data: hazards, isLoading: isLoadingHazards } = useSWR<Hazard[]>('datasets/hazards', (url: string) => api.get(url).then((r) => r.data));
  const { data: mappingSets, isLoading: isLoadingMappings } = useSWR<MappingSet[]>('datasets/mappings', (url: string) => api.get(url).then((r) => r.data));
  const { data: buildingDatasets, isLoading: isLoadingBuildings } = useSWR<BuildingDataset[]>('datasets/buildings', (url: string) => api.get(url).then((r) => r.data));
  const { data: runGroups, isLoading: isLoadingGroups } = useSWR<RunGroup[]>('runs/groups', (url: string) => api.get(url).then((r) => r.data));
  const { data: interventionTypes, isLoading: isLoadingInterventions } = useSWR<Intervention[]>('interventions', (url: string) => api.get(url).then((r) => r.data));
  
  // Fetch buildings for the selected building dataset
  const { data: buildings } = useSWR<Building[]>(
    buildingDatasetId ? `datasets/buildings/${buildingDatasetId}/buildings` : null,
    (url: string) => api.get(url).then((r) => r.data)
  );

  const addIntervention = () => {
    setInterventions([...interventions, {
      building_id: '',
      intervention_id: 1,
      parameters: { elevation_ft: 0 },
      cost: undefined
    }]);
  };

  const removeIntervention = (index: number) => {
    setInterventions(interventions.filter((_, i) => i !== index));
  };

  const updateIntervention = (index: number, field: keyof InterventionInput, value: any) => {
    const updated = [...interventions];
    if (field === 'parameters') {
      updated[index] = { ...updated[index], parameters: { ...updated[index].parameters, ...value } };
    } else {
      updated[index] = { ...updated[index], [field]: value };
    }
    setInterventions(updated);
  };

  // Format building display string for dropdown
  const formatBuildingOption = (building: Building) => {
    const propertyKeys = Object.keys(building.properties).slice(0, 2); // Show first 2 properties
    const propertyDisplay = propertyKeys.map(key => `${key}: ${building.properties[key]}`).join(', ');
    const assetValue = building.asset_value ? `$${building.asset_value.toLocaleString()}` : 'No value';
    
    return `${building.guid} | ${propertyDisplay} | ${assetValue}`;
  };

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
      const payload: any = {
        name,
        hazard_id: parseInt(hazardId, 10),
        mapping_set_id: parseInt(mappingSetId, 10),
        building_dataset_id: parseInt(buildingDatasetId, 10),
      };

      if (runGroupId) {
        payload.run_group_id = parseInt(runGroupId, 10);
      }

      if (interventions.length > 0) {
        payload.interventions = interventions.map(i => ({
          ...i,
          intervention_id: parseInt(i.intervention_id.toString(), 10),
          cost: i.cost ? parseFloat(i.cost.toString()) : undefined,
          parameters: {
            elevation_ft: i.parameters.elevation_ft ? parseFloat(i.parameters.elevation_ft.toString()) : 0
          }
        }));
      }

      await api.post('runs', payload);
      router.push('/runs');
    } catch (err: any) {
      console.error("Failed to create run:", err);
      setError(err.response?.data?.detail || 'Failed to create run. Please check inputs and try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const isFetchingData = isLoadingHazards || isLoadingMappings || isLoadingBuildings || isLoadingGroups || isLoadingInterventions;

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      <h1 className="text-2xl font-semibold">Create New Run</h1>

      {isFetchingData ? (
        <p>Loading datasets...</p>
      ) : (
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
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
              <Label htmlFor="group-select">Run Group (Optional)</Label>
              <Select value={runGroupId} onValueChange={setRunGroupId}>
                <SelectTrigger id="group-select" className="mt-1">
                  <SelectValue placeholder="Select a run group (optional)" />
                </SelectTrigger>
                <SelectContent>
                  {runGroups?.map((group) => (
                    <SelectItem key={group.id} value={String(group.id)}>
                      {group.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="grid grid-cols-3 gap-4">
            <div>
              <Label htmlFor="hazard-select">Hazard Dataset</Label>
              <Select value={hazardId} onValueChange={setHazardId} required>
                <SelectTrigger id="hazard-select" className="mt-1">
                  <SelectValue placeholder="Select a hazard dataset" />
                </SelectTrigger>
                <SelectContent>
                  {hazards?.map((hazard) => (
                    <SelectItem key={hazard.id} value={String(hazard.id)}>
                      {hazard.name}
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
                      {mapping.name}
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
                      {building.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="space-y-4">
            <div className="flex justify-between items-center">
              <h2 className="text-lg font-semibold">Interventions</h2>
              <Button type="button" onClick={addIntervention} variant="outline" size="sm">
                <PlusCircle className="w-4 h-4 mr-2" />
                Add Intervention
              </Button>
            </div>

            {interventions.length === 0 ? (
              <p className="text-sm text-muted-foreground">No interventions added. This will be a baseline run.</p>
            ) : (
              <div className="space-y-3">
                {interventions.map((intervention, index) => (
                  <div key={index} className="border rounded-lg p-4 space-y-3 bg-muted/20">
                    <div className="flex justify-between items-start">
                      <h3 className="font-medium">Intervention {index + 1}</h3>
                      <Button
                        type="button"
                        onClick={() => removeIntervention(index)}
                        variant="ghost"
                        size="sm"
                      >
                        <XCircle className="w-4 h-4" />
                      </Button>
                    </div>
                    
                    <div className="grid grid-cols-4 gap-3">
                      <div>
                        <Label>Building ID</Label>
                        {buildingDatasetId && buildings ? (
                          <Select
                            value={intervention.building_id}
                            onValueChange={(value) => updateIntervention(index, 'building_id', value)}
                          >
                            <SelectTrigger className="h-auto min-h-[60px] py-2">
                              <SelectValue placeholder="Select a building">
                                {intervention.building_id && buildings ? (
                                  <div className="flex flex-col items-start text-left">
                                    <span className="font-medium">{intervention.building_id}</span>
                                    {(() => {
                                      const building = buildings.find(b => b.guid === intervention.building_id);
                                      if (building) {
                                        return (
                                          <>
                                            <span className="text-xs text-muted-foreground">
                                              {Object.keys(building.properties).slice(0, 2).map(key => 
                                                `${key}: ${building.properties[key]}`
                                              ).join(', ')}
                                            </span>
                                            <span className="text-xs font-medium text-green-600">
                                              {building.asset_value ? `$${building.asset_value.toLocaleString()}` : 'No asset value'}
                                            </span>
                                          </>
                                        );
                                      }
                                      return null;
                                    })()}
                                  </div>
                                ) : null}
                              </SelectValue>
                            </SelectTrigger>
                            <SelectContent className="max-h-[400px]">
                              {buildings.map((building) => (
                                <SelectItem key={building.guid} value={building.guid}>
                                  <div className="flex flex-col items-start">
                                    <span className="font-medium">{building.guid}</span>
                                    <span className="text-xs text-muted-foreground">
                                      {Object.keys(building.properties).slice(0, 2).map(key => 
                                        `${key}: ${building.properties[key]}`
                                      ).join(', ')}
                                    </span>
                                    <span className="text-xs font-medium text-green-600">
                                      {building.asset_value ? `$${building.asset_value.toLocaleString()}` : 'No asset value'}
                                    </span>
                                  </div>
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        ) : (
                          <Input
                            value={intervention.building_id}
                            onChange={(e) => updateIntervention(index, 'building_id', e.target.value)}
                            placeholder="Select building dataset first"
                            disabled
                          />
                        )}
                      </div>
                      
                      <div>
                        <Label>Intervention Type</Label>
                        <Select
                          value={String(intervention.intervention_id)}
                          onValueChange={(value) => updateIntervention(index, 'intervention_id', parseInt(value))}
                        >
                          <SelectTrigger>
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            {interventionTypes?.filter(t => t.type === 'building_elevation').map((type) => (
                              <SelectItem key={type.id} value={String(type.id)}>
                                {type.name}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>
                      
                      <div>
                        <Label>Elevation (ft)</Label>
                        <Input
                          type="number"
                          step="0.5"
                          value={intervention.parameters.elevation_ft || ''}
                          onChange={(e) => updateIntervention(index, 'parameters', { elevation_ft: parseFloat(e.target.value) })}
                          placeholder="0"
                        />
                      </div>
                      
                      <div>
                        <Label>Cost ($)</Label>
                        <Input
                          type="number"
                          value={intervention.cost || ''}
                          onChange={(e) => updateIntervention(index, 'cost', e.target.value ? parseFloat(e.target.value) : undefined)}
                          placeholder="Optional"
                        />
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {error && <p className="text-red-600">{error}</p>}

          <Button type="submit" disabled={isLoading || isFetchingData}>
            {isLoading ? 'Creating...' : 'Create Run'}
          </Button>
        </form>
      )}
    </div>
  );
} 