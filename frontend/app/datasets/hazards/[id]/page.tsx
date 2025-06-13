'use client';

import { useParams } from 'next/navigation';
import { useEffect, useState } from 'react';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { HazardViewer } from '@/app/components/HazardViewer';
import { ArrowLeft, Info, Plus, Shield, Waves, Calendar, Settings, Trash2, Eye } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Textarea } from '@/components/ui/textarea';

export default function HazardDetailPage() {
  const params = useParams();
  const hazardId = parseInt(params.id as string);
  const [hazard, setHazard] = useState<any>(null);
  const [hazardInfo, setHazardInfo] = useState<any>(null);
  const [interventions, setInterventions] = useState<any[]>([]);
  const [modifiedHazards, setModifiedHazards] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [drawingMode, setDrawingMode] = useState(false);
  const [drawnGeometry, setDrawnGeometry] = useState<any>(null);
  
  // Form state for new intervention
  const [interventionForm, setInterventionForm] = useState({
    name: '',
    type: 'levee',
    geometry: null as any,
    parameters: {
      height: '',
      width: '',
      top_width: '',
      crest_elevation: ''
    }
  });

  useEffect(() => {
    const fetchData = async () => {
      try {
        // Fetch hazard basic info
        const hazardsResponse = await fetch('/api/datasets/hazards');
        const hazards = await hazardsResponse.json();
        const currentHazard = hazards.find((h: any) => h.id === hazardId);
        setHazard(currentHazard);

        // Fetch detailed info
        const infoResponse = await fetch(`/api/datasets/hazards/${hazardId}/info`);
        const info = await infoResponse.json();
        setHazardInfo(info);
        
        // Fetch interventions for this hazard
        const interventionsResponse = await fetch(`/api/hazard-interventions?hazard_id=${hazardId}`);
        const interventionsData = await interventionsResponse.json();
        setInterventions(interventionsData);
        
        // Fetch modified hazards for each intervention
        const allModifiedHazards = [];
        for (const intervention of interventionsData) {
          try {
            const modifiedResponse = await fetch(`/api/hazard-interventions/${intervention.id}/modified-hazards`);
            const modifiedData = await modifiedResponse.json();
            allModifiedHazards.push(...modifiedData.map((mh: any) => ({
              ...mh,
              intervention_name: intervention.name,
              intervention_type: intervention.type
            })));
          } catch (error) {
            console.error(`Error fetching modified hazards for intervention ${intervention.id}:`, error);
          }
        }
        setModifiedHazards(allModifiedHazards);
      } catch (error) {
        console.error('Error fetching hazard data:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [hazardId]);
  
  const handleCreateIntervention = async () => {
    try {
      // Use drawn geometry or fallback to mock geometry for testing
      const geometryToUse = drawnGeometry || {
        type: 'LineString',
        coordinates: [
          [-90.12, 35.15],
          [-90.13, 35.16],
          [-90.14, 35.17]
        ]
      };
      
      const payload = {
        name: interventionForm.name,
        type: interventionForm.type,
        hazard_id: hazardId,
        geometry: geometryToUse,
        parameters: interventionForm.type === 'dam' ? {
          height: parseFloat(interventionForm.parameters.height),
          width: parseFloat(interventionForm.parameters.width),
          crest_elevation: parseFloat(interventionForm.parameters.crest_elevation)
        } : {
          height: parseFloat(interventionForm.parameters.height),
          top_width: parseFloat(interventionForm.parameters.top_width)
        }
      };
      
      const response = await fetch('/api/hazard-interventions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      
      if (response.ok) {
        const newIntervention = await response.json();
        setInterventions([...interventions, newIntervention]);
        setCreateDialogOpen(false);
        // Reset form
        setInterventionForm({
          name: '',
          type: 'levee',
          geometry: null,
          parameters: { height: '', width: '', top_width: '', crest_elevation: '' }
        });
        setDrawnGeometry(null);
        setDrawingMode(false);
      } else {
        const error = await response.json();
        alert(`Error creating intervention: ${error.detail}`);
      }
    } catch (error) {
      console.error('Error creating intervention:', error);
      alert('Failed to create intervention');
    }
  };

  if (loading) {
    return (
      <div className="container mx-auto p-6">
        <div className="animate-pulse space-y-4">
          <div className="h-8 bg-gray-200 rounded w-1/3" />
          <div className="h-96 bg-gray-200 rounded" />
        </div>
      </div>
    );
  }

  if (!hazard) {
    return (
      <div className="container mx-auto p-6">
        <Card className="p-8 text-center">
          <h2 className="text-xl font-semibold mb-2">Hazard Not Found</h2>
          <p className="text-muted-foreground mb-4">The requested hazard could not be found.</p>
          <Link href="/datasets/hazards">
            <Button>
              <ArrowLeft className="mr-2 h-4 w-4" />
              Back to Hazards
            </Button>
          </Link>
        </Card>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="space-y-1">
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Link href="/datasets" className="hover:text-primary">Datasets</Link>
            <span>/</span>
            <Link href="/datasets/hazards" className="hover:text-primary">Hazards</Link>
            <span>/</span>
            <span>{hazard.name}</span>
          </div>
          <h1 className="text-3xl font-bold">{hazard.name}</h1>
          <p className="text-muted-foreground">
            Created: {new Date(hazard.created_at).toLocaleDateString()}
          </p>
        </div>
        <div className="flex gap-2">
          <Link href="/datasets/hazards">
            <Button variant="outline">
              <ArrowLeft className="mr-2 h-4 w-4" />
              Back
            </Button>
          </Link>
        </div>
      </div>

      {/* Metadata */}
      {hazardInfo && (
        <Card className="p-6">
          <div className="flex items-center gap-2 mb-4">
            <Info className="h-5 w-5" />
            <h2 className="text-xl font-semibold">Hazard Information</h2>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div>
              <p className="text-sm text-muted-foreground">Dimensions</p>
              <p className="font-medium">{hazardInfo.width} × {hazardInfo.height} pixels</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">CRS</p>
              <p className="font-medium text-sm">{hazardInfo.crs}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Min Elevation</p>
              <p className="font-medium">{hazardInfo.statistics.min.toFixed(2)}m</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Max Elevation</p>
              <p className="font-medium">{hazardInfo.statistics.max.toFixed(2)}m</p>
            </div>
          </div>
        </Card>
      )}
      
      {/* Interventions Section */}
      <Card className="p-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Shield className="h-5 w-5" />
            <h2 className="text-xl font-semibold">Interventions</h2>
          </div>
          <Dialog open={createDialogOpen} onOpenChange={setCreateDialogOpen}>
            <DialogTrigger asChild>
              <Button>
                <Plus className="mr-2 h-4 w-4" />
                Create Intervention
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-2xl">
              <DialogHeader>
                <DialogTitle>Create New Intervention</DialogTitle>
                <DialogDescription>
                  Add a levee or dam to modify this hazard scenario.
                </DialogDescription>
              </DialogHeader>
              <div className="space-y-4 py-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="name">Intervention Name</Label>
                    <Input
                      id="name"
                      value={interventionForm.name}
                      onChange={(e) => setInterventionForm({...interventionForm, name: e.target.value})}
                      placeholder="e.g., North Levee Protection"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="type">Type</Label>
                    <Select
                      value={interventionForm.type}
                      onValueChange={(value) => setInterventionForm({...interventionForm, type: value})}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="levee">Levee</SelectItem>
                        <SelectItem value="dam">Dam</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
                
                {/* Parameters based on type */}
                {interventionForm.type === 'levee' ? (
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="height">Height (m)</Label>
                      <Input
                        id="height"
                        type="number"
                        value={interventionForm.parameters.height}
                        onChange={(e) => setInterventionForm({
                          ...interventionForm,
                          parameters: {...interventionForm.parameters, height: e.target.value}
                        })}
                        placeholder="e.g., 3.5"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="top_width">Top Width (m)</Label>
                      <Input
                        id="top_width"
                        type="number"
                        value={interventionForm.parameters.top_width}
                        onChange={(e) => setInterventionForm({
                          ...interventionForm,
                          parameters: {...interventionForm.parameters, top_width: e.target.value}
                        })}
                        placeholder="e.g., 2.0"
                      />
                    </div>
                  </div>
                ) : (
                  <div className="grid grid-cols-3 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="height">Height (m)</Label>
                      <Input
                        id="height"
                        type="number"
                        value={interventionForm.parameters.height}
                        onChange={(e) => setInterventionForm({
                          ...interventionForm,
                          parameters: {...interventionForm.parameters, height: e.target.value}
                        })}
                        placeholder="e.g., 15"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="width">Width (m)</Label>
                      <Input
                        id="width"
                        type="number"
                        value={interventionForm.parameters.width}
                        onChange={(e) => setInterventionForm({
                          ...interventionForm,
                          parameters: {...interventionForm.parameters, width: e.target.value}
                        })}
                        placeholder="e.g., 50"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="crest_elevation">Crest Elevation (m)</Label>
                      <Input
                        id="crest_elevation"
                        type="number"
                        value={interventionForm.parameters.crest_elevation}
                        onChange={(e) => setInterventionForm({
                          ...interventionForm,
                          parameters: {...interventionForm.parameters, crest_elevation: e.target.value}
                        })}
                        placeholder="e.g., 120"
                      />
                    </div>
                  </div>
                )}
                
                <div className="space-y-2">
                  <Label>Geometry</Label>
                  <div className="border rounded-lg p-4 bg-muted/50">
                    {drawnGeometry ? (
                      <div className="space-y-2">
                        <div className="flex items-center justify-between">
                          <span className="text-sm font-medium text-green-600">
                            ✓ Geometry drawn ({drawnGeometry.type})
                          </span>
                          <Button 
                            variant="ghost" 
                            size="sm"
                            onClick={() => setDrawnGeometry(null)}
                          >
                            <Trash2 className="h-3 w-3 mr-1" />
                            Clear
                          </Button>
                        </div>
                        <p className="text-xs text-muted-foreground">
                          {drawnGeometry.coordinates.length} coordinate points
                        </p>
                      </div>
                    ) : (
                      <div className="space-y-2">
                        <p className="text-sm text-muted-foreground mb-2">
                          Use the drawing tools on the map below to draw your intervention geometry.
                        </p>
                        <Button 
                          variant="outline" 
                          className="w-full"
                          onClick={() => {
                            setDrawingMode(true);
                            // Close dialog temporarily to enable drawing
                            setCreateDialogOpen(false);
                            // Show a notification that drawing is active
                            setTimeout(() => {
                              alert('Drawing mode active! Use the "Draw Line" or "Draw Area" buttons on the map. Open the intervention dialog again when you\'re done drawing.');
                            }, 100);
                          }}
                        >
                          <Waves className="mr-2 h-4 w-4" />
                          Start Drawing on Map
                        </Button>
                        {drawingMode && (
                          <p className="text-xs text-blue-600 mt-2">
                            ✓ Drawing mode active - use the drawing tools on the map below
                          </p>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              </div>
              <div className="flex justify-end gap-2">
                <Button variant="outline" onClick={() => setCreateDialogOpen(false)}>
                  Cancel
                </Button>
                <Button 
                  onClick={handleCreateIntervention}
                  disabled={!interventionForm.name || 
                    (interventionForm.type === 'levee' ? 
                      !interventionForm.parameters.height || !interventionForm.parameters.top_width :
                      !interventionForm.parameters.height || !interventionForm.parameters.width || !interventionForm.parameters.crest_elevation
                    )
                  }
                >
                  Create Intervention
                </Button>
              </div>
            </DialogContent>
          </Dialog>
        </div>
        
        {interventions.length === 0 ? (
          <div className="text-center py-8 text-muted-foreground">
            <Shield className="h-12 w-12 mx-auto mb-2 opacity-30" />
            <p>No interventions created yet.</p>
            <p className="text-sm">Create levees or dams to modify this hazard scenario.</p>
          </div>
        ) : (
          <div className="space-y-3">
            {interventions.map((intervention) => (
              <div key={intervention.id} className="border rounded-lg p-4 hover:bg-muted/50 transition-colors">
                <div className="flex items-start justify-between">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <h3 className="font-medium">{intervention.name}</h3>
                      <Badge variant="outline">
                        {intervention.type === 'dam' ? 'Dam' : 'Levee'}
                      </Badge>
                    </div>
                    <div className="flex items-center gap-4 text-sm text-muted-foreground">
                      <span className="flex items-center gap-1">
                        <Calendar className="h-3 w-3" />
                        {new Date(intervention.created_at).toLocaleDateString()}
                      </span>
                      {intervention.type === 'levee' ? (
                        <span>Height: {intervention.parameters.height}m, Width: {intervention.parameters.top_width}m</span>
                      ) : (
                        <span>Height: {intervention.parameters.height}m, Width: {intervention.parameters.width}m</span>
                      )}
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <Button 
                      variant="outline" 
                      size="sm"
                      onClick={async () => {
                        try {
                          const response = await fetch(`/api/hazard-interventions/${intervention.id}/apply`, {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ model_type: 'simplified_flood_model' })
                          });
                          
                          if (response.ok) {
                            const result = await response.json();
                            alert(`${result.message}\n\nThis will take 1-2 minutes. Refresh the page to see results.`);
                            
                            // Optionally reload the page after a delay to show updated results
                            setTimeout(() => {
                              window.location.reload();
                            }, 30000); // Reload after 30 seconds
                          } else {
                            const error = await response.json();
                            alert(`Error: ${error.detail}`);
                          }
                        } catch (error) {
                          console.error('Error applying intervention:', error);
                          alert('Failed to start hydraulic modeling');
                        }
                      }}
                    >
                      <Settings className="mr-1 h-3 w-3" />
                      Apply Model
                    </Button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>

      {/* Modified Hazards Section */}
      {modifiedHazards.length > 0 && (
        <Card className="p-6">
          <div className="flex items-center gap-2 mb-4">
            <Settings className="h-5 w-5" />
            <h2 className="text-xl font-semibold">Modeling Results</h2>
            <Badge variant="secondary">
              {modifiedHazards.length} result{modifiedHazards.length !== 1 ? 's' : ''}
            </Badge>
          </div>
          
          <div className="space-y-4">
            {modifiedHazards.map((modifiedHazard) => (
              <div key={modifiedHazard.id} className="border rounded-lg p-4 hover:bg-muted/50 transition-colors">
                <div className="flex items-start justify-between">
                  <div className="space-y-2">
                    <div className="flex items-center gap-2">
                      <h3 className="font-medium">{modifiedHazard.name}</h3>
                      <Badge variant="outline">
                        {modifiedHazard.intervention_type === 'dam' ? 'Dam' : 'Levee'} Model
                      </Badge>
                      <Badge variant="secondary">
                        {modifiedHazard.model_type}
                      </Badge>
                    </div>
                    
                    <p className="text-sm text-muted-foreground">
                      Based on: {modifiedHazard.intervention_name}
                    </p>
                    
                    <div className="flex items-center gap-2 mt-2">
                      <Badge variant={modifiedHazard.status ? "default" : "secondary"}>
                        {modifiedHazard.status ? "✓ Complete" : "⏳ Processing"}
                      </Badge>
                      <span className="text-xs text-muted-foreground">
                        {new Date(modifiedHazard.created_at).toLocaleDateString()}
                      </span>
                    </div>
                    
                    {modifiedHazard.model_results && modifiedHazard.status && (
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-3">
                        <div className="text-sm">
                          <p className="text-muted-foreground">Water Reduction</p>
                          <p className="font-medium">
                            {modifiedHazard.model_results.reduction_stats?.mean_reduction_m?.toFixed(2) || 0}m avg
                          </p>
                        </div>
                        <div className="text-sm">
                          <p className="text-muted-foreground">Max Reduction</p>
                          <p className="font-medium">
                            {modifiedHazard.model_results.reduction_stats?.max_reduction_m?.toFixed(2) || 0}m
                          </p>
                        </div>
                        <div className="text-sm">
                          <p className="text-muted-foreground">Affected Area</p>
                          <p className="font-medium">
                            {modifiedHazard.model_results.reduction_stats?.affected_area_pixels || 0} pixels
                          </p>
                        </div>
                        <div className="text-sm">
                          <p className="text-muted-foreground">Status</p>
                          <p className="font-medium text-green-600">
                            {modifiedHazard.model_results.success ? "Success" : "Failed"}
                          </p>
                        </div>
                      </div>
                    )}
                  </div>
                  
                  <div className="flex gap-2">
                    <Button 
                      variant="outline" 
                      size="sm"
                      disabled={!modifiedHazard.status}
                      onClick={() => {
                        if (modifiedHazard.status) {
                          // Navigate to modified hazard view
                          window.open(`/datasets/modified-hazards/${modifiedHazard.id}`, '_blank');
                        }
                      }}
                    >
                      <Eye className="mr-1 h-3 w-3" />
                      {modifiedHazard.status ? 'View' : 'Processing...'}
                    </Button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Hazard Viewer */}
      <div>
        <h2 className="text-xl font-semibold mb-4">Hazard Visualization</h2>
        <HazardViewer 
          hazardId={hazardId} 
          hazardInfo={hazardInfo} 
          interventions={interventions}
          drawingMode={drawingMode}
          onGeometryDrawn={(geometry) => {
            setDrawnGeometry(geometry);
            setDrawingMode(false);
            // Auto-reopen dialog when geometry is drawn
            setTimeout(() => {
              setCreateDialogOpen(true);
              alert('Geometry captured! Complete the intervention details in the dialog.');
            }, 500);
          }}
          onDrawingModeChange={setDrawingMode}
        />
      </div>
    </div>
  );
}