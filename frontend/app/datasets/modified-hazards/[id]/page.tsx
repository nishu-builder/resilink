'use client';

import { useParams } from 'next/navigation';
import { useEffect, useState } from 'react';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { ModifiedHazardViewer } from '@/app/components/ModifiedHazardViewer';
import { ArrowLeft, Info, Shield, BarChart3 } from 'lucide-react';
import { Badge } from '@/components/ui/badge';

export default function ModifiedHazardDetailPage() {
  const params = useParams();
  const modifiedHazardId = parseInt(params.id as string);
  const [modifiedHazard, setModifiedHazard] = useState<any>(null);
  const [modifiedHazardInfo, setModifiedHazardInfo] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        // Fetch modified hazard info
        const infoResponse = await fetch(`/api/modified-hazards/${modifiedHazardId}/info`);
        if (!infoResponse.ok) {
          throw new Error('Failed to fetch modified hazard info');
        }
        const info = await infoResponse.json();
        setModifiedHazard(info);
        setModifiedHazardInfo(info);
      } catch (error) {
        console.error('Error fetching modified hazard data:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [modifiedHazardId]);

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

  if (!modifiedHazard) {
    return (
      <div className="container mx-auto p-6">
        <Card className="p-8 text-center">
          <h2 className="text-xl font-semibold mb-2">Modified Hazard Not Found</h2>
          <p className="text-muted-foreground mb-4">The requested modified hazard could not be found.</p>
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
            <span>Modified Hazards</span>
            <span>/</span>
            <span>{modifiedHazard.name}</span>
          </div>
          <h1 className="text-3xl font-bold">{modifiedHazard.name}</h1>
          <div className="flex items-center gap-2">
            <Badge variant="outline">
              {modifiedHazard.model_type}
            </Badge>
            <p className="text-muted-foreground">
              Generated: {new Date(modifiedHazardInfo.model_results?.created_at || Date.now()).toLocaleDateString()}
            </p>
          </div>
        </div>
        <div className="flex gap-2">
          <Button 
            variant="outline"
            onClick={() => window.history.back()}
          >
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back
          </Button>
        </div>
      </div>

      {/* Intervention Summary */}
      <Card className="p-6">
        <div className="flex items-center gap-2 mb-4">
          <Shield className="h-5 w-5" />
          <h2 className="text-xl font-semibold">Intervention Impact Summary</h2>
        </div>
        
        {modifiedHazard.model_results && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
            <div className="text-center p-4 border rounded-lg">
              <div className="text-2xl font-bold text-blue-600">
                {modifiedHazard.model_results.reduction_stats?.mean_reduction_m?.toFixed(2) || 0}m
              </div>
              <p className="text-sm text-muted-foreground">Average Water Reduction</p>
            </div>
            <div className="text-center p-4 border rounded-lg">
              <div className="text-2xl font-bold text-green-600">
                {modifiedHazard.model_results.reduction_stats?.max_reduction_m?.toFixed(2) || 0}m
              </div>
              <p className="text-sm text-muted-foreground">Maximum Reduction</p>
            </div>
            <div className="text-center p-4 border rounded-lg">
              <div className="text-2xl font-bold text-purple-600">
                {modifiedHazard.model_results.reduction_stats?.affected_area_pixels || 0}
              </div>
              <p className="text-sm text-muted-foreground">Affected Pixels</p>
            </div>
            <div className="text-center p-4 border rounded-lg">
              <div className="text-2xl font-bold text-orange-600">
                {modifiedHazard.model_results.reduction_stats?.total_reduction_m3?.toFixed(0) || 0}
              </div>
              <p className="text-sm text-muted-foreground">Total Volume Reduced (m³)</p>
            </div>
          </div>
        )}
      </Card>

      {/* Metadata */}
      {modifiedHazardInfo && (
        <Card className="p-6">
          <div className="flex items-center gap-2 mb-4">
            <Info className="h-5 w-5" />
            <h2 className="text-xl font-semibold">Modified Hazard Information</h2>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div>
              <p className="text-sm text-muted-foreground">Dimensions</p>
              <p className="font-medium">{modifiedHazardInfo.width} × {modifiedHazardInfo.height} pixels</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">CRS</p>
              <p className="font-medium text-sm">{modifiedHazardInfo.crs}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Min Elevation</p>
              <p className="font-medium">{modifiedHazardInfo.statistics.min.toFixed(2)}m</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Max Elevation</p>
              <p className="font-medium">{modifiedHazardInfo.statistics.max.toFixed(2)}m</p>
            </div>
          </div>
        </Card>
      )}

      {/* Comparison Stats */}
      {modifiedHazard.model_results && (
        <Card className="p-6">
          <div className="flex items-center gap-2 mb-4">
            <BarChart3 className="h-5 w-5" />
            <h2 className="text-xl font-semibold">Before vs After Comparison</h2>
          </div>
          <div className="grid grid-cols-2 gap-6">
            <div>
              <h3 className="font-medium mb-3">Original Hazard</h3>
              <div className="space-y-2">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Min:</span>
                  <span>{modifiedHazard.model_results.original_stats.min.toFixed(2)}m</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Max:</span>
                  <span>{modifiedHazard.model_results.original_stats.max.toFixed(2)}m</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Mean:</span>
                  <span>{modifiedHazard.model_results.original_stats.mean.toFixed(2)}m</span>
                </div>
              </div>
            </div>
            <div>
              <h3 className="font-medium mb-3">Modified Hazard</h3>
              <div className="space-y-2">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Min:</span>
                  <span>{modifiedHazard.model_results.modified_stats.min.toFixed(2)}m</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Max:</span>
                  <span>{modifiedHazard.model_results.modified_stats.max.toFixed(2)}m</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Mean:</span>
                  <span>{modifiedHazard.model_results.modified_stats.mean.toFixed(2)}m</span>
                </div>
              </div>
            </div>
          </div>
        </Card>
      )}

      {/* Modified Hazard Visualization */}
      <div>
        <h2 className="text-xl font-semibold mb-4">Modified Hazard Visualization</h2>
        <ModifiedHazardViewer 
          modifiedHazardId={modifiedHazardId} 
          modifiedHazardInfo={modifiedHazardInfo} 
        />
      </div>
    </div>
  );
}