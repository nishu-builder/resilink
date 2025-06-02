"use client";

import { useParams } from 'next/navigation';
import useSWR from 'swr';
import api from '@/app/hooks/useApi';
import Link from 'next/link';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import dynamic from 'next/dynamic'; // Import dynamic
import { useMemo, useEffect } from 'react'; // Import useMemo and useEffect
import { useMap } from 'react-leaflet';
// Import icon images directly
import iconRetinaUrl from 'leaflet/dist/images/marker-icon-2x.png';
import iconUrl from 'leaflet/dist/images/marker-icon.png';
import shadowUrl from 'leaflet/dist/images/marker-shadow.png';
import { DollarSign, TrendingUp, Building } from 'lucide-react';

// Assuming GeoJSON types (you might want a more specific type)
type GeoJsonObject = any;

type RunDetail = {
  id: number;
  name: string;
  status: string;
  created_at: string;
  updated_at: string | null; // Allow null for updated_at
  finished_at: string | null;
  hazard_id: number;
  mapping_set_id: number;
  building_dataset_id: number;
  run_group_id?: number;
  result_path: string | null;
  interventions?: RunIntervention[];
  // Add nested object types if API returns them, e.g.:
  // hazard: { id: number; name: string };
  // mapping_set: { id: number; name: string };
  // building_dataset: { id: number; name: string };
};

type RunIntervention = {
  id: number;
  building_id: string;
  intervention_id: number;
  parameters: { elevation_ft?: number };
  cost?: number;
  intervention?: {
    id: number;
    name: string;
    type: string;
  };
};

type EALResponse = {
  total_eal: number;
  building_count: number;
  building_eals?: Record<string, number>;
};

// Dynamically import the Map component
const MapContainer = dynamic(() => import('react-leaflet').then((mod) => mod.MapContainer), { ssr: false });
const TileLayer = dynamic(() => import('react-leaflet').then((mod) => mod.TileLayer), { ssr: false });
const GeoJSON = dynamic(() => import('react-leaflet').then((mod) => mod.GeoJSON), { ssr: false });

// --- Constants for Styling ---
const DS_COLORS = {
  DS0: '#00FF00', // Green
  DS1: '#FFFF00', // Yellow
  DS2: '#FFA500', // Orange
  DS3: '#FF0000', // Red
  Error: '#808080', // Grey
  Default: '#808080' // Default/fallback color
};

// --- Helper Function to Determine Style ---
function getFeatureStyle(feature: GeoJsonObject): L.CircleMarkerOptions {
  const props = feature?.properties;
  let color = DS_COLORS.Default;
  // Explicitly type the keys for type safety
  type DamageStateKey = 'DS0' | 'DS1' | 'DS2' | 'DS3';

  if (props) {
    if (props.error) {
      color = DS_COLORS.Error;
    } else if (props.P_DS0 !== undefined) {
      const probs: Record<DamageStateKey, number> = {
        DS0: props.P_DS0 ?? 0, // Use nullish coalescing for safety
        DS1: props.P_DS1 ?? 0,
        DS2: props.P_DS2 ?? 0,
        DS3: props.P_DS3 ?? 0
      };
      // Get the keys explicitly typed
      const dsKeys = Object.keys(probs) as DamageStateKey[];

      // Find the key with the maximum value, ensuring type safety
      const mostLikelyDS = dsKeys.reduce((a, b) => (probs[a] ?? 0) > (probs[b] ?? 0) ? a : b);
      color = DS_COLORS[mostLikelyDS] ?? DS_COLORS.Default; // Use nullish coalescing for color lookup
    } else {
      color = DS_COLORS.Error;
    }
  }

  return {
    radius: 6,
    fillColor: color,
    color: "#000",
    weight: 1,
    opacity: 1,
    fillOpacity: 0.8
  };
}

// --- Helper Component to Set Map Bounds and Fix Icons ---
interface MapBoundsSetterProps {
  data: GeoJsonObject | undefined;
}

function MapBoundsSetter({ data }: MapBoundsSetterProps) {
  // Import L here, only runs client-side when component renders
  const L = require('leaflet');
  const map = useMap();

  useEffect(() => {
    if (!L) return; // Ensure L is loaded

    // --- Fix Default Icon Path --- 
    // Delete existing icon defaults before setting new ones
    // @ts-ignore Property '_getIconUrl' does not exist on type 'typeof Icon'.
    delete L.Icon.Default.prototype._getIconUrl;
    L.Icon.Default.mergeOptions({
      iconRetinaUrl: iconRetinaUrl.src, // Use .src for Next.js image imports
      iconUrl: iconUrl.src,
      shadowUrl: shadowUrl.src,
    });
    // --- End Icon Fix ---

    // --- Fit Bounds Logic --- 
    if (data) {
      try {
        const geoJsonLayer = L.geoJSON(data);
        const bounds = geoJsonLayer.getBounds();

        if (bounds.isValid()) {
          map.fitBounds(bounds.pad(0.1));
        } else {
          console.warn("GeoJSON bounds are invalid, map not auto-fitted.");
        }
      } catch (error) {
        console.error("Error processing GeoJSON for bounds:", error);
      }
    }
  }, [data, map, L]); // Add L to dependency array

  return null;
}

