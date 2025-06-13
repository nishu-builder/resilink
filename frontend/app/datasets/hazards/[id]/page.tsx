'use client';

import { useParams } from 'next/navigation';
import { useEffect, useState } from 'react';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { HazardViewer } from '@/app/components/HazardViewer';
import { ArrowLeft, Download, Info } from 'lucide-react';

export default function HazardDetailPage() {
  const params = useParams();
  const hazardId = parseInt(params.id as string);
  const [hazard, setHazard] = useState<any>(null);
  const [hazardInfo, setHazardInfo] = useState<any>(null);
  const [loading, setLoading] = useState(true);

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
      } catch (error) {
        console.error('Error fetching hazard data:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [hazardId]);

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
          <Button
            onClick={() => {
              // Download preview image
              window.open(`/api/datasets/hazards/${hazardId}/preview?width=1920&height=1080`, '_blank');
            }}
          >
            <Download className="mr-2 h-4 w-4" />
            Download Preview
          </Button>
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

      {/* Hazard Viewer */}
      <div>
        <h2 className="text-xl font-semibold mb-4">Hazard Visualization</h2>
        <HazardViewer hazardId={hazardId} hazardInfo={hazardInfo} />
      </div>
    </div>
  );
}