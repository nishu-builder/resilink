"use client";

import { useState } from 'react';
import { useParams } from 'next/navigation';
import useSWR from 'swr';
import api from '@/app/hooks/useApi';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { ArrowRight, DollarSign, TrendingDown, Clock } from 'lucide-react';

type RunGroup = {
  id: number;
  name: string;
  description: string | null;
  created_at: string;
};

type Run = {
  id: number;
  name: string;
  status: string;
  created_at: string;
  run_group_id: number;
};

type EALResponse = {
  total_eal: number;
  building_count: number;
};

type ComparisonResponse = {
  run_1: {
    id: number;
    eal: number;
    intervention_cost: number;
  };
  run_2: {
    id: number;
    eal: number;
    intervention_cost: number;
  };
  comparison: {
    eal_reduction: number;
    eal_reduction_percent: number;
    incremental_cost: number;
    roi: number;
    payback_years: number;
  };
};

export default function RunGroupDetailPage() {
  const params = useParams();
  const groupId = parseInt(params.id as string);
  
  const [compareRun1, setCompareRun1] = useState<string>('');
  const [compareRun2, setCompareRun2] = useState<string>('');
  const [comparison, setComparison] = useState<ComparisonResponse | null>(null);
  const [isComparing, setIsComparing] = useState(false);
  const [compareError, setCompareError] = useState<string | null>(null);

  const { data: group, isLoading: isLoadingGroup } = useSWR<RunGroup>(
    `runs/groups/${groupId}`,
    (url: string) => api.get(url).then((r) => r.data)
  );

  const { data: runs, isLoading: isLoadingRuns } = useSWR<Run[]>(
    'runs',
    (url: string) => api.get(url).then((r) => r.data)
  );

  const groupRuns = runs?.filter(run => run.run_group_id === groupId) || [];

  const handleCompare = async () => {
    if (!compareRun1 || !compareRun2) return;
    
    setIsComparing(true);
    setCompareError(null);
    setComparison(null);

    try {
      const response = await api.post('financial/compare-runs', {
        run_id_1: parseInt(compareRun1),
        run_id_2: parseInt(compareRun2),
      });
      setComparison(response.data);
    } catch (err: any) {
      setCompareError(err.response?.data?.detail || 'Failed to compare runs');
    } finally {
      setIsComparing(false);
    }
  };

  if (isLoadingGroup || isLoadingRuns) {
    return <div>Loading...</div>;
  }

  if (!group) {
    return <div>Run group not found</div>;
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">{group.name}</h1>
        {group.description && (
          <p className="text-muted-foreground mt-2">{group.description}</p>
        )}
        <p className="text-sm text-muted-foreground mt-1">
          Created: {new Date(group.created_at).toLocaleString()}
        </p>
      </div>

      <div className="space-y-4">
        <div className="flex justify-between items-center">
          <h2 className="text-xl font-semibold">Runs in this Group</h2>
          <Link href={`/runs/new?group=${groupId}`}>
            <Button>Add Run to Group</Button>
          </Link>
        </div>

        {groupRuns.length === 0 ? (
          <p className="text-muted-foreground">No runs in this group yet.</p>
        ) : (
          <div className="space-y-3">
            {groupRuns.map((run) => (
              <RunCard key={run.id} run={run} />
            ))}
          </div>
        )}
      </div>

      {groupRuns.length >= 2 && (
        <div className="border-t pt-6 space-y-4">
          <h2 className="text-xl font-semibold">Compare Runs</h2>
          
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-sm font-medium">Baseline Run</label>
              <Select value={compareRun1} onValueChange={setCompareRun1}>
                <SelectTrigger className="mt-1">
                  <SelectValue placeholder="Select baseline run" />
                </SelectTrigger>
                <SelectContent>
                  {groupRuns.map((run) => (
                    <SelectItem key={run.id} value={String(run.id)}>
                      {run.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div>
              <label className="text-sm font-medium">Intervention Run</label>
              <Select value={compareRun2} onValueChange={setCompareRun2}>
                <SelectTrigger className="mt-1">
                  <SelectValue placeholder="Select intervention run" />
                </SelectTrigger>
                <SelectContent>
                  {groupRuns.map((run) => (
                    <SelectItem key={run.id} value={String(run.id)}>
                      {run.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <Button 
            onClick={handleCompare} 
            disabled={!compareRun1 || !compareRun2 || isComparing}
            className="w-full"
          >
            {isComparing ? 'Comparing...' : 'Compare Runs'}
          </Button>

          {compareError && (
            <p className="text-red-600 text-sm">{compareError}</p>
          )}

          {comparison && (
            <div className="bg-muted/30 rounded-lg p-6 space-y-4">
              <h3 className="font-semibold text-lg">Comparison Results</h3>
              
              <div className="grid grid-cols-2 gap-6">
                <div className="space-y-2">
                  <h4 className="font-medium text-sm text-muted-foreground">Baseline</h4>
                  <div className="space-y-1">
                    <p className="text-2xl font-bold">${comparison.run_1.eal.toLocaleString()}</p>
                    <p className="text-sm text-muted-foreground">Annual Expected Loss</p>
                  </div>
                </div>

                <div className="space-y-2">
                  <h4 className="font-medium text-sm text-muted-foreground">With Interventions</h4>
                  <div className="space-y-1">
                    <p className="text-2xl font-bold">${comparison.run_2.eal.toLocaleString()}</p>
                    <p className="text-sm text-muted-foreground">Annual Expected Loss</p>
                  </div>
                  <div className="space-y-1">
                    <p className="text-lg">${comparison.run_2.intervention_cost.toLocaleString()}</p>
                    <p className="text-sm text-muted-foreground">Intervention Cost</p>
                  </div>
                </div>
              </div>

              <div className="border-t pt-4 grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="flex items-start space-x-2">
                  <TrendingDown className="w-5 h-5 text-green-600 mt-0.5" />
                  <div>
                    <p className="font-semibold">${comparison.comparison.eal_reduction.toLocaleString()}</p>
                    <p className="text-sm text-muted-foreground">Annual Savings</p>
                  </div>
                </div>

                <div className="flex items-start space-x-2">
                  <TrendingDown className="w-5 h-5 text-green-600 mt-0.5" />
                  <div>
                    <p className="font-semibold">{comparison.comparison.eal_reduction_percent.toFixed(1)}%</p>
                    <p className="text-sm text-muted-foreground">Risk Reduction</p>
                  </div>
                </div>

                <div className="flex items-start space-x-2">
                  <DollarSign className="w-5 h-5 text-blue-600 mt-0.5" />
                  <div>
                    <p className="font-semibold">{(comparison.comparison.roi * 100).toFixed(0)}%</p>
                    <p className="text-sm text-muted-foreground">ROI</p>
                  </div>
                </div>

                <div className="flex items-start space-x-2">
                  <Clock className="w-5 h-5 text-purple-600 mt-0.5" />
                  <div>
                    <p className="font-semibold">{comparison.comparison.payback_years.toFixed(1)} years</p>
                    <p className="text-sm text-muted-foreground">Payback Period</p>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function RunCard({ run }: { run: Run }) {
  const { data: eal, isLoading } = useSWR<EALResponse>(
    run.status === 'COMPLETED' ? `financial/runs/${run.id}/eal` : null,
    (url: string) => api.get(url).then((r) => r.data)
  );

  return (
    <div className="border rounded-lg p-4 hover:bg-muted/20 transition-colors">
      <div className="flex justify-between items-start">
        <div>
          <h3 className="font-semibold">
            <Link href={`/runs/${run.id}`} className="text-blue-600 hover:underline">
              {run.name}
            </Link>
          </h3>
          <p className="text-sm text-muted-foreground mt-1">
            Status: <span className={run.status === 'COMPLETED' ? 'text-green-600' : ''}>{run.status}</span>
          </p>
          {run.status === 'COMPLETED' && !isLoading && eal && (
            <p className="text-sm mt-2">
              EAL: <span className="font-semibold">${eal.total_eal.toLocaleString()}</span>
              {' '}({eal.building_count} buildings)
            </p>
          )}
        </div>
        <Link href={`/runs/${run.id}`}>
          <Button variant="ghost" size="sm">
            <ArrowRight className="w-4 h-4" />
          </Button>
        </Link>
      </div>
    </div>
  );
} 