// --- Main Page Component ---
export default function RunDetailPage() {
  const params = useParams();
  const runId = params.id as string;

  const { data: run, isLoading, error } = useSWR<RunDetail>(
    runId ? `runs/${runId}` : null,
    (url: string) => api.get(url).then((r) => r.data)
  );

  const shouldFetchResults = run?.status === 'COMPLETED' && run?.result_path;
  const { data: resultsData, isLoading: isLoadingResults, error: resultsError } = useSWR<GeoJsonObject>(
    shouldFetchResults ? `runs/${runId}/results` : null,
    (url: string) => api.get(url).then((r) => r.data)
  );

  const { data: ealData, isLoading: isLoadingEAL } = useSWR<EALResponse>(
    run?.status === 'COMPLETED' ? `financial/runs/${runId}/eal` : null,
    (url: string) => api.get(url).then((r) => r.data)
  );

  const getStatusVariant = (status: string): 'default' | 'destructive' | 'secondary' | 'outline' => {
    switch (status?.toUpperCase()) {
      case 'COMPLETED': return 'default';
      case 'FAILED': return 'destructive';
      case 'RUNNING': case 'QUEUED': return 'secondary';
      case 'PENDING': default: return 'outline';
    }
  };

  // Restore map style prop
  const mapStyle = useMemo(() => ({
    height: '500px',
    width: '100%'
  }), []);

  // Add logging
  console.log("Run Data:", run);
  console.log("Should Fetch Results:", shouldFetchResults);
  console.log("Results Loading:", isLoadingResults);
  console.log("Results Error:", resultsError);
  console.log("Results Data:", resultsData);

  if (isLoading) return <p>Loading run details...</p>;
  if (error) return <p>Error loading run details: {error.message}</p>;
  if (!run) return <p>Run not found.</p>;

  const formattedUpdatedAt = run.updated_at ? new Date(run.updated_at).toLocaleString() : 'N/A';

  // --- pointToLayer function for GeoJSON --- 
  const pointToLayer = (feature: GeoJsonObject, latlng: L.LatLngExpression): L.Layer => {
    const L = require('leaflet'); // Ensure L is available
    const style = getFeatureStyle(feature);
    return L.circleMarker(latlng, style);
  };

  // --- onEachFeature function to bind tooltips --- 
  const onEachFeature = (feature: GeoJsonObject, layer: L.Layer) => {
    if (feature.properties) {
      let tooltipContent = '<div style="max-height: 150px; overflow-y: auto; font-size: 0.8rem;">';
      tooltipContent += '<strong>Properties:</strong><br/>';
      // Loop through properties and format them
      for (const key in feature.properties) {
        let value = feature.properties[key];
        // Format numbers nicely, handle null/undefined
        if (typeof value === 'number') {
          value = value.toFixed(4); // Adjust decimal places as needed
        } else if (value === null || value === undefined) {
          value = 'N/A';
        }
        tooltipContent += `<b>${key}:</b> ${value}<br/>`;
      }
      tooltipContent += '</div>';
      // Bind the formatted content as a tooltip
      layer.bindTooltip(tooltipContent);
    }
  };

  const totalInterventionCost = run.interventions?.reduce((sum, i) => sum + (i.cost || 0), 0) || 0;

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-start">
        <div>
          <h1 className="text-2xl font-semibold">Run: {run.name}</h1>
          <p className="text-sm text-muted-foreground">ID: {run.id}</p>
        </div>
        <Link href="/runs" className="text-blue-600 hover:underline">Back to Runs</Link>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Run Details</CardTitle>
          <CardDescription>Information about this analysis run.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex justify-between items-center">
            <span className="text-muted-foreground">Status:</span>
            <Badge variant={getStatusVariant(run.status)}>{run.status || 'Unknown'}</Badge>
          </div>
          <div className="flex justify-between items-center">
            <span className="text-muted-foreground">Created:</span>
            <span>{new Date(run.created_at).toLocaleString()}</span>
          </div>
          <div className="flex justify-between items-center">
            <span className="text-muted-foreground">Last Updated:</span>
            <span>{formattedUpdatedAt}</span>
          </div>
          {run.finished_at && (
            <div className="flex justify-between items-center">
              <span className="text-muted-foreground">Finished:</span>
              <span>{new Date(run.finished_at).toLocaleString()}</span>
            </div>
          )}
          {run.run_group_id && (
            <div className="flex justify-between items-center">
              <span className="text-muted-foreground">Run Group:</span>
              <Link href={`/run-groups/${run.run_group_id}`} className="text-blue-600 hover:underline">
                View Group
              </Link>
            </div>
          )}
          <hr />
          <h3 className="font-medium pt-2">Inputs</h3>
          <div className="flex justify-between items-center">
            <span className="text-muted-foreground">Hazard Dataset ID:</span>
            <span>{run.hazard_id}</span>
          </div>
          <div className="flex justify-between items-center">
            <span className="text-muted-foreground">Mapping Set ID:</span>
            <span>{run.mapping_set_id}</span>
          </div>
          <div className="flex justify-between items-center">
            <span className="text-muted-foreground">Building Dataset ID:</span>
            <span>{run.building_dataset_id}</span>
          </div>
          <hr />
          <h3 className="font-medium pt-2">Outputs</h3>
          <div className="flex justify-between items-center">
            <span className="text-muted-foreground">Result Path:</span>
            <span>{run.result_path || 'Not available'}</span>
          </div>
        </CardContent>
      </Card>

      {/* Interventions Section */}
      {run.interventions && run.interventions.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Applied Interventions</CardTitle>
            <CardDescription>Building-level interventions applied in this run.</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {run.interventions.map((intervention) => (
                <div key={intervention.id} className="border rounded-lg p-3 bg-muted/20">
                  <div className="flex items-start justify-between">
                    <div className="flex items-start space-x-3">
                      <Building className="w-5 h-5 text-blue-600 mt-0.5" />
                      <div>
                        <p className="font-medium">Building {intervention.building_id}</p>
                        <p className="text-sm text-muted-foreground">
                          {intervention.intervention?.name || 'Intervention'} - 
                          {intervention.parameters.elevation_ft ? ` ${intervention.parameters.elevation_ft} ft elevation` : ''}
                        </p>
                      </div>
                    </div>
                    {intervention.cost && (
                      <div className="text-right">
                        <p className="font-medium">${intervention.cost.toLocaleString()}</p>
                        <p className="text-xs text-muted-foreground">Cost</p>
                      </div>
                    )}
                  </div>
                </div>
              ))}
              <div className="border-t pt-3 flex justify-between items-center">
                <span className="font-medium">Total Intervention Cost:</span>
                <span className="font-bold text-lg">${totalInterventionCost.toLocaleString()}</span>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Financial Analysis Section */}
      {run.status === 'COMPLETED' && ealData && (
        <Card>
          <CardHeader>
            <CardTitle>Financial Analysis</CardTitle>
            <CardDescription>Expected Annual Loss (EAL) calculations for this run.</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="flex items-start space-x-3">
                <DollarSign className="w-5 h-5 text-red-600 mt-0.5" />
                <div>
                  <p className="text-2xl font-bold">${ealData.total_eal.toLocaleString()}</p>
                  <p className="text-sm text-muted-foreground">Total EAL</p>
                </div>
              </div>
              
              <div className="flex items-start space-x-3">
                <Building className="w-5 h-5 text-blue-600 mt-0.5" />
                <div>
                  <p className="text-2xl font-bold">{ealData.building_count}</p>
                  <p className="text-sm text-muted-foreground">Buildings Analyzed</p>
                </div>
              </div>

              <div className="flex items-start space-x-3">
                <TrendingUp className="w-5 h-5 text-green-600 mt-0.5" />
                <div>
                  <p className="text-2xl font-bold">
                    ${Math.round(ealData.total_eal / ealData.building_count).toLocaleString()}
                  </p>
                  <p className="text-sm text-muted-foreground">Average per Building</p>
                </div>
              </div>
            </div>

            {run.run_group_id && (
              <div className="mt-4 pt-4 border-t">
                <Link 
                  href={`/run-groups/${run.run_group_id}`} 
                  className="text-blue-600 hover:underline text-sm"
                >
                  Compare with other runs in group →
                </Link>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Results Map Section */}
      {run.status === 'COMPLETED' && (
        <Card>
          <CardHeader>
            <CardTitle>Results Map</CardTitle>
            <CardDescription>Visualization of the analysis results.</CardDescription>
          </CardHeader>
          <CardContent>
            {!shouldFetchResults && <p>Run completed, but no result path found.</p>}
            {isLoadingResults && <p>Loading results map...</p>}
            {resultsError && <p className="text-red-600">Error loading results: {resultsError.message || 'Unknown error'}</p>}
            {shouldFetchResults && resultsData && (
              <MapContainer style={mapStyle}>
                <TileLayer
                  attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                  url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                />
                <GeoJSON
                  data={resultsData}
                  key={JSON.stringify(resultsData)}
                  pointToLayer={pointToLayer}
                  onEachFeature={onEachFeature}
                />
                <MapBoundsSetter data={resultsData} />
              </MapContainer>
            )}
            {shouldFetchResults && !isLoadingResults && !resultsData && !resultsError &&
              <p>Attempted to load results, but no data was returned.</p>
            }
          </CardContent>
        </Card>
      )}
    </div>
  );
} 