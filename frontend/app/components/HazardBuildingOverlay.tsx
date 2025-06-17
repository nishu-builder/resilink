"use client";

import { useEffect, useRef, useState } from 'react';
import mapboxgl from 'mapbox-gl';
import 'mapbox-gl/dist/mapbox-gl.css';
import api from '@/app/hooks/useApi';

mapboxgl.accessToken = process.env.NEXT_PUBLIC_MAPBOX_TOKEN || '';

interface HazardBuildingOverlayProps {
  hazardId?: number;
  modifiedHazardId?: number;
  buildingDatasetId?: number;
  className?: string;
  showLegend?: boolean;
}

export default function HazardBuildingOverlay({ 
  hazardId, 
  modifiedHazardId,
  buildingDatasetId, 
  className = '',
  showLegend = true
}: HazardBuildingOverlayProps) {
  const mapContainer = useRef<HTMLDivElement>(null);
  const map = useRef<mapboxgl.Map | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [bounds, setBounds] = useState<mapboxgl.LngLatBounds | null>(null);

  useEffect(() => {
    if (!mapContainer.current || map.current) return;

    // Initialize map
    map.current = new mapboxgl.Map({
      container: mapContainer.current,
      style: 'mapbox://styles/mapbox/light-v11',
      center: [-104.95, 39.75], // Denver default
      zoom: 11,
    });

    map.current.on('load', async () => {
      try {
        const loadPromises = [];
        let overallBounds = new mapboxgl.LngLatBounds();

        // Load hazard if specified
        if (hazardId || modifiedHazardId) {
          const hazardType = hazardId ? 'hazards' : 'modified-hazards';
          const id = hazardId || modifiedHazardId;
          
          loadPromises.push(
            api.get(`datasets/${hazardType}/${id}/tiles/{z}/{x}/{y}`).catch(() => {
              // Get tile URL for raster
              const tileUrl = `${window.location.origin}/api/datasets/${hazardType}/${id}/tiles/{z}/{x}/{y}`;
              
              // Add hazard raster source
              map.current!.addSource('hazard', {
                type: 'raster',
                tiles: [tileUrl],
                tileSize: 256,
                minzoom: 0,
                maxzoom: 20,
              });

              // Add hazard layer
              map.current!.addLayer({
                id: 'hazard-layer',
                type: 'raster',
                source: 'hazard',
                paint: {
                  'raster-opacity': 0.7,
                },
              });
            })
          );

          // Get hazard bounds
          loadPromises.push(
            api.get(`datasets/${hazardType}/${id}/bounds`).then((response) => {
              const bounds = response.data;
              if (bounds && bounds.length === 4) {
                overallBounds.extend([bounds[0], bounds[1]]);
                overallBounds.extend([bounds[2], bounds[3]]);
              }
            }).catch(() => {
              // Default bounds if API fails
              overallBounds.extend([-105.0, 39.7]);
              overallBounds.extend([-104.9, 39.8]);
            })
          );
        }

        // Load buildings if specified
        if (buildingDatasetId) {
          loadPromises.push(
            api.get(`datasets/buildings/${buildingDatasetId}/geojson`).then((response) => {
              const geojsonData = response.data;

              if (geojsonData.features && geojsonData.features.length > 0) {
                // Add building source
                map.current!.addSource('buildings', {
                  type: 'geojson',
                  data: geojsonData,
                });

                // Check if buildings are points or polygons
                const firstFeature = geojsonData.features[0];
                const isPoint = firstFeature && firstFeature.geometry.type === 'Point';

                if (isPoint) {
                  // Add building points layer
                  map.current!.addLayer({
                    id: 'buildings-points',
                    type: 'circle',
                    source: 'buildings',
                    paint: {
                      'circle-radius': 6,
                      'circle-color': '#3b82f6',
                      'circle-stroke-color': '#1e40af',
                      'circle-stroke-width': 2,
                      'circle-opacity': 0.8,
                    },
                  });
                } else {
                  // Add building fill layer for polygons
                  map.current!.addLayer({
                    id: 'buildings-fill',
                    type: 'fill',
                    source: 'buildings',
                    paint: {
                      'fill-color': '#3b82f6',
                      'fill-opacity': 0.4,
                    },
                  });

                  // Add building outline layer
                  map.current!.addLayer({
                    id: 'buildings-outline',
                    type: 'line',
                    source: 'buildings',
                    paint: {
                      'line-color': '#1e40af',
                      'line-width': 1.5,
                    },
                  });
                }

                // Calculate bounds from buildings
                geojsonData.features.forEach((feature: any) => {
                  if (feature.geometry.type === 'Polygon') {
                    feature.geometry.coordinates[0].forEach((coord: number[]) => {
                      overallBounds.extend(coord as [number, number]);
                    });
                  } else if (feature.geometry.type === 'MultiPolygon') {
                    feature.geometry.coordinates.forEach((polygon: number[][][]) => {
                      polygon[0].forEach((coord: number[]) => {
                        overallBounds.extend(coord as [number, number]);
                      });
                    });
                  }
                });

                // Add popup on building click
                const clickLayer = isPoint ? 'buildings-points' : 'buildings-fill';
                map.current!.on('click', clickLayer, (e) => {
                  if (!e.features || e.features.length === 0) return;

                  const feature = e.features[0];
                  const properties = feature.properties || {};
                  
                  let popupContent = `<div class="p-2">`;
                  popupContent += `<h3 class="font-bold">Building ${properties.guid}</h3>`;
                  
                  if (properties.asset_value) {
                    popupContent += `<p><strong>Asset Value:</strong> $${Number(properties.asset_value).toLocaleString()}</p>`;
                  }
                  
                  Object.entries(properties).forEach(([key, value]) => {
                    if (key !== 'guid' && key !== 'asset_value' && value) {
                      popupContent += `<p><strong>${key}:</strong> ${value}</p>`;
                    }
                  });
                  
                  popupContent += `</div>`;

                  new mapboxgl.Popup()
                    .setLngLat(e.lngLat)
                    .setHTML(popupContent)
                    .addTo(map.current!);
                });

                // Change cursor on hover
                map.current!.on('mouseenter', clickLayer, () => {
                  if (map.current) map.current.getCanvas().style.cursor = 'pointer';
                });

                map.current!.on('mouseleave', clickLayer, () => {
                  if (map.current) map.current.getCanvas().style.cursor = '';
                });
              }
            })
          );
        }

        // Wait for all loads to complete
        await Promise.all(loadPromises);

        // Fit map to combined bounds
        if (!overallBounds.isEmpty()) {
          map.current!.fitBounds(overallBounds, { padding: 50 });
          setBounds(overallBounds);
        }

        setLoading(false);
      } catch (err) {
        console.error('Error loading overlay:', err);
        setError('Failed to load map data');
        setLoading(false);
      }
    });

    return () => {
      if (map.current) {
        map.current.remove();
        map.current = null;
      }
    };
  }, [hazardId, modifiedHazardId, buildingDatasetId]);

  return (
    <div className={`relative ${className}`}>
      <div ref={mapContainer} className="w-full h-full" />
      
      {showLegend && (hazardId || modifiedHazardId) && (
        <div className="absolute top-4 right-4 bg-white p-3 rounded-lg shadow-lg">
          <h4 className="font-semibold text-sm mb-2">Legend</h4>
          <div className="space-y-1 text-xs">
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 bg-gradient-to-r from-blue-200 to-blue-600 opacity-70"></div>
              <span>Water Depth (Low to High)</span>
            </div>
            {buildingDatasetId && (
              <div className="flex items-center gap-2">
                <div className="w-4 h-4 bg-blue-500 opacity-40 border border-blue-700"></div>
                <span>Buildings</span>
              </div>
            )}
          </div>
        </div>
      )}
      
      {loading && (
        <div className="absolute inset-0 flex items-center justify-center bg-white bg-opacity-75">
          <div className="text-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-2"></div>
            <p className="text-sm text-gray-600">Loading map data...</p>
          </div>
        </div>
      )}
      
      {error && (
        <div className="absolute inset-0 flex items-center justify-center bg-white bg-opacity-75">
          <div className="text-center text-red-600">
            <p>{error}</p>
          </div>
        </div>
      )}
    </div>
  );
}