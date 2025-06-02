"use client";

import useSWR from 'swr';
import api from '@/app/hooks/useApi';
import Link from 'next/link';

type Run = {
  id: number;
  name: string;
  status: string;
  created_at: string;
};

export default function RunsPage() {
  const { data, isLoading } = useSWR<Run[]>('runs/', (url: string) => api.get(url).then((r) => r.data));

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-semibold">Runs</h1>
        <Link href="/runs/new" className="px-4 py-2 bg-blue-600 text-white rounded">
          New Run
        </Link>
      </div>

      {isLoading ? (
        <p>Loading…</p>
      ) : (
        <table className="w-full text-left">
          <thead>
            <tr>
              <th className="py-2">ID</th>
              <th>Name</th>
              <th>Status</th>
              <th>Created</th>
            </tr>
          </thead>
          <tbody>
            {data?.map((run) => (
              <tr key={run.id} className="border-t hover:bg-muted/50">
                <td className="py-2">{run.id}</td>
                <td>
                  <Link href={`/runs/${run.id}`} className="text-blue-600 hover:underline">
                    {run.name}
                  </Link>
                </td>
                <td>{run.status}</td>
                <td>{new Date(run.created_at).toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
} 