'use client';

import { useEffect, useRef, useState } from 'react';
import mapboxgl from 'mapbox-gl';
import 'mapbox-gl/dist/mapbox-gl.css';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';

// Set Mapbox access token (you'll need to set this in env)
mapboxgl.accessToken = process.env.NEXT_PUBLIC_MAPBOX_TOKEN || '';

interface ModifiedHazardViewerProps {
  modifiedHazardId: number;
  modifiedHazardInfo?: any;
}

const COLORMAPS = [
  { value: 'Blues', label: 'Blues (Water Depth)' },
  { value: 'YlOrRd', label: 'Yellow-Orange-Red (Heat)' },
  { value: 'viridis', label: 'Viridis' },
  { value: 'plasma', label: 'Plasma' },
  { value: 'RdBu', label: 'Red-Blue (Diverging)' },
];

export function ModifiedHazardViewer({ 
  modifiedHazardId, 
  modifiedHazardInfo
}: ModifiedHazardViewerProps) {
  const mapContainer = useRef<HTMLDivElement>(null);
  const map = useRef<mapboxgl.Map | null>(null);
  const [colormap, setColormap] = useState('Blues');
  const [opacity, setOpacity] = useState(0.8);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [stats, setStats] = useState<any>(null);

  useEffect(() => {
    if (!mapContainer.current || map.current) return;

    const initializeMap = async () => {
      try {
        // Fetch modified hazard info first
        let info = modifiedHazardInfo;
        if (!info) {
          try {
            const response = await fetch(`/api/modified-hazards/${modifiedHazardId}/info`);
            if (!response.ok) {
              throw new Error(`HTTP error! status: ${response.status}`);
            }
            info = await response.json();
            setStats(info.statistics);
          } catch (error) {
            console.error('Error fetching modified hazard info:', error);
            setError('Failed to load modified hazard information');
            setLoading(false);
            return;
          }
        }

        // Create a simple style for the map
        const mapStyle = {
          version: 8,
          sources: {
            'osm': {
              type: 'raster',
              tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],
              tileSize: 256,
              attribution: '© OpenStreetMap contributors'
            }
          },
          layers: [
            {
              id: 'osm',
              type: 'raster',
              source: 'osm',
              minzoom: 0,
              maxzoom: 22
            }
          ]
        };

        // Initialize map
        map.current = new mapboxgl.Map({
          container: mapContainer.current!,
          style: mapStyle as any,
          center: [(info.bounds.minx + info.bounds.maxx) / 2, (info.bounds.miny + info.bounds.maxy) / 2],
          zoom: 10,
        });

        map.current.on('load', () => {
          if (!map.current) return;

          // Add modified hazard raster tile source
          map.current.addSource('modified-hazard-tiles', {
            type: 'raster',
            tiles: [`/api/modified-hazards/${modifiedHazardId}/tiles/{z}/{x}/{y}?colormap=${colormap}`],
            tileSize: 256,
            bounds: [info.bounds.minx, info.bounds.miny, info.bounds.maxx, info.bounds.maxy],
          });

          // Add raster layer
          map.current.addLayer({
            id: 'modified-hazard-layer',
            type: 'raster',
            source: 'modified-hazard-tiles',
            paint: {
              'raster-opacity': opacity,
            },
          });

          // Fit to bounds
          map.current.fitBounds(
            [
              [info.bounds.minx, info.bounds.miny],
              [info.bounds.maxx, info.bounds.maxy],
            ],
            { padding: 50 }
          );

          setLoading(false);
        });

        map.current.on('error', (e) => {
          console.error('Map error:', e);
          setError('Map failed to load');
          setLoading(false);
        });

      } catch (error) {
        console.error('Error initializing map:', error);
        setError('Failed to initialize map');
        setLoading(false);
      }
    };

    initializeMap();

    return () => {
      map.current?.remove();
      map.current = null;
    };
  }, [modifiedHazardId]);

  // Update colormap
  useEffect(() => {
    if (!map.current || !map.current.getSource('modified-hazard-tiles')) return;

    const source = map.current.getSource('modified-hazard-tiles') as mapboxgl.RasterTileSource;
    source.setTiles([`/api/modified-hazards/${modifiedHazardId}/tiles/{z}/{x}/{y}?colormap=${colormap}`]);
  }, [colormap, modifiedHazardId]);

  // Update opacity
  useEffect(() => {
    if (!map.current || !map.current.getLayer('modified-hazard-layer')) return;
    map.current.setPaintProperty('modified-hazard-layer', 'raster-opacity', opacity);
  }, [opacity]);

  return (
    <div className="space-y-4">
      {/* Controls */}
      <Card className="p-4">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <label className="text-sm font-medium">Colormap:</label>
            <Select value={colormap} onValueChange={setColormap}>
              <SelectTrigger className="w-48">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {COLORMAPS.map((cm) => (
                  <SelectItem key={cm.value} value={cm.value}>
                    {cm.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="flex items-center gap-2">
            <label className="text-sm font-medium">Opacity:</label>
            <input
              type="range"
              min="0"
              max="1"
              step="0.1"
              value={opacity}
              onChange={(e) => setOpacity(parseFloat(e.target.value))}
              className="w-32"
            />
            <span className="text-sm">{Math.round(opacity * 100)}%</span>
          </div>

          {stats && (
            <div className="ml-auto text-sm text-muted-foreground">
              <span>Min: {stats.min.toFixed(2)}m</span>
              <span className="mx-2">|</span>
              <span>Max: {stats.max.toFixed(2)}m</span>
              <span className="mx-2">|</span>
              <span>Mean: {stats.mean.toFixed(2)}m</span>
            </div>
          )}

          <Badge variant="secondary">
            Modified Hazard
          </Badge>
        </div>
      </Card>

      {/* Map Container */}
      <Card className="relative overflow-hidden">
        <div ref={mapContainer} className="h-[600px] w-full" />
        {loading && !error && (
          <div className="absolute inset-0 flex items-center justify-center bg-background/80">
            <div className="text-center">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto mb-2" />
              <p className="text-sm text-muted-foreground">Loading modified hazard data...</p>
            </div>
          </div>
        )}
        {error && (
          <div className="absolute inset-0 flex items-center justify-center bg-background/80">
            <div className="text-center">
              <p className="text-red-500 mb-2">{error}</p>
              <Button 
                onClick={() => {
                  setError(null);
                  setLoading(true);
                  window.location.reload();
                }}
                variant="outline"
              >
                Retry
              </Button>
            </div>
          </div>
        )}
      </Card>

      {/* Legend */}
      <Card className="p-4">
        <h3 className="font-medium mb-2">Modified Water Surface Elevation Legend</h3>
        <div className="space-y-3">
          {/* Water Elevation Legend */}
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <div className="w-6 h-6 bg-gradient-to-r from-blue-100 to-blue-900 border" />
              <span className="text-sm font-medium">Modified Water Surface Elevation</span>
            </div>
            <span className="text-sm text-muted-foreground">
              {stats ? `${stats.min.toFixed(1)}m - ${stats.max.toFixed(1)}m` : 'Loading...'}
            </span>
          </div>
          
          <p className="text-sm text-muted-foreground">
            This shows water surface elevations after applying the intervention. 
            Areas with reduced flooding indicate the protective effect of the intervention.
          </p>
        </div>
      </Card>
    </div>
  );
}

export type { ModifiedHazardViewerProps };