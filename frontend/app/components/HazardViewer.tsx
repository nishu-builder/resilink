'use client';

import { useEffect, useRef, useState } from 'react';
import mapboxgl from 'mapbox-gl';
import 'mapbox-gl/dist/mapbox-gl.css';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';

// Set Mapbox access token (you'll need to set this in env)
mapboxgl.accessToken = process.env.NEXT_PUBLIC_MAPBOX_TOKEN || 'pk.test';

interface HazardViewerProps {
  hazardId: number;
  hazardInfo?: any;
}

const COLORMAPS = [
  { value: 'Blues', label: 'Blues (Water Depth)' },
  { value: 'YlOrRd', label: 'Yellow-Orange-Red (Heat)' },
  { value: 'viridis', label: 'Viridis' },
  { value: 'plasma', label: 'Plasma' },
  { value: 'RdBu', label: 'Red-Blue (Diverging)' },
];

export function HazardViewer({ hazardId, hazardInfo }: HazardViewerProps) {
  const mapContainer = useRef<HTMLDivElement>(null);
  const map = useRef<mapboxgl.Map | null>(null);
  const [colormap, setColormap] = useState('Blues');
  const [opacity, setOpacity] = useState(0.8);
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState<any>(null);

  useEffect(() => {
    if (!mapContainer.current || map.current) return;

    // Initialize map
    map.current = new mapboxgl.Map({
      container: mapContainer.current,
      style: 'mapbox://styles/mapbox/light-v11',
      center: [-95, 40], // Default center (US)
      zoom: 4,
    });

    map.current.on('load', async () => {
      if (!map.current) return;

      // Fetch hazard info if not provided
      let info = hazardInfo;
      if (!info) {
        try {
          const response = await fetch(`/api/datasets/hazards/${hazardId}/info`);
          info = await response.json();
          setStats(info.statistics);
        } catch (error) {
          console.error('Error fetching hazard info:', error);
          setLoading(false);
          return;
        }
      }

      // Add raster tile source
      map.current.addSource('hazard-tiles', {
        type: 'raster',
        tiles: [`/api/datasets/hazards/${hazardId}/tiles/{z}/{x}/{y}?colormap=${colormap}`],
        tileSize: 256,
        bounds: [info.bounds.minx, info.bounds.miny, info.bounds.maxx, info.bounds.maxy],
      });

      // Add raster layer
      map.current.addLayer({
        id: 'hazard-layer',
        type: 'raster',
        source: 'hazard-tiles',
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

    return () => {
      map.current?.remove();
      map.current = null;
    };
  }, [hazardId]);

  // Update colormap
  useEffect(() => {
    if (!map.current || !map.current.getSource('hazard-tiles')) return;

    const source = map.current.getSource('hazard-tiles') as mapboxgl.RasterTileSource;
    source.setTiles([`/api/datasets/hazards/${hazardId}/tiles/{z}/{x}/{y}?colormap=${colormap}`]);
  }, [colormap, hazardId]);

  // Update opacity
  useEffect(() => {
    if (!map.current || !map.current.getLayer('hazard-layer')) return;
    map.current.setPaintProperty('hazard-layer', 'raster-opacity', opacity);
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
        </div>
      </Card>

      {/* Map Container */}
      <Card className="relative overflow-hidden">
        <div ref={mapContainer} className="h-[600px] w-full" />
        {loading && (
          <div className="absolute inset-0 flex items-center justify-center bg-background/80">
            <div className="text-center">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto mb-2" />
              <p className="text-sm text-muted-foreground">Loading hazard data...</p>
            </div>
          </div>
        )}
      </Card>

      {/* Legend */}
      <Card className="p-4">
        <h3 className="font-medium mb-2">Water Surface Elevation Legend</h3>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 bg-gradient-to-r from-blue-100 to-blue-900" />
            <span className="text-sm">
              {stats ? `${stats.min.toFixed(1)}m - ${stats.max.toFixed(1)}m` : 'Loading...'}
            </span>
          </div>
          <p className="text-sm text-muted-foreground ml-auto">
            Darker colors indicate deeper water levels
          </p>
        </div>
      </Card>
    </div>
  );
}