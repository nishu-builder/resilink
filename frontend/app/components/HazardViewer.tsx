'use client';

import { useEffect, useRef, useState } from 'react';
import mapboxgl from 'mapbox-gl';
import MapboxDraw from '@mapbox/mapbox-gl-draw';
import 'mapbox-gl/dist/mapbox-gl.css';
import '@mapbox/mapbox-gl-draw/dist/mapbox-gl-draw.css';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Pencil, Square, Trash2, Eye, EyeOff } from 'lucide-react';

// Set Mapbox access token (you'll need to set this in env)
mapboxgl.accessToken = process.env.NEXT_PUBLIC_MAPBOX_TOKEN || '';

interface HazardViewerProps {
  hazardId: number;
  hazardInfo?: any;
  interventions?: any[];
  drawingMode?: boolean;
  onGeometryDrawn?: (geometry: any) => void;
  onDrawingModeChange?: (enabled: boolean) => void;
}

const COLORMAPS = [
  { value: 'Blues', label: 'Blues (Water Depth)' },
  { value: 'YlOrRd', label: 'Yellow-Orange-Red (Heat)' },
  { value: 'viridis', label: 'Viridis' },
  { value: 'plasma', label: 'Plasma' },
  { value: 'RdBu', label: 'Red-Blue (Diverging)' },
];

