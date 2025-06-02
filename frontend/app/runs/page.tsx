"use client";

import useSWR from 'swr';
import api from '@/app/hooks/useApi';
import Link from 'next/link';

type Run = {
  id: number;
  name: string;
  status: string;
  created_at: string;
  run_group_id?: number;
};

type RunGroup = {
  id: number;
  name: string;
};

export default function RunsPage() {
  const { data: runs, isLoading: isLoadingRuns } = useSWR<Run[]>('runs', (url: string) => api.get(url).then((r) => r.data));
  const { data: groups, isLoading: isLoadingGroups } = useSWR<RunGroup[]>('runs/groups', (url: string) => api.get(url).then((r) => r.data));

  const isLoading = isLoadingRuns || isLoadingGroups;

  // Create a map for quick group lookup
  const groupMap = new Map(groups?.map(g => [g.id, g.name]) || []);

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-semibold">Runs</h1>
        <div className="space-x-3">
          <Link href="/run-groups" className="px-4 py-2 bg-gray-600 text-white rounded hover:bg-gray-700">
            View Groups
          </Link>
          <Link href="/runs/new" className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700">
            New Run
          </Link>
        </div>
      </div>

      {isLoading ? (
        <p>Loading…</p>
      ) : (
        <table className="w-full text-left">
          <thead>
            <tr>
              <th className="py-2">ID</th>
              <th>Name</th>
              <th>Run Group</th>
              <th>Status</th>
              <th>Created</th>
            </tr>
          </thead>
          <tbody>
            {runs?.map((run) => (
              <tr key={run.id} className="border-t hover:bg-muted/50">
                <td className="py-2">{run.id}</td>
                <td>
                  <Link href={`/runs/${run.id}`} className="text-blue-600 hover:underline">
                    {run.name}
                  </Link>
                </td>
                <td>
                  {run.run_group_id ? (
                    <Link href={`/run-groups/${run.run_group_id}`} className="text-blue-600 hover:underline">
                      {groupMap.get(run.run_group_id) || `Group ${run.run_group_id}`}
                    </Link>
                  ) : (
                    <span className="text-muted-foreground">—</span>
                  )}
                </td>
                <td>
                  <span className={run.status === 'COMPLETED' ? 'text-green-600' : ''}>
                    {run.status}
                  </span>
                </td>
                <td>{new Date(run.created_at).toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
} 