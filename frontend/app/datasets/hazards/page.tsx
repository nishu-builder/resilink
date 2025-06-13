'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Eye, Upload, Calendar, MapPin } from 'lucide-react';

interface Hazard {
  id: number;
  name: string;
  created_at: string;
  wse_raster_path: string;
}

export default function HazardsPage() {
  const [hazards, setHazards] = useState<Hazard[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchHazards = async () => {
      try {
        const response = await fetch('/api/datasets/hazards');
        const data = await response.json();
        setHazards(data);
      } catch (error) {
        console.error('Error fetching hazards:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchHazards();
  }, []);

  return (
    <div className="container mx-auto p-6">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-3xl font-bold">Flood Hazards</h1>
          <p className="text-muted-foreground mt-1">
            Manage water surface elevation rasters for flood analysis
          </p>
        </div>
        <Link href="/datasets/hazards/upload">
          <Button>
            <Upload className="mr-2 h-4 w-4" />
            Upload Hazard
          </Button>
        </Link>
      </div>

      {loading ? (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {[1, 2, 3].map((i) => (
            <Card key={i} className="p-6 animate-pulse">
              <div className="h-6 bg-gray-200 rounded mb-2" />
              <div className="h-4 bg-gray-200 rounded w-2/3" />
            </Card>
          ))}
        </div>
      ) : hazards.length === 0 ? (
        <Card className="p-12 text-center">
          <MapPin className="mx-auto h-12 w-12 text-muted-foreground mb-4" />
          <h2 className="text-xl font-semibold mb-2">No Hazards Found</h2>
          <p className="text-muted-foreground mb-4">
            Upload your first flood hazard raster to get started.
          </p>
          <Link href="/datasets/hazards/upload">
            <Button>
              <Upload className="mr-2 h-4 w-4" />
              Upload Hazard
            </Button>
          </Link>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {hazards.map((hazard) => (
            <Card key={hazard.id} className="p-6 hover:shadow-lg transition-shadow">
              <div className="space-y-3">
                <div>
                  <h3 className="font-semibold text-lg">{hazard.name}</h3>
                  <div className="flex items-center gap-2 text-sm text-muted-foreground mt-1">
                    <Calendar className="h-3 w-3" />
                    <span>{new Date(hazard.created_at).toLocaleDateString()}</span>
                  </div>
                </div>
                
                <div className="flex items-center justify-between pt-3 border-t">
                  <span className="text-sm text-muted-foreground">
                    ID: {hazard.id}
                  </span>
                  <Link href={`/datasets/hazards/${hazard.id}`}>
                    <Button size="sm">
                      <Eye className="mr-2 h-4 w-4" />
                      View
                    </Button>
                  </Link>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}