export function HazardViewer({ 
  hazardId, 
  hazardInfo, 
  interventions = [], 
  drawingMode = false, 
  onGeometryDrawn, 
  onDrawingModeChange 
}: HazardViewerProps) {
  const mapContainer = useRef<HTMLDivElement>(null);
  const map = useRef<mapboxgl.Map | null>(null);
  const draw = useRef<MapboxDraw | null>(null);
  const [colormap, setColormap] = useState('Blues');
  const [opacity, setOpacity] = useState(0.8);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [stats, setStats] = useState<any>(null);
  const [showInterventions, setShowInterventions] = useState(true);
  const [activeDrawMode, setActiveDrawMode] = useState<string | null>(null);

  useEffect(() => {
    if (!mapContainer.current || map.current) return;

    const initializeMap = async () => {
      try {
        // Fetch hazard info first
        let info = hazardInfo;
        if (!info) {
          try {
            const response = await fetch(`/api/datasets/hazards/${hazardId}/info`);
            if (!response.ok) {
              throw new Error(`HTTP error! status: ${response.status}`);
            }
            info = await response.json();
            setStats(info.statistics);
          } catch (error) {
            console.error('Error fetching hazard info:', error);
            setError('Failed to load hazard information');
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

          // Initialize Mapbox Draw
          draw.current = new MapboxDraw({
            displayControlsDefault: false,
            controls: {},
            styles: [
              // Custom styles for intervention lines
              {
                id: 'gl-draw-line',
                type: 'line',
                filter: ['all', ['==', '$type', 'LineString'], ['!=', 'mode', 'static']],
                layout: {
                  'line-cap': 'round',
                  'line-join': 'round'
                },
                paint: {
                  'line-color': '#3b82f6',
                  'line-width': 4,
                  'line-opacity': 0.8
                }
              },
              {
                id: 'gl-draw-polygon-fill',
                type: 'fill',
                filter: ['all', ['==', '$type', 'Polygon'], ['!=', 'mode', 'static']],
                paint: {
                  'fill-color': '#3b82f6',
                  'fill-opacity': 0.3
                }
              },
              {
                id: 'gl-draw-polygon-stroke',
                type: 'line',
                filter: ['all', ['==', '$type', 'Polygon'], ['!=', 'mode', 'static']],
                layout: {
                  'line-cap': 'round',
                  'line-join': 'round'
                },
                paint: {
                  'line-color': '#3b82f6',
                  'line-width': 3,
                  'line-opacity': 0.8
                }
              },
              // Vertex points
              {
                id: 'gl-draw-point',
                type: 'circle',
                filter: ['all', ['==', '$type', 'Point'], ['!=', 'meta', 'midpoint']],
                paint: {
                  'circle-radius': 6,
                  'circle-color': '#3b82f6',
                  'circle-stroke-width': 2,
                  'circle-stroke-color': '#ffffff'
                }
              }
            ]
          });

          map.current.addControl(draw.current);

          // Handle draw events
          map.current.on('draw.create', (e: any) => {
            if (onGeometryDrawn && e.features.length > 0) {
              const geometry = e.features[0].geometry;
              onGeometryDrawn(geometry);
              // Clear the drawing
              draw.current?.deleteAll();
              setActiveDrawMode(null);
            }
          });

          map.current.on('draw.modechange', (e: any) => {
            if (e.mode === 'simple_select') {
              setActiveDrawMode(null);
            }
          });

          // Add interventions source and layer
          addInterventionsToMap();

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
      if (draw.current) {
        map.current?.removeControl(draw.current);
        draw.current = null;
      }
      map.current?.remove();
      map.current = null;
    };
  }, [hazardId]);

  // Function to add interventions to map
  const addInterventionsToMap = () => {
    if (!map.current || !interventions.length) return;

    // Remove existing interventions layer if it exists
    if (map.current.getLayer('interventions-layer')) {
      map.current.removeLayer('interventions-layer');
    }
    if (map.current.getSource('interventions')) {
      map.current.removeSource('interventions');
    }

    // Create GeoJSON from interventions
    const geojson = {
      type: 'FeatureCollection' as const,
      features: interventions.map(intervention => ({
        type: 'Feature' as const,
        id: intervention.id,
        properties: {
          id: intervention.id,
          name: intervention.name,
          type: intervention.type,
          parameters: intervention.parameters
        },
        geometry: intervention.geometry
      }))
    };

    // Add source
    map.current.addSource('interventions', {
      type: 'geojson',
      data: geojson
    });

    // Add layer for lines (levees and linear dams)
    map.current.addLayer({
      id: 'interventions-layer',
      type: 'line',
      source: 'interventions',
      layout: {
        'line-join': 'round',
        'line-cap': 'round'
      },
      paint: {
        'line-color': [
          'case',
          ['==', ['get', 'type'], 'dam'],
          '#dc2626', // Red for dams
          '#16a34a'  // Green for levees
        ],
        'line-width': 5,
        'line-opacity': showInterventions ? 0.8 : 0
      }
    });

    // Add click handler for interventions
    map.current.on('click', 'interventions-layer', (e) => {
      if (e.features && e.features.length > 0) {
        const feature = e.features[0];
        const props = feature.properties;
        
        new mapboxgl.Popup()
          .setLngLat(e.lngLat)
          .setHTML(`
            <div class="p-2">
              <h3 class="font-semibold">${props?.name}</h3>
              <p class="text-sm text-gray-600">${props?.type === 'dam' ? 'Dam' : 'Levee'}</p>
              <div class="text-sm mt-1">
                ${props?.type === 'dam' ? 
                  `Height: ${props?.parameters?.height}m, Width: ${props?.parameters?.width}m` :
                  `Height: ${props?.parameters?.height}m, Top Width: ${props?.parameters?.top_width}m`
                }
              </div>
            </div>
          `)
          .addTo(map.current!);
      }
    });

    // Change cursor on hover
    map.current.on('mouseenter', 'interventions-layer', () => {
      if (map.current) map.current.getCanvas().style.cursor = 'pointer';
    });
    
    map.current.on('mouseleave', 'interventions-layer', () => {
      if (map.current) map.current.getCanvas().style.cursor = '';
    });
  };

  // Update interventions when prop changes
  useEffect(() => {
    if (map.current && map.current.isStyleLoaded()) {
      addInterventionsToMap();
    }
  }, [interventions, showInterventions]);

  // Drawing mode functions
  const startDrawing = (mode: 'line_string' | 'polygon') => {
    if (!draw.current) return;
    
    draw.current.changeMode(`draw_${mode}`);
    setActiveDrawMode(mode);
    onDrawingModeChange?.(true);
  };

  const stopDrawing = () => {
    if (!draw.current) return;
    
    draw.current.changeMode('simple_select');
    draw.current.deleteAll();
    setActiveDrawMode(null);
    onDrawingModeChange?.(false);
  };

  // Handle drawing mode prop changes
  useEffect(() => {
    if (!drawingMode && activeDrawMode) {
      stopDrawing();
    }
  }, [drawingMode, activeDrawMode]);

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
        <div className="space-y-4">
          {/* Visualization Controls */}
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

          {/* Drawing and Intervention Controls */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium">Drawing Tools:</span>
              {drawingMode && !activeDrawMode && (
                <span className="text-xs bg-blue-100 text-blue-700 px-2 py-1 rounded">
                  Drawing Mode Active
                </span>
              )}
              <Button
                variant={activeDrawMode === 'line_string' ? 'default' : drawingMode ? 'default' : 'outline'}
                size="sm"
                onClick={() => activeDrawMode === 'line_string' ? stopDrawing() : startDrawing('line_string')}
                disabled={loading}
              >
                <Pencil className="h-4 w-4 mr-1" />
                {activeDrawMode === 'line_string' ? 'Stop Drawing' : 'Draw Line'}
              </Button>
              <Button
                variant={activeDrawMode === 'polygon' ? 'default' : 'outline'}
                size="sm"
                onClick={() => activeDrawMode === 'polygon' ? stopDrawing() : startDrawing('polygon')}
                disabled={loading}
              >
                <Square className="h-4 w-4 mr-1" />
                {activeDrawMode === 'polygon' ? 'Stop Drawing' : 'Draw Area'}
              </Button>
              {activeDrawMode && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={stopDrawing}
                >
                  <Trash2 className="h-4 w-4 mr-1" />
                  Clear
                </Button>
              )}
            </div>

            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowInterventions(!showInterventions)}
                disabled={!interventions.length}
              >
                {showInterventions ? <EyeOff className="h-4 w-4 mr-1" /> : <Eye className="h-4 w-4 mr-1" />}
                {showInterventions ? 'Hide' : 'Show'} Interventions
              </Button>
              {interventions.length > 0 && (
                <Badge variant="secondary">
                  {interventions.length} intervention{interventions.length !== 1 ? 's' : ''}
                </Badge>
              )}
            </div>
          </div>

          {(activeDrawMode || drawingMode) && (
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
              <p className="text-sm text-blue-700">
                {activeDrawMode === 'line_string' 
                  ? 'Click on the map to draw a line for your levee or dam. Click to add points, double-click to finish.'
                  : activeDrawMode === 'polygon'
                  ? 'Click on the map to draw an area. Click to add points, double-click to finish.'
                  : 'Drawing mode enabled. Use the "Draw Line" or "Draw Area" buttons above to start drawing your intervention.'
                }
              </p>
            </div>
          )}
        </div>
      </Card>

      {/* Map Container */}
      <Card className="relative overflow-hidden">
        <div ref={mapContainer} className="h-[600px] w-full" />
        {loading && !error && (
          <div className="absolute inset-0 flex items-center justify-center bg-background/80">
            <div className="text-center">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto mb-2" />
              <p className="text-sm text-muted-foreground">Loading hazard data...</p>
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
        <h3 className="font-medium mb-2">Legend</h3>
        <div className="space-y-3">
          {/* Water Elevation Legend */}
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <div className="w-6 h-6 bg-gradient-to-r from-blue-100 to-blue-900 border" />
              <span className="text-sm font-medium">Water Surface Elevation</span>
            </div>
            <span className="text-sm text-muted-foreground">
              {stats ? `${stats.min.toFixed(1)}m - ${stats.max.toFixed(1)}m` : 'Loading...'}
            </span>
          </div>
          
          {/* Interventions Legend */}
          {interventions.length > 0 && (
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <div className="w-6 h-1 bg-green-500" />
                <span className="text-sm">Levees</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-6 h-1 bg-red-600" />
                <span className="text-sm">Dams</span>
              </div>
            </div>
          )}
        </div>
      </Card>
    </div>
  );
}

// Export the draw functions for external use
export type { HazardViewerProps };