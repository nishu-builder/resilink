"use client";

import { useEffect, useRef, useState } from 'react';
import mapboxgl from 'mapbox-gl';
import 'mapbox-gl/dist/mapbox-gl.css';
import api from '@/app/hooks/useApi';

mapboxgl.accessToken = process.env.NEXT_PUBLIC_MAPBOX_TOKEN || '';

interface BuildingsMapViewerProps {
  datasetId: number;
  className?: string;
}

export default function BuildingsMapViewer({ datasetId, className = '' }: BuildingsMapViewerProps) {
  const mapContainer = useRef<HTMLDivElement>(null);
  const map = useRef<mapboxgl.Map | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

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
        // Fetch building GeoJSON
        const response = await api.get(`datasets/buildings/${datasetId}/geojson`);
        const geojsonData = response.data;

        if (!geojsonData.features || geojsonData.features.length === 0) {
          setError('No buildings found in dataset');
          setLoading(false);
          return;
        }

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
              'fill-opacity': 0.6,
            },
          });

          // Add building outline layer
          map.current!.addLayer({
            id: 'buildings-outline',
            type: 'line',
            source: 'buildings',
            paint: {
              'line-color': '#1e40af',
              'line-width': 1,
            },
          });
        }

        // Calculate bounds and fit map
        const bounds = new mapboxgl.LngLatBounds();
        geojsonData.features.forEach((feature: any) => {
          if (feature.geometry.type === 'Polygon') {
            feature.geometry.coordinates[0].forEach((coord: number[]) => {
              if (coord.length >= 2) {
                bounds.extend([coord[0], coord[1]] as [number, number]);
              }
            });
          } else if (feature.geometry.type === 'MultiPolygon') {
            feature.geometry.coordinates.forEach((polygon: number[][][]) => {
              polygon[0].forEach((coord: number[]) => {
                if (coord.length >= 2) {
                  bounds.extend([coord[0], coord[1]] as [number, number]);
                }
              });
            });
          } else if (feature.geometry.type === 'Point') {
            const coord = feature.geometry.coordinates;
            if (coord.length >= 2) {
              bounds.extend([coord[0], coord[1]] as [number, number]);
            }
          }
        });

        // Only fit bounds if we have valid bounds
        if (!bounds.isEmpty()) {
          map.current!.fitBounds(bounds, { padding: 50 });
        }

        // Add popup on click
        const clickLayer = isPoint ? 'buildings-points' : 'buildings-fill';
        map.current!.on('click', clickLayer, (e) => {
          if (!e.features || e.features.length === 0) return;

          const feature = e.features[0];
          const properties = feature.properties || {};
          
          // Build popup content
          let popupContent = `<div class="p-2">`;
          popupContent += `<h3 class="font-bold">Building ${properties.guid}</h3>`;
          
          if (properties.asset_value) {
            popupContent += `<p><strong>Asset Value:</strong> $${Number(properties.asset_value).toLocaleString()}</p>`;
          }
          
          // Show other properties
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

        setLoading(false);
      } catch (err) {
        console.error('Error loading buildings:', err);
        setError('Failed to load buildings');
        setLoading(false);
      }
    });

    return () => {
      if (map.current) {
        map.current.remove();
        map.current = null;
      }
    };
  }, [datasetId]);

  return (
    <div className={`relative ${className}`}>
      <div ref={mapContainer} className="w-full h-full" />
      {loading && (
        <div className="absolute inset-0 flex items-center justify-center bg-white bg-opacity-75">
          <div className="text-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-2"></div>
            <p className="text-sm text-gray-600">Loading buildings...</p>
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